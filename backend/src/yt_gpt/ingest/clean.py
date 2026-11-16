"""Turn raw caption cues into readable, LLM-ready transcript segments."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

TAG_RE = re.compile(r"<[^>]+>")
ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
WHITESPACE_RE = re.compile(r"\s+")
NON_SPEECH_RE = re.compile(
    r"^\[(music|applause|laughter|silence|inaudible|sound effect|foreign|no audio)\]$", re.IGNORECASE
)
SENTENCE_END = (".", "!", "?", ":", ";", '"', "'", ")")


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = ZERO_WIDTH_RE.sub("", text)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _word_overlap(previous: str, current: str, limit: int = 12) -> int:
    previous_words = previous.split()
    current_words = current.split()
    longest = min(len(previous_words), len(current_words), limit)
    for size in range(longest, 1, -1):
        if previous_words[-size:] == current_words[:size]:
            return size
    return 0


def dedupe_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse rolling captions, which repeat earlier text while growing."""
    out: list[dict[str, Any]] = []
    recent: list[str] = []
    for segment in segments:
        text = normalize_text(segment.get("text", ""))
        if not text or NON_SPEECH_RE.match(text):
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end < start:
            end = start

        # A short line that the next cumulative line already contains.
        if any(previous.endswith(text) and len(previous) > len(text) for previous in recent):
            continue

        for previous in reversed(recent):
            if text.startswith(previous):
                text = text[len(previous) :].strip()
                break
            overlap = _word_overlap(previous, text)
            if overlap:
                text = " ".join(text.split()[overlap:]).strip()
                break
        if not text:
            continue

        if out and text == out[-1]["text"]:
            out[-1]["end"] = max(out[-1]["end"], end)
        else:
            out.append({"start": round(start, 3), "end": round(end, 3), "text": text})
        recent.append(text)
        if len(recent) > 3:
            recent.pop(0)
    return out


def merge_fragments(
    segments: list[dict[str, Any]], max_chars: int = 220, max_gap: float = 1.6
) -> list[dict[str, Any]]:
    """Glue tiny ASR fragments into sentence-sized segments."""
    out: list[dict[str, Any]] = []
    for segment in segments:
        if not out:
            out.append(dict(segment))
            continue
        previous = out[-1]
        gap = float(segment["start"]) - float(previous["end"])
        joined_length = len(previous["text"]) + 1 + len(segment["text"])
        ends_sentence = previous["text"].endswith(SENTENCE_END)
        if gap <= max_gap and joined_length <= max_chars and not ends_sentence:
            previous["text"] = f"{previous['text']} {segment['text']}".strip()
            previous["end"] = max(float(previous["end"]), float(segment["end"]))
        else:
            out.append(dict(segment))
    return out


def clean_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for segment in dedupe_segments(segments):
        text = segment["text"].strip()
        if not text or NON_SPEECH_RE.match(text):
            continue
        cleaned.append(segment)
    return merge_fragments(cleaned)


def format_seconds(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def render_clean_text(segments: list[dict[str, Any]], marker_interval: float = 45.0) -> str:
    """One paragraph with sparse ``[mm:ss]`` anchors, good for an LLM."""
    parts: list[str] = []
    next_marker = 0.0
    for segment in segments:
        text = segment["text"].strip()
        if not text:
            continue
        start = float(segment["start"])
        if start >= next_marker or not parts:
            if parts:
                parts.append("\n\n")
            parts.append(f"[{format_seconds(start)}] {text}")
            next_marker = start + marker_interval
        else:
            parts.append(" " + text)
    rendered = "".join(parts).strip()
    return rendered + "\n" if rendered else ""
