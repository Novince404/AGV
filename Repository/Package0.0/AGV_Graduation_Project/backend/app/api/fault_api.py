from fastapi import APIRouter
from pydantic import BaseModel

from app.api.agv_api import agv_list
from app.api.task_api import task_list
from app.utils.api_error import raise_api_error
from app.utils.fault_state import create_fault_event, list_fault_events, resolve_fault_event
from app.utils.task_chain import mark_task_blocked


router = APIRouter(prefix="/fault", tags=["Fault"])


class FaultReportRequest(BaseModel):
    agv_id: int
    fault_type: str
    severity: str = "medium"
    message: str | None = None
    reported_by: str = "system"


def _find_agv(agv_id: int):
    agv = next((item for item in agv_list if item.id == agv_id), None)
    if not agv:
        raise_api_error(404, "agv_not_found")
    return agv


def _find_active_task_for_agv(agv_id: int):
    return next(
        (
            task
            for task in task_list
            if task.agv_id == agv_id and task.status in {"assigned", "running"}
        ),
        None,
    )


@router.post("/report")
def report_fault(req: FaultReportRequest):
    agv = _find_agv(req.agv_id)
    task = _find_active_task_for_agv(req.agv_id)
    event = create_fault_event(
        agv_id=req.agv_id,
        fault_type=req.fault_type,
        severity=req.severity,
        message=req.message,
        reported_by=req.reported_by,
        event_type="fault",
        task_id=task.id if task else agv.task_id,
    )

    agv.status = "fault"
    agv.task_id = None
    agv.active_fault_event_id = event.id

    if task:
        mark_task_blocked(task, "agv_fault_stop", task.dispatch_algorithm)

    return {
        "message": "Fault reported",
        "event": event,
        "agv": agv,
        "task": task,
    }


@router.get("/list")
def get_fault_list(status: str | None = None):
    return list_fault_events(status)


@router.post("/{event_id}/resolve")
def resolve_fault(event_id: int):
    event = resolve_fault_event(event_id)
    if not event:
        raise_api_error(404, "fault_event_not_found")

    agv = next((item for item in agv_list if item.id == event.agv_id), None)
    if agv and event.event_type == "fault":
        still_open_faults = [
            item
            for item in list_fault_events("open")
            if item.agv_id == agv.id and item.event_type == "fault"
        ]
        if not still_open_faults and agv.status == "fault":
            agv.status = "idle"
            agv.active_fault_event_id = None

    return {"message": "Fault resolved", "event": event, "agv": agv}
