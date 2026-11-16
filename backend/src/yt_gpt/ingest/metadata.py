"""yt-dlp metadata (no media download) and playlist expansion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .. import config
from .urls import canonical_url

try:  # yt-dlp is a hard dependency, but keep the import boundary kind.
    import yt_dlp
except Exception:  # pragma: no cover - broken install
    yt_dlp = None  # type: ignore[assignment]


class MetadataError(Exception):
    """A human-readable metadata failure."""


@dataclass(slots=True)
class CaptionTrack:
    source: str  # manual | auto
    language: str
    url: str
    ext: str


def _base_options() -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noprogress": True,
        "socket_timeout": 25,
        "retries": 2,
        "extractor_retries": 2,
    }
    cookies = config.cookies_file()
    if cookies:
        options["cookiefile"] = str(cookies)
    return options


def friendly_error(exc: BaseException | str) -> str:
    text = str(exc) or exc.__class__.__name__
    lower = text.lower()
    if "private video" in lower or "this video is private" in lower:
        return "Video is private. Add a cookies file or remove it from the library."
    if "members-only" in lower or "join this channel" in lower:
        return "Video is members-only. Add a cookies file with access or remove it."
    if "age" in lower and ("restrict" in lower or "confirm" in lower):
        return "Video is age-restricted. Add a cookies file to fetch it."
    if "sign in to confirm" in lower or "not a bot" in lower:
        return "YouTube asked for a sign-in check. Add a cookies file and retry."
    if "429" in lower or "too many requests" in lower:
        return "YouTube rate-limited the request. Wait a little and retry."
    if "unavailable" in lower or "does not exist" in lower or "removed" in lower:
        return "Video is unavailable or removed."
    if "timed out" in lower or "timeout" in lower:
        return "YouTube did not answer in time. Retry later."
    if "unsupported url" in lower:
        return "That link is not a YouTube video."
    return f"Could not fetch the video: {text[:240]}"


def _require_ytdlp() -> Any:
    if yt_dlp is None:  # pragma: no cover
        raise MetadataError("yt-dlp is not installed correctly. Reinstall yt-gpt.")
    return yt_dlp


def fetch_info(video_id: str) -> dict[str, Any]:
    """Return the yt-dlp info dict for a single video."""
    module = _require_ytdlp()
    options = _base_options()
    options.update({"noplaylist": True, "extract_flat": False})
    url = canonical_url(video_id)
    try:
        with module.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:  # yt-dlp raises DownloadError and friends
        raise MetadataError(friendly_error(exc)) from exc
    if not isinstance(info, dict):
        raise MetadataError("YouTube returned no metadata for this video.")
    if info.get("_type") == "playlist":
        entries = [entry for entry in (info.get("entries") or []) if isinstance(entry, dict)]
        if not entries:
            raise MetadataError("The playlist is empty.")
        info = entries[0]
    return info


def expand_playlist(url: str, limit: int = 200) -> list[str]:
    """Expand a playlist URL into video ids, capped to avoid runaway jobs."""
    module = _require_ytdlp()
    options = _base_options()
    options.update({"noplaylist": False, "extract_flat": "in_playlist", "playlistend": limit})
    try:
        with module.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise MetadataError(friendly_error(exc)) from exc
    if not isinstance(info, dict):
        return []
    entries = info.get("entries") or []
    ids: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video_id = entry.get("id")
        if isinstance(video_id, str) and re.match(r"^[A-Za-z0-9_-]{6,}$", video_id) and video_id not in seen:
            seen.add(video_id)
            ids.append(video_id)
    return ids


def _track_entries(info: dict[str, Any], key: str) -> dict[str, list[dict[str, Any]]]:
    value = info.get(key)
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for language, tracks in value.items():
        if language == "live_chat" or not isinstance(tracks, list):
            continue
        usable = [track for track in tracks if isinstance(track, dict) and track.get("url")]
        if usable:
            out[str(language)] = usable
    return out


def _language_order(info: dict[str, Any], available: list[str]) -> list[str]:
    preferred: list[str] = []
    language = info.get("language")
    if isinstance(language, str) and language:
        preferred.append(language)
        preferred.append(language.split("-")[0])
    preferred.extend(["en", "en-US", "en-GB"])
    ordered: list[str] = []
    for candidate in preferred:
        if candidate in available and candidate not in ordered:
            ordered.append(candidate)
    for candidate in available:
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _pick_track(tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not tracks:
        return None
    priority = {"json3": 0, "vtt": 1, "srv3": 2, "ttml": 3, "srv1": 4, "srv2": 4}
    return sorted(tracks, key=lambda track: priority.get(str(track.get("ext", "")), 9))[0]


def choose_caption_track(info: dict[str, Any]) -> CaptionTrack | None:
    manual = _track_entries(info, "subtitles")
    automatic = _track_entries(info, "automatic_captions")
    if manual:
        for language in _language_order(info, list(manual)):
            track = _pick_track(manual[language])
            if track:
                return CaptionTrack("manual", language, str(track["url"]), str(track.get("ext", "vtt")))
    if automatic:
        for language in _language_order(info, list(automatic)):
            track = _pick_track(automatic[language])
            if track:
                return CaptionTrack("auto", language, str(track["url"]), str(track.get("ext", "vtt")))
    return None
