from app.models.tracked_model import TrackedModel


class FaultEvent(TrackedModel):
    id: int
    scope_key: str | None = None
    agv_id: int
    fault_type: str
    severity: str
    message: str | None = None
    event_type: str = "fault"
    status: str = "open"
    reported_at: str
    resolved_at: str | None = None
    reported_by: str = "system"
    task_id: int | None = None
