from pydantic import BaseModel


class ScheduleWithPathRequest(BaseModel):
    task_id: int | None = None
    agv_id: int | None = None
    schedule_mode: str | None = None
    algorithm: str = "simple"
    grid_cols: int = 10
    grid_rows: int = 8


class CompareStagePayload(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None


class PathCompareRequest(BaseModel):
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    stages: list[CompareStagePayload] | None = None
    grid_cols: int = 10
    grid_rows: int = 8


class RetryBlockedTaskRequest(BaseModel):
    algorithm: str = "astar"
    grid_cols: int = 10
    grid_rows: int = 8


class RecoverBlockedTaskRequest(BaseModel):
    mode: str = "reassign"  # bound / reassign
    algorithm: str | None = None
    grid_cols: int = 10
    grid_rows: int = 8
