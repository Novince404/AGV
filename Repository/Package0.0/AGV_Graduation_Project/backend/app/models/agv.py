from app.models.tracked_model import TrackedModel


class AGV(TrackedModel):
    id: int
    x: int
    y: int
    status: str
    task_id: int | None = None
    active_fault_event_id: int | None = None
