from __future__ import annotations

from app.repositories.agv_repository import get_agv_by_id
from app.repositories.task_repository import list_tasks
from app.services.operation_audit_service import (
    build_first_audit_map,
    build_latest_audit_map,
    record_operation_audit,
)
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


def _serialize_fault_event_with_audit(event):
    payload = event.model_dump() if hasattr(event, "model_dump") else event.dict()
    latest = build_latest_audit_map("fault", [str(event.id)]).get(str(event.id))
    created = build_first_audit_map("fault", [str(event.id)], create_actions={"report"}).get(str(event.id))
    if created is not None:
        payload["reported_by"] = created.operator_display_name
        payload["reported_by_role"] = created.operator_role
    if latest is not None:
        payload["last_operator"] = latest.operator_display_name
        payload["last_operator_role"] = latest.operator_role
        payload["last_operator_action"] = latest.action
        payload["last_operator_at"] = latest.performed_at
    resolved = build_latest_audit_map("fault", [str(event.id)]).get(str(event.id))
    if resolved is not None and resolved.action == "resolve":
        payload["resolved_by"] = resolved.operator_display_name
        payload["resolved_by_role"] = resolved.operator_role
    return payload


def report_fault(
    agv_id: int,
    fault_type: str,
    severity: str = "medium",
    message: str | None = None,
    reported_by: str = "system",
    actor: dict | None = None,
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
        record_operation_audit("task", task.id, "fault_interrupt", actor, {"agv_id": agv.id, "fault_type": fault_type})

    audit = record_operation_audit("fault", event.id, "report", actor, {"agv_id": agv.id, "fault_type": fault_type})
    return {
        "message": "Fault reported",
        "event": _serialize_fault_event_with_audit(event),
        "agv": agv,
        "task": task,
        "operator": audit.operator_display_name,
    }


def get_fault_list(status: str | None = None):
    return [_serialize_fault_event_with_audit(event) for event in list_fault_events(status)]


def resolve_fault(event_id: int, actor: dict | None = None):
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

    record_operation_audit("fault", event.id, "resolve", actor, {"agv_id": event.agv_id})
    return {"message": "Fault resolved", "event": _serialize_fault_event_with_audit(event), "agv": agv}
