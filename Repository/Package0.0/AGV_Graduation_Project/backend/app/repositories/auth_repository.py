"""Public auth repository facade."""

from __future__ import annotations

import logging

from app.repositories.memory import auth_store as _memory_store
from app.repositories.runtime import is_sql_backend

logger = logging.getLogger(__name__)
_warned_sql_fallback = False

_sql_store = None
if is_sql_backend():
    from app.repositories.sql import auth_store as _sql_store


def _call_store(method_name: str, *args):
    global _warned_sql_fallback
    if _sql_store is not None:
        try:
            return getattr(_sql_store, method_name)(*args)
        except Exception as exc:  # pragma: no cover - fallback path for broken SQL runtime
            if not _warned_sql_fallback:
                logger.warning("Auth SQL store failed, falling back to memory store: %s", exc)
                _warned_sql_fallback = True
    return getattr(_memory_store, method_name)(*args)


def list_users():
    return _call_store("list_users")


def get_user_by_id(user_id: str):
    return _call_store("get_user_by_id", user_id)


def get_user_by_username(username: str):
    return _call_store("get_user_by_username", username)


def upsert_user(user):
    return _call_store("upsert_user", user)


def get_session_by_token(token: str):
    return _call_store("get_session_by_token", token)


def upsert_session(session):
    return _call_store("upsert_session", session)


def remove_session(token: str) -> None:
    _call_store("remove_session", token)


def remove_sessions_for_user(user_id: str) -> None:
    _call_store("remove_sessions_for_user", user_id)


__all__ = [
    "get_session_by_token",
    "get_user_by_id",
    "get_user_by_username",
    "list_users",
    "remove_session",
    "remove_sessions_for_user",
    "upsert_session",
    "upsert_user",
]
