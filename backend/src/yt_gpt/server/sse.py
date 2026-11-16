"""Server-sent event helpers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi.responses import StreamingResponse

from ..events import EventBus

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def sse(data: Any, event: str | None = None) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {payload}\n\n"


def sse_response(source: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(source, media_type="text/event-stream", headers=SSE_HEADERS)


async def workspace_events(bus: EventBus, channel: str) -> AsyncIterator[str]:
    queue = await bus.subscribe(channel)
    try:
        yield sse("update")
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            yield sse(message)
    finally:
        await bus.unsubscribe(channel, queue)
