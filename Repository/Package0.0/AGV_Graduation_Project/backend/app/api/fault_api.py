from fastapi import APIRouter

from app.services import fault_service
from app.schemas.fault import FaultReportRequest


router = APIRouter(prefix="/fault", tags=["Fault"])


@router.post("/report")
def report_fault(req: FaultReportRequest):
    return fault_service.report_fault(
        req.agv_id,
        req.fault_type,
        req.severity,
        req.message,
        req.reported_by,
    )


@router.get("/list")
def get_fault_list(status: str | None = None):
    return fault_service.get_fault_list(status)


@router.post("/{event_id}/resolve")
def resolve_fault(event_id: int):
    return fault_service.resolve_fault(event_id)
