from __future__ import annotations

from app.repositories.agv_repository import agv_list, get_agv_by_id, list_agvs
from app.repositories.task_repository import list_tasks
from app.services.operation_audit_service import record_operation_audit
from app.utils.api_error import raise_api_error
from app.utils.fault_state import (
    create_fault_event,
    get_open_fault_events_for_agv,
    resolve_latest_open_event_for_agv,
)
from app.utils.task_chain import mark_task_blocked


#
# Keep compatibility for modules that still import `agv_service.agv_list`
# during the A3 transition. New code should prefer repository helpers.
#

def _find_agv(agv_id: int):
    agv = get_agv_by_id(agv_id)
    if not agv:
        raise_api_error(404, "agv_not_found")
    return agv


def _find_active_task_for_agv(agv_id: int):
    return next(
        (
            task
            for task in list_tasks()
            if task.agv_id == agv_id and task.status in {"assigned", "running"}
        ),
        None,
    )


def _assert_agv_can_enter_maintenance(agv):
    if agv.status in {"running", "relocating"}:
        raise_api_error(400, "agv_busy_for_maintenance")


def get_agvs():
    return list_agvs()


def emergency_stop_agv(
    agv_id: int,
    message: str | None = None,
    reported_by: str = "system",
    actor: dict | None = None,
):
    agv = _find_agv(agv_id)
    if agv.status == "emergency_stop":
        return {"message": "AGV already emergency stopped", "agv": agv, "task": None, "event": None}

    task = _find_active_task_for_agv(agv_id)
    event = create_fault_event(
        agv_id=agv.id,
        fault_type="emergency_stop",
        severity="critical",
        message=message,
        reported_by=str(actor.get("display_name") or actor.get("username") or reported_by) if actor else reported_by,
        event_type="emergency_stop",
        task_id=task.id if task else agv.task_id,
    )

    agv.active_fault_event_id = event.id
    agv.status = "emergency_stop"
    agv.task_id = None
    agv.clear_motion(motion_state="emergency_stop")

    if task:
        task.preferred_agv_id = agv.id
        mark_task_blocked(task, "recover_required_emergency_stop", task.dispatch_algorithm)

    record_operation_audit(
        "agv",
        agv.id,
        "emergency_stop",
        actor,
        {
            "task_id": task.id if task else None,
            "fault_event_id": event.id,
        },
    )

    return {
        "message": "AGV emergency stopped",
        "agv": agv,
        "task": task,
        "event": event,
    }


def resume_agv(agv_id: int, actor: dict | None = None):
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
    agv.clear_motion()
    record_operation_audit(
        "agv",
        agv.id,
        "resume",
        actor,
        {
            "resolved_event_id": getattr(resolved_event, "id", None),
        },
    )
    return {
        "message": "AGV resumed",
        "agv": agv,
        "event": resolved_event,
    }


def move_agv_to_maintenance(agv_id: int, actor: dict | None = None):
    agv = _find_agv(agv_id)
    if agv.status == "maintenance":
        return {"message": "AGV already in maintenance", "agv": agv}

    _assert_agv_can_enter_maintenance(agv)
    agv.status = "maintenance"
    agv.task_id = None
    agv.clear_motion(motion_state="maintenance")
    record_operation_audit("agv", agv.id, "to_maintenance", actor)
    return {"message": "AGV moved to maintenance", "agv": agv}


def return_agv_to_service(agv_id: int, actor: dict | None = None):
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
    agv.clear_motion()
    record_operation_audit("agv", agv.id, "return_to_service", actor)
    return {"message": "AGV returned to service", "agv": agv}
