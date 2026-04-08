from __future__ import annotations

from app.core.data_scope import get_current_scope_key
from app.models.map_profile import MapProfile


map_profiles_by_scope: dict[str, list[MapProfile]] = {}


def _scope_cache() -> list[MapProfile]:
    return map_profiles_by_scope.setdefault(get_current_scope_key(), [])


def list_map_profiles() -> list[MapProfile]:
    return _scope_cache()


def get_map_profile_by_key(profile_key: str) -> MapProfile | None:
    return next((profile for profile in _scope_cache() if profile.key == profile_key), None)


def upsert_map_profile(profile: MapProfile) -> MapProfile:
    existing = get_map_profile_by_key(profile.key)
    cache = _scope_cache()
    if existing is None:
        cache.append(profile)
        return profile

    index = cache.index(existing)
    cache[index] = profile
    return profile


def remove_map_profile(profile_key: str) -> None:
    existing = get_map_profile_by_key(profile_key)
    if existing is not None:
        _scope_cache().remove(existing)
