from __future__ import annotations

from sqlalchemy import inspect, select, text

from app.core.database import get_engine
from app.core.database import get_db_session
from app.models.agv import AGV
from app.repositories.db_init import create_all_tables
from app.repositories.memory.agv_store import agv_list as default_agv_list
from app.repositories.sql.mappers import agv_entity_to_model, agv_model_to_entity
from app.repositories.sql_models import AgvEntity


agv_list: list[AGV] = []
_loaded = False


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    if "agv" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("agv")}
    ddl_statements: list[str] = []
    if "render_x" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN render_x FLOAT")
    if "render_y" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN render_y FLOAT")
    if "current_node" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN current_node VARCHAR(128)")
    if "current_edge" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN current_edge VARCHAR(128)")
    if "edge_progress" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN edge_progress FLOAT NOT NULL DEFAULT 0")
    if "motion_state" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_state VARCHAR(32) NOT NULL DEFAULT 'idle'")
    if "current_speed" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN current_speed FLOAT NOT NULL DEFAULT 0")
    if "target_speed" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN target_speed FLOAT NOT NULL DEFAULT 0")
    if "heading" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN heading FLOAT NOT NULL DEFAULT 0")
    if "motion_started_at" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_started_at VARCHAR(32)")
    if "motion_updated_at" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_updated_at VARCHAR(32)")
    if "motion_duration_ms" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_duration_ms INTEGER NOT NULL DEFAULT 0")
    if "motion_source_x" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_source_x FLOAT")
    if "motion_source_y" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_source_y FLOAT")
    if "motion_target_x" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_target_x FLOAT")
    if "motion_target_y" not in columns:
        ddl_statements.append("ALTER TABLE agv ADD COLUMN motion_target_y FLOAT")

    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                connection.execute(text(statement))


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
    _ensure_schema()
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
