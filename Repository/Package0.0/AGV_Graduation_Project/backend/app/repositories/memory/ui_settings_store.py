from __future__ import annotations

from copy import deepcopy


ui_settings_payload: dict | None = None


def get_ui_settings(default_settings: dict) -> dict:
    if ui_settings_payload is None:
        return deepcopy(default_settings)
    return deepcopy(ui_settings_payload)


def save_ui_settings(settings_payload: dict) -> dict:
    global ui_settings_payload
    ui_settings_payload = deepcopy(settings_payload)
    return deepcopy(ui_settings_payload)
