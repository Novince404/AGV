from app.models.fault_event import FaultEvent


fault_event_list: list[FaultEvent] = []


def list_fault_events_store() -> list[FaultEvent]:
    return fault_event_list


def get_fault_event_by_id(event_id: int) -> FaultEvent | None:
    return next((event for event in fault_event_list if event.id == event_id), None)


def get_next_fault_event_id() -> int:
    return max((event.id for event in fault_event_list), default=0) + 1


def add_fault_event(event: FaultEvent) -> FaultEvent:
    fault_event_list.append(event)
    return event


def list_open_fault_events_for_agv(agv_id: int, event_type: str | None = None) -> list[FaultEvent]:
    return [
        event
        for event in fault_event_list
        if event.agv_id == agv_id
        and event.status == "open"
        and (event_type is None or event.event_type == event_type)
    ]
