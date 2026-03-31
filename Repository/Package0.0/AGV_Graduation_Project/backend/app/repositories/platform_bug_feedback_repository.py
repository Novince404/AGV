"""Public platform bug feedback repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import platform_bug_feedback_store as _store
else:
    from app.repositories.memory import platform_bug_feedback_store as _store


platform_bug_feedback_list = _store.platform_bug_feedback_items if hasattr(_store, "platform_bug_feedback_items") else None


def list_platform_bug_feedback():
    return _store.list_platform_bug_feedback()


def get_platform_bug_feedback_by_id(feedback_id: int):
    return _store.get_platform_bug_feedback_by_id(feedback_id)


def get_next_platform_bug_feedback_id():
    return _store.get_next_platform_bug_feedback_id()


def upsert_platform_bug_feedback(item):
    return _store.upsert_platform_bug_feedback(item)


__all__ = [
    "get_next_platform_bug_feedback_id",
    "get_platform_bug_feedback_by_id",
    "list_platform_bug_feedback",
    "platform_bug_feedback_list",
    "upsert_platform_bug_feedback",
]
