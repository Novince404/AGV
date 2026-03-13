from pydantic import BaseModel


class EmergencyStopRequest(BaseModel):
    message: str | None = None
    reported_by: str = "system"

