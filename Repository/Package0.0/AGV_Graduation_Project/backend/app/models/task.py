from pydantic import BaseModel

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
