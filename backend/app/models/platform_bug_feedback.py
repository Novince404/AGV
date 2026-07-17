from __future__ import annotations

from pydantic import BaseModel


class PlatformBugFeedback(BaseModel):
    id: int
    category: str
    title: str
    content: str
    submitter_id: str
    submitter_username: str
    submitter_display_name: str
    submitter_role: str
    status: str = "open"
    response_note: str | None = None
    created_at: str
    updated_at: str
