from pydantic import BaseModel


class FaultReportRequest(BaseModel):
    agv_id: int
    fault_type: str
    severity: str = "medium"
    message: str | None = None
    reported_by: str = "system"

