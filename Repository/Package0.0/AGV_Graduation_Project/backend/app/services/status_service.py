from __future__ import annotations

import re
import time

from app.models.map_profile import MapProfile, MapProfileCell
from app.models.map_preset import MapPreset, MapPresetCell
from app.models.map_topology import MapTopology, MapTopologyEdge, MapTopologyNode
from app.core.settings import get_settings
from app.repositories.agv_repository import list_agvs
from app.repositories.map_profile_repository import (
    get_map_profile_by_key,
    list_map_profiles,
    remove_map_profile,
    upsert_map_profile,
)
from app.repositories.point_repository import list_points
from app.repositories.task_repository import list_tasks
from app.repositories.map_preset_repository import (
    get_map_preset_by_key,
    list_map_presets,
    remove_map_preset,
    upsert_map_preset,
)
from app.repositories.template_repository import list_task_templates
from app.repositories.ui_settings_repository import get_ui_settings as get_ui_settings_store
from app.repositories.ui_settings_repository import save_ui_settings as save_ui_settings_store
from app.services.operation_audit_service import build_first_audit_map, build_latest_audit_map, record_operation_audit
from app.utils.api_error import raise_api_error
from app.utils.map_validity import (
    ACTIVE_TASK_INVALIDATION_STATUSES,
    build_map_validity_context,
    build_point_validity_payload,
    build_task_invalidity_payload,
    build_template_validity_payload,
)
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR
from app.utils.task_chain import mark_task_invalid
from app.utils.warehouse_map import (
    DEFAULT_MAP_PRESETS,
    build_map_profile_payload,
    build_map_preset_payload,
    build_map_topology_signature,
    build_map_topology_summary,
    create_empty_map_topology,
    get_blocked_cell_payload,
    get_blocked_cells,
    get_current_grid_size,
    get_default_blocked_cells,
    get_default_valid_cells,
    get_map_layout_state,
    get_map_profile_cells,
    get_map_profile_definition,
    get_map_profile_valid_cells,
    get_map_profiles_payload,
    get_map_preset_cells,
    get_map_preset_valid_cells,
    get_map_presets_payload,
    get_valid_cell_payload,
    get_valid_cells,
    get_topology_node_default_capacity,
    normalize_map_topology_payload,
    set_layout_cells,
)


DEFAULT_UI_SETTINGS = {
    "show_minimap": True,
    "show_marker_icons": True,
    "show_path_arrows": False,
    "show_business_points": True,
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

FORCE_APPLY_ALLOWED_BLOCKERS = {"agvs_out_of_bounds", "blocked_cells_out_of_bounds"}


def _filter_occupied_cells(cells: set[tuple[int, int]]):
    occupied = {(agv.x, agv.y) for agv in list_agvs() if agv.status != "maintenance"}
    filtered = {cell for cell in cells if cell not in occupied}
    skipped = sorted(cell for cell in cells if cell in occupied)
    return filtered, skipped


def _normalize_requested_cells(cells: list, grid_cols: int, grid_rows: int) -> set[tuple[int, int]]:
    normalized = set()
    for cell in cells:
        x = int(cell.x)
        y = int(cell.y)
        if 0 <= x < grid_cols and 0 <= y < grid_rows:
            normalized.add((x, y))
    return normalized


def _build_full_grid_cells(grid_cols: int, grid_rows: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(int(grid_cols))
        for y in range(int(grid_rows))
    }


def _normalize_requested_valid_cells(
    cells: list | None,
    grid_cols: int,
    grid_rows: int,
) -> set[tuple[int, int]]:
    if cells is None:
        return get_default_valid_cells(grid_cols, grid_rows)
    normalized = _normalize_requested_cells(cells, grid_cols, grid_rows)
    return normalized or get_default_valid_cells(grid_cols, grid_rows)


def _normalize_blocked_for_valid_cells(
    blocked_cells: set[tuple[int, int]],
    valid_cells: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    return {(int(x), int(y)) for x, y in blocked_cells if (int(x), int(y)) in valid_cells}


def _cells_to_payload(cells: set[tuple[int, int]]) -> list[dict[str, int]]:
    return [{"x": int(x), "y": int(y)} for x, y in sorted(cells)]


def _is_within_grid(x: int, y: int, grid_cols: int, grid_rows: int) -> bool:
    return 0 <= int(x) < int(grid_cols) and 0 <= int(y) < int(grid_rows)


def _build_custom_preset_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    slug = slug or "preset"
    return f"custom_{slug}_{int(time.time() * 1000)}"


def _build_custom_profile_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    slug = slug or "profile"
    return f"custom_profile_{slug}_{int(time.time() * 1000)}"


def _collect_existing_profile_names() -> set[str]:
    names = set()
    for profile_payload in get_map_profiles_payload():
        name = str(profile_payload.get("name") or "").strip()
        if name:
            names.add(name.casefold())
    for profile in list_map_profiles():
        name = str(getattr(profile, "custom_name", "") or "").strip()
        if name:
            names.add(name.casefold())
    return names


def _resolve_unique_profile_name(requested_name: str) -> tuple[str, bool]:
    normalized = requested_name.strip()
    if not normalized:
        return "", False

    existing_names = _collect_existing_profile_names()
    if normalized.casefold() not in existing_names:
        return normalized, False

    suffix = 2
    while True:
        candidate = f"{normalized} ({suffix})"
        if candidate.casefold() not in existing_names:
            return candidate, True
        suffix += 1


def _get_custom_map_preset_cells(
    preset_key: str,
    grid_cols: int,
    grid_rows: int,
) -> set[tuple[int, int]]:
    preset = get_map_preset_by_key(preset_key)
    if preset is None:
        raise KeyError(preset_key)
    return {
        (int(cell.x), int(cell.y))
        for cell in preset.blocked_cells
        if 0 <= int(cell.x) < grid_cols and 0 <= int(cell.y) < grid_rows
    }


def _get_custom_map_preset_valid_cells(
    preset_key: str,
    grid_cols: int,
    grid_rows: int,
) -> set[tuple[int, int]]:
    preset = get_map_preset_by_key(preset_key)
    if preset is None:
        raise KeyError(preset_key)
    cells = {
        (int(cell.x), int(cell.y))
        for cell in preset.valid_cells
        if 0 <= int(cell.x) < grid_cols and 0 <= int(cell.y) < grid_rows
    }
    return cells or get_default_valid_cells(grid_cols, grid_rows)


def _get_custom_map_profile_cells(profile_key: str) -> set[tuple[int, int]]:
    profile = get_map_profile_by_key(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    return {(int(cell.x), int(cell.y)) for cell in profile.blocked_cells}


def _get_custom_map_profile_valid_cells(profile_key: str) -> set[tuple[int, int]]:
    profile = get_map_profile_by_key(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    cells = {(int(cell.x), int(cell.y)) for cell in profile.valid_cells}
    return cells or get_default_valid_cells(int(profile.grid_cols), int(profile.grid_rows))


def _normalize_cells_signature(cells: set[tuple[int, int]] | list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((int(x), int(y)) for x, y in cells))


def _topology_payload_to_model(topology_payload: dict[str, object] | None) -> MapTopology | None:
    normalized = topology_payload or create_empty_map_topology()
    if not normalized.get("nodes") and not normalized.get("edges"):
        return None
    return MapTopology(
        topology_version=int(normalized.get("topology_version", 1)),
        nodes=[
            MapTopologyNode(
                key=str(node["key"]),
                x=int(node["x"]),
                y=int(node["y"]),
                label=node.get("label"),
                node_type=str(node.get("node_type") or "waypoint"),
                capacity=int(node.get("capacity") or get_topology_node_default_capacity(node.get("node_type") or "waypoint")),
            )
            for node in normalized.get("nodes", [])
        ],
        edges=[
            MapTopologyEdge(
                key=str(edge["key"]),
                source=str(edge["source"]),
                target=str(edge["target"]),
                direction=str(edge.get("direction") or "bidirectional"),
                lane_type=str(edge.get("lane_type") or "main"),
                weight=float(edge.get("weight") or 1.0),
                speed_multiplier=float(edge.get("speed_multiplier") or 1.0),
            )
            for edge in normalized.get("edges", [])
        ],
        stations=list(normalized.get("stations", [])),
        parking_nodes=list(normalized.get("parking_nodes", [])),
        charge_nodes=list(normalized.get("charge_nodes", [])),
    )


def _get_custom_map_profile_topology(profile_key: str) -> dict[str, object]:
    profile = get_map_profile_by_key(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    return normalize_map_topology_payload(
        profile.topology,
        int(profile.grid_cols),
        int(profile.grid_rows),
        _get_custom_map_profile_valid_cells(profile_key),
    )


def _is_force_apply_allowed(precheck: dict) -> bool:
    blockers = set(precheck.get("blockers") or [])
    if not blockers:
        return False
    if not blockers.issubset(FORCE_APPLY_ALLOWED_BLOCKERS):
        return False
    return (
        int(precheck.get("active_task_count", 0)) == 0
        and int(precheck.get("busy_agv_count", 0)) == 0
        and int(precheck.get("point_overflow_count", 0)) == 0
        and int(precheck.get("template_overflow_count", 0)) == 0
    )


def _find_nearest_available_cell(
    origin_x: int,
    origin_y: int,
    grid_cols: int,
    grid_rows: int,
    blocked_cells: set[tuple[int, int]],
    reserved_cells: set[tuple[int, int]],
) -> tuple[int, int] | None:
    candidates = []
    for x in range(int(grid_cols)):
        for y in range(int(grid_rows)):
            cell = (x, y)
            if cell in blocked_cells or cell in reserved_cells:
                continue
            distance = abs(int(origin_x) - x) + abs(int(origin_y) - y)
            candidates.append((distance, abs(int(origin_y) - y), abs(int(origin_x) - x), y, x, cell))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][-1]


def _relocate_out_of_bounds_agvs_for_force_apply(
    requested_grid_cols: int,
    requested_grid_rows: int,
    blocked_cells: set[tuple[int, int]],
) -> list[dict]:
    all_agvs = list_agvs()
    reserved_cells = {
        (int(agv.x), int(agv.y))
        for agv in all_agvs
        if _is_within_grid(agv.x, agv.y, requested_grid_cols, requested_grid_rows)
    }
    relocated = []
    for agv in sorted(all_agvs, key=lambda item: int(item.id)):
        if _is_within_grid(agv.x, agv.y, requested_grid_cols, requested_grid_rows):
            continue
        next_cell = _find_nearest_available_cell(
            origin_x=int(agv.x),
            origin_y=int(agv.y),
            grid_cols=requested_grid_cols,
            grid_rows=requested_grid_rows,
            blocked_cells=blocked_cells,
            reserved_cells=reserved_cells,
        )
        if next_cell is None:
            raise_api_error(400, "map_profile_force_no_safe_agv_cell")
        previous = {"x": int(agv.x), "y": int(agv.y)}
        agv.x = int(next_cell[0])
        agv.y = int(next_cell[1])
        reserved_cells.add(next_cell)
        relocated.append(
            {
                "id": int(agv.id),
                "from": previous,
                "to": {"x": int(next_cell[0]), "y": int(next_cell[1])},
            }
        )
    return relocated


def _build_custom_profile_payload(profile: MapProfile) -> dict:
    cells = {(int(cell.x), int(cell.y)) for cell in profile.blocked_cells}
    valid_cells = {(int(cell.x), int(cell.y)) for cell in profile.valid_cells} or get_default_valid_cells(
        int(profile.grid_cols),
        int(profile.grid_rows),
    )
    topology = normalize_map_topology_payload(
        profile.topology,
        int(profile.grid_cols),
        int(profile.grid_rows),
        valid_cells,
    )
    payload = build_map_profile_payload(
        key=profile.key,
        name=profile.custom_name,
        description=profile.description,
        grid_cols=int(profile.grid_cols),
        grid_rows=int(profile.grid_rows),
        valid_cells=valid_cells,
        topology=topology,
        custom=True,
        editable=True,
        deletable=True,
    ) | {
        "blocked_count": len(cells),
        "blocked_cells": _cells_to_payload(cells),
    }
    return _attach_map_profile_audit(payload)


def _resolve_current_profile_payload(
    grid_cols: int,
    grid_rows: int,
    blocked_cells: set[tuple[int, int]] | None = None,
    valid_cells: set[tuple[int, int]] | None = None,
    topology: dict[str, object] | None = None,
) -> dict:
    normalized_cells = _normalize_cells_signature(blocked_cells or get_blocked_cells(grid_cols, grid_rows))
    normalized_valid_cells = _normalize_cells_signature(valid_cells or get_valid_cells(grid_cols, grid_rows))
    normalized_topology_signature = build_map_topology_signature(
        topology,
        grid_cols,
        grid_rows,
        valid_cells or get_valid_cells(grid_cols, grid_rows),
    )

    for profile in list_map_profiles():
        profile_cells = {(int(cell.x), int(cell.y)) for cell in profile.blocked_cells}
        profile_valid_cells = {(int(cell.x), int(cell.y)) for cell in profile.valid_cells} or get_default_valid_cells(
            int(profile.grid_cols),
            int(profile.grid_rows),
        )
        profile_topology = normalize_map_topology_payload(
            profile.topology,
            int(profile.grid_cols),
            int(profile.grid_rows),
            profile_valid_cells,
        )
        if (
            int(profile.grid_cols) == int(grid_cols)
            and int(profile.grid_rows) == int(grid_rows)
            and _normalize_cells_signature(profile_cells) == normalized_cells
            and _normalize_cells_signature(profile_valid_cells) == normalized_valid_cells
            and build_map_topology_signature(
                profile_topology,
                int(profile.grid_cols),
                int(profile.grid_rows),
                profile_valid_cells,
            ) == normalized_topology_signature
        ):
            return _build_custom_profile_payload(profile)

    for profile_payload in get_map_profiles_payload():
        definition = get_map_profile_definition(profile_payload["key"])
        if definition is None:
            continue
        if (
            int(definition["grid_cols"]) == int(grid_cols)
            and int(definition["grid_rows"]) == int(grid_rows)
            and _normalize_cells_signature(definition["cells"]) == normalized_cells
            and _normalize_cells_signature(definition["valid_cells"]) == normalized_valid_cells
            and build_map_topology_signature(
                definition.get("topology"),
                int(definition["grid_cols"]),
                int(definition["grid_rows"]),
                definition["valid_cells"],
            ) == normalized_topology_signature
        ):
            return profile_payload

    runtime_valid_cells = valid_cells or get_valid_cells(grid_cols, grid_rows)
    runtime_topology = normalize_map_topology_payload(topology, grid_cols, grid_rows, runtime_valid_cells)
    return build_map_profile_payload(
        key=f"runtime_{int(grid_cols)}x{int(grid_rows)}",
        name={
            "zh": "运行时地图方案",
            "ja": "実行時マップ構成",
            "en": "Runtime Map Profile",
        },
        description={
            "zh": "当前地图布局与已有内置方案不完全一致，系统会将其识别为适合异形地图或自定义路网的运行时方案。",
            "ja": "現在のマップ構成は既存の内蔵プロファイルと完全には一致しないため、異形マップやカスタム路網向けの実行時プロファイルとして扱われます。",
            "en": "The active map layout no longer matches a built-in profile exactly and is treated as a runtime transition state for custom or irregular layouts.",
        },
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        valid_cells=runtime_valid_cells,
        topology=runtime_topology,
        custom=True,
        editable=False,
        deletable=False,
    ) | {
        "blocked_count": len(normalized_cells),
        "blocked_cells": _cells_to_payload(set(normalized_cells)),
    }


def _attach_map_profile_audit(payload: dict) -> dict:
    profile_key = str(payload.get("key") or "")
    if not profile_key:
        return payload
    created = build_first_audit_map("map_profile", [profile_key], create_actions={"save", "import"}).get(profile_key)
    latest = build_latest_audit_map("map_profile", [profile_key]).get(profile_key)
    enriched = dict(payload)
    if created is not None:
        enriched["created_by"] = created.operator_display_name
        enriched["created_by_role"] = created.operator_role
        enriched["created_by_at"] = created.performed_at
    if latest is not None:
        enriched["last_operator"] = latest.operator_display_name
        enriched["last_operator_role"] = latest.operator_role
        enriched["last_operator_at"] = latest.performed_at
        enriched["last_operator_action"] = latest.action
    return enriched


def get_agv_status_map():
    return AGV_STATUS_COLOR


def get_task_status_map():
    return TASK_STATUS_COLOR


def get_map_layout():
    state = get_map_layout_state()
    grid_cols = int(state["grid_cols"])
    grid_rows = int(state["grid_rows"])
    valid_cells = get_valid_cells(grid_cols, grid_rows)
    blocked_cells = get_blocked_cells(grid_cols, grid_rows)
    topology = normalize_map_topology_payload(state.get("topology"), grid_cols, grid_rows, valid_cells)
    return {
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": get_blocked_cell_payload(grid_cols, grid_rows),
        "blocked_count": len(blocked_cells),
        "valid_cells": get_valid_cell_payload(grid_cols, grid_rows),
        "valid_count": len(valid_cells),
        "is_irregular": len(valid_cells) != grid_cols * grid_rows,
        "topology": topology,
        "topology_summary": build_map_topology_summary(topology),
        "has_topology": bool(build_map_topology_summary(topology).get("enabled")),
    }


def _normalize_ui_settings(payload) -> dict:
    sections = (
        payload.panel_sections.model_dump(by_alias=True)
        if hasattr(payload.panel_sections, "model_dump")
        else dict(payload["panel_sections"])
    )
    opacity = max(0.2, min(0.9, float(payload.status_legend_opacity)))
    base_speed = max(0.2, min(6.0, float(payload.base_speed)))
    follow_distance = max(0.25, min(3.0, float(payload.follow_distance)))
    deadlock_timeout_sec = max(1.0, min(20.0, float(payload.deadlock_timeout_sec)))
    idle_return_timeout_sec = max(5.0, min(600.0, float(payload.idle_return_timeout_sec)))
    idle_charge_timeout_sec = max(5.0, min(600.0, float(payload.idle_charge_timeout_sec)))
    low_battery_threshold = max(5.0, min(80.0, float(payload.low_battery_threshold)))
    idle_charge_battery_threshold = max(low_battery_threshold, min(95.0, float(payload.idle_charge_battery_threshold)))
    battery_active_drain_per_sec = max(0.01, min(10.0, float(payload.battery_active_drain_per_sec)))
    battery_waiting_drain_per_sec = max(0.0, min(5.0, float(payload.battery_waiting_drain_per_sec)))
    battery_idle_drain_per_sec = max(0.0, min(2.0, float(payload.battery_idle_drain_per_sec)))
    battery_parking_idle_drain_per_sec = max(0.0, min(2.0, float(payload.battery_parking_idle_drain_per_sec)))
    battery_charge_per_sec = max(0.1, min(20.0, float(payload.battery_charge_per_sec)))
    return {
        "show_minimap": bool(payload.show_minimap),
        "show_marker_icons": bool(payload.show_marker_icons),
        "show_path_arrows": bool(payload.show_path_arrows),
        "show_business_points": bool(payload.show_business_points),
        "show_status_legend": bool(payload.show_status_legend),
        "show_topology_edge_speed": bool(payload.show_topology_edge_speed),
        "show_runtime_segment_type": bool(payload.show_runtime_segment_type),
        "show_runtime_conflict_reason": bool(payload.show_runtime_conflict_reason),
        "show_selected_agv_runtime_overlay": bool(payload.show_selected_agv_runtime_overlay),
        "status_legend_layout": payload.status_legend_layout,
        "status_legend_opacity": opacity,
        "base_speed": base_speed,
        "follow_distance": follow_distance,
        "deadlock_timeout_sec": deadlock_timeout_sec,
        "idle_return_timeout_sec": idle_return_timeout_sec,
        "idle_charge_timeout_sec": idle_charge_timeout_sec,
        "idle_charge_battery_threshold": idle_charge_battery_threshold,
        "low_battery_threshold": low_battery_threshold,
        "battery_active_drain_per_sec": battery_active_drain_per_sec,
        "battery_waiting_drain_per_sec": battery_waiting_drain_per_sec,
        "battery_idle_drain_per_sec": battery_idle_drain_per_sec,
        "battery_parking_idle_drain_per_sec": battery_parking_idle_drain_per_sec,
        "battery_charge_per_sec": battery_charge_per_sec,
        "compare_display_mode": payload.compare_display_mode,
        "panel_sections": {
            "control": bool(sections.get("control", DEFAULT_UI_SETTINGS["panel_sections"]["control"])),
            "queue": bool(sections.get("queue", DEFAULT_UI_SETTINGS["panel_sections"]["queue"])),
            "templates": bool(sections.get("templates", DEFAULT_UI_SETTINGS["panel_sections"]["templates"])),
            "points": bool(sections.get("points", DEFAULT_UI_SETTINGS["panel_sections"]["points"])),
            "json": bool(sections.get("json", DEFAULT_UI_SETTINGS["panel_sections"]["json"])),
            "experiments": bool(sections.get("experiments", DEFAULT_UI_SETTINGS["panel_sections"]["experiments"])),
            "ai": bool(sections.get("ai", DEFAULT_UI_SETTINGS["panel_sections"]["ai"])),
            "operations": bool(sections.get("operations", DEFAULT_UI_SETTINGS["panel_sections"]["operations"])),
        },
    }


def get_ui_settings():
    payload = get_ui_settings_store(DEFAULT_UI_SETTINGS)
    return {
        **payload,
        "data_backend": get_settings().data_backend,
    }


def update_ui_settings(payload):
    normalized = _normalize_ui_settings(payload)
    saved = save_ui_settings_store(normalized)
    return {
        **saved,
        "data_backend": get_settings().data_backend,
        "message": "UI settings updated",
    }


def get_map_presets():
    grid_cols, grid_rows = get_current_grid_size()
    current_profile = _resolve_current_profile_payload(
        grid_cols,
        grid_rows,
        get_blocked_cells(grid_cols, grid_rows),
        get_valid_cells(grid_cols, grid_rows),
    )
    builtin_presets = get_map_presets_payload(grid_cols, grid_rows)
    custom_presets = []
    for preset in list_map_presets():
        cells = {
            (int(cell.x), int(cell.y))
            for cell in preset.blocked_cells
            if 0 <= int(cell.x) < grid_cols and 0 <= int(cell.y) < grid_rows
        }
        valid_cells = {
            (int(cell.x), int(cell.y))
            for cell in preset.valid_cells
            if 0 <= int(cell.x) < grid_cols and 0 <= int(cell.y) < grid_rows
        } or get_default_valid_cells(grid_cols, grid_rows)
        custom_presets.append(
            build_map_preset_payload(
                key=preset.key,
                name=preset.custom_name,
                description=preset.description,
                cells=cells,
                valid_cells=valid_cells,
                custom=True,
                deletable=True,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
                profile_key=current_profile["key"],
            )
        )
    return {
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "presets": builtin_presets + custom_presets,
    }


def get_map_profiles():
    grid_cols, grid_rows = get_current_grid_size()
    blocked_cells = get_blocked_cells(grid_cols, grid_rows)
    valid_cells = get_valid_cells(grid_cols, grid_rows)
    current_topology = normalize_map_topology_payload(
        get_map_layout_state().get("topology"),
        grid_cols,
        grid_rows,
        valid_cells,
    )
    active_tasks = [
        task
        for task in list_tasks()
        if task.status in {"pending", "assigned", "running", "blocked"}
    ]
    busy_agvs = [
        agv
        for agv in list_agvs()
        if agv.status not in {"idle", "maintenance"}
    ]
    can_resize_now = not active_tasks and not busy_agvs
    if active_tasks and busy_agvs:
        resize_lock_reason = "active_tasks_and_busy_agvs"
    elif active_tasks:
        resize_lock_reason = "active_tasks_present"
    elif busy_agvs:
        resize_lock_reason = "agvs_not_idle"
    else:
        resize_lock_reason = "ready"

    custom_profiles = [_build_custom_profile_payload(profile) for profile in list_map_profiles()]
    return {
        "current_profile": _attach_map_profile_audit(
            _resolve_current_profile_payload(grid_cols, grid_rows, blocked_cells, valid_cells, current_topology)
        ),
        "profiles": [_attach_map_profile_audit(profile) for profile in get_map_profiles_payload()] + custom_profiles,
        "can_resize_now": can_resize_now,
        "resize_lock_reason": resize_lock_reason,
        "active_task_count": len(active_tasks),
        "busy_agv_count": len(busy_agvs),
    }


def get_map_profile_detail(profile_key: str):
    custom_profile = get_map_profile_by_key(profile_key)
    if custom_profile is not None:
        cells = {(int(cell.x), int(cell.y)) for cell in custom_profile.blocked_cells}
        valid_cells = {(int(cell.x), int(cell.y)) for cell in custom_profile.valid_cells} or get_default_valid_cells(
            int(custom_profile.grid_cols),
            int(custom_profile.grid_rows),
        )
        topology = normalize_map_topology_payload(
            custom_profile.topology,
            int(custom_profile.grid_cols),
            int(custom_profile.grid_rows),
            valid_cells,
        )
        return _attach_map_profile_audit(build_map_profile_payload(
            key=custom_profile.key,
            name=custom_profile.custom_name,
            description=custom_profile.description,
            grid_cols=int(custom_profile.grid_cols),
            grid_rows=int(custom_profile.grid_rows),
            valid_cells=valid_cells,
            topology=topology,
            custom=True,
            editable=True,
            deletable=True,
        ) | {
            "blocked_count": len(cells),
            "blocked_cells": _cells_to_payload(cells),
        })

    profile_definition = get_map_profile_definition(profile_key)
    if profile_definition is None:
        raise_api_error(404, "profile_not_found")

    cells = {(int(x), int(y)) for x, y in profile_definition["cells"]}
    valid_cells = set(profile_definition["valid_cells"])
    topology = normalize_map_topology_payload(
        profile_definition.get("topology"),
        int(profile_definition["grid_cols"]),
        int(profile_definition["grid_rows"]),
        valid_cells,
    )
    return _attach_map_profile_audit(build_map_profile_payload(
        key=profile_definition["key"],
        name=profile_definition["name"],
        description=profile_definition["description"],
        grid_cols=int(profile_definition["grid_cols"]),
        grid_rows=int(profile_definition["grid_rows"]),
        valid_cells=valid_cells,
        topology=topology,
        custom=bool(profile_definition.get("custom", False)),
        editable=False,
        deletable=False,
    ) | {
        "blocked_count": len(cells),
        "blocked_cells": _cells_to_payload(cells),
    })


def get_map_resize_precheck(requested_grid_cols: int, requested_grid_rows: int):
    requested_grid_cols = int(requested_grid_cols)
    requested_grid_rows = int(requested_grid_rows)
    if requested_grid_cols <= 0 or requested_grid_rows <= 0:
        raise_api_error(400, "invalid_grid_size")

    current_grid_cols, current_grid_rows = get_current_grid_size()
    all_agvs = list_agvs()
    active_tasks = [
        task
        for task in list_tasks()
        if task.status in {"pending", "assigned", "running", "blocked"}
    ]
    busy_agvs = [
        agv
        for agv in all_agvs
        if agv.status not in {"idle", "maintenance"}
    ]
    agv_overflows = [
        {
            "id": int(agv.id),
            "status": agv.status,
            "x": int(agv.x),
            "y": int(agv.y),
        }
        for agv in all_agvs
        if not _is_within_grid(agv.x, agv.y, requested_grid_cols, requested_grid_rows)
    ]
    point_overflows = [
        {
            "id": point.id,
            "name": point.custom_name or point.name_key or point.id,
            "x": int(point.x),
            "y": int(point.y),
        }
        for point in list_points()
        if not _is_within_grid(point.x, point.y, requested_grid_cols, requested_grid_rows)
    ]

    template_overflows = []
    for template in list_task_templates():
        invalid_stage_indexes = []
        for stage in template.stages:
            if not (
                _is_within_grid(stage.start_x, stage.start_y, requested_grid_cols, requested_grid_rows)
                and _is_within_grid(stage.end_x, stage.end_y, requested_grid_cols, requested_grid_rows)
            ):
                invalid_stage_indexes.append(int(stage.index))
        if invalid_stage_indexes:
            template_overflows.append(
                {
                    "id": template.id,
                    "name": template.custom_name or template.name_key or template.id,
                    "invalid_stage_indexes": invalid_stage_indexes,
                }
            )

    blocked_overflows = [
        {"x": int(x), "y": int(y)}
        for x, y in sorted(get_blocked_cells(current_grid_cols, current_grid_rows))
        if not _is_within_grid(x, y, requested_grid_cols, requested_grid_rows)
    ]

    blockers = []
    if active_tasks:
        blockers.append("active_tasks_present")
    if busy_agvs:
        blockers.append("agvs_not_idle")
    if agv_overflows:
        blockers.append("agvs_out_of_bounds")
    if point_overflows:
        blockers.append("points_out_of_bounds")
    if template_overflows:
        blockers.append("templates_out_of_bounds")
    if blocked_overflows:
        blockers.append("blocked_cells_out_of_bounds")

    return {
        "current_grid_cols": current_grid_cols,
        "current_grid_rows": current_grid_rows,
        "requested_grid_cols": requested_grid_cols,
        "requested_grid_rows": requested_grid_rows,
        "can_apply": len(blockers) == 0,
        "force_apply_allowed": _is_force_apply_allowed(
            {
                "blockers": blockers,
                "active_task_count": len(active_tasks),
                "busy_agv_count": len(busy_agvs),
                "point_overflow_count": len(point_overflows),
                "template_overflow_count": len(template_overflows),
            }
        ),
        "blockers": blockers,
        "active_task_count": len(active_tasks),
        "busy_agv_count": len(busy_agvs),
        "agv_overflow_count": len(agv_overflows),
        "point_overflow_count": len(point_overflows),
        "template_overflow_count": len(template_overflows),
        "blocked_overflow_count": len(blocked_overflows),
        "agv_overflows": agv_overflows[:8],
        "point_overflows": point_overflows[:8],
        "template_overflows": template_overflows[:8],
        "blocked_overflows": blocked_overflows[:8],
    }


def _build_map_layout_impact_preview(
    *,
    grid_cols: int,
    grid_rows: int,
    blocked_cells: set[tuple[int, int]],
    valid_cells: set[tuple[int, int]],
    topology: dict | None,
):
    context = build_map_validity_context(
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        blocked_cells=blocked_cells,
        valid_cells=valid_cells,
        topology=topology,
    )
    agv_conflicts = []
    agv_by_id = {}

    for agv in list_agvs():
        agv_by_id[int(agv.id)] = agv
        validity = build_point_validity_payload(agv, context)
        if validity["is_invalid"]:
            agv_conflicts.append(
                {
                    "id": int(agv.id),
                    "status": str(getattr(agv, "status", "") or ""),
                    "x": int(agv.x),
                    "y": int(agv.y),
                    "invalid_reason": validity["invalid_reason"],
                }
            )

    invalid_points = [
        {
            "id": payload["id"],
            "name": payload.get("custom_name") or payload.get("name_key") or payload["id"],
            "x": int(payload["x"]),
            "y": int(payload["y"]),
            "invalid_reason": payload["invalid_reason"],
        }
        for payload in (build_point_validity_payload(point, context) for point in list_points())
        if payload["is_invalid"]
    ]

    invalid_templates = [
        {
            "id": payload["id"],
            "name": payload.get("custom_name") or payload.get("name_key") or payload["id"],
            "invalid_reason": payload["invalid_reason"],
            "invalid_stage_indexes": payload["invalid_stage_indexes"],
        }
        for payload in (build_template_validity_payload(template, context) for template in list_task_templates())
        if payload["is_invalid"]
    ]

    invalid_tasks = []
    for task in list_tasks():
        if str(getattr(task, "status", "") or "") not in ACTIVE_TASK_INVALIDATION_STATUSES:
            continue
        related_agv = None
        if getattr(task, "agv_id", None) is not None:
            related_agv = agv_by_id.get(int(task.agv_id))
        if related_agv is None:
            related_agv = next((agv for agv in agv_by_id.values() if getattr(agv, "task_id", None) == task.id), None)
        payload = build_task_invalidity_payload(task, context, agv=related_agv)
        if payload["is_invalid"]:
            invalid_tasks.append(payload)

    blockers = []
    if agv_conflicts:
        blockers.append("agvs_in_physical_cells")
    if invalid_points:
        blockers.append("points_invalid")
    if invalid_templates:
        blockers.append("templates_invalid")
    if invalid_tasks:
        blockers.append("tasks_invalid")

    return {
        "can_apply": len(blockers) == 0,
        "force_apply_allowed": len(agv_conflicts) == 0,
        "blockers": blockers,
        "agv_conflicts": agv_conflicts,
        "agv_conflict_count": len(agv_conflicts),
        "invalid_points": invalid_points,
        "invalid_point_count": len(invalid_points),
        "invalid_templates": invalid_templates,
        "invalid_template_count": len(invalid_templates),
        "invalidated_tasks": invalid_tasks,
        "invalidated_task_count": len(invalid_tasks),
    }


def _apply_invalidated_tasks_for_map_change(invalidated_tasks: list[dict], actor: dict | None = None):
    if not invalidated_tasks:
        return []

    task_by_id = {int(task.id): task for task in list_tasks()}
    agvs = list_agvs()
    agv_by_id = {int(agv.id): agv for agv in agvs}
    invalidated = []

    for item in invalidated_tasks:
        task = task_by_id.get(int(item["id"]))
        if task is None:
            continue

        previous_status = str(getattr(task, "status", "") or "")
        related_agv = None
        if getattr(task, "agv_id", None) is not None:
            related_agv = agv_by_id.get(int(task.agv_id))
        if related_agv is None:
            related_agv = next((agv for agv in agvs if getattr(agv, "task_id", None) == task.id), None)

        if related_agv is not None:
            if getattr(related_agv, "task_id", None) == task.id:
                related_agv.task_id = None
            if str(getattr(related_agv, "status", "") or "") not in {"fault", "emergency_stop", "maintenance"}:
                related_agv.status = "idle"
            related_agv.clear_motion(motion_state=str(getattr(related_agv, "status", "") or "idle"))

        mark_task_invalid(
            task,
            str(item.get("invalid_reason") or "map_invalid:unreachable"),
            getattr(task, "dispatch_algorithm", None),
        )
        record_operation_audit(
            "task",
            task.id,
            "invalidate",
            actor,
            {
                "source": "map_layout",
                "previous_status": previous_status,
                "reason": task.dispatch_reason,
                "invalid_stage_indexes": list(item.get("invalid_stage_indexes") or []),
            },
        )
        invalidated.append(
            {
                "id": int(task.id),
                "previous_status": previous_status,
                "invalid_reason": task.dispatch_reason,
                "invalid_stage_indexes": list(item.get("invalid_stage_indexes") or []),
            }
        )

    return invalidated


def resize_map_layout(requested_grid_cols: int, requested_grid_rows: int, actor: dict | None = None):
    precheck = get_map_resize_precheck(requested_grid_cols, requested_grid_rows)
    if not precheck["can_apply"]:
        raise_api_error(
            400,
            "map_resize_blocked",
            blockers=precheck["blockers"],
            active_task_count=precheck["active_task_count"],
            busy_agv_count=precheck["busy_agv_count"],
            agv_overflow_count=precheck["agv_overflow_count"],
            point_overflow_count=precheck["point_overflow_count"],
            template_overflow_count=precheck["template_overflow_count"],
            blocked_overflow_count=precheck["blocked_overflow_count"],
        )

    current_grid_cols, current_grid_rows = get_current_grid_size()
    current_cells = get_blocked_cells(current_grid_cols, current_grid_rows)
    current_valid_cells = get_valid_cells(current_grid_cols, current_grid_rows)
    current_topology = normalize_map_topology_payload(
        get_map_layout_state().get("topology"),
        current_grid_cols,
        current_grid_rows,
        current_valid_cells,
    )
    full_current_layout = _build_full_grid_cells(current_grid_cols, current_grid_rows)
    if current_valid_cells == full_current_layout:
        next_valid_cells = get_default_valid_cells(requested_grid_cols, requested_grid_rows)
    else:
        next_valid_cells = {
            (x, y)
            for x, y in current_valid_cells
            if _is_within_grid(x, y, requested_grid_cols, requested_grid_rows)
        }
        if not next_valid_cells:
            next_valid_cells = get_default_valid_cells(requested_grid_cols, requested_grid_rows)
    updated_state = set_layout_cells(
        current_cells,
        next_valid_cells,
        requested_grid_cols,
        requested_grid_rows,
        topology=current_topology,
    )
    updated = updated_state["blocked_cells"]
    updated_valid_cells = updated_state["valid_cells"]
    updated_topology = updated_state["topology"]
    record_operation_audit(
        "map_layout",
        "global",
        "resize",
        actor,
        {
            "before_grid_cols": current_grid_cols,
            "before_grid_rows": current_grid_rows,
            "grid_cols": int(requested_grid_cols),
            "grid_rows": int(requested_grid_rows),
            "blocked_count": len(updated),
            "valid_count": len(updated_valid_cells),
            "topology_node_count": len(updated_topology.get("nodes", [])),
            "topology_edge_count": len(updated_topology.get("edges", [])),
        },
    )
    return {
        "message": "Map size updated",
        "grid_cols": int(requested_grid_cols),
        "grid_rows": int(requested_grid_rows),
        "blocked_cells": _cells_to_payload(updated),
        "blocked_count": len(updated),
        "valid_cells": _cells_to_payload(updated_valid_cells),
        "valid_count": len(updated_valid_cells),
        "is_irregular": len(updated_valid_cells) != int(requested_grid_cols) * int(requested_grid_rows),
        "topology": updated_topology,
        "topology_summary": build_map_topology_summary(updated_topology),
        "current_profile": _resolve_current_profile_payload(
            requested_grid_cols,
            requested_grid_rows,
            updated,
            updated_valid_cells,
            updated_topology,
        ),
        "can_apply": True,
    }


def apply_map_profile(profile_key: str, force: bool = False, actor: dict | None = None):
    profile = get_map_profile_definition(profile_key)
    if profile is None:
        custom_profile = get_map_profile_by_key(profile_key)
        if custom_profile is None:
            raise_api_error(404, "map_profile_not_found")
        profile = {
            "key": custom_profile.key,
            "name": custom_profile.custom_name,
            "description": custom_profile.description,
            "grid_cols": int(custom_profile.grid_cols),
            "grid_rows": int(custom_profile.grid_rows),
            "cells": _get_custom_map_profile_cells(profile_key),
            "valid_cells": _get_custom_map_profile_valid_cells(profile_key),
            "custom": True,
        }

    target_cols = int(profile["grid_cols"])
    target_rows = int(profile["grid_rows"])
    precheck = get_map_resize_precheck(target_cols, target_rows)
    if not precheck["can_apply"]:
        force_apply_allowed = _is_force_apply_allowed(precheck)
        if force and force_apply_allowed:
            if profile.get("custom"):
                raw_profile_cells = _get_custom_map_profile_cells(profile_key)
                raw_profile_valid_cells = _get_custom_map_profile_valid_cells(profile_key)
            else:
                raw_profile_cells = get_map_profile_cells(profile_key)
                raw_profile_valid_cells = get_map_profile_valid_cells(profile_key)
            in_bounds_profile_valid_cells = {
                (int(x), int(y))
                for x, y in raw_profile_valid_cells
                if _is_within_grid(x, y, target_cols, target_rows)
            } or get_default_valid_cells(target_cols, target_rows)
            in_bounds_profile_cells = {
                (int(x), int(y))
                for x, y in raw_profile_cells
                if _is_within_grid(x, y, target_cols, target_rows)
            } & in_bounds_profile_valid_cells
            trimmed_blocked_cells = sorted(raw_profile_cells - in_bounds_profile_cells)
            relocated_agvs = _relocate_out_of_bounds_agvs_for_force_apply(
                requested_grid_cols=target_cols,
                requested_grid_rows=target_rows,
                blocked_cells=_normalize_blocked_for_valid_cells(
                    in_bounds_profile_cells | (_build_full_grid_cells(target_cols, target_rows) - in_bounds_profile_valid_cells),
                    _build_full_grid_cells(target_cols, target_rows),
                ),
            )
            if profile.get("custom"):
                in_bounds_profile_topology = _get_custom_map_profile_topology(profile_key)
            else:
                in_bounds_profile_topology = normalize_map_topology_payload(
                    profile.get("topology"),
                    target_cols,
                    target_rows,
                    in_bounds_profile_valid_cells,
                )
            filtered, skipped = _filter_occupied_cells(in_bounds_profile_cells)
            updated_state = set_layout_cells(
                filtered,
                in_bounds_profile_valid_cells,
                target_cols,
                target_rows,
                topology=in_bounds_profile_topology,
            )
            updated = updated_state["blocked_cells"]
            updated_valid_cells = updated_state["valid_cells"]
            updated_topology = updated_state["topology"]
            record_operation_audit(
                "map_profile",
                profile_key,
                "force_apply",
                actor,
                {
                    "grid_cols": target_cols,
                    "grid_rows": target_rows,
                    "relocated_agv_count": len(relocated_agvs),
                    "trimmed_blocked_cells_count": len(trimmed_blocked_cells),
                    "valid_count": len(updated_valid_cells),
                    "topology_node_count": len(updated_topology.get("nodes", [])),
                    "topology_edge_count": len(updated_topology.get("edges", [])),
                },
            )
            return {
                "message": "Map profile force applied",
                "profile_key": profile_key,
                "grid_cols": target_cols,
                "grid_rows": target_rows,
                "blocked_cells": _cells_to_payload(updated),
                "blocked_count": len(updated),
                "valid_cells": _cells_to_payload(updated_valid_cells),
                "valid_count": len(updated_valid_cells),
                "is_irregular": len(updated_valid_cells) != target_cols * target_rows,
                "topology": updated_topology,
                "topology_summary": build_map_topology_summary(updated_topology),
                "skipped_occupied_cells": _cells_to_payload(set(skipped)),
                "skipped_occupied_count": len(skipped),
                "current_profile": _attach_map_profile_audit(
                    _resolve_current_profile_payload(target_cols, target_rows, updated, updated_valid_cells, updated_topology)
                ),
                "can_apply": True,
                "forced": True,
                "force_apply_allowed": True,
                "relocated_agvs": relocated_agvs,
                "relocated_agv_count": len(relocated_agvs),
                "trimmed_blocked_cells_count": len(trimmed_blocked_cells),
                "trimmed_blocked_cells": [{"x": int(x), "y": int(y)} for x, y in trimmed_blocked_cells],
            }
        raise_api_error(
            400,
            "map_profile_blocked",
            profile_key=profile_key,
            force_apply_allowed=force_apply_allowed,
            blockers=precheck["blockers"],
            active_task_count=precheck["active_task_count"],
            busy_agv_count=precheck["busy_agv_count"],
            agv_overflow_count=precheck["agv_overflow_count"],
            point_overflow_count=precheck["point_overflow_count"],
            template_overflow_count=precheck["template_overflow_count"],
            blocked_overflow_count=precheck["blocked_overflow_count"],
            agv_overflows=precheck["agv_overflows"],
            point_overflows=precheck["point_overflows"],
            template_overflows=precheck["template_overflows"],
            blocked_overflows=precheck["blocked_overflows"],
        )

    if profile.get("custom"):
        profile_cells = _get_custom_map_profile_cells(profile_key)
        profile_valid_cells = _get_custom_map_profile_valid_cells(profile_key)
        profile_topology = _get_custom_map_profile_topology(profile_key)
    else:
        profile_cells = get_map_profile_cells(profile_key)
        profile_valid_cells = get_map_profile_valid_cells(profile_key)
        profile_topology = normalize_map_topology_payload(
            profile.get("topology"),
            target_cols,
            target_rows,
            profile_valid_cells,
        )
    filtered, skipped = _filter_occupied_cells(profile_cells)
    updated_state = set_layout_cells(
        filtered,
        profile_valid_cells,
        target_cols,
        target_rows,
        topology=profile_topology,
    )
    updated = updated_state["blocked_cells"]
    updated_valid_cells = updated_state["valid_cells"]
    updated_topology = updated_state["topology"]
    record_operation_audit(
        "map_profile",
        profile_key,
        "apply",
        actor,
        {
            "grid_cols": target_cols,
            "grid_rows": target_rows,
            "skipped_occupied_count": len(skipped),
            "valid_count": len(updated_valid_cells),
            "topology_node_count": len(updated_topology.get("nodes", [])),
            "topology_edge_count": len(updated_topology.get("edges", [])),
        },
    )
    return {
        "message": "Map profile applied",
        "profile_key": profile_key,
        "grid_cols": target_cols,
        "grid_rows": target_rows,
        "blocked_cells": _cells_to_payload(updated),
        "blocked_count": len(updated),
        "valid_cells": _cells_to_payload(updated_valid_cells),
        "valid_count": len(updated_valid_cells),
        "is_irregular": len(updated_valid_cells) != target_cols * target_rows,
        "topology": updated_topology,
        "topology_summary": build_map_topology_summary(updated_topology),
        "skipped_occupied_cells": _cells_to_payload(set(skipped)),
        "skipped_occupied_count": len(skipped),
        "current_profile": _attach_map_profile_audit(
            _resolve_current_profile_payload(target_cols, target_rows, updated, updated_valid_cells, updated_topology)
        ),
        "can_apply": True,
    }


def save_map_profile(payload, actor: dict | None = None):
    grid_cols = int(payload.grid_cols)
    grid_rows = int(payload.grid_rows)
    requested_name = payload.name.strip()
    if not requested_name:
        raise_api_error(400, "profile_name_required")
    resolved_name, name_adjusted = _resolve_unique_profile_name(requested_name)

    requested = _normalize_requested_cells(payload.blocked_cells, grid_cols, grid_rows)
    requested_valid_cells = _normalize_requested_valid_cells(payload.valid_cells, grid_cols, grid_rows)
    filtered_blocked = _normalize_blocked_for_valid_cells(requested, requested_valid_cells)
    normalized_topology = normalize_map_topology_payload(
        payload.topology,
        grid_cols,
        grid_rows,
        requested_valid_cells,
    )
    profile = MapProfile(
        key=_build_custom_profile_key(resolved_name),
        custom_name=resolved_name,
        description=(payload.description or "").strip() or None,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        blocked_cells=[MapProfileCell(x=x, y=y) for x, y in sorted(filtered_blocked)],
        valid_cells=[MapProfileCell(x=x, y=y) for x, y in sorted(requested_valid_cells)],
        topology=_topology_payload_to_model(normalized_topology),
        custom=True,
    )
    upsert_map_profile(profile)
    action = "import" if str(getattr(payload, "import_source", "") or "").strip() else "save"
    record_operation_audit(
        "map_profile",
        profile.key,
        action,
        actor,
        {
            "requested_name": requested_name,
            "resolved_name": resolved_name,
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "valid_count": len(requested_valid_cells),
            "topology_node_count": len(normalized_topology.get("nodes", [])),
            "topology_edge_count": len(normalized_topology.get("edges", [])),
        },
    )
    return {
        "message": "Map profile saved",
        "profile": _build_custom_profile_payload(profile),
        "requested_name": requested_name,
        "resolved_name": resolved_name,
        "name_adjusted": name_adjusted,
    }


def delete_map_profile(profile_key: str, actor: dict | None = None):
    if get_map_profile_definition(profile_key) is not None:
        raise_api_error(400, "builtin_profile_cannot_be_deleted")

    profile = get_map_profile_by_key(profile_key)
    if profile is None:
        raise_api_error(404, "map_profile_not_found")

    record_operation_audit("map_profile", profile_key, "delete", actor, {"name": profile.custom_name})
    remove_map_profile(profile_key)
    return {
        "message": "Map profile deleted",
        "profile_key": profile_key,
    }


def update_map_layout(
    blocked_cells: list,
    valid_cells: list | None,
    grid_cols: int,
    grid_rows: int,
    topology=None,
    force_apply: bool = False,
    actor: dict | None = None,
):
    requested = {(cell.x, cell.y) for cell in blocked_cells}
    requested_valid_cells = _normalize_requested_valid_cells(valid_cells, grid_cols, grid_rows)
    current_topology = normalize_map_topology_payload(
        get_map_layout_state().get("topology"),
        grid_cols,
        grid_rows,
        requested_valid_cells,
    )
    normalized_topology = (
        normalize_map_topology_payload(topology, grid_cols, grid_rows, requested_valid_cells)
        if topology is not None
        else current_topology
    )

    preview = _build_map_layout_impact_preview(
        grid_cols=int(grid_cols),
        grid_rows=int(grid_rows),
        blocked_cells=requested,
        valid_cells=requested_valid_cells,
        topology=normalized_topology,
    )
    if not preview["can_apply"]:
        if not force_apply or not preview["force_apply_allowed"]:
            raise_api_error(
                400,
                "map_layout_blocked",
                force_apply_allowed=preview["force_apply_allowed"],
                blockers=preview["blockers"],
                agv_conflict_count=preview["agv_conflict_count"],
                agv_conflicts=preview["agv_conflicts"][:8],
                invalid_point_count=preview["invalid_point_count"],
                invalid_points=preview["invalid_points"][:8],
                invalid_template_count=preview["invalid_template_count"],
                invalid_templates=preview["invalid_templates"][:8],
                invalidated_task_count=preview["invalidated_task_count"],
                invalidated_tasks=preview["invalidated_tasks"][:8],
            )

    filtered, skipped = _filter_occupied_cells(requested)
    updated_state = set_layout_cells(
        filtered,
        requested_valid_cells,
        grid_cols,
        grid_rows,
        topology=normalized_topology,
    )
    updated = updated_state["blocked_cells"]
    updated_valid_cells = updated_state["valid_cells"]
    updated_topology = updated_state["topology"]
    applied_preview = _build_map_layout_impact_preview(
        grid_cols=int(grid_cols),
        grid_rows=int(grid_rows),
        blocked_cells=updated,
        valid_cells=updated_valid_cells,
        topology=updated_topology,
    )
    invalidated_tasks = (
        _apply_invalidated_tasks_for_map_change(applied_preview["invalidated_tasks"], actor)
        if force_apply and applied_preview["invalidated_task_count"] > 0
        else []
    )
    record_operation_audit(
        "map_layout",
        "global",
        "force_apply" if force_apply else "save",
        actor,
        {
            "grid_cols": int(grid_cols),
            "grid_rows": int(grid_rows),
            "blocked_count": len(updated),
            "valid_count": len(updated_valid_cells),
            "skipped_occupied_count": len(skipped),
            "topology_node_count": len(updated_topology.get("nodes", [])),
            "topology_edge_count": len(updated_topology.get("edges", [])),
            "invalidated_task_count": len(invalidated_tasks),
            "invalid_point_count": applied_preview["invalid_point_count"],
            "invalid_template_count": applied_preview["invalid_template_count"],
            "forced": bool(force_apply),
        },
    )
    return {
        "message": "Map layout updated",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": _cells_to_payload(updated),
        "blocked_count": len(updated),
        "valid_cells": _cells_to_payload(updated_valid_cells),
        "valid_count": len(updated_valid_cells),
        "is_irregular": len(updated_valid_cells) != int(grid_cols) * int(grid_rows),
        "topology": updated_topology,
        "topology_summary": build_map_topology_summary(updated_topology),
        "skipped_occupied_cells": _cells_to_payload(set(skipped)),
        "skipped_occupied_count": len(skipped),
        "current_profile": _resolve_current_profile_payload(grid_cols, grid_rows, updated, updated_valid_cells, updated_topology),
        "forced": bool(force_apply),
        "force_apply_allowed": applied_preview["force_apply_allowed"],
        "blockers": applied_preview["blockers"],
        "agv_conflicts": applied_preview["agv_conflicts"][:8],
        "agv_conflict_count": applied_preview["agv_conflict_count"],
        "invalid_points": applied_preview["invalid_points"][:8],
        "invalid_point_count": applied_preview["invalid_point_count"],
        "invalid_templates": applied_preview["invalid_templates"][:8],
        "invalid_template_count": applied_preview["invalid_template_count"],
        "invalidated_tasks": invalidated_tasks[:8] if force_apply else applied_preview["invalidated_tasks"][:8],
        "invalidated_task_count": len(invalidated_tasks) if force_apply else applied_preview["invalidated_task_count"],
    }


def apply_map_layout_preset(preset_key: str, actor: dict | None = None):
    grid_cols, grid_rows = get_current_grid_size()
    current_topology = normalize_map_topology_payload(
        get_map_layout_state().get("topology"),
        grid_cols,
        grid_rows,
        get_valid_cells(grid_cols, grid_rows),
    )
    try:
        preset_cells = get_map_preset_cells(preset_key, grid_cols, grid_rows)
        preset_valid_cells = get_map_preset_valid_cells(preset_key, grid_cols, grid_rows)
    except KeyError:
        try:
            preset_cells = _get_custom_map_preset_cells(preset_key, grid_cols, grid_rows)
            preset_valid_cells = _get_custom_map_preset_valid_cells(preset_key, grid_cols, grid_rows)
        except KeyError:
            raise_api_error(404, "preset_not_found")

    filtered, skipped = _filter_occupied_cells(preset_cells)
    updated_state = set_layout_cells(
        filtered,
        preset_valid_cells,
        grid_cols,
        grid_rows,
        topology=current_topology,
    )
    updated = updated_state["blocked_cells"]
    updated_valid_cells = updated_state["valid_cells"]
    updated_topology = updated_state["topology"]
    record_operation_audit(
        "map_preset",
        preset_key,
        "apply",
        actor,
        {
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "blocked_count": len(updated),
            "valid_count": len(updated_valid_cells),
            "skipped_occupied_count": len(skipped),
            "topology_node_count": len(updated_topology.get("nodes", [])),
            "topology_edge_count": len(updated_topology.get("edges", [])),
        },
    )
    return {
        "message": "Map preset applied",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": _cells_to_payload(updated),
        "blocked_count": len(updated),
        "valid_cells": _cells_to_payload(updated_valid_cells),
        "valid_count": len(updated_valid_cells),
        "is_irregular": len(updated_valid_cells) != grid_cols * grid_rows,
        "topology": updated_topology,
        "topology_summary": build_map_topology_summary(updated_topology),
        "preset_key": preset_key,
        "skipped_occupied_cells": _cells_to_payload(set(skipped)),
        "skipped_occupied_count": len(skipped),
        "current_profile": _resolve_current_profile_payload(grid_cols, grid_rows, updated, updated_valid_cells, updated_topology),
    }


def save_map_layout_preset(payload, actor: dict | None = None):
    grid_cols = int(payload.grid_cols)
    grid_rows = int(payload.grid_rows)
    custom_name = payload.name.strip()
    if not custom_name:
        raise_api_error(400, "preset_name_required")

    requested = _normalize_requested_cells(payload.blocked_cells, grid_cols, grid_rows)
    requested_valid_cells = _normalize_requested_valid_cells(payload.valid_cells, grid_cols, grid_rows)
    filtered, skipped = _filter_occupied_cells(requested)
    filtered = _normalize_blocked_for_valid_cells(filtered, requested_valid_cells)
    preset = MapPreset(
        key=_build_custom_preset_key(custom_name),
        custom_name=custom_name,
        description=(payload.description or "").strip() or None,
        blocked_cells=[MapPresetCell(x=x, y=y) for x, y in sorted(filtered)],
        valid_cells=[MapPresetCell(x=x, y=y) for x, y in sorted(requested_valid_cells)],
        custom=True,
    )
    upsert_map_preset(preset)
    record_operation_audit(
        "map_preset",
        preset.key,
        "save",
        actor,
        {
            "name": custom_name,
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "blocked_count": len(filtered),
            "valid_count": len(requested_valid_cells),
            "skipped_occupied_count": len(skipped),
        },
    )
    return {
        "message": "Map preset saved",
        "preset": build_map_preset_payload(
            key=preset.key,
            name=preset.custom_name,
            description=preset.description,
            cells=filtered,
            valid_cells=requested_valid_cells,
            custom=True,
            deletable=True,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
        ),
        "skipped_occupied_cells": _cells_to_payload(set(skipped)),
        "skipped_occupied_count": len(skipped),
    }


def delete_map_layout_preset(preset_key: str, actor: dict | None = None):
    if preset_key in DEFAULT_MAP_PRESETS:
        raise_api_error(400, "builtin_preset_cannot_be_deleted")

    preset = get_map_preset_by_key(preset_key)
    if preset is None:
        raise_api_error(404, "preset_not_found")

    record_operation_audit("map_preset", preset_key, "delete", actor, {"name": preset.custom_name})
    remove_map_preset(preset_key)
    return {
        "message": "Map preset deleted",
        "preset_key": preset_key,
    }


def reset_map_layout(actor: dict | None = None):
    grid_cols, grid_rows = get_current_grid_size()
    default_cells = get_default_blocked_cells(grid_cols, grid_rows)
    default_valid_cells = get_default_valid_cells(grid_cols, grid_rows)
    filtered, skipped = _filter_occupied_cells(default_cells)
    updated_state = set_layout_cells(
        filtered,
        default_valid_cells,
        grid_cols,
        grid_rows,
        topology=create_empty_map_topology(),
    )
    updated = updated_state["blocked_cells"]
    updated_valid_cells = updated_state["valid_cells"]
    updated_topology = updated_state["topology"]
    record_operation_audit(
        "map_layout",
        "global",
        "reset",
        actor,
        {
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "blocked_count": len(updated),
            "valid_count": len(updated_valid_cells),
            "skipped_occupied_count": len(skipped),
            "topology_node_count": len(updated_topology.get("nodes", [])),
            "topology_edge_count": len(updated_topology.get("edges", [])),
        },
    )
    return {
        "message": "Map layout reset",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": _cells_to_payload(updated),
        "blocked_count": len(updated),
        "valid_cells": _cells_to_payload(updated_valid_cells),
        "valid_count": len(updated_valid_cells),
        "is_irregular": False,
        "topology": updated_topology,
        "topology_summary": build_map_topology_summary(updated_topology),
        "skipped_occupied_cells": _cells_to_payload(set(skipped)),
        "skipped_occupied_count": len(skipped),
        "current_profile": _resolve_current_profile_payload(grid_cols, grid_rows, updated, updated_valid_cells, updated_topology),
    }

