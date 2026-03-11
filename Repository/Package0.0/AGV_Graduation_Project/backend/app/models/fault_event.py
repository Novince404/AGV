from pydantic import BaseModel


class FaultEvent(BaseModel):
    id: int
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
