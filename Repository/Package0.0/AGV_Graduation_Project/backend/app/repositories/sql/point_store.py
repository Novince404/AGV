from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.point_library import PointLibraryItem
from app.repositories.db_init import create_all_tables
from app.repositories.memory.point_store import point_library as default_point_library
from app.repositories.sql_models import PointLibraryEntity


point_library: list[PointLibraryItem] = []
_loaded = False


def _bind_point(point: PointLibraryItem) -> PointLibraryItem:
    point.bind_on_change(lambda point_id=point.id: _persist_cached_point(point_id))
    return point


def _entity_to_model(entity: PointLibraryEntity) -> PointLibraryItem:
    return PointLibraryItem(
        id=entity.id,
        x=entity.x,
        y=entity.y,
        name_key=entity.name_key,
        zone_key=entity.zone_key,
        custom_name=entity.custom_name,
        aliases=list(entity.aliases or []),
        custom=entity.custom,
    )


def _model_to_entity(point: PointLibraryItem, entity: PointLibraryEntity | None = None) -> PointLibraryEntity:
    entity = entity or PointLibraryEntity(id=point.id)
    entity.x = point.x
    entity.y = point.y
    entity.name_key = point.name_key
    entity.zone_key = point.zone_key
    entity.custom_name = point.custom_name
    entity.aliases = list(point.aliases or [])
    entity.custom = point.custom
    return entity


def _persist_cached_point(point_id: str) -> None:
    point = next((item for item in point_library if item.id == point_id), None)
    if point is None:
        return
    with get_db_session() as session:
        entity = session.get(PointLibraryEntity, point.id)
        session.add(_model_to_entity(point, entity))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(select(PointLibraryEntity).order_by(PointLibraryEntity.id)).scalars().all()
    point_library[:] = [_bind_point(_entity_to_model(entity)) for entity in entities]


def _seed_defaults_if_empty() -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(PointLibraryEntity.id).limit(1)).first() is not None
        if has_rows:
            return
        for default_point in default_point_library:
            session.add(_model_to_entity(PointLibraryItem(**default_point.model_dump())))
        session.commit()


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _seed_defaults_if_empty()
    _load_cache()
    _loaded = True


def list_points() -> list[PointLibraryItem]:
    _ensure_loaded()
    return point_library


def get_point_by_id(point_id: str) -> PointLibraryItem | None:
    _ensure_loaded()
    return next((point for point in point_library if point.id == point_id), None)


def upsert_point(point: PointLibraryItem) -> PointLibraryItem:
    _ensure_loaded()
    existing = get_point_by_id(point.id)
    bound = _bind_point(point)
    if existing is None:
        point_library.append(bound)
    else:
        point_library[point_library.index(existing)] = bound
    _persist_cached_point(bound.id)
    return bound


def remove_point(point_id: str) -> None:
    _ensure_loaded()
    existing = get_point_by_id(point_id)
    if existing is None:
        return
    point_library.remove(existing)
    with get_db_session() as session:
        entity = session.get(PointLibraryEntity, point_id)
        if entity is not None:
            session.delete(entity)
            session.commit()
