from pydantic import BaseModel, Field


class TaskTemplateStagePayload(BaseModel):
    index: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None


class TaskTemplateUpsertRequest(BaseModel):
    id: str = Field(min_length=1)
    priority: int = 1
    name_key: str | None = None
    custom_name: str | None = None
    custom: bool = True
    stages: list[TaskTemplateStagePayload]
