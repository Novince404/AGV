"""Temporary SQL fault adapter.

Current behavior intentionally proxies to the memory implementation to keep
demo/runtime behavior unchanged during the A3 repository migration.
"""

from app.repositories.memory.fault_store import (
    add_fault_event,
    fault_event_list,
    get_fault_event_by_id,
    get_next_fault_event_id,
    list_fault_events_store,
    list_open_fault_events_for_agv,
)

__all__ = [
    "add_fault_event",
    "fault_event_list",
    "get_fault_event_by_id",
    "get_next_fault_event_id",
    "list_fault_events_store",
    "list_open_fault_events_for_agv",
]
