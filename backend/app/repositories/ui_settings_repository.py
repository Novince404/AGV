"""Public UI-settings repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import ui_settings_store as _store
else:
    from app.repositories.memory import ui_settings_store as _store


def get_ui_settings(default_settings: dict) -> dict:
    return _store.get_ui_settings(default_settings)


def save_ui_settings(settings_payload: dict) -> dict:
    return _store.save_ui_settings(settings_payload)


__all__ = [
    "get_ui_settings",
    "save_ui_settings",
]
