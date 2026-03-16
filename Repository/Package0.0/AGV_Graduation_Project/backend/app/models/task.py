from app.models.tracked_model import TrackedModel


class TaskStage(TrackedModel):
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


class Task(TrackedModel):
    id: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    priority: int = 1
    status: str
    agv_id: int | None = None
    preferred_agv_id: int | None = None
    dispatch_origin_x: int | None = None
    dispatch_origin_y: int | None = None
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
    cell_wait_retry_count: int = 0
    cell_wait_retry_budget: int = 1
    current_stage_index: int = 0
    total_stages: int = 1
    overall_start_x: int | None = None
    overall_start_y: int | None = None
    overall_end_x: int | None = None
    overall_end_y: int | None = None
    stages: list[TaskStage] | None = None

    def bind_on_change(self, callback):
        super().bind_on_change(callback)
        self._bind_stage_callbacks()
        return self

    def _bind_stage_callbacks(self):
        if not self.stages:
            return
        for stage in self.stages:
            if hasattr(stage, "bind_on_change"):
                stage.bind_on_change(self._notify_change)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name == "stages":
            self._bind_stage_callbacks()
