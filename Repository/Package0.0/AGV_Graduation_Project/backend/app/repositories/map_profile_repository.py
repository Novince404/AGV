"""Public map-profile repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import map_profile_store as _store
else:
    from app.repositories.memory import map_profile_store as _store


def list_map_profiles():
    return _store.list_map_profiles()


def get_map_profile_by_key(profile_key: str):
    return _store.get_map_profile_by_key(profile_key)


def upsert_map_profile(profile):
    return _store.upsert_map_profile(profile)


def remove_map_profile(profile_key: str):
    return _store.remove_map_profile(profile_key)


__all__ = [
    "get_map_profile_by_key",
    "list_map_profiles",
    "remove_map_profile",
    "upsert_map_profile",
]
