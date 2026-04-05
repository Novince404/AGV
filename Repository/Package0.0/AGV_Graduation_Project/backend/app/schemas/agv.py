from pydantic import BaseModel


class EmergencyStopRequest(BaseModel):
    message: str | None = None
    reported_by: str = "system"


class AgvCreateRequest(BaseModel):
    x: int
    y: int

