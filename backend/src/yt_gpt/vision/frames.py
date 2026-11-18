"""Lazy visual indexing: download, scene sampling, contact sheets and frames."""

from __future__ import annotations

import base64
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from .. import config
from ..ingest.urls import canonical_url
from ..util import format_seconds, iso_now, read_json, write_json

log = logging.getLogger(__name__)

SCENE_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")
MAX_FRAMES = 24
SHEET_FRAMES = 6
SHEET_COLUMNS = 3
SHEET_ROWS = 2
THUMB_WIDTH = 480
THUMB_HEIGHT = 270
LABEL_HEIGHT = 24
SHEET_PADDING = 8


class VisualError(Exception):
    """A user-facing visual indexing failure."""


def _ytdlp() -> Any:
    try:
        import yt_dlp
    except Exception as exc:  # pragma: no cover - broken install
        raise VisualError("yt-dlp is unavailable. Reinstall yt-gpt.") from exc
    return yt_dlp


def _download_options(dest_dir: Path, *, height: int, section: tuple[float, float] | None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
        "extractor_retries": 2,
        "outtmpl": str(dest_dir / "source.%(ext)s"),
        "format": f"bv*[height<={height}]/b[height<={height}]/bv*/b",
    }
    cookies = config.cookies_file()
    if cookies:
        options["cookiefile"] = str(cookies)
    if section is not None:
        start, end = section
        options["download_ranges"] = lambda _info, _ydl: [
            {"start_time": max(0.0, start), "end_time": max(start + 0.5, end)}
        ]
        options["force_keyframes_at_cuts"] = True
    return options


def _download(
    video_id: str, dest_dir: Path, *, height: int = 360, section: tuple[float, float] | None = None
) -> Path:
    module = _ytdlp()
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with module.YoutubeDL(_download_options(dest_dir, height=height, section=section)) as ydl:
            ydl.download([canonical_url(video_id)])
    except VisualError:
        raise
    except Exception as exc:
        raise VisualError(f"Could not download video frames: {exc}") from exc
    files = sorted(
        path
        for path in dest_dir.iterdir()
        if path.is_file() and path.suffix.lower() not in {".part", ".ytdl", ".temp"}
    )
    if not files:
        raise VisualError("The video download produced no playable file.")
    return files[0]


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffmpeg(arguments: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [_ffmpeg(), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise VisualError("Frame extraction timed out.") from exc
    except OSError as exc:
        raise VisualError(f"ffmpeg could not start: {exc}") from exc


def parse_scene_times(stderr: str, duration: float) -> list[float]:
    values: list[float] = []
    for raw in SCENE_RE.findall(stderr or ""):
        try:
            value = float(raw)
        except ValueError:
            continue
        if 0 <= value <= max(0.0, duration):
            values.append(round(value, 3))
    return sorted(set(values))


def select_timestamps(duration: float, scene_times: list[float]) -> list[float]:
    duration = max(0.0, float(duration))
    if duration <= 0.5:
        return [0.0]
    usable = sorted({round(value, 3) for value in scene_times if 0.5 < value < duration - 0.5})
    filtered: list[float] = []
    for value in usable:
        if not filtered or value - filtered[-1] >= 4.0:
            filtered.append(value)
    target = min(MAX_FRAMES, max(6, int(duration / 90) + 4))
    if len(filtered) >= 4:
        selected = [0.5, *filtered][:MAX_FRAMES]
        if len(selected) > target:
            step = (len(selected) - 1) / max(1, target - 1)
            selected = [selected[round(index * step)] for index in range(target)]
        return [round(min(duration - 0.2, max(0.0, value)), 3) for value in selected]
    return [round((index + 0.5) * duration / target, 3) for index in range(target)]


def _scene_times(video: Path, duration: float) -> list[float]:
    result = _run_ffmpeg(
        [
            "-hide_banner",
            "-i",
            str(video),
            "-an",
            "-vf",
            "select='gt(scene,0.3)',showinfo",
            "-f",
            "null",
            "-",
        ],
        timeout=240,
    )
    return parse_scene_times(result.stderr, duration)


def _extract_frame(video: Path, timestamp: float, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = _run_ffmpeg(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{max(0.0, timestamp):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-y",
            str(destination),
        ],
        timeout=90,
    )
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        raise VisualError("ffmpeg could not extract a frame from this video.")


def _font(size: int) -> Any:
    for name in ("arial.ttf", "DejaVuSans.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - Pillow < 10.1
        return ImageFont.load_default()


def build_contact_sheets(frames: list[tuple[float, Path]], output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[dict[str, Any]] = []
    font = _font(16)
    for sheet_index in range(0, len(frames), SHEET_FRAMES):
        batch = frames[sheet_index : sheet_index + SHEET_FRAMES]
        width = SHEET_COLUMNS * (THUMB_WIDTH + SHEET_PADDING) + SHEET_PADDING
        height = SHEET_ROWS * (THUMB_HEIGHT + LABEL_HEIGHT + SHEET_PADDING) + SHEET_PADDING
        sheet = Image.new("RGB", (width, height), (24, 24, 28))
        draw = ImageDraw.Draw(sheet)
        for index, (timestamp, path) in enumerate(batch):
            column = index % SHEET_COLUMNS
            row = index // SHEET_COLUMNS
            x = SHEET_PADDING + column * (THUMB_WIDTH + SHEET_PADDING)
            y = SHEET_PADDING + row * (THUMB_HEIGHT + LABEL_HEIGHT + SHEET_PADDING)
            with Image.open(path) as image:
                thumb = image.convert("RGB")
                thumb.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
                offset_x = x + max(0, (THUMB_WIDTH - thumb.width) // 2)
                offset_y = y + max(0, (THUMB_HEIGHT - thumb.height) // 2)
                sheet.paste(thumb, (offset_x, offset_y))
            label = format_seconds(timestamp)
            draw.rectangle(
                (x, y + THUMB_HEIGHT, x + THUMB_WIDTH, y + THUMB_HEIGHT + LABEL_HEIGHT),
                fill=(12, 12, 14),
            )
            draw.text((x + 8, y + THUMB_HEIGHT + 4), label, font=font, fill=(238, 238, 242))
        filename = f"sheet_{len(sheets) + 1:03d}.jpg"
        sheet.save(output_dir / filename, "JPEG", quality=84)
        sheets.append(
            {
                "file": f"sheets/{filename}",
                "index": len(sheets),
                "frames": [{"t": timestamp, "label": format_seconds(timestamp)} for timestamp, _ in batch],
            }
        )
    return sheets


def _safe_visual_file(visual_dir: Path, relative: str) -> Path:
    candidate = (visual_dir / relative).resolve()
    root = visual_dir.resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise VisualError("The cached visual file is missing.")
    return candidate


def ensure_contact_sheets(
    store: Any, ws_dir: Path, video_id: str, *, refresh: bool = False
) -> dict[str, Any]:
    visual_dir = store.video_dir(ws_dir, video_id) / "visual"
    manifest_path = visual_dir / "frames.json"
    if not refresh:
        existing = read_json(manifest_path)
        if isinstance(existing, dict) and existing.get("sheets"):
            try:
                for sheet in existing.get("sheets") or []:
                    _safe_visual_file(visual_dir, str(sheet.get("file") or ""))
                return existing
            except (VisualError, OSError):
                pass
    video = store.get_video(ws_dir, video_id)
    duration = float(video.get("durationS") or 0)
    visual_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = visual_dir / "frames"
    sheets_dir = visual_dir / "sheets"
    shutil.rmtree(frames_dir, ignore_errors=True)
    shutil.rmtree(sheets_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    sheets_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix=".download-", dir=visual_dir))
    try:
        source = _download(video_id, work_dir, height=360)
        scenes = _scene_times(source, duration) if duration >= 1 else []
        timestamps = select_timestamps(duration, scenes)
        frame_entries: list[tuple[float, Path]] = []
        for index, timestamp in enumerate(timestamps, start=1):
            destination = frames_dir / f"frame_{index:03d}.jpg"
            _extract_frame(source, timestamp, destination)
            frame_entries.append((timestamp, destination))
        sheets = build_contact_sheets(frame_entries, sheets_dir)
        manifest = {
            "video_id": video_id,
            "duration_s": duration,
            "created_at": iso_now(),
            "frames": [{"t": timestamp, "file": f"frames/{path.name}"} for timestamp, path in frame_entries],
            "sheets": sheets,
        }
        write_json(manifest_path, manifest)
        return manifest
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def contact_sheet(
    store: Any, ws_dir: Path, video_id: str, index: int = 0, *, refresh: bool = False
) -> dict[str, Any]:
    manifest = ensure_contact_sheets(store, ws_dir, video_id, refresh=refresh)
    sheets = [item for item in manifest.get("sheets") or [] if isinstance(item, dict)]
    if not sheets:
        raise VisualError("No contact sheet could be built for this video.")
    index = max(0, min(index, len(sheets) - 1))
    sheet = sheets[index]
    path = _safe_visual_file(store.video_dir(ws_dir, video_id) / "visual", str(sheet.get("file") or ""))
    return {"path": path, "sheet": sheet, "index": index, "sheet_count": len(sheets), "manifest": manifest}


def frame_at(store: Any, ws_dir: Path, video_id: str, start: float) -> dict[str, Any]:
    start = max(0.0, float(start))
    visual_dir = store.video_dir(ws_dir, video_id) / "visual"
    cache_dir = visual_dir / "moments"
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / f"moment_{int(round(start)):06d}.jpg"
    if destination.is_file() and destination.stat().st_size > 0:
        return {"path": destination, "start": int(round(start)), "low_resolution": False}
    work_dir = Path(tempfile.mkdtemp(prefix=".moment-", dir=visual_dir))
    try:
        section_start = max(0.0, start - 1.0)
        try:
            source = _download(
                video_id,
                work_dir,
                height=720,
                section=(section_start, start + 1.5),
            )
            _extract_frame(source, max(0.0, start - section_start), destination)
            return {"path": destination, "start": int(round(start)), "low_resolution": False}
        except VisualError as exc:
            log.warning("High-resolution frame failed for %s: %s", video_id, exc)
        manifest = ensure_contact_sheets(store, ws_dir, video_id)
        candidates = [
            item
            for item in manifest.get("frames") or []
            if isinstance(item, dict) and isinstance(item.get("t"), (int, float))
        ]
        if not candidates:
            raise VisualError("No frame is available for this video.")
        nearest = min(candidates, key=lambda item: abs(float(item["t"]) - start))
        path = _safe_visual_file(visual_dir, str(nearest.get("file") or ""))
        return {
            "path": path,
            "start": int(round(float(nearest["t"]))),
            "low_resolution": True,
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def image_data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def clear_visuals(store: Any, ws_dir: Path, video_id: str) -> None:
    shutil.rmtree(store.video_dir(ws_dir, video_id) / "visual", ignore_errors=True)
