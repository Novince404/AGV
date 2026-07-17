from __future__ import annotations

from datetime import datetime

from app.core.data_scope import get_current_scope_key
from app.models.task import Task


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


task_list = [
    Task(
        id=1,
        start_x=1,
        start_y=1,
        end_x=5,
        end_y=5,
        priority=3,
        status="pending",
        created_at=now_iso(),
    ),
    Task(
        id=2,
        start_x=2,
        start_y=3,
        end_x=6,
        end_y=2,
        priority=2,
        status="pending",
        created_at=now_iso(),
    ),
]

_task_lists_by_scope: dict[str, list[Task]] = {}
_next_id = max((item.id for item in task_list), default=0)


def _current_scope() -> str:
    return get_current_scope_key()


def _clone_default_tasks(scope_key: str) -> list[Task]:
    return [Task(**{**item.model_dump(), "scope_key": scope_key}) for item in task_list]


def _scope_cache(scope_key: str | None = None) -> list[Task]:
    normalized_scope = str(scope_key or _current_scope())
    if normalized_scope not in _task_lists_by_scope:
        _task_lists_by_scope[normalized_scope] = _clone_default_tasks(normalized_scope)
    return _task_lists_by_scope[normalized_scope]


def list_tasks() -> list[Task]:
    return _scope_cache()


def get_task_by_id(task_id: int) -> Task | None:
    return next((task for task in _scope_cache() if task.id == task_id), None)


def get_next_task_id() -> int:
    return _next_id + 1


def get_existing_task_ids() -> set[int]:
    return {task.id for task in _scope_cache()}


def add_task(task: Task) -> Task:
    global _next_id
    if not task.id:
        _next_id += 1
        task.id = _next_id
    else:
        _next_id = max(_next_id, int(task.id))
    task.scope_key = task.scope_key or _current_scope()
    _scope_cache().append(task)
    return task


def remove_task(task: Task) -> None:
    cache = _scope_cache()
    cache[:] = [item for item in cache if item.id != task.id]
