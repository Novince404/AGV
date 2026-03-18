from __future__ import annotations

from copy import deepcopy

from app.core.database import get_db_session
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import UiSettingsEntity


UI_SETTINGS_ROW_ID = 1


def _entity_to_payload(entity: UiSettingsEntity) -> dict:
    return {
        "show_minimap": bool(entity.show_minimap),
        "show_marker_icons": bool(entity.show_marker_icons),
        "show_path_arrows": bool(entity.show_path_arrows),
        "show_status_legend": bool(entity.show_status_legend),
        "status_legend_layout": entity.status_legend_layout,
        "status_legend_opacity": float(entity.status_legend_opacity),
        "compare_display_mode": entity.compare_display_mode,
        "panel_sections": dict(entity.panel_sections or {}),
    }


def _apply_payload(entity: UiSettingsEntity, payload: dict) -> UiSettingsEntity:
    entity.show_minimap = bool(payload["show_minimap"])
    entity.show_marker_icons = bool(payload["show_marker_icons"])
    entity.show_path_arrows = bool(payload["show_path_arrows"])
    entity.show_status_legend = bool(payload["show_status_legend"])
    entity.status_legend_layout = str(payload["status_legend_layout"])
    entity.status_legend_opacity = float(payload["status_legend_opacity"])
    entity.compare_display_mode = str(payload["compare_display_mode"])
    entity.panel_sections = dict(payload.get("panel_sections") or {})
    return entity


def get_ui_settings(default_settings: dict) -> dict:
    create_all_tables()
    with get_db_session() as session:
        entity = session.get(UiSettingsEntity, UI_SETTINGS_ROW_ID)
        if entity is None:
            return deepcopy(default_settings)
        return _entity_to_payload(entity)


def save_ui_settings(settings_payload: dict) -> dict:
    create_all_tables()
    payload = deepcopy(settings_payload)
    with get_db_session() as session:
        entity = session.get(UiSettingsEntity, UI_SETTINGS_ROW_ID)
        entity = _apply_payload(entity or UiSettingsEntity(id=UI_SETTINGS_ROW_ID), payload)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return _entity_to_payload(entity)
