from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.fault_event import FaultEvent
from app.repositories.db_init import create_all_tables
from app.repositories.sql.mappers import fault_event_entity_to_model, fault_event_model_to_entity
from app.repositories.sql_models import FaultEventEntity


fault_event_list: list[FaultEvent] = []
_loaded = False


def _persist_fault_snapshot(event: FaultEvent) -> None:
    with get_db_session() as session:
        entity = session.get(FaultEventEntity, event.id)
        entity = fault_event_model_to_entity(event, entity)
        session.add(entity)
        session.commit()


def _bind_fault_event(event: FaultEvent) -> FaultEvent:
    event.bind_on_change(lambda event_id=event.id: _persist_cached_fault_event(event_id))
    return event


def _persist_cached_fault_event(event_id: int) -> None:
    event = next((item for item in fault_event_list if item.id == event_id), None)
    if event is None:
        return
    _persist_fault_snapshot(event)


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(select(FaultEventEntity).order_by(FaultEventEntity.id)).scalars().all()

    loaded_models = [_bind_fault_event(fault_event_entity_to_model(entity)) for entity in entities]
    fault_event_list[:] = loaded_models


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _load_cache()
    _loaded = True


def list_fault_events_store() -> list[FaultEvent]:
    _ensure_loaded()
    return fault_event_list


def get_fault_event_by_id(event_id: int) -> FaultEvent | None:
    _ensure_loaded()
    return next((event for event in fault_event_list if event.id == event_id), None)


def get_next_fault_event_id() -> int:
    _ensure_loaded()
    return max((event.id for event in fault_event_list), default=0) + 1


def add_fault_event(event: FaultEvent) -> FaultEvent:
    _ensure_loaded()
    bound = _bind_fault_event(event)
    fault_event_list.append(bound)
    _persist_fault_snapshot(bound)
    return bound


def list_open_fault_events_for_agv(agv_id: int, event_type: str | None = None) -> list[FaultEvent]:
    _ensure_loaded()
    return [
        event
        for event in fault_event_list
        if event.agv_id == agv_id
        and event.status == "open"
        and (event_type is None or event.event_type == event_type)
    ]


__all__ = [
    "add_fault_event",
    "fault_event_list",
    "get_fault_event_by_id",
    "get_next_fault_event_id",
    "list_fault_events_store",
    "list_open_fault_events_for_agv",
]
