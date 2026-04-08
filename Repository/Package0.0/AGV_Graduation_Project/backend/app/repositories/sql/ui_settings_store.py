from __future__ import annotations

from copy import deepcopy

from sqlalchemy import inspect, text

from app.core.database import get_engine
from app.core.database import get_db_session
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import UiSettingsEntity


UI_SETTINGS_ROW_ID = 1


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    if "ui_settings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ui_settings")}
    ddl_statements: list[str] = []
    if "show_topology_edge_speed" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN show_topology_edge_speed BOOLEAN NOT NULL DEFAULT 0")
    if "show_runtime_segment_type" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN show_runtime_segment_type BOOLEAN NOT NULL DEFAULT 0")
    if "show_runtime_conflict_reason" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN show_runtime_conflict_reason BOOLEAN NOT NULL DEFAULT 0")
    if "show_selected_agv_runtime_overlay" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN show_selected_agv_runtime_overlay BOOLEAN NOT NULL DEFAULT 0")
    if "base_speed" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN base_speed FLOAT NOT NULL DEFAULT 1.11")
    if "follow_distance" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN follow_distance FLOAT NOT NULL DEFAULT 0.75")
    if "deadlock_timeout_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN deadlock_timeout_sec FLOAT NOT NULL DEFAULT 4.5")
    if "idle_return_timeout_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN idle_return_timeout_sec FLOAT NOT NULL DEFAULT 12")
    if "idle_charge_timeout_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN idle_charge_timeout_sec FLOAT NOT NULL DEFAULT 45")
    if "battery_active_drain_per_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN battery_active_drain_per_sec FLOAT NOT NULL DEFAULT 0.16")
    if "battery_waiting_drain_per_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN battery_waiting_drain_per_sec FLOAT NOT NULL DEFAULT 0.05")
    if "battery_idle_drain_per_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN battery_idle_drain_per_sec FLOAT NOT NULL DEFAULT 0.01")
    if "battery_parking_idle_drain_per_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN battery_parking_idle_drain_per_sec FLOAT NOT NULL DEFAULT 0.003")
    if "battery_charge_per_sec" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN battery_charge_per_sec FLOAT NOT NULL DEFAULT 6")
    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                connection.execute(text(statement))


def _entity_to_payload(entity: UiSettingsEntity) -> dict:
    return {
        "show_minimap": bool(entity.show_minimap),
        "show_marker_icons": bool(entity.show_marker_icons),
        "show_path_arrows": bool(entity.show_path_arrows),
        "show_status_legend": bool(entity.show_status_legend),
        "show_topology_edge_speed": bool(entity.show_topology_edge_speed),
        "show_runtime_segment_type": bool(entity.show_runtime_segment_type),
        "show_runtime_conflict_reason": bool(entity.show_runtime_conflict_reason),
        "show_selected_agv_runtime_overlay": bool(entity.show_selected_agv_runtime_overlay),
        "status_legend_layout": entity.status_legend_layout,
        "status_legend_opacity": float(entity.status_legend_opacity),
        "base_speed": float(entity.base_speed),
        "follow_distance": float(entity.follow_distance),
        "deadlock_timeout_sec": float(entity.deadlock_timeout_sec),
        "idle_return_timeout_sec": float(entity.idle_return_timeout_sec),
        "idle_charge_timeout_sec": float(entity.idle_charge_timeout_sec),
        "battery_active_drain_per_sec": float(entity.battery_active_drain_per_sec),
        "battery_waiting_drain_per_sec": float(entity.battery_waiting_drain_per_sec),
        "battery_idle_drain_per_sec": float(entity.battery_idle_drain_per_sec),
        "battery_parking_idle_drain_per_sec": float(entity.battery_parking_idle_drain_per_sec),
        "battery_charge_per_sec": float(entity.battery_charge_per_sec),
        "compare_display_mode": entity.compare_display_mode,
        "panel_sections": dict(entity.panel_sections or {}),
    }


def _apply_payload(entity: UiSettingsEntity, payload: dict) -> UiSettingsEntity:
    entity.show_minimap = bool(payload["show_minimap"])
    entity.show_marker_icons = bool(payload["show_marker_icons"])
    entity.show_path_arrows = bool(payload["show_path_arrows"])
    entity.show_status_legend = bool(payload["show_status_legend"])
    entity.show_topology_edge_speed = bool(payload.get("show_topology_edge_speed", False))
    entity.show_runtime_segment_type = bool(payload.get("show_runtime_segment_type", False))
    entity.show_runtime_conflict_reason = bool(payload.get("show_runtime_conflict_reason", False))
    entity.show_selected_agv_runtime_overlay = bool(payload.get("show_selected_agv_runtime_overlay", False))
    entity.status_legend_layout = str(payload["status_legend_layout"])
    entity.status_legend_opacity = float(payload["status_legend_opacity"])
    entity.base_speed = float(payload.get("base_speed", 1.11))
    entity.follow_distance = float(payload.get("follow_distance", 0.75))
    entity.deadlock_timeout_sec = float(payload.get("deadlock_timeout_sec", 4.5))
    entity.idle_return_timeout_sec = float(payload.get("idle_return_timeout_sec", 12.0))
    entity.idle_charge_timeout_sec = float(payload.get("idle_charge_timeout_sec", 45.0))
    entity.battery_active_drain_per_sec = float(payload.get("battery_active_drain_per_sec", 0.16))
    entity.battery_waiting_drain_per_sec = float(payload.get("battery_waiting_drain_per_sec", 0.05))
    entity.battery_idle_drain_per_sec = float(payload.get("battery_idle_drain_per_sec", 0.01))
    entity.battery_parking_idle_drain_per_sec = float(payload.get("battery_parking_idle_drain_per_sec", 0.003))
    entity.battery_charge_per_sec = float(payload.get("battery_charge_per_sec", 6.0))
    entity.compare_display_mode = str(payload["compare_display_mode"])
    entity.panel_sections = dict(payload.get("panel_sections") or {})
    return entity


def get_ui_settings(default_settings: dict) -> dict:
    _ensure_schema()
    with get_db_session() as session:
        entity = session.get(UiSettingsEntity, UI_SETTINGS_ROW_ID)
        if entity is None:
            return deepcopy(default_settings)
        return _entity_to_payload(entity)


def save_ui_settings(settings_payload: dict) -> dict:
    _ensure_schema()
    payload = deepcopy(settings_payload)
    with get_db_session() as session:
        entity = session.get(UiSettingsEntity, UI_SETTINGS_ROW_ID)
        entity = _apply_payload(entity or UiSettingsEntity(id=UI_SETTINGS_ROW_ID), payload)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return _entity_to_payload(entity)
