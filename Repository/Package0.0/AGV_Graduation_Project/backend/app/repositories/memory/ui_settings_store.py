from __future__ import annotations

from copy import deepcopy

from app.core.data_scope import get_current_scope_key


ui_settings_payloads_by_scope: dict[str, dict] = {}


def get_ui_settings(default_settings: dict) -> dict:
    scope_key = get_current_scope_key()
    if scope_key not in ui_settings_payloads_by_scope:
        ui_settings_payloads_by_scope[scope_key] = deepcopy(default_settings)
    return deepcopy(ui_settings_payloads_by_scope[scope_key])


def save_ui_settings(settings_payload: dict) -> dict:
    scope_key = get_current_scope_key()
    ui_settings_payloads_by_scope[scope_key] = deepcopy(settings_payload)
    return deepcopy(ui_settings_payloads_by_scope[scope_key])
