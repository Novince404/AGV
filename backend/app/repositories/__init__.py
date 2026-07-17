"""Repository entry points without import-time storage side effects.

Alembic imports ``sql_models`` through this package.  Importing concrete
repositories here used to seed data and run schema checks before a migration
could create the schema.  Public convenience exports remain available lazily
for older callers, while migration tooling can load model metadata safely.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "add_task": ("app.repositories.task_repository", "add_task"),
    "add_fault_event": ("app.repositories.fault_repository", "add_fault_event"),
    "get_agv_by_id": ("app.repositories.agv_repository", "get_agv_by_id"),
    "get_fault_event_by_id": ("app.repositories.fault_repository", "get_fault_event_by_id"),
    "get_existing_task_ids": ("app.repositories.task_repository", "get_existing_task_ids"),
    "get_first_idle_agv": ("app.repositories.agv_repository", "get_first_idle_agv"),
    "get_next_fault_event_id": ("app.repositories.fault_repository", "get_next_fault_event_id"),
    "get_next_task_id": ("app.repositories.task_repository", "get_next_task_id"),
    "get_task_by_id": ("app.repositories.task_repository", "get_task_by_id"),
    "get_layout_state": ("app.repositories.map_repository", "get_layout_state"),
    "get_map_preset_by_key": ("app.repositories.map_preset_repository", "get_map_preset_by_key"),
    "list_agvs": ("app.repositories.agv_repository", "list_agvs"),
    "list_fault_events_store": ("app.repositories.fault_repository", "list_fault_events_store"),
    "list_idle_agvs": ("app.repositories.agv_repository", "list_idle_agvs"),
    "list_map_presets": ("app.repositories.map_preset_repository", "list_map_presets"),
    "list_open_fault_events_for_agv": ("app.repositories.fault_repository", "list_open_fault_events_for_agv"),
    "list_tasks": ("app.repositories.task_repository", "list_tasks"),
    "remove_task": ("app.repositories.task_repository", "remove_task"),
    "remove_map_preset": ("app.repositories.map_preset_repository", "remove_map_preset"),
    "set_layout_state": ("app.repositories.map_repository", "set_layout_state"),
    "upsert_map_preset": ("app.repositories.map_preset_repository", "upsert_map_preset"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = sorted(_EXPORTS)
