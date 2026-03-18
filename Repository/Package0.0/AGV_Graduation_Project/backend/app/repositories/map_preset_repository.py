"""Public map-preset repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import map_preset_store as _store
else:
    from app.repositories.memory import map_preset_store as _store


def list_map_presets():
    return _store.list_map_presets()


def get_map_preset_by_key(preset_key: str):
    return _store.get_map_preset_by_key(preset_key)


def upsert_map_preset(preset):
    return _store.upsert_map_preset(preset)


def remove_map_preset(preset_key: str):
    return _store.remove_map_preset(preset_key)


__all__ = [
    "get_map_preset_by_key",
    "list_map_presets",
    "remove_map_preset",
    "upsert_map_preset",
]
