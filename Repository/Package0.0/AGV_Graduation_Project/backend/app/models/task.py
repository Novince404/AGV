from pydantic import BaseModel


class TaskStage(BaseModel):
    index: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None
    path_to_start: list[dict] | None = None
    path_to_end: list[dict] | None = None
    path_length_to_start: int | None = None
    path_length_to_end: int | None = None
    started_at: str | None = None
    finished_at: str | None = None


class Task(BaseModel):
    id: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    priority: int = 1
    status: str
    agv_id: int | None = None
    created_at: str | None = None
    assigned_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    path_to_start: list[dict] | None = None
    path_to_end: list[dict] | None = None
    path_length_to_start: int | None = None
    path_length_to_end: int | None = None
    dispatch_mode: str | None = None
    dispatch_distance: int | None = None
    dispatch_algorithm: str | None = None
    dispatch_reason: str | None = None
    current_stage_index: int = 0
    total_stages: int = 1
    overall_start_x: int | None = None
    overall_start_y: int | None = None
    overall_end_x: int | None = None
    overall_end_y: int | None = None
    stages: list[TaskStage] | None = None
