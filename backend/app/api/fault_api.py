from fastapi import APIRouter, Request

from app.services import auth_service, fault_service
from app.schemas.fault import FaultReportRequest


router = APIRouter(prefix="/fault", tags=["Fault"])


@router.post("/report")
def report_fault(req: FaultReportRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "fault.write")
    return fault_service.report_fault(
        req.agv_id,
        req.fault_type,
        req.severity,
        req.message,
        actor.get("display_name") or req.reported_by,
        actor,
    )


@router.get("/list")
def get_fault_list(status: str | None = None):
    return fault_service.get_fault_list(status)


@router.post("/{event_id}/resolve")
def resolve_fault(event_id: int, request: Request):
    actor = auth_service.require_actor_capability(request, "fault.write")
    return fault_service.resolve_fault(event_id, actor)
