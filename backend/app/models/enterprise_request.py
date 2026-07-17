from __future__ import annotations

from pydantic import BaseModel


class EnterpriseRequest(BaseModel):
    id: int
    organization_id: str
    organization_name: str | None = None
    category: str
    title: str
    content: str
    submitter_id: str
    submitter_username: str
    submitter_display_name: str
    submitter_role: str
    target_user_id: str
    target_username: str
    target_display_name: str
    target_role: str
    status: str = "open"
    response_note: str | None = None
    created_at: str
    updated_at: str
