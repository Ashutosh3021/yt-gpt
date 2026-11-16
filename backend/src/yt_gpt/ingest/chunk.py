"""Sentence-aware transcript chunking with timestamp anchors."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from ..util import estimate_tokens

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def _sentence_units(segments: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end < start:
            end = start
        sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        if len(sentences) <= 1:
            yield {"start": start, "end": end, "text": text}
            continue
        total_chars = sum(len(sentence) for sentence in sentences) or 1
        cursor = start
        duration = max(0.0, end - start)
        for index, sentence in enumerate(sentences):
            share = len(sentence) / total_chars
            sentence_end = end if index == len(sentences) - 1 else cursor + duration * share
            yield {"start": cursor, "end": sentence_end, "text": sentence}
            cursor = sentence_end


def _tail_overlap(units: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
    tail: list[dict[str, Any]] = []
    tokens = 0
    for unit in reversed(units):
        unit_tokens = estimate_tokens(unit["text"])
        if tail and tokens + unit_tokens > max_tokens:
            break
        tail.insert(0, unit)
        tokens += unit_tokens
    return tail


def chunk_segments(
    video_id: str,
    segments: list[dict[str, Any]],
    *,
    target_tokens: int = 450,
    max_tokens: int = 650,
    min_tokens: int = 200,
    overlap_tokens: int = 50,
) -> list[dict[str, Any]]:
    units = list(_sentence_units(segments))
    if not units:
        return []

    chunks: list[dict[str, Any]] = []
    buffer: list[dict[str, Any]] = []
    buffer_tokens = 0

    def flush() -> None:
        nonlocal buffer, buffer_tokens
        if not buffer:
            return
        text = " ".join(unit["text"] for unit in buffer).strip()
        if not text:
            buffer, buffer_tokens = [], 0
            return
        index = len(chunks)
        chunks.append(
            {
                "id": f"{video_id}:{index:04d}",
                "video_id": video_id,
                "start": round(float(buffer[0]["start"]), 3),
                "end": round(float(buffer[-1]["end"]), 3),
                "text": text,
                "tokens": estimate_tokens(text),
            }
        )
        buffer = _tail_overlap(buffer, overlap_tokens)
        buffer_tokens = sum(estimate_tokens(unit["text"]) for unit in buffer)

    for unit in units:
        unit_tokens = estimate_tokens(unit["text"])
        if buffer and buffer_tokens >= target_tokens and buffer_tokens + unit_tokens > max_tokens:
            flush()
        buffer.append(unit)
        buffer_tokens += unit_tokens
        if buffer_tokens >= target_tokens:
            flush()
    if buffer and (buffer_tokens >= min_tokens or not chunks or buffer[-1]["end"] > chunks[-1]["end"]):
        flush()
    return chunks
