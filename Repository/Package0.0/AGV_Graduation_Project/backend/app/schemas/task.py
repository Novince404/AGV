from pydantic import BaseModel


class TaskStagePayload(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None


class TaskCreateRequest(BaseModel):
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    priority: int = 1
    stages: list[TaskStagePayload] | None = None
    dispatch_mode: str | None = None
    preferred_agv_id: int | None = None
    dispatch_origin_x: int | None = None
    dispatch_origin_y: int | None = None
    dispatch_algorithm: str | None = None
    dispatch_reason: str | None = None


class TaskImportItem(BaseModel):
    id: int | None = None
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    priority: int = 1
    stages: list[TaskStagePayload] | None = None
    dispatch_mode: str | None = None
    preferred_agv_id: int | None = None
    dispatch_origin_x: int | None = None
    dispatch_origin_y: int | None = None
    dispatch_algorithm: str | None = None
    dispatch_reason: str | None = None


class TaskImportRequest(BaseModel):
    tasks: list[TaskImportItem]

