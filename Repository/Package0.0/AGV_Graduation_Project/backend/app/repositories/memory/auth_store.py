from __future__ import annotations

from app.core.auth_capabilities import normalize_role
from app.core.auth_defaults import build_default_auth_users
from app.models.auth import AuthSession, AuthUser


users: list[AuthUser] = build_default_auth_users()
sessions: dict[str, AuthSession] = {}


def list_users() -> list[AuthUser]:
    return users


def get_user_by_id(user_id: str) -> AuthUser | None:
    return next((user for user in users if user.id == user_id), None)


def get_user_by_username(username: str) -> AuthUser | None:
    normalized = str(username or "").strip().casefold()
    return next((user for user in users if user.username.casefold() == normalized), None)


def upsert_user(user: AuthUser) -> AuthUser:
    user.role = normalize_role(user.role)
    existing = get_user_by_id(user.id)
    if existing is None:
        users.append(user)
        return user
    users[users.index(existing)] = user
    return user


def get_session_by_token(token: str) -> AuthSession | None:
    return sessions.get(str(token or ""))


def upsert_session(session: AuthSession) -> AuthSession:
    sessions[session.token] = session
    return session


def remove_session(token: str) -> None:
    sessions.pop(str(token or ""), None)


def remove_sessions_for_user(user_id: str) -> None:
    normalized_user_id = str(user_id or "")
    for token in [token for token, session in sessions.items() if session.user_id == normalized_user_id]:
        sessions.pop(token, None)
