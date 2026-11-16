"""Optional local transcription fallback using faster-whisper."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .. import config
from .urls import canonical_url


class WhisperUnavailable(RuntimeError):
    pass


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True


def _download_audio(video_id: str, directory: Path) -> Path:
    try:
        import yt_dlp
    except Exception as exc:  # pragma: no cover
        raise WhisperUnavailable("yt-dlp is not installed correctly.") from exc

    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": "bestaudio/best",
        "outtmpl": str(directory / "audio.%(ext)s"),
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
    }
    cookies = config.cookies_file()
    if cookies:
        options["cookiefile"] = str(cookies)
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([canonical_url(video_id)])
    files = [path for path in directory.glob("audio.*") if path.is_file()]
    if not files:
        raise WhisperUnavailable("Could not download audio for transcription.")
    return files[0]


def transcribe(video_id: str, model_size: str | None = None) -> list[dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise WhisperUnavailable(
            "Whisper fallback is not installed. Install it with: pip install 'yt-gpt[whisper]'"
        ) from exc

    engine = os.environ.get("YT_GPT_WHISPER_MODEL", "").strip() or model_size or "base"
    directory = Path(tempfile.mkdtemp(prefix="yt-gpt-whisper-"))
    try:
        audio = _download_audio(video_id, directory)
        model = WhisperModel(engine, device="auto", compute_type="int8")
        raw_segments, _info = model.transcribe(str(audio), vad_filter=True)
        segments: list[dict[str, Any]] = []
        for segment in raw_segments:
            text = str(getattr(segment, "text", "")).strip()
            if not text:
                continue
            start = float(getattr(segment, "start", 0.0) or 0.0)
            end = float(getattr(segment, "end", start) or start)
            segments.append({"start": start, "end": end, "text": text})
        if not segments:
            raise WhisperUnavailable("Whisper found no speech in this video.")
        return segments
    finally:
        shutil.rmtree(directory, ignore_errors=True)
