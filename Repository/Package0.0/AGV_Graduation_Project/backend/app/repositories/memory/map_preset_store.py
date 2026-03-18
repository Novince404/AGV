from __future__ import annotations

from app.models.map_preset import MapPreset


map_presets: list[MapPreset] = []


def list_map_presets() -> list[MapPreset]:
    return map_presets


def get_map_preset_by_key(preset_key: str) -> MapPreset | None:
    return next((preset for preset in map_presets if preset.key == preset_key), None)


def upsert_map_preset(preset: MapPreset) -> MapPreset:
    existing = get_map_preset_by_key(preset.key)
    if existing is None:
        map_presets.append(preset)
        return preset

    index = map_presets.index(existing)
    map_presets[index] = preset
    return preset


def remove_map_preset(preset_key: str) -> None:
    existing = get_map_preset_by_key(preset_key)
    if existing is not None:
        map_presets.remove(existing)
