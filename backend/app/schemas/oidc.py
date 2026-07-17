from __future__ import annotations

from pydantic import BaseModel, Field


class OIDCLinkReviewRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)


class OIDCRejectRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)
