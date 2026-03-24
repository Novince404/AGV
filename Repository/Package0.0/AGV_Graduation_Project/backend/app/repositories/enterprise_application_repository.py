"""Public enterprise-application repository facade."""

from __future__ import annotations

import logging

from app.repositories.memory import enterprise_application_store as _memory_store
from app.repositories.runtime import is_sql_backend

logger = logging.getLogger(__name__)
_warned_sql_fallback = False

_sql_store = None
if is_sql_backend():
    from app.repositories.sql import enterprise_application_store as _sql_store


def _call_store(method_name: str, *args):
    global _warned_sql_fallback
    if _sql_store is not None:
        try:
            return getattr(_sql_store, method_name)(*args)
        except Exception as exc:  # pragma: no cover - fallback path for broken SQL runtime
            if not _warned_sql_fallback:
                logger.warning("Enterprise-application SQL store failed, falling back to memory store: %s", exc)
                _warned_sql_fallback = True
    return getattr(_memory_store, method_name)(*args)


def list_enterprise_applications():
    return _call_store("list_enterprise_applications")


def get_enterprise_application_by_id(application_id: int):
    return _call_store("get_enterprise_application_by_id", application_id)


def get_enterprise_application_by_username(username: str):
    return _call_store("get_enterprise_application_by_username", username)


def get_enterprise_application_by_user_id(user_id: str):
    return _call_store("get_enterprise_application_by_user_id", user_id)


def get_next_enterprise_application_id():
    return _call_store("get_next_enterprise_application_id")


def upsert_enterprise_application(application):
    return _call_store("upsert_enterprise_application", application)


__all__ = [
    "get_enterprise_application_by_id",
    "get_enterprise_application_by_user_id",
    "get_enterprise_application_by_username",
    "get_next_enterprise_application_id",
    "list_enterprise_applications",
    "upsert_enterprise_application",
]
