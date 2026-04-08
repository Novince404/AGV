from __future__ import annotations

from sqlalchemy import inspect, select, text

from app.core.data_scope import get_current_scope_key
from app.core.database import get_engine
from app.core.database import get_db_session
from app.models.fault_event import FaultEvent
from app.repositories.db_init import create_all_tables
from app.repositories.sql.mappers import fault_event_entity_to_model, fault_event_model_to_entity
from app.repositories.sql_models import FaultEventEntity


fault_event_lists_by_scope: dict[str, list[FaultEvent]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    if "fault_event" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("fault_event")}
    if "scope_key" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE fault_event ADD COLUMN scope_key VARCHAR(128)"))


def _scope_query(scope_key: str):
    return select(FaultEventEntity).where(FaultEventEntity.scope_key == scope_key).order_by(FaultEventEntity.id)


def _legacy_query():
    return select(FaultEventEntity).where((FaultEventEntity.scope_key.is_(None)) | (FaultEventEntity.scope_key == "")).order_by(FaultEventEntity.id)


def _scope_cache(scope_key: str | None = None) -> list[FaultEvent]:
    normalized_scope = str(scope_key or _current_scope())
    return fault_event_lists_by_scope.setdefault(normalized_scope, [])


def _persist_fault_snapshot(event: FaultEvent) -> None:
    with get_db_session() as session:
        entity = session.get(FaultEventEntity, event.id)
        entity = fault_event_model_to_entity(event, entity)
        session.add(entity)
        session.commit()


def _bind_fault_event(event: FaultEvent) -> FaultEvent:
    event.bind_on_change(lambda event_id=event.id, scope_key=event.scope_key or _current_scope(): _persist_cached_fault_event(event_id, scope_key))
    return event


def _persist_cached_fault_event(event_id: int, scope_key: str | None = None) -> None:
    event = next((item for item in _scope_cache(scope_key) if item.id == event_id), None)
    if event is None:
        return
    _persist_fault_snapshot(event)


def _seed_legacy_scope(scope_key: str) -> None:
    with get_db_session() as session:
        has_scoped_rows = session.execute(select(FaultEventEntity.id).where(FaultEventEntity.scope_key == scope_key).limit(1)).first() is not None
        if has_scoped_rows:
            return
        legacy_entities = session.execute(_legacy_query()).scalars().all()
        if not legacy_entities:
            return
        for entity in legacy_entities:
            entity.scope_key = scope_key
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_fault_event(fault_event_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    _ensure_schema()
    _seed_legacy_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_fault_events_store() -> list[FaultEvent]:
    _ensure_loaded()
    return _scope_cache()


def get_fault_event_by_id(event_id: int) -> FaultEvent | None:
    _ensure_loaded()
    return next((event for event in _scope_cache() if event.id == event_id), None)


def get_next_fault_event_id() -> int:
    _ensure_loaded()
    with get_db_session() as session:
        next_id = session.execute(select(FaultEventEntity.id).order_by(FaultEventEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
    return int(next_id) + 1


def add_fault_event(event: FaultEvent) -> FaultEvent:
    _ensure_loaded()
    scope_key = _current_scope()
    bound = _bind_fault_event(FaultEvent(**{**event.model_dump(), "scope_key": event.scope_key or scope_key}))
    _scope_cache(scope_key).append(bound)
    _persist_fault_snapshot(bound)
    return bound


def list_open_fault_events_for_agv(agv_id: int, event_type: str | None = None) -> list[FaultEvent]:
    _ensure_loaded()
    return [
        event
        for event in _scope_cache()
        if event.agv_id == agv_id
        and event.status == "open"
        and (event_type is None or event.event_type == event_type)
    ]


__all__ = [
    "add_fault_event",
    "get_fault_event_by_id",
    "get_next_fault_event_id",
    "list_fault_events_store",
    "list_open_fault_events_for_agv",
]
