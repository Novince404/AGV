"""Public enterprise-request repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import enterprise_request_store as _store
else:
    from app.repositories.memory import enterprise_request_store as _store


enterprise_request_list = _store.enterprise_requests if hasattr(_store, "enterprise_requests") else None


def list_enterprise_requests():
    return _store.list_enterprise_requests()


def get_enterprise_request_by_id(request_id: int):
    return _store.get_enterprise_request_by_id(request_id)


def get_next_enterprise_request_id():
    return _store.get_next_enterprise_request_id()


def upsert_enterprise_request(item):
    return _store.upsert_enterprise_request(item)


__all__ = [
    "enterprise_request_list",
    "get_enterprise_request_by_id",
    "get_next_enterprise_request_id",
    "list_enterprise_requests",
    "upsert_enterprise_request",
]
