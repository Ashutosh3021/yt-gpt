"""Normalise the YouTube links a user pastes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,}$")
ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
    "www.youtu.be",
}


@dataclass(slots=True)
class NormalizedLinks:
    video_ids: list[str] = field(default_factory=list)
    playlist_urls: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.video_ids and not self.playlist_urls and not self.invalid


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _host(url) -> str:
    return (url.hostname or "").lower()


def extract_video_id(raw: str) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    if VIDEO_ID_RE.match(value) and "://" not in value and "/" not in value:
        # Accept a bare id as a convenience.
        return value
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        value = "https://" + value
    try:
        url = urlparse(value)
    except ValueError:
        return None
    host = _host(url)
    if host not in ALLOWED_HOSTS:
        return None
    if host in {"youtu.be", "www.youtu.be"}:
        candidate = url.path.strip("/").split("/")[0]
        return candidate if VIDEO_ID_RE.match(candidate or "") else None
    query = parse_qs(url.query)
    values = query.get("v")
    query_id = values[0] if values else None
    if query_id and VIDEO_ID_RE.match(query_id):
        return query_id
    match = re.match(r"^/(?:shorts|live|embed|v)/([A-Za-z0-9_-]{6,})", url.path)
    if match:
        return match.group(1)
    return None


def playlist_url(raw: str) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        value = "https://" + value
    try:
        url = urlparse(value)
    except ValueError:
        return None
    if _host(url) not in ALLOWED_HOSTS:
        return None
    query = parse_qs(url.query)
    if not query.get("list"):
        return None
    # A watch link with both v and list is a single video, matching the UI.
    if query.get("v") and extract_video_id(value):
        return None
    return value


def normalize_links(text: str) -> NormalizedLinks:
    result = NormalizedLinks()
    seen: set[str] = set()
    seen_playlists: set[str] = set()
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        video_id = extract_video_id(line)
        if video_id:
            if video_id not in seen:
                seen.add(video_id)
                result.video_ids.append(video_id)
            continue
        pl = playlist_url(line)
        if pl:
            if pl not in seen_playlists:
                seen_playlists.add(pl)
                result.playlist_urls.append(pl)
            continue
        result.invalid.append(line)
    return result
