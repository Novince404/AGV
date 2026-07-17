from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from itertools import count
from typing import AsyncIterator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    id: str
    type: str
    occurred_at: str
    scope_key: str
    entity_type: str
    entity_id: str | None
    correlation_id: str | None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_sse(self) -> str:
        payload = json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))
        return f"id: {self.id}\nevent: {self.type}\ndata: {payload}\n\n"


class EventBroker:
    """Process-local replayable event broker used until the durable outbox is enabled."""

    def __init__(self, history_size: int = 1000) -> None:
        self._history: deque[RuntimeEvent] = deque(maxlen=max(history_size, 100))
        self._subscribers: set[asyncio.Queue[RuntimeEvent]] = set()
        self._lock = threading.RLock()
        self._ids = count(1)

    def publish(
        self,
        event_type: str,
        *,
        scope_key: str = "system",
        entity_type: str = "system",
        entity_id: str | int | None = None,
        correlation_id: str | None = None,
        data: dict | None = None,
    ) -> RuntimeEvent:
        event = RuntimeEvent(
            id=str(next(self._ids)),
            type=str(event_type),
            occurred_at=_now_iso(),
            scope_key=str(scope_key),
            entity_type=str(entity_type),
            entity_id=None if entity_id is None else str(entity_id),
            correlation_id=correlation_id,
            data=dict(data or {}),
        )
        with self._lock:
            self._history.append(event)
            subscribers = tuple(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
        return event

    def publish_event(self, event: RuntimeEvent) -> RuntimeEvent:
        """Publish an event whose durable identifier was assigned by the database."""
        with self._lock:
            if not any(item.id == event.id and item.type == event.type for item in self._history):
                self._history.append(event)
            subscribers = tuple(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except asyncio.QueueEmpty:
                    pass
        return event

    def replay_after(self, event_id: str | None) -> list[RuntimeEvent]:
        with self._lock:
            history = list(self._history)
        if not event_id:
            return history[-50:]
        try:
            marker = int(event_id)
        except (TypeError, ValueError):
            return history[-50:]
        return [event for event in history if int(event.id) > marker]

    async def subscribe(self, last_event_id: str | None = None) -> AsyncIterator[RuntimeEvent | None]:
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=200)
        with self._lock:
            self._subscribers.add(queue)
        try:
            for event in self.replay_after(last_event_id):
                yield event
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield None
        finally:
            with self._lock:
                self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


event_broker = EventBroker()
