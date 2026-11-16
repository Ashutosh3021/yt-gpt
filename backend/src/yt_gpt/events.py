"""A tiny in-process pub/sub used by the SSE progress stream."""

from __future__ import annotations

import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=32)
        async with self._lock:
            self._subscribers[channel].add(queue)
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(channel)
            if subscribers:
                subscribers.discard(queue)
                if not subscribers:
                    self._subscribers.pop(channel, None)

    def publish(self, channel: str, message: str = "update") -> None:
        """Publish without awaiting; slow subscribers drop old messages."""
        for queue in list(self._subscribers.get(channel, ())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    pass
