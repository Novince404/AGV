from __future__ import annotations

from app.repositories.agv_repository import agv_list
from app.utils.api_error import raise_api_error
from app.utils.fault_state import (
    create_fault_event,
    get_open_fault_events_for_agv,
    resolve_latest_open_event_for_agv,
)
from app.utils.task_chain import mark_task_blocked


def _find_agv(agv_id: int):
    agv = next((item for item in agv_list if item.id == agv_id), None)
    if not agv:
        raise_api_error(404, "agv_not_found")
    return agv


def _find_active_task_for_agv(agv_id: int):
    from app.repositories.task_repository import task_list

    return next(
        (
            task
            for task in task_list
            if task.agv_id == agv_id and task.status in {"assigned", "running"}
        ),
        None,
    )


def _assert_agv_can_enter_maintenance(agv):
    if agv.status in {"running", "relocating"}:
        raise_api_error(400, "agv_busy_for_maintenance")


def get_agvs():
    return agv_list


def emergency_stop_agv(agv_id: int, message: str | None = None, reported_by: str = "system"):
    agv = _find_agv(agv_id)
    if agv.status == "emergency_stop":
        return {"message": "AGV already emergency stopped", "agv": agv, "task": None, "event": None}

    task = _find_active_task_for_agv(agv_id)
    event = create_fault_event(
        agv_id=agv.id,
        fault_type="emergency_stop",
        severity="critical",
        message=message,
        reported_by=reported_by,
        event_type="emergency_stop",
        task_id=task.id if task else agv.task_id,
    )

    agv.active_fault_event_id = event.id
    agv.status = "emergency_stop"
    agv.task_id = None

    if task:
        task.preferred_agv_id = agv.id
        mark_task_blocked(task, "recover_required_emergency_stop", task.dispatch_algorithm)

    return {
        "message": "AGV emergency stopped",
        "agv": agv,
        "task": task,
        "event": event,
    }


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


def move_agv_to_maintenance(agv_id: int):
    agv = _find_agv(agv_id)
    if agv.status == "maintenance":
        return {"message": "AGV already in maintenance", "agv": agv}

    _assert_agv_can_enter_maintenance(agv)
    agv.status = "maintenance"
    agv.task_id = None
    return {"message": "AGV moved to maintenance", "agv": agv}


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
