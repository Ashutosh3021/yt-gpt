"""File-backed workspace store.

The on-disk layout is the product: a workspace is a folder the user can read,
back up or grep. Every write is atomic; derived files can be rebuilt from
``segments.jsonl`` and ``meta.json``.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import threading
import time
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .. import config
from ..util import (
    atomic_write_text,
    estimate_tokens,
    iso_now,
    read_json,
    read_jsonl,
    safe_child,
    slugify,
    write_json,
    write_jsonl,
)
from .export import render_workspace_markdown

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,}$")
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_]{3,80}$")
VERSION_ID_RE = re.compile(r"^[A-Za-z0-9_]{3,80}$")
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class StoreError(Exception):
    status_code = 400


class NotFound(StoreError):
    status_code = 404


class Conflict(StoreError):
    status_code = 409


_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_meta(video_dir: Path) -> dict[str, Any]:
    meta = read_json(video_dir / "meta.json")
    return meta if isinstance(meta, dict) else {}


def sanitize_source_name(name: str) -> str:
    raw = (name or "").strip().replace("\\", "/")
    base = raw.split("/")[-1].strip()
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", base)
    base = base.lstrip(".").strip()
    if not base or base in {".", ".."}:
        raise StoreError("Give the source a file name.")
    if not re.search(r"\.(md|txt)$", base, re.IGNORECASE):
        base += ".md"
    if len(base) > 120:
        stem, dot, ext = base.rpartition(".")
        base = f"{stem[:110]}{dot}{ext}" if dot else base[:120]
    if base.rsplit(".", 1)[0].strip().upper() in RESERVED_WINDOWS_NAMES:
        base = f"_{base}"
    return base


def _validate_video_id(video_id: str) -> str:
    value = (video_id or "").strip()
    if not VIDEO_ID_RE.match(value):
        raise StoreError("That video id is not valid.")
    return value


def _validate_session_id(session_id: str) -> str:
    value = (session_id or "").strip()
    if not SESSION_ID_RE.match(value):
        raise NotFound("Session not found.")
    return value


def _clamp_title(title: str, fallback: str) -> str:
    clean = (title or "").strip()
    return clean[:120] if clean else fallback


class WorkspaceStore:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.root = config.user_root(user_id)
        self.workspaces_root = self.root / "workspaces"
        self.workspaces_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ paths

    def _lock(self, ws_dir: Path) -> threading.RLock:
        return _lock_for(ws_dir)

    def _ws_json_path(self, ws_dir: Path) -> Path:
        return ws_dir / "workspace.json"

    def _read_workspace_json(self, ws_dir: Path) -> dict[str, Any]:
        data = read_json(self._ws_json_path(ws_dir))
        if not isinstance(data, dict):
            raise NotFound("Workspace not found.")
        return data

    def touch_workspace(self, ws_dir: Path) -> dict[str, Any]:
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            data["updated_at"] = iso_now()
            self._save_workspace_json(ws_dir, data)
            return data

    def _save_workspace_json(self, ws_dir: Path, data: dict[str, Any]) -> None:
        data["updated_at"] = iso_now()
        write_json(self._ws_json_path(ws_dir), data)

    def resolve(self, ws_id: str) -> Path:
        value = (ws_id or "").strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise NotFound("Workspace not found.")
        direct = self.workspaces_root / value
        if (direct / "workspace.json").exists():
            return direct.resolve()
        if self.workspaces_root.exists():
            for child in self.workspaces_root.iterdir():
                if not child.is_dir():
                    continue
                data = read_json(child / "workspace.json")
                if not isinstance(data, dict):
                    continue
                if data.get("id") == value or data.get("slug") == value:
                    return child.resolve()
        raise NotFound("Workspace not found.")

    def _unique_slug(self, name: str, exclude: Path | None = None) -> str:
        base = slugify(name)
        taken = {
            child.name
            for child in self.workspaces_root.iterdir()
            if child.is_dir() and (exclude is None or child.resolve() != exclude.resolve())
        }
        slug = base
        index = 2
        while slug in taken:
            slug = f"{base}-{index}"
            index += 1
        return slug

    def _video_dir(self, ws_dir: Path, video_id: str) -> Path:
        return safe_child(ws_dir / "videos", _validate_video_id(video_id))

    def _session_path(self, ws_dir: Path, session_id: str) -> Path:
        return safe_child(ws_dir / "sessions", f"{_validate_session_id(session_id)}.json")

    def _source_path(self, ws_dir: Path, name: str) -> tuple[str, Path]:
        clean = sanitize_source_name(name)
        return clean, safe_child(ws_dir / "sources", clean)

    def _versions_dir(self, ws_dir: Path, name: str) -> Path:
        clean = sanitize_source_name(name)
        return safe_child(ws_dir / "sources", ".versions", clean)

    # -------------------------------------------------------------- workspaces

    def list_workspaces(self) -> list[dict[str, Any]]:
        if not self.workspaces_root.exists():
            return []
        rows: list[dict[str, Any]] = []
        for child in self.workspaces_root.iterdir():
            if not child.is_dir():
                continue
            data = read_json(child / "workspace.json")
            if isinstance(data, dict):
                rows.append(self._workspace_response(child, data))
        rows.sort(key=lambda row: row.get("updatedAt", ""), reverse=True)
        return rows

    def get_workspace(self, ws_id: str) -> dict[str, Any]:
        ws_dir = self.resolve(ws_id)
        return self._workspace_response(ws_dir, self._read_workspace_json(ws_dir))

    def create_workspace(self, name: str) -> dict[str, Any]:
        clean = (name or "").strip()
        if not clean:
            raise StoreError("Give the workspace a name.")
        with self._lock(self.workspaces_root):
            slug = self._unique_slug(clean)
            ws_dir = self.workspaces_root / slug
            ws_dir.mkdir(parents=True, exist_ok=False)
            for child in ("videos", "sessions", "sources", "sources/.versions"):
                (ws_dir / child).mkdir(parents=True, exist_ok=True)
            now = iso_now()
            data = {
                "id": f"ws_{uuid.uuid4().hex[:12]}",
                "owner_id": self.user_id,
                "name": clean[:80],
                "slug": slug,
                "created_at": now,
                "updated_at": now,
                "settings": {"use_visuals": False, "summarize": False},
                "video_order": [],
            }
            self._save_workspace_json(ws_dir, data)
            session = self._new_session_data(ws_dir, title="First session", data=data)
            write_json(ws_dir / "sessions" / f"{session['session_id']}.json", session)
            atomic_write_text(ws_dir / "transcripts.md", f"# {data['name']}\n\nNo videos yet.\n")
            return self._workspace_response(ws_dir, data)

    def rename_workspace(self, ws_id: str, name: str) -> dict[str, Any]:
        clean = (name or "").strip()
        if not clean:
            raise StoreError("The name cannot be empty.")
        ws_dir = self.resolve(ws_id)
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            new_slug = self._unique_slug(clean, exclude=ws_dir)
            if new_slug != ws_dir.name:
                target = self.workspaces_root / new_slug
                if target.exists():
                    raise Conflict("A workspace with that name already exists.")
                shutil.move(str(ws_dir), str(target))
                ws_dir = target
            data["name"] = clean[:80]
            data["slug"] = ws_dir.name
            self._save_workspace_json(ws_dir, data)
            return self._workspace_response(ws_dir, data)

    def delete_workspace(self, ws_id: str) -> None:
        ws_dir = self.resolve(ws_id)
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            trash = config.home() / "trash" / self.user_id
            trash.mkdir(parents=True, exist_ok=True)
            target = trash / f"{data.get('slug', ws_dir.name)}-{int(time.time())}"
            suffix = 2
            while target.exists():
                target = trash / f"{data.get('slug', ws_dir.name)}-{int(time.time())}-{suffix}"
                suffix += 1
            shutil.move(str(ws_dir), str(target))

    # ------------------------------------------------------------------ videos

    def _video_response(self, video_dir: Path, meta: dict[str, Any]) -> dict[str, Any]:
        segments = read_jsonl(video_dir / "segments.jsonl")
        summary = _read_text(video_dir / "summary.md")
        tokens = int(meta.get("tokens") or 0)
        if not tokens and segments:
            tokens = estimate_tokens(" ".join(str(s.get("text", "")) for s in segments))
        visual = meta.get("visual")
        if not isinstance(visual, dict):
            visual = {}
        frames = 0
        frames_file = read_json(video_dir / "visual" / "frames.json")
        if isinstance(frames_file, dict):
            frames = len(frames_file.get("frames") or [])
        elif isinstance(frames_file, list):
            frames = len(frames_file)
        video_id = str(meta.get("video_id") or video_dir.name)
        return {
            "id": video_id,
            "youtubeId": video_id,
            "url": meta.get("url") or f"https://www.youtube.com/watch?v={video_id}",
            "title": meta.get("title") or f"YouTube video {video_id}",
            "channel": meta.get("channel") or "",
            "durationS": int(meta.get("duration_s") or 0),
            "language": meta.get("language") or "",
            "transcriptSource": meta.get("transcript_source") or "auto",
            "status": meta.get("status") or "queued",
            "error": meta.get("error"),
            "addedAt": meta.get("added_at") or iso_now(),
            "tokens": tokens,
            "summary": summary.strip(),
            "segments": [
                {
                    "start": float(segment.get("start") or 0),
                    "end": float(segment.get("end") or 0),
                    "text": str(segment.get("text") or ""),
                }
                for segment in segments
                if str(segment.get("text") or "").strip()
            ],
            "visual": {
                "enabled": bool(visual.get("enabled", False)),
                "status": visual.get("status", "none"),
                "frames": frames,
            },
        }

    def list_video_dirs(self, ws_dir: Path) -> list[Path]:
        data = self._read_workspace_json(ws_dir)
        order = data.get("video_order") or []
        dirs: list[Path] = []
        seen: set[str] = set()
        for video_id in order:
            if not isinstance(video_id, str) or video_id in seen:
                continue
            seen.add(video_id)
            candidate = ws_dir / "videos" / video_id
            if candidate.is_dir():
                dirs.append(candidate)
        if len(dirs) != len(order):
            for child in sorted((ws_dir / "videos").glob("*")):
                if child.is_dir() and child.name not in seen:
                    dirs.append(child)
        return dirs

    def _video_meta(self, ws_dir: Path, video_id: str) -> dict[str, Any]:
        path = self._video_dir(ws_dir, video_id) / "meta.json"
        meta = read_json(path)
        if not isinstance(meta, dict):
            raise NotFound("Video not found.")
        return meta

    def add_video(self, ws_dir: Path, video_id: str, url: str) -> dict[str, Any] | None:
        video_id = _validate_video_id(video_id)
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            order = list(data.get("video_order") or [])
            video_dir = ws_dir / "videos" / video_id
            if video_id in order or (video_dir / "meta.json").exists():
                return None
            video_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "video_id": video_id,
                "url": url,
                "title": f"YouTube video {video_id}",
                "channel": "",
                "duration_s": 0,
                "language": "",
                "transcript_source": "auto",
                "status": "queued",
                "error": None,
                "added_at": iso_now(),
                "visual": {"enabled": False, "status": "none"},
            }
            write_json(video_dir / "meta.json", meta)
            order.append(video_id)
            data["video_order"] = order
            self._save_workspace_json(ws_dir, data)
            return self._video_response(video_dir, meta)

    def get_video(self, ws_dir: Path, video_id: str) -> dict[str, Any]:
        video_dir = self._video_dir(ws_dir, video_id)
        meta = self._video_meta(ws_dir, video_id)
        return self._video_response(video_dir, meta)

    def update_video_meta(self, ws_dir: Path, video_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        video_id = _validate_video_id(video_id)
        with self._lock(ws_dir):
            video_dir = ws_dir / "videos" / video_id
            meta = read_json(video_dir / "meta.json")
            if not isinstance(meta, dict):
                raise NotFound("Video not found.")
            meta.update(patch)
            write_json(video_dir / "meta.json", meta)
            return meta

    def set_video_status(
        self,
        ws_dir: Path,
        video_id: str,
        status: str,
        *,
        error: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        patch = {"status": status, "error": error, **fields}
        return self.update_video_meta(ws_dir, video_id, patch)

    def write_segments(self, ws_dir: Path, video_id: str, segments: Iterable[dict[str, Any]]) -> None:
        video_dir = self._video_dir(ws_dir, video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(video_dir / "segments.jsonl", segments)

    def write_clean(self, ws_dir: Path, video_id: str, text: str) -> None:
        video_dir = self._video_dir(ws_dir, video_id)
        atomic_write_text(video_dir / "clean.txt", text)

    def write_chunks(self, ws_dir: Path, video_id: str, chunks: Iterable[dict[str, Any]]) -> None:
        video_dir = self._video_dir(ws_dir, video_id)
        write_jsonl(video_dir / "chunks.jsonl", chunks)

    def write_summary(self, ws_dir: Path, video_id: str, text: str) -> None:
        video_dir = self._video_dir(ws_dir, video_id)
        atomic_write_text(video_dir / "summary.md", text)

    def read_segments(self, ws_dir: Path, video_id: str) -> list[dict[str, Any]]:
        return read_jsonl(self._video_dir(ws_dir, video_id) / "segments.jsonl")

    def read_clean(self, ws_dir: Path, video_id: str) -> str:
        return _read_text(self._video_dir(ws_dir, video_id) / "clean.txt")

    def read_chunks(self, ws_dir: Path, video_id: str) -> list[dict[str, Any]]:
        return read_jsonl(self._video_dir(ws_dir, video_id) / "chunks.jsonl")

    def remove_video(self, ws_dir: Path, video_id: str) -> None:
        video_id = _validate_video_id(video_id)
        with self._lock(ws_dir):
            video_dir = ws_dir / "videos" / video_id
            if not video_dir.exists():
                raise NotFound("Video not found.")
            shutil.rmtree(video_dir, ignore_errors=True)
            data = self._read_workspace_json(ws_dir)
            order = [value for value in (data.get("video_order") or []) if value != video_id]
            data["video_order"] = order
            self._save_workspace_json(ws_dir, data)
            self._write_transcripts_locked(ws_dir, data)

    def retry_video(self, ws_dir: Path, video_id: str) -> dict[str, Any]:
        return self.set_video_status(ws_dir, video_id, "queued", error=None)

    # ---------------------------------------------------------------- sessions

    def _new_session_data(
        self, ws_dir: Path, title: str | None, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if data is None:
            data = self._read_workspace_json(ws_dir)
        settings = data.get("settings") or {}
        now = iso_now()
        return {
            "session_id": f"s_{uuid.uuid4().hex[:12]}",
            "title": _clamp_title(title or "New session", "New session"),
            "created_at": now,
            "updated_at": now,
            "settings": {
                "grounding": "strict",
                "persona_id": "default",
                "persona_prompt": None,
                "model_override": None,
                "use_visuals": bool(settings.get("use_visuals", False)),
            },
            "rolling_summary": "",
            "messages": [],
        }

    def _session_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        settings = raw.get("settings")
        if not isinstance(settings, dict):
            settings = {}
        return {
            "id": raw.get("session_id", ""),
            "title": raw.get("title") or "Session",
            "createdAt": raw.get("created_at", ""),
            "updatedAt": raw.get("updated_at", raw.get("created_at", "")),
            "settings": {
                "grounding": settings.get("grounding", "strict"),
                "personaId": settings.get("persona_id", "default"),
                "personaPrompt": settings.get("persona_prompt"),
                "modelOverride": settings.get("model_override"),
                "useVisuals": bool(settings.get("use_visuals", False)),
            },
            "rollingSummary": raw.get("rolling_summary", ""),
            "messages": raw.get("messages") or [],
        }

    def list_session_files(self, ws_dir: Path) -> list[Path]:
        return sorted((ws_dir / "sessions").glob("*.json"), key=lambda path: path.stat().st_mtime)

    def list_sessions(self, ws_dir: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in self.list_session_files(ws_dir):
            raw = read_json(path)
            if isinstance(raw, dict):
                rows.append(self._session_response(raw))
        rows.sort(key=lambda row: row.get("createdAt", ""))
        return rows

    def create_session(self, ws_dir: Path, title: str | None = None) -> dict[str, Any]:
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            session = self._new_session_data(ws_dir, title, data)
            write_json(ws_dir / "sessions" / f"{session['session_id']}.json", session)
            self._save_workspace_json(ws_dir, data)
            return self._session_response(session)

    def load_session(self, ws_dir: Path, session_id: str) -> dict[str, Any]:
        raw = read_json(self._session_path(ws_dir, session_id))
        if not isinstance(raw, dict):
            raise NotFound("Session not found.")
        return raw

    def get_session(self, ws_dir: Path, session_id: str) -> dict[str, Any]:
        return self._session_response(self.load_session(ws_dir, session_id))

    def save_session(self, ws_dir: Path, raw: dict[str, Any]) -> None:
        raw["updated_at"] = iso_now()
        write_json(self._session_path(ws_dir, str(raw.get("session_id", ""))), raw)
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)

    def update_session(
        self,
        ws_dir: Path,
        session_id: str,
        *,
        title: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock(ws_dir):
            raw = self.load_session(ws_dir, session_id)
            if title is not None and str(title).strip():
                raw["title"] = str(title).strip()[:120]
            if settings:
                current = raw.get("settings")
                if not isinstance(current, dict):
                    current = {}
                mapping = {
                    "grounding": "grounding",
                    "personaId": "persona_id",
                    "personaPrompt": "persona_prompt",
                    "modelOverride": "model_override",
                    "useVisuals": "use_visuals",
                }
                for key, value in settings.items():
                    if key in mapping:
                        current[mapping[key]] = value
                raw["settings"] = current
            raw["updated_at"] = iso_now()
            write_json(self._session_path(ws_dir, session_id), raw)
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)
            return self._session_response(raw)

    def delete_session(self, ws_dir: Path, session_id: str) -> None:
        with self._lock(ws_dir):
            path = self._session_path(ws_dir, session_id)
            if not path.exists():
                raise NotFound("Session not found.")
            path.unlink()
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)

    def append_message(self, ws_dir: Path, session_id: str, message: dict[str, Any]) -> dict[str, Any]:
        with self._lock(ws_dir):
            raw = self.load_session(ws_dir, session_id)
            messages = raw.get("messages")
            if not isinstance(messages, list):
                messages = []
            messages.append(message)
            raw["messages"] = messages
            raw["updated_at"] = iso_now()
            write_json(self._session_path(ws_dir, session_id), raw)
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)
            return self._session_response(raw)

    # ----------------------------------------------------------------- sources

    def _versions(self, ws_dir: Path, name: str) -> list[dict[str, Any]]:
        versions_dir = self._versions_dir(ws_dir, name)
        if not versions_dir.is_dir():
            return []
        rows: list[dict[str, Any]] = []
        for path in versions_dir.glob("*.json"):
            raw = read_json(path)
            if isinstance(raw, dict) and raw.get("id"):
                rows.append(raw)
        rows.sort(key=lambda row: row.get("ts", ""))
        return rows

    def _source_response(self, ws_dir: Path, name: str, content: str) -> dict[str, Any]:
        versions = self._versions(ws_dir, name)
        updated = versions[-1]["ts"] if versions else iso_now()
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
        return {
            "id": f"src_{digest}",
            "name": name,
            "content": content,
            "updatedAt": updated,
            "versions": versions,
        }

    def list_sources(self, ws_dir: Path) -> list[dict[str, Any]]:
        sources_dir = ws_dir / "sources"
        if not sources_dir.is_dir():
            return []
        rows: list[dict[str, Any]] = []
        for path in sources_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            rows.append(self._source_response(ws_dir, path.name, _read_text(path)))
        rows.sort(key=lambda row: row.get("updatedAt", ""), reverse=True)
        return rows

    def get_source(self, ws_dir: Path, name: str) -> dict[str, Any]:
        clean, path = self._source_path(ws_dir, name)
        if not path.exists():
            raise NotFound("Source not found.")
        return self._source_response(ws_dir, clean, _read_text(path))

    def _add_version(self, ws_dir: Path, name: str, content: str, note: str) -> dict[str, Any]:
        versions_dir = self._versions_dir(ws_dir, name)
        versions_dir.mkdir(parents=True, exist_ok=True)
        version_id = f"ver_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        raw = {"id": version_id, "ts": iso_now(), "content": content, "note": note}
        write_json(versions_dir / f"{version_id}.json", raw)
        return raw

    def create_source(self, ws_dir: Path, name: str, content: str | None = None) -> dict[str, Any]:
        clean, path = self._source_path(ws_dir, name)
        with self._lock(ws_dir):
            existing = {row["name"].lower() for row in self.list_sources(ws_dir)}
            if clean.lower() in existing or path.exists():
                raise Conflict("A source with that name already exists.")
            body = content if content is not None else f"# {clean.rsplit('.', 1)[0]}\n\n"
            atomic_write_text(path, body)
            self._add_version(ws_dir, clean, body, "Created")
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)
            return self._source_response(ws_dir, clean, body)

    def update_source(self, ws_dir: Path, name: str, content: str, note: str | None = None) -> dict[str, Any]:
        clean, path = self._source_path(ws_dir, name)
        if not path.exists():
            raise NotFound("Source not found.")
        with self._lock(ws_dir):
            atomic_write_text(path, content)
            self._add_version(ws_dir, clean, content, note or "Saved")
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)
            return self._source_response(ws_dir, clean, content)

    def delete_source(self, ws_dir: Path, name: str) -> None:
        clean, path = self._source_path(ws_dir, name)
        if not path.exists():
            raise NotFound("Source not found.")
        with self._lock(ws_dir):
            path.unlink()
            shutil.rmtree(self._versions_dir(ws_dir, clean), ignore_errors=True)
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)

    def restore_version(self, ws_dir: Path, name: str, version_id: str) -> dict[str, Any]:
        clean, path = self._source_path(ws_dir, name)
        if not path.exists():
            raise NotFound("Source not found.")
        if not VERSION_ID_RE.match(version_id or ""):
            raise NotFound("Version not found.")
        with self._lock(ws_dir):
            version_path = self._versions_dir(ws_dir, clean) / f"{version_id}.json"
            version = read_json(version_path)
            if not isinstance(version, dict):
                raise NotFound("Version not found.")
            content = str(version.get("content", ""))
            atomic_write_text(path, content)
            stamp = version.get("ts", "")
            self._add_version(ws_dir, clean, content, f"Restored from {stamp}")
            data = self._read_workspace_json(ws_dir)
            self._save_workspace_json(ws_dir, data)
            return self._source_response(ws_dir, clean, content)

    # ------------------------------------------------------------------ export

    def _write_transcripts_locked(self, ws_dir: Path, data: dict[str, Any] | None = None) -> str:
        if data is None:
            data = self._read_workspace_json(ws_dir)
        videos = [self._video_response(path, _read_meta(path)) for path in self.list_video_dirs(ws_dir)]
        content = render_workspace_markdown(str(data.get("name", "Workspace")), videos)
        atomic_write_text(ws_dir / "transcripts.md", content)
        return content

    def write_transcripts(self, ws_dir: Path) -> str:
        with self._lock(ws_dir):
            data = self._read_workspace_json(ws_dir)
            return self._write_transcripts_locked(ws_dir, data)

    def read_transcripts(self, ws_dir: Path) -> str:
        return _read_text(ws_dir / "transcripts.md")

    # ------------------------------------------------------------- index cache

    def index_signature(self, ws_dir: Path) -> tuple[tuple[str, int, int], ...]:
        rows: list[tuple[str, int, int]] = []
        for video_dir in self.list_video_dirs(ws_dir):
            path = video_dir / "chunks.jsonl"
            try:
                stat = path.stat()
            except OSError:
                continue
            rows.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(sorted(rows))

    def all_chunks(self, ws_dir: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for video_dir in self.list_video_dirs(ws_dir):
            rows.extend(read_jsonl(video_dir / "chunks.jsonl"))
        return rows

    def rebuild_derived(self, ws_dir: Path) -> int:
        from ..ingest.chunk import chunk_segments
        from ..ingest.clean import clean_segments, render_clean_text
        from ..util import estimate_tokens

        count = 0
        with self._lock(ws_dir):
            for video_dir in self.list_video_dirs(ws_dir):
                segments = read_jsonl(video_dir / "segments.jsonl")
                if not segments:
                    continue
                cleaned = clean_segments(segments)
                write_jsonl(video_dir / "segments.jsonl", cleaned)
                atomic_write_text(video_dir / "clean.txt", render_clean_text(cleaned))
                chunks = chunk_segments(video_dir.name, cleaned)
                write_jsonl(video_dir / "chunks.jsonl", chunks)
                meta = _read_meta(video_dir)
                meta["tokens"] = estimate_tokens(_read_text(video_dir / "clean.txt"))
                meta["status"] = "ready"
                meta["error"] = None
                write_json(video_dir / "meta.json", meta)
                count += 1
            data = self._read_workspace_json(ws_dir)
            self._write_transcripts_locked(ws_dir, data)
        return count

    # ------------------------------------------------------------------ lookup

    def _workspace_response(self, ws_dir: Path, data: dict[str, Any]) -> dict[str, Any]:
        videos = [self._video_response(path, _read_meta(path)) for path in self.list_video_dirs(ws_dir)]
        sessions = self.list_sessions(ws_dir)
        sources = self.list_sources(ws_dir)
        settings = data.get("settings")
        if not isinstance(settings, dict):
            settings = {}
        return {
            "id": data.get("id", ws_dir.name),
            "ownerId": self.user_id,
            "name": data.get("name", ws_dir.name),
            "slug": data.get("slug", ws_dir.name),
            "createdAt": data.get("created_at", ""),
            "updatedAt": data.get("updated_at", ""),
            "settings": {
                "useVisuals": bool(settings.get("use_visuals", False)),
                "summarize": bool(settings.get("summarize", False)),
            },
            "videos": videos,
            "sessions": sessions,
            "sources": sources,
        }
