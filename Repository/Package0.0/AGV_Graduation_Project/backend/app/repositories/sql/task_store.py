"""Temporary SQL task adapter.

Current behavior intentionally proxies to the memory implementation to keep
demo/runtime behavior unchanged during the A3 repository migration.
"""

from app.repositories.memory.task_store import (
    add_task,
    get_existing_task_ids,
    get_next_task_id,
    get_task_by_id,
    list_tasks,
    remove_task,
    task_list,
)

__all__ = [
    "add_task",
    "get_existing_task_ids",
    "get_next_task_id",
    "get_task_by_id",
    "list_tasks",
    "remove_task",
    "task_list",
]
