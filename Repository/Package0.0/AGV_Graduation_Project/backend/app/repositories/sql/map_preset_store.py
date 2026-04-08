from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.data_scope import (
    build_scoped_storage_id,
    extract_public_id,
    get_current_scope_key,
    get_scope_storage_prefix,
    is_legacy_unscoped_storage_id,
)
from app.core.database import get_db_session
from app.models.map_preset import MapPreset, MapPresetCell
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import MapPresetCellEntity, MapPresetEntity, MapPresetValidCellEntity


map_presets_by_scope: dict[str, list[MapPreset]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _scope_prefix(scope_key: str | None = None) -> str:
    return get_scope_storage_prefix(scope_key or _current_scope())


def _bind_preset(preset: MapPreset) -> MapPreset:
    preset.bind_on_change(lambda preset_key=preset.key, scope_key=_current_scope(): _persist_cached_preset(preset_key, scope_key))
    return preset


def _scope_query(scope_key: str):
    return (
        select(MapPresetEntity)
        .options(
            selectinload(MapPresetEntity.blocked_cells),
            selectinload(MapPresetEntity.valid_cells),
        )
        .where(MapPresetEntity.id.like(f"{_scope_prefix(scope_key)}%"))
        .order_by(MapPresetEntity.id)
    )


def _legacy_query():
    return (
        select(MapPresetEntity)
        .options(
            selectinload(MapPresetEntity.blocked_cells),
            selectinload(MapPresetEntity.valid_cells),
        )
        .order_by(MapPresetEntity.id)
    )


def _scope_cache(scope_key: str | None = None) -> list[MapPreset]:
    normalized_scope = str(scope_key or _current_scope())
    return map_presets_by_scope.setdefault(normalized_scope, [])


def _entity_to_model(entity: MapPresetEntity, scope_key: str | None = None) -> MapPreset:
    cells = [MapPresetCell(x=int(cell.x), y=int(cell.y)) for cell in entity.blocked_cells]
    valid_cells = [MapPresetCell(x=int(cell.x), y=int(cell.y)) for cell in entity.valid_cells]
    return MapPreset(
        key=extract_public_id(entity.id, scope_key),
        custom_name=entity.custom_name,
        description=entity.description,
        valid_cells=valid_cells,
        blocked_cells=cells,
        custom=entity.custom,
    )


def _model_to_entity(preset: MapPreset, entity: MapPresetEntity | None = None, scope_key: str | None = None) -> MapPresetEntity:
    storage_id = build_scoped_storage_id(preset.key, scope_key)
    entity = entity or MapPresetEntity(id=storage_id)
    entity.id = storage_id
    entity.custom_name = preset.custom_name
    entity.description = preset.description
    entity.custom = preset.custom
    entity.valid_cells = [
        MapPresetValidCellEntity(x=int(cell.x), y=int(cell.y))
        for cell in preset.valid_cells
    ]
    entity.blocked_cells = [
        MapPresetCellEntity(x=int(cell.x), y=int(cell.y))
        for cell in preset.blocked_cells
    ]
    return entity


def _persist_cached_preset(preset_key: str, scope_key: str | None = None) -> None:
    preset = next((item for item in _scope_cache(scope_key) if item.key == preset_key), None)
    if preset is None:
        return
    scoped_id = build_scoped_storage_id(preset.key, scope_key)
    with get_db_session() as session:
        entity = session.get(MapPresetEntity, scoped_id)
        session.add(_model_to_entity(preset, entity, scope_key))
        session.commit()


def _seed_scope(scope_key: str) -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(MapPresetEntity.id).where(MapPresetEntity.id.like(f"{_scope_prefix(scope_key)}%")).limit(1)).first() is not None
        if has_rows:
            return

        legacy_entities = [
            entity
            for entity in session.execute(_legacy_query()).scalars().all()
            if is_legacy_unscoped_storage_id(entity.id)
        ]
        if not legacy_entities:
            return
        for entity in legacy_entities:
            scoped_id = build_scoped_storage_id(entity.id, scope_key)
            if session.get(MapPresetEntity, scoped_id) is not None:
                continue
            session.add(_model_to_entity(_entity_to_model(entity), scope_key=scope_key))
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_preset(_entity_to_model(entity, scope_key)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    create_all_tables()
    _seed_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_map_presets() -> list[MapPreset]:
    _ensure_loaded()
    return _scope_cache()


def get_map_preset_by_key(preset_key: str) -> MapPreset | None:
    _ensure_loaded()
    return next((preset for preset in _scope_cache() if preset.key == preset_key), None)


def upsert_map_preset(preset: MapPreset) -> MapPreset:
    _ensure_loaded()
    existing = get_map_preset_by_key(preset.key)
    bound = _bind_preset(preset)
    cache = _scope_cache()
    if existing is None:
        cache.append(bound)
    else:
        cache[cache.index(existing)] = bound
    _persist_cached_preset(bound.key)
    return bound


def remove_map_preset(preset_key: str) -> None:
    _ensure_loaded()
    existing = get_map_preset_by_key(preset_key)
    if existing is None:
        return
    _scope_cache().remove(existing)
    scoped_id = build_scoped_storage_id(preset_key)
    with get_db_session() as session:
        entity = session.get(MapPresetEntity, scoped_id)
        if entity is not None:
            session.delete(entity)
            session.commit()
