from __future__ import annotations

from sqlalchemy import select

from app.core.data_scope import (
    build_scoped_storage_id,
    extract_public_id,
    get_current_scope_key,
    get_scope_storage_prefix,
    is_legacy_unscoped_storage_id,
)
from app.core.database import get_db_session
from app.models.point_library import PointLibraryItem
from app.repositories.db_init import create_all_tables
from app.repositories.memory.point_store import DEFAULT_POINT_LIBRARY
from app.repositories.sql_models import PointLibraryEntity


point_library_by_scope: dict[str, list[PointLibraryItem]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _scope_prefix(scope_key: str | None = None) -> str:
    return get_scope_storage_prefix(scope_key or _current_scope())


def _scope_query(scope_key: str):
    return select(PointLibraryEntity).where(PointLibraryEntity.id.like(f"{_scope_prefix(scope_key)}%")).order_by(PointLibraryEntity.id)


def _legacy_query():
    return select(PointLibraryEntity).order_by(PointLibraryEntity.id)


def _scope_cache(scope_key: str | None = None) -> list[PointLibraryItem]:
    normalized_scope = str(scope_key or _current_scope())
    return point_library_by_scope.setdefault(normalized_scope, [])


def _bind_point(point: PointLibraryItem) -> PointLibraryItem:
    point.bind_on_change(lambda point_id=point.id, scope_key=_current_scope(): _persist_cached_point(point_id, scope_key))
    return point


def _entity_to_model(entity: PointLibraryEntity, scope_key: str | None = None) -> PointLibraryItem:
    return PointLibraryItem(
        id=extract_public_id(entity.id, scope_key),
        x=entity.x,
        y=entity.y,
        name_key=entity.name_key,
        zone_key=entity.zone_key,
        custom_name=entity.custom_name,
        aliases=list(entity.aliases or []),
        custom=entity.custom,
    )


def _model_to_entity(point: PointLibraryItem, entity: PointLibraryEntity | None = None, scope_key: str | None = None) -> PointLibraryEntity:
    storage_id = build_scoped_storage_id(point.id, scope_key)
    entity = entity or PointLibraryEntity(id=storage_id)
    entity.id = storage_id
    entity.x = point.x
    entity.y = point.y
    entity.name_key = point.name_key
    entity.zone_key = point.zone_key
    entity.custom_name = point.custom_name
    entity.aliases = list(point.aliases or [])
    entity.custom = point.custom
    return entity


def _persist_cached_point(point_id: str, scope_key: str | None = None) -> None:
    cache = _scope_cache(scope_key)
    point = next((item for item in cache if item.id == point_id), None)
    if point is None:
        return
    scoped_id = build_scoped_storage_id(point.id, scope_key)
    with get_db_session() as session:
        entity = session.get(PointLibraryEntity, scoped_id)
        session.add(_model_to_entity(point, entity, scope_key))
        session.commit()


def _seed_defaults_for_scope(scope_key: str) -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(PointLibraryEntity.id).where(PointLibraryEntity.id.like(f"{_scope_prefix(scope_key)}%")).limit(1)).first() is not None
        if has_rows:
            return

        legacy_entities = [
            entity
            for entity in session.execute(_legacy_query()).scalars().all()
            if is_legacy_unscoped_storage_id(entity.id)
        ]
        if legacy_entities:
            for entity in legacy_entities:
                scoped_id = build_scoped_storage_id(entity.id, scope_key)
                if session.get(PointLibraryEntity, scoped_id) is not None:
                    continue
                session.add(
                    PointLibraryEntity(
                        id=scoped_id,
                        x=entity.x,
                        y=entity.y,
                        name_key=entity.name_key,
                        zone_key=entity.zone_key,
                        custom_name=entity.custom_name,
                        aliases=list(entity.aliases or []),
                        custom=entity.custom,
                    )
                )
            session.commit()
            return

        for default_point in DEFAULT_POINT_LIBRARY:
            session.add(_model_to_entity(PointLibraryItem(**default_point.model_dump()), scope_key=scope_key))
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_point(_entity_to_model(entity, scope_key)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    create_all_tables()
    _seed_defaults_for_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_points() -> list[PointLibraryItem]:
    _ensure_loaded()
    return _scope_cache()


def get_point_by_id(point_id: str) -> PointLibraryItem | None:
    _ensure_loaded()
    return next((point for point in _scope_cache() if point.id == point_id), None)


def upsert_point(point: PointLibraryItem) -> PointLibraryItem:
    _ensure_loaded()
    existing = get_point_by_id(point.id)
    bound = _bind_point(point)
    cache = _scope_cache()
    if existing is None:
        cache.append(bound)
    else:
        cache[cache.index(existing)] = bound
    _persist_cached_point(bound.id)
    return bound


def remove_point(point_id: str) -> None:
    _ensure_loaded()
    existing = get_point_by_id(point_id)
    if existing is None:
        return
    _scope_cache().remove(existing)
    scoped_id = build_scoped_storage_id(point_id)
    with get_db_session() as session:
        entity = session.get(PointLibraryEntity, scoped_id)
        if entity is not None:
            session.delete(entity)
            session.commit()
