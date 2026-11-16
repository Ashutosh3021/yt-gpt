"""Background ingest queue: captions -> clean -> chunk -> index."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .. import config
from ..events import EventBus
from ..util import estimate_tokens, read_json
from ..workspace.store import NotFound, WorkspaceStore
from . import whisper
from .captions import CaptionError, download_captions
from .chunk import chunk_segments
from .clean import clean_segments, render_clean_text
from .metadata import CaptionTrack, MetadataError, choose_caption_track, fetch_info, friendly_error
from .urls import canonical_url

log = logging.getLogger(__name__)

ACTIVE_STATUSES = {"queued", "fetching", "transcribing", "cleaning", "indexing", "pending"}


class IngestError(Exception):
    """A user-facing ingest failure."""


def _duration(info: dict[str, Any]) -> int:
    value = info.get("duration")
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    return 0


def _language(info: dict[str, Any], track: CaptionTrack | None) -> str:
    if track and track.language:
        return track.language
    value = info.get("language")
    return value if isinstance(value, str) else ""


class IngestRunner:
    def __init__(self, bus: EventBus, workers: int = 2) -> None:
        self.bus = bus
        self.workers = max(1, workers)
        self.queue: asyncio.Queue[tuple[str, Path, str]] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._active: set[tuple[str, str, str]] = set()
        self._whisper_lock = asyncio.Semaphore(1)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        for index in range(self.workers):
            self._tasks.append(asyncio.create_task(self._worker(index), name=f"yt-gpt-worker-{index}"))
        await self.resume_all()

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._started = False

    async def submit(self, user_id: str, ws_dir: Path, video_id: str) -> bool:
        key = (user_id, str(ws_dir), video_id)
        if key in self._active:
            return False
        self._active.add(key)
        await self.queue.put((user_id, ws_dir, video_id))
        return True

    async def resume_all(self) -> int:
        count = 0
        users_root = config.users_root()
        if not users_root.is_dir():
            return 0
        for profile_dir in users_root.iterdir():
            if not profile_dir.is_dir():
                continue
            workspaces = profile_dir / "workspaces"
            if not workspaces.is_dir():
                continue
            for ws_dir in workspaces.iterdir():
                videos = ws_dir / "videos"
                if not ws_dir.is_dir() or not videos.is_dir():
                    continue
                for video_dir in videos.iterdir():
                    if not video_dir.is_dir():
                        continue
                    meta = read_json(video_dir / "meta.json")
                    if not isinstance(meta, dict):
                        continue
                    if str(meta.get("status")) in ACTIVE_STATUSES:
                        if await self.submit(profile_dir.name, ws_dir, video_dir.name):
                            count += 1
        if count:
            log.info("Resumed %s pending ingest job(s).", count)
        return count

    async def _worker(self, index: int) -> None:
        while True:
            user_id, ws_dir, video_id = await self.queue.get()
            try:
                await self._process(user_id, ws_dir, video_id)
            except asyncio.CancelledError:
                raise
            except Exception:  # never let a worker die
                log.exception("Unhandled ingest failure for %s/%s", ws_dir, video_id)
                self._safe_fail(user_id, ws_dir, video_id, "Ingest crashed. Check the server logs.")
            finally:
                self._active.discard((user_id, str(ws_dir), video_id))
                self.queue.task_done()

    def _workspace_id(self, store: WorkspaceStore, ws_dir: Path) -> str:
        try:
            data = store._read_workspace_json(ws_dir)
        except Exception:
            return ws_dir.name
        value = data.get("id")
        return value if isinstance(value, str) and value else ws_dir.name

    def _publish(self, store: WorkspaceStore, ws_dir: Path) -> None:
        self.bus.publish(self._workspace_id(store, ws_dir), "update")

    def _status(
        self,
        store: WorkspaceStore,
        ws_dir: Path,
        video_id: str,
        status: str,
        *,
        error: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        meta = store.set_video_status(ws_dir, video_id, status, error=error, **fields)
        self._publish(store, ws_dir)
        return meta

    def _safe_fail(self, user_id: str, ws_dir: Path, video_id: str, message: str) -> None:
        try:
            store = WorkspaceStore(user_id)
            self._status(store, ws_dir, video_id, "failed", error=message)
        except Exception:
            log.exception("Could not mark %s/%s as failed", ws_dir, video_id)

    async def _process(self, user_id: str, ws_dir: Path, video_id: str) -> None:
        store = WorkspaceStore(user_id)
        try:
            meta = store._video_meta(ws_dir, video_id)
        except NotFound:
            return
        if meta.get("status") == "ready":
            return

        try:
            self._status(store, ws_dir, video_id, "fetching", error=None)
            info = await asyncio.to_thread(fetch_info, video_id)
            common: dict[str, Any] = {
                "title": str(info.get("title") or meta.get("title") or f"YouTube video {video_id}"),
                "channel": str(info.get("channel") or info.get("uploader") or ""),
                "duration_s": _duration(info),
                "url": canonical_url(video_id),
            }

            track = choose_caption_track(info)
            if track is not None:
                self._status(
                    store,
                    ws_dir,
                    video_id,
                    "cleaning",
                    transcript_source=track.source,
                    language=_language(info, track),
                    **common,
                )
                raw_segments = await asyncio.to_thread(download_captions, track)
                source = track.source
            else:
                self._status(
                    store,
                    ws_dir,
                    video_id,
                    "transcribing",
                    language=_language(info, None),
                    **common,
                )
                if not whisper.is_available():
                    raise IngestError(
                        "No captions are available for this video. Install the optional Whisper "
                        "fallback with: pip install 'yt-gpt[whisper]'"
                    )
                async with self._whisper_lock:
                    raw_segments = await asyncio.to_thread(whisper.transcribe, video_id)
                source = "whisper"

            if not raw_segments:
                raise IngestError("No transcript could be found for this video.")

            self._status(store, ws_dir, video_id, "cleaning", error=None)
            segments = clean_segments(raw_segments)
            if not segments:
                raise IngestError("The transcript was empty after cleaning.")
            store.write_segments(ws_dir, video_id, segments)
            clean_text = render_clean_text(segments)
            store.write_clean(ws_dir, video_id, clean_text)

            self._status(store, ws_dir, video_id, "indexing", error=None)
            chunks = chunk_segments(video_id, segments)
            store.write_chunks(ws_dir, video_id, chunks)
            store.write_transcripts(ws_dir)
            store.touch_workspace(ws_dir)

            self._status(
                store,
                ws_dir,
                video_id,
                "ready",
                error=None,
                transcript_source=source,
                tokens=estimate_tokens(clean_text),
                **common,
            )
        except (IngestError, MetadataError, CaptionError) as exc:
            self._status(store, ws_dir, video_id, "failed", error=str(exc))
        except (NotFound, FileNotFoundError):
            return
        except Exception as exc:
            log.exception("Ingest failed for %s", video_id)
            self._status(store, ws_dir, video_id, "failed", error=friendly_error(exc))
