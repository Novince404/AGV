"""Public task-template repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import template_store as _store
else:
    from app.repositories.memory import template_store as _store


# Keep the legacy export without triggering a database read at import time.
task_template_list = getattr(_store, "task_template_list", [])


def list_task_templates():
    return _store.list_task_templates()


def get_task_template_by_id(template_id: str):
    return _store.get_task_template_by_id(template_id)


def upsert_task_template(template):
    return _store.upsert_task_template(template)


def remove_task_template(template_id: str):
    return _store.remove_task_template(template_id)


__all__ = [
    "get_task_template_by_id",
    "list_task_templates",
    "remove_task_template",
    "task_template_list",
    "upsert_task_template",
]
