from pydantic import BaseModel

class AGV(BaseModel):
    id: int
    x: int
    y: int
    status: str
    task_id: int | None = None
    active_fault_event_id: int | None = None
