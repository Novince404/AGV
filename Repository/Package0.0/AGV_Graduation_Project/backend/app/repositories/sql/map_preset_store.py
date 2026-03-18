from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.map_preset import MapPreset, MapPresetCell
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import MapPresetCellEntity, MapPresetEntity


map_presets: list[MapPreset] = []
_loaded = False


def _bind_preset(preset: MapPreset) -> MapPreset:
    preset.bind_on_change(lambda preset_key=preset.key: _persist_cached_preset(preset_key))
    return preset


def _query_presets():
    return select(MapPresetEntity).options(selectinload(MapPresetEntity.blocked_cells)).order_by(MapPresetEntity.id)


def _entity_to_model(entity: MapPresetEntity) -> MapPreset:
    cells = [MapPresetCell(x=int(cell.x), y=int(cell.y)) for cell in entity.blocked_cells]
    return MapPreset(
        key=entity.id,
        custom_name=entity.custom_name,
        description=entity.description,
        blocked_cells=cells,
        custom=entity.custom,
    )


def _model_to_entity(preset: MapPreset, entity: MapPresetEntity | None = None) -> MapPresetEntity:
    entity = entity or MapPresetEntity(id=preset.key)
    entity.custom_name = preset.custom_name
    entity.description = preset.description
    entity.custom = preset.custom
    entity.blocked_cells = [
        MapPresetCellEntity(x=int(cell.x), y=int(cell.y))
        for cell in preset.blocked_cells
    ]
    return entity


def _persist_cached_preset(preset_key: str) -> None:
    preset = next((item for item in map_presets if item.key == preset_key), None)
    if preset is None:
        return
    with get_db_session() as session:
        entity = session.get(MapPresetEntity, preset.key)
        session.add(_model_to_entity(preset, entity))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(_query_presets()).scalars().all()
    map_presets[:] = [_bind_preset(_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _load_cache()
    _loaded = True


def list_map_presets() -> list[MapPreset]:
    _ensure_loaded()
    return map_presets


def get_map_preset_by_key(preset_key: str) -> MapPreset | None:
    _ensure_loaded()
    return next((preset for preset in map_presets if preset.key == preset_key), None)


def upsert_map_preset(preset: MapPreset) -> MapPreset:
    _ensure_loaded()
    existing = get_map_preset_by_key(preset.key)
    bound = _bind_preset(preset)
    if existing is None:
        map_presets.append(bound)
    else:
        map_presets[map_presets.index(existing)] = bound
    _persist_cached_preset(bound.key)
    return bound


def remove_map_preset(preset_key: str) -> None:
    _ensure_loaded()
    existing = get_map_preset_by_key(preset_key)
    if existing is None:
        return
    map_presets.remove(existing)
    with get_db_session() as session:
        entity = session.get(MapPresetEntity, preset_key)
        if entity is not None:
            session.delete(entity)
            session.commit()
