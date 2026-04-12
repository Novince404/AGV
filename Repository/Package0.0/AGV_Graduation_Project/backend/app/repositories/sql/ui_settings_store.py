from __future__ import annotations

from copy import deepcopy

from sqlalchemy import inspect, select, text

from app.core.data_scope import get_current_scope_key
from app.core.database import get_db_session, get_engine
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import UiSettingsEntity


UI_SETTINGS_STORE_DEFAULTS = {
    "show_minimap": True,
    "show_marker_icons": True,
    "show_path_arrows": False,
    "show_status_legend": True,
    "show_topology_edge_speed": False,
    "show_runtime_segment_type": False,
    "show_runtime_conflict_reason": False,
    "show_selected_agv_runtime_overlay": False,
    "status_legend_layout": "horizontal",
    "status_legend_opacity": 0.55,
    "base_speed": 1.11,
    "follow_distance": 0.75,
    "deadlock_timeout_sec": 4.5,
    "idle_return_timeout_sec": 12.0,
    "idle_charge_timeout_sec": 45.0,
    "idle_charge_battery_threshold": 60.0,
    "low_battery_threshold": 24.0,
    "battery_active_drain_per_sec": 0.16,
    "battery_waiting_drain_per_sec": 0.05,
    "battery_idle_drain_per_sec": 0.01,
    "battery_parking_idle_drain_per_sec": 0.003,
    "battery_charge_per_sec": 6.0,
    "compare_display_mode": "panel",
    "panel_sections": {
        "control": True,
        "queue": True,
        "templates": False,
        "points": False,
        "json": False,
        "experiments": False,
        "ai": False,
        "operations": False,
    },
}


def _current_scope() -> str:
    return get_current_scope_key()


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    if "ui_settings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ui_settings")}
    ddl_statements: list[str] = []
    if "scope_key" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN scope_key VARCHAR(128)")
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
    if "idle_charge_battery_threshold" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN idle_charge_battery_threshold FLOAT NOT NULL DEFAULT 60")
    if "low_battery_threshold" not in columns:
        ddl_statements.append("ALTER TABLE ui_settings ADD COLUMN low_battery_threshold FLOAT NOT NULL DEFAULT 24")
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


def _scope_query(scope_key: str):
    return select(UiSettingsEntity).where(UiSettingsEntity.scope_key == scope_key).order_by(UiSettingsEntity.id.desc())


def _legacy_query():
    return (
        select(UiSettingsEntity)
        .where((UiSettingsEntity.scope_key.is_(None)) | (UiSettingsEntity.scope_key == ""))
        .order_by(UiSettingsEntity.id.desc())
    )


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
        "idle_charge_battery_threshold": float(entity.idle_charge_battery_threshold),
        "low_battery_threshold": float(entity.low_battery_threshold),
        "battery_active_drain_per_sec": float(entity.battery_active_drain_per_sec),
        "battery_waiting_drain_per_sec": float(entity.battery_waiting_drain_per_sec),
        "battery_idle_drain_per_sec": float(entity.battery_idle_drain_per_sec),
        "battery_parking_idle_drain_per_sec": float(entity.battery_parking_idle_drain_per_sec),
        "battery_charge_per_sec": float(entity.battery_charge_per_sec),
        "compare_display_mode": entity.compare_display_mode,
        "panel_sections": dict(entity.panel_sections or {}),
    }


def _apply_payload(entity: UiSettingsEntity, payload: dict, scope_key: str) -> UiSettingsEntity:
    merged_payload = _clone_payload(payload)
    entity.scope_key = scope_key
    entity.show_minimap = bool(merged_payload["show_minimap"])
    entity.show_marker_icons = bool(merged_payload["show_marker_icons"])
    entity.show_path_arrows = bool(merged_payload["show_path_arrows"])
    entity.show_status_legend = bool(merged_payload["show_status_legend"])
    entity.show_topology_edge_speed = bool(merged_payload["show_topology_edge_speed"])
    entity.show_runtime_segment_type = bool(merged_payload["show_runtime_segment_type"])
    entity.show_runtime_conflict_reason = bool(merged_payload["show_runtime_conflict_reason"])
    entity.show_selected_agv_runtime_overlay = bool(merged_payload["show_selected_agv_runtime_overlay"])
    entity.status_legend_layout = str(merged_payload["status_legend_layout"])
    entity.status_legend_opacity = float(merged_payload["status_legend_opacity"])
    entity.base_speed = float(merged_payload["base_speed"])
    entity.follow_distance = float(merged_payload["follow_distance"])
    entity.deadlock_timeout_sec = float(merged_payload["deadlock_timeout_sec"])
    entity.idle_return_timeout_sec = float(merged_payload["idle_return_timeout_sec"])
    entity.idle_charge_timeout_sec = float(merged_payload["idle_charge_timeout_sec"])
    entity.idle_charge_battery_threshold = float(merged_payload["idle_charge_battery_threshold"])
    entity.low_battery_threshold = float(merged_payload["low_battery_threshold"])
    entity.battery_active_drain_per_sec = float(merged_payload["battery_active_drain_per_sec"])
    entity.battery_waiting_drain_per_sec = float(merged_payload["battery_waiting_drain_per_sec"])
    entity.battery_idle_drain_per_sec = float(merged_payload["battery_idle_drain_per_sec"])
    entity.battery_parking_idle_drain_per_sec = float(merged_payload["battery_parking_idle_drain_per_sec"])
    entity.battery_charge_per_sec = float(merged_payload["battery_charge_per_sec"])
    entity.compare_display_mode = str(merged_payload["compare_display_mode"])
    entity.panel_sections = dict(merged_payload.get("panel_sections") or {})
    return entity


def _clone_payload(default_settings: dict) -> dict:
    payload = deepcopy(UI_SETTINGS_STORE_DEFAULTS)
    overrides = deepcopy(default_settings or {})
    panel_section_overrides = overrides.pop("panel_sections", None)
    payload.update(overrides)
    if isinstance(panel_section_overrides, dict):
        payload["panel_sections"] = {
            **dict(UI_SETTINGS_STORE_DEFAULTS.get("panel_sections") or {}),
            **panel_section_overrides,
        }
    return payload


def _ensure_scope_entity(default_settings: dict, scope_key: str) -> UiSettingsEntity:
    with get_db_session() as session:
        entity = session.execute(_scope_query(scope_key)).scalar_one_or_none()
        if entity is not None:
            return entity

        legacy = session.execute(_legacy_query()).scalar_one_or_none()
        if legacy is not None:
            payload = _entity_to_payload(legacy)
        else:
            payload = _clone_payload(default_settings)

        next_id = session.execute(select(UiSettingsEntity.id).order_by(UiSettingsEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
        entity = _apply_payload(UiSettingsEntity(id=next_id + 1), payload, scope_key)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return entity


def get_ui_settings(default_settings: dict) -> dict:
    _ensure_schema()
    entity = _ensure_scope_entity(default_settings, _current_scope())
    return _entity_to_payload(entity)


def save_ui_settings(settings_payload: dict) -> dict:
    _ensure_schema()
    payload = deepcopy(settings_payload)
    scope_key = _current_scope()
    with get_db_session() as session:
        entity = session.execute(_scope_query(scope_key)).scalar_one_or_none()
        if entity is None:
            next_id = session.execute(select(UiSettingsEntity.id).order_by(UiSettingsEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
            entity = UiSettingsEntity(id=next_id + 1)
        entity = _apply_payload(entity, payload, scope_key)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return _entity_to_payload(entity)
