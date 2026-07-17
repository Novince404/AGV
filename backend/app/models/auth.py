from __future__ import annotations

from pydantic import BaseModel


class AuthUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    password_hash: str
    must_change_password: bool = False
    active: bool = True
    builtin: bool = True
    account_status: str = "approved"
    organization_id: str | None = None
    organization_name: str | None = None
    suspension_reason: str | None = None
    suspension_note: str | None = None
    suspended_at: str | None = None
    suspended_until: str | None = None
    suspended_by: str | None = None
    deactivated_at: str | None = None
    deactivated_by: str | None = None
    created_at: str | None = None
    last_login_at: str | None = None
    governance_updated_at: str | None = None


class AuthSession(BaseModel):
    token: str
    user_id: str
    created_at: int
    expires_at: int
    last_seen_at: int
