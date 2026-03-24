from __future__ import annotations

from pydantic import Field

from app.models.tracked_model import TrackedModel


class ComfyWorkflowTemplate(TrackedModel):
    id: str
    name: str
    scope: str = "organization"
    organization_id: str | None = None
    created_by_id: str | None = None
    created_by: str
    source_type: str
    source_ref: str | None = None
    checkpoint_name: str | None = None
    workflow_preset: str = "preview"
    prompt_style: str = "report"
    prompt_text: str = ""
    input_json_text: str = ""
    workflow_json_text: str = ""
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
