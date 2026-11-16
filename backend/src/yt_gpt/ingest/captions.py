"""Caption fetching and parsing for YouTube's several subtitle formats."""

from __future__ import annotations

import html
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from .clean import normalize_text
from .metadata import CaptionTrack

TIMING_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
INT_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


class CaptionError(Exception):
    """Caption download or parse failure."""


def parse_timestamp(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    parts = value.split(":")
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return None
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds


def _merge(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for segment in segments:
        text = normalize_text(segment.get("text", ""))
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end < start:
            end = start
        if out:
            previous = out[-1]
            if text == previous["text"]:
                previous["end"] = max(previous["end"], end)
                continue
            if start <= previous["end"] + 0.05 and text.startswith(previous["text"]):
                previous["text"] = text
                previous["end"] = max(previous["end"], end)
                continue
        out.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return out


def parse_vtt(payload: str) -> list[dict[str, Any]]:
    text = payload.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n{2,}", text)
    segments: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if first.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            continue
        match = TIMING_RE.search(lines[timing_index])
        if not match:
            continue
        start = parse_timestamp(match.group("start"))
        end = parse_timestamp(match.group("end"))
        if start is None:
            continue
        body = " ".join(lines[timing_index + 1 :])
        body = re.sub(r"<[^>]+>", " ", body)
        body = html.unescape(body)
        segments.append({"start": start, "end": end if end is not None else start + 1.0, "text": body})
    return _merge(segments)


def parse_json3(payload: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CaptionError("Caption data was not valid JSON.") from exc
    events = data.get("events") if isinstance(data, dict) else None
    if not isinstance(events, list):
        return []
    segments: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        start_ms = event.get("tStartMs")
        if not isinstance(start_ms, (int, float)):
            continue
        duration_ms = event.get("dDurationMs")
        duration = float(duration_ms) if isinstance(duration_ms, (int, float)) else 0.0
        pieces: list[str] = []
        for segment in event.get("segs") or []:
            if isinstance(segment, dict):
                piece = segment.get("utf8")
                if isinstance(piece, str):
                    pieces.append(piece)
        text = "".join(pieces)
        if not text.strip():
            continue
        start = float(start_ms) / 1000.0
        segments.append({"start": start, "end": start + duration / 1000.0, "text": text})
    return _merge(segments)


def parse_xml_captions(payload: str) -> list[dict[str, Any]]:
    text = payload.lstrip("\ufeff")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise CaptionError("Caption data was not valid XML.") from exc
    segments: list[dict[str, Any]] = []
    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()
        if tag != "text" and tag != "p":
            continue
        body = "".join(element.itertext())
        start_raw = element.attrib.get("start") or element.attrib.get("begin")
        end_raw = element.attrib.get("dur") or element.attrib.get("end")
        if start_raw is None:
            continue
        if INT_RE.match(start_raw.strip()):
            start = float(start_raw) / 1000.0 if float(start_raw) > 1000 else float(start_raw)
        else:
            parsed_start = parse_timestamp(start_raw)
            if parsed_start is None:
                continue
            start = parsed_start
        if end_raw is None:
            end = start + 1.0
        elif INT_RE.match(end_raw.strip()):
            end = start + float(end_raw) / 1000.0
        else:
            parsed_end = parse_timestamp(end_raw)
            end = parsed_end if parsed_end is not None else start + 1.0
        segments.append({"start": start, "end": end, "text": body})
    return _merge(segments)


def parse_captions(payload: str, ext: str) -> list[dict[str, Any]]:
    ext = (ext or "").lower().lstrip(".")
    if ext == "json3" or payload.lstrip().startswith("{"):
        return parse_json3(payload)
    if ext == "vtt" or "WEBVTT" in payload[:64]:
        return parse_vtt(payload)
    return parse_xml_captions(payload)


def download_captions(track: CaptionTrack, attempts: int = 3) -> list[dict[str, Any]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
                response = client.get(track.url)
                response.raise_for_status()
                segments = parse_captions(response.text, track.ext)
                if segments:
                    return segments
                last_error = CaptionError("The caption track was empty.")
        except Exception as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(1.5 * (attempt + 1))
    raise CaptionError(f"Could not download captions: {str(last_error)[:200]}")
