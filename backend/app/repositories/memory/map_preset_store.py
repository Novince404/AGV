from __future__ import annotations

from app.core.data_scope import get_current_scope_key
from app.models.map_preset import MapPreset


map_presets_by_scope: dict[str, list[MapPreset]] = {}


def _scope_cache() -> list[MapPreset]:
    return map_presets_by_scope.setdefault(get_current_scope_key(), [])


def list_map_presets() -> list[MapPreset]:
    return _scope_cache()


def get_map_preset_by_key(preset_key: str) -> MapPreset | None:
    return next((preset for preset in _scope_cache() if preset.key == preset_key), None)


def upsert_map_preset(preset: MapPreset) -> MapPreset:
    existing = get_map_preset_by_key(preset.key)
    cache = _scope_cache()
    if existing is None:
        cache.append(preset)
        return preset

    index = cache.index(existing)
    cache[index] = preset
    return preset


def remove_map_preset(preset_key: str) -> None:
    existing = get_map_preset_by_key(preset_key)
    if existing is not None:
        _scope_cache().remove(existing)
