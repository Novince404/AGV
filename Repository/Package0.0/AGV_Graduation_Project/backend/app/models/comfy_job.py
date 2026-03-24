from __future__ import annotations

from pydantic import Field

from app.models.tracked_model import TrackedModel


class ComfyRenderJob(TrackedModel):
    id: int
    source_type: str
    source_ref: str | None = None
    input_summary: dict = Field(default_factory=dict)
    workflow_payload: dict = Field(default_factory=dict)
    status: str
    created_by: str
    created_at: str
    completed_at: str | None = None
    asset_urls: list[str] = Field(default_factory=list)
    error_message: str | None = None
    prompt_id: str | None = None
