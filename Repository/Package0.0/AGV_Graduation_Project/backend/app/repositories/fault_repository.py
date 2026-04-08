"""Public fault repository facade.

This facade is the stable import target for service/utils layers.
The concrete implementation is selected by backend runtime mode.
"""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import fault_store as _store
else:
    from app.repositories.memory import fault_store as _store


fault_event_list = getattr(_store, "fault_event_list", _store.list_fault_events_store())


def list_fault_events_store():
    return _store.list_fault_events_store()


def get_fault_event_by_id(event_id: int):
    return _store.get_fault_event_by_id(event_id)


def get_next_fault_event_id():
    return _store.get_next_fault_event_id()


def add_fault_event(event):
    return _store.add_fault_event(event)


def list_open_fault_events_for_agv(agv_id: int, event_type: str | None = None):
    return _store.list_open_fault_events_for_agv(agv_id, event_type)


__all__ = [
    "add_fault_event",
    "fault_event_list",
    "get_fault_event_by_id",
    "get_next_fault_event_id",
    "list_fault_events_store",
    "list_open_fault_events_for_agv",
]
