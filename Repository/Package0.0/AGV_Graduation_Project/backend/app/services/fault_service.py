from __future__ import annotations

from app.repositories.agv_repository import get_agv_by_id
from app.repositories.task_repository import list_tasks
from app.utils.api_error import raise_api_error
from app.utils.fault_state import create_fault_event, list_fault_events, resolve_fault_event
from app.utils.task_chain import mark_task_blocked


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


def report_fault(
    agv_id: int,
    fault_type: str,
    severity: str = "medium",
    message: str | None = None,
    reported_by: str = "system",
):
    agv = _find_agv(agv_id)
    task = _find_active_task_for_agv(agv_id)
    event = create_fault_event(
        agv_id=agv_id,
        fault_type=fault_type,
        severity=severity,
        message=message,
        reported_by=reported_by,
        event_type="fault",
        task_id=task.id if task else agv.task_id,
    )

    agv.status = "fault"
    agv.task_id = None
    agv.active_fault_event_id = event.id

    if task:
        task.preferred_agv_id = agv.id
        mark_task_blocked(task, "recover_required_fault", task.dispatch_algorithm)

    return {
        "message": "Fault reported",
        "event": event,
        "agv": agv,
        "task": task,
    }


def get_fault_list(status: str | None = None):
    return list_fault_events(status)


def resolve_fault(event_id: int):
    event = resolve_fault_event(event_id)
    if not event:
        raise_api_error(404, "fault_event_not_found")

    agv = get_agv_by_id(event.agv_id)
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
