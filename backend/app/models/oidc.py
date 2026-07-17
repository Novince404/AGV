from __future__ import annotations

from pydantic import BaseModel


class OIDCIdentity(BaseModel):
    id: int | None = None
    issuer: str
    subject: str
    user_id: str
    email: str | None = None
    created_at: str


class OIDCLinkRequest(BaseModel):
    id: str
    issuer: str
    subject: str
    email: str | None = None
    display_name: str | None = None
    status: str = "pending"
    requested_at: str
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    user_id: str | None = None
