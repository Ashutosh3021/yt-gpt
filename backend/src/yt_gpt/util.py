"""Small shared helpers used across the backend.

Everything here is deliberately dependency-free so it stays cheap to import.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def iso_from_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically: temp file, fsync, os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


_SLUG_STRIP = re.compile(r"[^\w\s-]", re.UNICODE)
_SLUG_SPACE = re.compile(r"[\s_]+")


def slugify(value: str, *, fallback: str = "workspace", max_len: int = 48) -> str:
    normalised = unicodedata.normalize("NFKD", value or "")
    normalised = normalised.encode("ascii", "ignore").decode("ascii")
    normalised = _SLUG_STRIP.sub("", normalised.lower())
    normalised = _SLUG_SPACE.sub("-", normalised.strip())
    normalised = re.sub(r"-+", "-", normalised).strip("-")
    return (normalised[:max_len] or fallback).strip("-") or fallback


def safe_child(root: Path, *parts: str) -> Path:
    """Resolve *parts* under *root* and refuse traversal."""

    root_resolved = root.resolve()
    for part in parts:
        if not part:
            raise ValueError("empty path segment")
        if part in {".", ".."} or "/" in part or "\\" in part or Path(part).is_absolute():
            raise ValueError(f"unsafe path segment: {part!r}")
    candidate = root_resolved.joinpath(*parts).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("path escapes its root")
    return candidate


def estimate_tokens(text: str) -> int:
    """Cheap cross-provider token estimate (about 4 characters per token)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def format_seconds(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_seconds(value: str | int | float) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value).strip()
    if ":" in text:
        total = 0
        for part in text.split(":"):
            total = total * 60 + int(float(part or 0))
        return max(0, total)
    return max(0, int(float(text or 0)))


def truncate(text: str, limit: int, suffix: str = "…") -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(suffix))].rstrip() + suffix


def ensure_private(path: Path) -> None:
    """Best-effort 0600 for secret files on POSIX."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
