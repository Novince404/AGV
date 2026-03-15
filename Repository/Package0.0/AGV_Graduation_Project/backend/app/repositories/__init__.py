"""Repository entrypoints for the A3 transition layer."""

from app.repositories.agv_repository import get_agv_by_id, get_first_idle_agv, list_agvs, list_idle_agvs
from app.repositories.fault_repository import (
    add_fault_event,
    get_fault_event_by_id,
    get_next_fault_event_id,
    list_fault_events_store,
    list_open_fault_events_for_agv,
)
from app.repositories.task_repository import (
    add_task,
    get_existing_task_ids,
    get_next_task_id,
    get_task_by_id,
    list_tasks,
    remove_task,
)

__all__ = [
    "add_task",
    "add_fault_event",
    "get_agv_by_id",
    "get_fault_event_by_id",
    "get_existing_task_ids",
    "get_first_idle_agv",
    "get_next_fault_event_id",
    "get_next_task_id",
    "get_task_by_id",
    "list_agvs",
    "list_fault_events_store",
    "list_idle_agvs",
    "list_open_fault_events_for_agv",
    "list_tasks",
    "remove_task",
]
