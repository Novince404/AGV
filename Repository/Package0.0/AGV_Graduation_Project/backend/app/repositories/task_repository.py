"""Public task repository facade.

This facade is the stable import target for service/utils layers.
The concrete implementation is selected by backend runtime mode.
"""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import task_store as _store
else:
    from app.repositories.memory import task_store as _store


task_list = _store.task_list


def list_tasks():
    return _store.list_tasks()


def get_task_by_id(task_id: int):
    return _store.get_task_by_id(task_id)


def get_next_task_id():
    return _store.get_next_task_id()


def get_existing_task_ids():
    return _store.get_existing_task_ids()


def add_task(task):
    return _store.add_task(task)


def remove_task(task):
    return _store.remove_task(task)


__all__ = [
    "add_task",
    "get_existing_task_ids",
    "get_next_task_id",
    "get_task_by_id",
    "list_tasks",
    "remove_task",
    "task_list",
]
