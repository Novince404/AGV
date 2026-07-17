from datetime import datetime

from app.models.fault_event import FaultEvent
from app.repositories.fault_repository import (
    add_fault_event,
    get_fault_event_by_id,
    get_next_fault_event_id,
    list_fault_events_store,
    list_open_fault_events_for_agv,
)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def create_fault_event(
    agv_id: int,
    fault_type: str,
    severity: str = "medium",
    message: str | None = None,
    reported_by: str = "system",
    event_type: str = "fault",
    task_id: int | None = None,
):
    next_id = get_next_fault_event_id()
    event = FaultEvent(
        id=next_id,
        agv_id=agv_id,
        fault_type=fault_type,
        severity=severity,
        message=message,
        event_type=event_type,
        status="open",
        reported_at=now_iso(),
        reported_by=reported_by,
        task_id=task_id,
    )
    return add_fault_event(event)


def list_fault_events(status: str | None = None):
    events = list_fault_events_store()
    if status in {"open", "resolved"}:
        events = [event for event in events if event.status == status]
    return sorted(events, key=lambda item: (item.reported_at, item.id), reverse=True)


def get_fault_event(event_id: int):
    return get_fault_event_by_id(event_id)


def get_open_fault_events_for_agv(agv_id: int, event_type: str | None = None):
    return list_open_fault_events_for_agv(agv_id, event_type)


def resolve_fault_event(event_id: int):
    event = get_fault_event(event_id)
    if not event:
        return None
    if event.status == "resolved":
        return event
    event.status = "resolved"
    event.resolved_at = now_iso()
    return event


def resolve_latest_open_event_for_agv(agv_id: int, event_type: str | None = None):
    open_events = get_open_fault_events_for_agv(agv_id, event_type)
    if not open_events:
        return None
    latest = sorted(open_events, key=lambda item: (item.reported_at, item.id), reverse=True)[0]
    return resolve_fault_event(latest.id)
