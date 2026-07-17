from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from app.core.auth_capabilities import normalize_role


DEFAULT_SCOPE_KEY = "guest:default"
SCOPE_ID_DELIMITER = "::"

_current_scope_key: ContextVar[str] = ContextVar("agv_current_scope_key", default=DEFAULT_SCOPE_KEY)


def normalize_scope_key(scope_key: str | None) -> str:
    raw = str(scope_key or "").strip()
    return raw or DEFAULT_SCOPE_KEY


def build_scope_key_from_actor(actor: dict | None) -> str:
    if not actor:
        return DEFAULT_SCOPE_KEY
    role = normalize_role(actor.get("role"))
    if role == "personal":
        user_id = str(actor.get("id") or actor.get("username") or "personal").strip()
        return normalize_scope_key(f"user:{user_id}")
    if role.startswith("enterprise_"):
        organization_id = str(actor.get("organization_id") or "").strip()
        if organization_id:
            return normalize_scope_key(f"organization:{organization_id}")
        user_id = str(actor.get("id") or actor.get("username") or "enterprise").strip()
        return normalize_scope_key(f"organization:user:{user_id}")
    if role == "platform_admin":
        user_id = str(actor.get("id") or actor.get("username") or "platform_admin").strip()
        return normalize_scope_key(f"platform:{user_id}")
    return DEFAULT_SCOPE_KEY


def get_current_scope_key() -> str:
    return normalize_scope_key(_current_scope_key.get())


def set_current_scope_key(scope_key: str | None) -> None:
    _current_scope_key.set(normalize_scope_key(scope_key))


@contextmanager
def use_scope(scope_key: str | None):
    normalized = normalize_scope_key(scope_key)
    token = _current_scope_key.set(normalized)
    try:
        yield normalized
    finally:
        _current_scope_key.reset(token)


def build_scoped_storage_id(public_id: str, scope_key: str | None = None) -> str:
    normalized_scope = normalize_scope_key(scope_key or get_current_scope_key())
    logical_id = str(public_id or "").strip()
    if not logical_id:
        return logical_id
    return f"{normalized_scope}{SCOPE_ID_DELIMITER}{logical_id}"


def get_scope_storage_prefix(scope_key: str | None = None) -> str:
    normalized_scope = normalize_scope_key(scope_key or get_current_scope_key())
    return f"{normalized_scope}{SCOPE_ID_DELIMITER}"


def extract_public_id(storage_id: str, scope_key: str | None = None) -> str:
    raw = str(storage_id or "").strip()
    normalized_scope = normalize_scope_key(scope_key or get_current_scope_key())
    prefix = f"{normalized_scope}{SCOPE_ID_DELIMITER}"
    if raw.startswith(prefix):
        return raw[len(prefix):]
    return raw


def is_scoped_storage_id(storage_id: str, scope_key: str | None = None) -> bool:
    raw = str(storage_id or "").strip()
    normalized_scope = normalize_scope_key(scope_key or get_current_scope_key())
    return raw.startswith(f"{normalized_scope}{SCOPE_ID_DELIMITER}")


def is_legacy_unscoped_storage_id(storage_id: str) -> bool:
    raw = str(storage_id or "").strip()
    if not raw:
        return False
    return SCOPE_ID_DELIMITER not in raw
