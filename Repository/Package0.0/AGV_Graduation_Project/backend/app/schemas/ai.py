from pydantic import BaseModel, Field


class ComfyRenderRequest(BaseModel):
    source_type: str
    source_ref: str | None = None
    input_payload: dict = Field(default_factory=dict)
    input_summary: dict = Field(default_factory=dict)
    prompt_text: str | None = None
    workflow_payload: dict = Field(default_factory=dict)
