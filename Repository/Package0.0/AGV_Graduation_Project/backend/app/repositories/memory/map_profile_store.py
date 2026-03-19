from __future__ import annotations

from app.models.map_profile import MapProfile


map_profiles: list[MapProfile] = []


def list_map_profiles() -> list[MapProfile]:
    return map_profiles


def get_map_profile_by_key(profile_key: str) -> MapProfile | None:
    return next((profile for profile in map_profiles if profile.key == profile_key), None)


def upsert_map_profile(profile: MapProfile) -> MapProfile:
    existing = get_map_profile_by_key(profile.key)
    if existing is None:
        map_profiles.append(profile)
        return profile

    index = map_profiles.index(existing)
    map_profiles[index] = profile
    return profile


def remove_map_profile(profile_key: str) -> None:
    existing = get_map_profile_by_key(profile_key)
    if existing is not None:
        map_profiles.remove(existing)
