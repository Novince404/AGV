from __future__ import annotations

from sqlalchemy import select

from app.core.data_scope import get_current_scope_key
from app.core.database import get_db_session
from app.models.agv import AGV
from app.repositories.db_init import require_current_schema
from app.repositories.memory.agv_store import agv_list as default_agv_list
from app.repositories.sql.mappers import agv_entity_to_model, agv_model_to_entity
from app.repositories.sql_models import AgvEntity


agv_lists_by_scope: dict[str, list[AGV]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _ensure_schema() -> None:
    require_current_schema()


def _scope_query(scope_key: str):
    return select(AgvEntity).where(AgvEntity.scope_key == scope_key).order_by(AgvEntity.id)


def _legacy_query():
    return select(AgvEntity).where((AgvEntity.scope_key.is_(None)) | (AgvEntity.scope_key == "")).order_by(AgvEntity.id)


def _scope_cache(scope_key: str | None = None) -> list[AGV]:
    normalized_scope = str(scope_key or _current_scope())
    return agv_lists_by_scope.setdefault(normalized_scope, [])


def _persist_agv_snapshot(agv: AGV) -> None:
    with get_db_session() as session:
        entity = session.get(AgvEntity, agv.id)
        entity = agv_model_to_entity(agv, entity)
        session.add(entity)
        session.commit()


def _bind_agv(agv: AGV) -> AGV:
    agv.bind_on_change(lambda agv_id=agv.id, scope_key=agv.scope_key or _current_scope(): _persist_cached_agv(agv_id, scope_key))
    return agv


def _persist_cached_agv(agv_id: int, scope_key: str | None = None) -> None:
    cache = _scope_cache(scope_key)
    agv = next((item for item in cache if item.id == agv_id), None)
    if agv is None:
        return
    _persist_agv_snapshot(agv)


def _seed_defaults_for_scope(scope_key: str) -> None:
    with get_db_session() as session:
        scoped_has_rows = session.execute(select(AgvEntity.id).where(AgvEntity.scope_key == scope_key).limit(1)).first() is not None
        if scoped_has_rows:
            return

        legacy_entities = session.execute(_legacy_query()).scalars().all()
        if legacy_entities:
            for entity in legacy_entities:
                entity.scope_key = scope_key
            session.commit()
            return

        next_id = session.execute(select(AgvEntity.id).order_by(AgvEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
        for default_agv in default_agv_list:
            next_id += 1
            session.add(
                agv_model_to_entity(
                    AGV(**{**default_agv.model_dump(), "id": next_id, "scope_key": scope_key})
                )
            )
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_agv(agv_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    _ensure_schema()
    _seed_defaults_for_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_agvs() -> list[AGV]:
    _ensure_loaded()
    return _scope_cache()


def get_agv_by_id(agv_id: int) -> AGV | None:
    _ensure_loaded()
    return next((agv for agv in _scope_cache() if agv.id == agv_id), None)


def list_idle_agvs() -> list[AGV]:
    _ensure_loaded()
    return [agv for agv in _scope_cache() if agv.status in {"idle", "idle_returning"}]


def get_first_idle_agv() -> AGV | None:
    _ensure_loaded()
    return next((agv for agv in _scope_cache() if agv.status in {"idle", "idle_returning"}), None)


def create_agv(agv: AGV) -> AGV:
    _ensure_loaded()
    scope_key = _current_scope()
    with get_db_session() as session:
        next_id = session.execute(select(AgvEntity.id).order_by(AgvEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
        next_id += 1
    created = _bind_agv(AGV(**{**agv.model_dump(), "id": next_id, "scope_key": scope_key}))
    _scope_cache(scope_key).append(created)
    _persist_agv_snapshot(created)
    return created


def delete_agv(agv_id: int) -> AGV | None:
    _ensure_loaded()
    scope_key = _current_scope()
    cache = _scope_cache(scope_key)
    target = next((item for item in cache if item.id == agv_id), None)
    if target is None:
        return None

    with get_db_session() as session:
        entity = session.execute(
            select(AgvEntity).where(AgvEntity.id == agv_id, AgvEntity.scope_key == scope_key)
        ).scalar_one_or_none()
        if entity is not None:
            session.delete(entity)
            session.commit()

    cache[:] = [agv for agv in cache if agv.id != agv_id]
    return target


__all__ = [
    "create_agv",
    "delete_agv",
    "get_agv_by_id",
    "get_first_idle_agv",
    "list_agvs",
    "list_idle_agvs",
]
