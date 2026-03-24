from pydantic import BaseModel, Field


class ComfyRenderRequest(BaseModel):
    source_type: str
    source_ref: str | None = None
    input_payload: dict = Field(default_factory=dict)
    input_summary: dict = Field(default_factory=dict)
    prompt_text: str | None = None
    workflow_payload: dict = Field(default_factory=dict)


class ComfyWorkflowTemplateUpsertRequest(BaseModel):
    id: str | None = None
    name: str
    source_type: str = "custom_json"
    source_ref: str | None = None
    checkpoint_name: str | None = None
    workflow_preset: str = "preview"
    prompt_style: str = "report"
    prompt_text: str = ""
    input_json_text: str = ""
    workflow_json_text: str = ""
