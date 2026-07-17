from __future__ import annotations

from app.core.data_scope import get_current_scope_key
from app.models.fault_event import FaultEvent


_fault_event_lists_by_scope: dict[str, list[FaultEvent]] = {}
_next_id = 0


def _current_scope() -> str:
    return get_current_scope_key()


def _scope_cache(scope_key: str | None = None) -> list[FaultEvent]:
    normalized_scope = str(scope_key or _current_scope())
    return _fault_event_lists_by_scope.setdefault(normalized_scope, [])


def list_fault_events_store() -> list[FaultEvent]:
    return _scope_cache()


def get_fault_event_by_id(event_id: int) -> FaultEvent | None:
    return next((event for event in _scope_cache() if event.id == event_id), None)


def get_next_fault_event_id() -> int:
    return _next_id + 1


def add_fault_event(event: FaultEvent) -> FaultEvent:
    global _next_id
    if not event.id:
        _next_id += 1
        event.id = _next_id
    else:
        _next_id = max(_next_id, int(event.id))
    event.scope_key = event.scope_key or _current_scope()
    _scope_cache().append(event)
    return event


def list_open_fault_events_for_agv(agv_id: int, event_type: str | None = None) -> list[FaultEvent]:
    return [
        event
        for event in _scope_cache()
        if event.agv_id == agv_id
        and event.status == "open"
        and (event_type is None or event.event_type == event_type)
    ]
