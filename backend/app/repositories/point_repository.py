"""Public point-library repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import point_store as _store
else:
    from app.repositories.memory import point_store as _store


# Keep the legacy export without triggering a database read at import time.
point_library = getattr(_store, "point_library", [])


def list_points():
    return _store.list_points()


def get_point_by_id(point_id: str):
    return _store.get_point_by_id(point_id)


def upsert_point(point):
    return _store.upsert_point(point)


def remove_point(point_id: str):
    return _store.remove_point(point_id)


__all__ = [
    "get_point_by_id",
    "list_points",
    "point_library",
    "remove_point",
    "upsert_point",
]
