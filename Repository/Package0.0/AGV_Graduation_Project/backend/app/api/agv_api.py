from fastapi import APIRouter
from pydantic import BaseModel

from app.models.agv import AGV
from app.utils.api_error import raise_api_error
from app.utils.fault_state import (
    create_fault_event,
    get_open_fault_events_for_agv,
    resolve_latest_open_event_for_agv,
)
from app.utils.task_chain import mark_task_blocked

router = APIRouter(prefix="/agv", tags=["AGV"])

# 模拟 AGV 数据，后续会迁移到数据库
agv_list = [
    AGV(id=1, x=2, y=3, status="idle"),
    AGV(id=2, x=5, y=7, status="idle"),
    AGV(id=3, x=1, y=4, status="idle"),
]


class EmergencyStopRequest(BaseModel):
    message: str | None = None
    reported_by: str = "system"


def _find_agv(agv_id: int):
    agv = next((item for item in agv_list if item.id == agv_id), None)
    if not agv:
        raise_api_error(404, "agv_not_found")
    return agv


def _find_active_task_for_agv(agv_id: int):
    from app.api.task_api import task_list

    return next(
        (
            task
            for task in task_list
            if task.agv_id == agv_id and task.status in {"assigned", "running"}
        ),
        None,
    )


@router.get("/list")
def get_agvs():
    return agv_list


def _assert_agv_can_enter_maintenance(agv: AGV):
    if agv.status in {"running", "relocating"}:
        raise_api_error(400, "agv_busy_for_maintenance")


@router.post("/{agv_id}/emergency-stop")
def emergency_stop_agv(agv_id: int, req: EmergencyStopRequest):
    agv = _find_agv(agv_id)
    if agv.status == "emergency_stop":
        return {"message": "AGV already emergency stopped", "agv": agv, "task": None, "event": None}

    task = _find_active_task_for_agv(agv_id)
    event = create_fault_event(
        agv_id=agv.id,
        fault_type="emergency_stop",
        severity="critical",
        message=req.message,
        reported_by=req.reported_by,
        event_type="emergency_stop",
        task_id=task.id if task else agv.task_id,
    )

    agv.active_fault_event_id = event.id
    agv.status = "emergency_stop"
    agv.task_id = None

    if task:
        # Keep the interrupted AGV binding so the task can be resumed on the same vehicle.
        task.preferred_agv_id = agv.id
        mark_task_blocked(task, "recover_required_emergency_stop", task.dispatch_algorithm)

    return {
        "message": "AGV emergency stopped",
        "agv": agv,
        "task": task,
        "event": event,
    }


@router.post("/{agv_id}/resume")
def resume_agv(agv_id: int):
    agv = _find_agv(agv_id)
    if agv.status != "emergency_stop":
        raise_api_error(400, "agv_not_emergency_stopped")

    active_faults = get_open_fault_events_for_agv(agv.id, "fault")
    if active_faults:
        raise_api_error(400, "agv_has_open_fault")

    resolved_event = resolve_latest_open_event_for_agv(agv.id, "emergency_stop")
    agv.status = "idle"
    agv.task_id = None
    agv.active_fault_event_id = None
    return {
        "message": "AGV resumed",
        "agv": agv,
        "event": resolved_event,
    }


@router.post("/{agv_id}/to-maintenance")
def move_agv_to_maintenance(agv_id: int):
    agv = _find_agv(agv_id)
    if agv.status == "maintenance":
        return {"message": "AGV already in maintenance", "agv": agv}

    _assert_agv_can_enter_maintenance(agv)
    agv.status = "maintenance"
    agv.task_id = None
    return {"message": "AGV moved to maintenance", "agv": agv}


@router.post("/{agv_id}/return-to-service")
def return_agv_to_service(agv_id: int):
    agv = _find_agv(agv_id)
    if agv.status != "maintenance":
        raise_api_error(400, "agv_not_in_maintenance")

    active_faults = get_open_fault_events_for_agv(agv.id, "fault")
    if active_faults:
        raise_api_error(400, "agv_has_open_fault")

    resolve_latest_open_event_for_agv(agv.id, "emergency_stop")
    agv.status = "idle"
    agv.task_id = None
    agv.active_fault_event_id = None
    return {"message": "AGV returned to service", "agv": agv}
