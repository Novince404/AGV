from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.agv import AGV
from app.repositories.db_init import create_all_tables
from app.repositories.memory.agv_store import agv_list as default_agv_list
from app.repositories.sql.mappers import agv_entity_to_model, agv_model_to_entity
from app.repositories.sql_models import AgvEntity


agv_list: list[AGV] = []
_loaded = False


def _persist_agv_snapshot(agv: AGV) -> None:
    with get_db_session() as session:
        entity = session.get(AgvEntity, agv.id)
        entity = agv_model_to_entity(agv, entity)
        session.add(entity)
        session.commit()


def _bind_agv(agv: AGV) -> AGV:
    agv.bind_on_change(lambda agv_id=agv.id: _persist_cached_agv(agv_id))
    return agv


def _persist_cached_agv(agv_id: int) -> None:
    agv = next((item for item in agv_list if item.id == agv_id), None)
    if agv is None:
        return
    _persist_agv_snapshot(agv)


def _seed_defaults_if_empty() -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(AgvEntity.id).limit(1)).first() is not None
        if has_rows:
            return

        for default_agv in default_agv_list:
            session.add(agv_model_to_entity(AGV(**default_agv.model_dump())))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(select(AgvEntity).order_by(AgvEntity.id)).scalars().all()

    loaded_models = [_bind_agv(agv_entity_to_model(entity)) for entity in entities]
    agv_list[:] = loaded_models


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _seed_defaults_if_empty()
    _load_cache()
    _loaded = True


def list_agvs() -> list[AGV]:
    _ensure_loaded()
    return agv_list


def get_agv_by_id(agv_id: int) -> AGV | None:
    _ensure_loaded()
    return next((agv for agv in agv_list if agv.id == agv_id), None)


def list_idle_agvs() -> list[AGV]:
    _ensure_loaded()
    return [agv for agv in agv_list if agv.status == "idle"]


def get_first_idle_agv() -> AGV | None:
    _ensure_loaded()
    return next((agv for agv in agv_list if agv.status == "idle"), None)


__all__ = [
    "agv_list",
    "get_agv_by_id",
    "get_first_idle_agv",
    "list_agvs",
    "list_idle_agvs",
]
