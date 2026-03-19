from __future__ import annotations

import re
import time

from app.models.map_preset import MapPreset, MapPresetCell
from app.core.settings import get_settings
from app.repositories.agv_repository import list_agvs
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
from app.utils.api_error import raise_api_error
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR
from app.utils.warehouse_map import (
    DEFAULT_MAP_PRESETS,
    build_map_preset_payload,
    get_current_map_profile_payload,
    get_blocked_cell_payload,
    get_blocked_cells,
    get_current_grid_size,
    get_default_blocked_cells,
    get_map_layout_state,
    get_map_profiles_payload,
    get_map_preset_cells,
    get_map_presets_payload,
    set_blocked_cells,
)


DEFAULT_UI_SETTINGS = {
    "show_minimap": True,
    "show_marker_icons": True,
    "show_path_arrows": False,
    "show_status_legend": True,
    "status_legend_layout": "horizontal",
    "status_legend_opacity": 0.55,
    "compare_display_mode": "panel",
    "panel_sections": {
        "control": True,
        "queue": True,
        "templates": False,
        "points": False,
        "json": False,
        "experiments": False,
    },
}


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


def _is_within_grid(x: int, y: int, grid_cols: int, grid_rows: int) -> bool:
    return 0 <= int(x) < int(grid_cols) and 0 <= int(y) < int(grid_rows)


def _build_custom_preset_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    slug = slug or "preset"
    return f"custom_{slug}_{int(time.time() * 1000)}"


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


def get_agv_status_map():
    return AGV_STATUS_COLOR


def get_task_status_map():
    return TASK_STATUS_COLOR


def get_map_layout():
    state = get_map_layout_state()
    grid_cols = int(state["grid_cols"])
    grid_rows = int(state["grid_rows"])
    return {
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": get_blocked_cell_payload(grid_cols, grid_rows),
    }


def _normalize_ui_settings(payload) -> dict:
    sections = (
        payload.panel_sections.model_dump(by_alias=True)
        if hasattr(payload.panel_sections, "model_dump")
        else dict(payload["panel_sections"])
    )
    opacity = max(0.2, min(0.9, float(payload.status_legend_opacity)))
    return {
        "show_minimap": bool(payload.show_minimap),
        "show_marker_icons": bool(payload.show_marker_icons),
        "show_path_arrows": bool(payload.show_path_arrows),
        "show_status_legend": bool(payload.show_status_legend),
        "status_legend_layout": payload.status_legend_layout,
        "status_legend_opacity": opacity,
        "compare_display_mode": payload.compare_display_mode,
        "panel_sections": {
            "control": bool(sections.get("control", DEFAULT_UI_SETTINGS["panel_sections"]["control"])),
            "queue": bool(sections.get("queue", DEFAULT_UI_SETTINGS["panel_sections"]["queue"])),
            "templates": bool(sections.get("templates", DEFAULT_UI_SETTINGS["panel_sections"]["templates"])),
            "points": bool(sections.get("points", DEFAULT_UI_SETTINGS["panel_sections"]["points"])),
            "json": bool(sections.get("json", DEFAULT_UI_SETTINGS["panel_sections"]["json"])),
            "experiments": bool(sections.get("experiments", DEFAULT_UI_SETTINGS["panel_sections"]["experiments"])),
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
    builtin_presets = get_map_presets_payload(grid_cols, grid_rows)
    custom_presets = []
    for preset in list_map_presets():
        cells = {
            (int(cell.x), int(cell.y))
            for cell in preset.blocked_cells
            if 0 <= int(cell.x) < grid_cols and 0 <= int(cell.y) < grid_rows
        }
        custom_presets.append(
            build_map_preset_payload(
                key=preset.key,
                name=preset.custom_name,
                description=preset.description,
                cells=cells,
                custom=True,
                deletable=True,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
                profile_key=get_current_map_profile_payload(grid_cols, grid_rows)["key"],
            )
        )
    return {
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "presets": builtin_presets + custom_presets,
    }


def get_map_profiles():
    grid_cols, grid_rows = get_current_grid_size()
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

    return {
        "current_profile": get_current_map_profile_payload(grid_cols, grid_rows),
        "profiles": get_map_profiles_payload(),
        "can_resize_now": can_resize_now,
        "resize_lock_reason": resize_lock_reason,
        "active_task_count": len(active_tasks),
        "busy_agv_count": len(busy_agvs),
    }


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


def update_map_layout(blocked_cells: list, grid_cols: int, grid_rows: int):
    requested = {(cell.x, cell.y) for cell in blocked_cells}
    filtered, skipped = _filter_occupied_cells(requested)
    updated = set_blocked_cells(filtered, grid_cols, grid_rows)
    return {
        "message": "Map layout updated",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


def apply_map_layout_preset(preset_key: str):
    grid_cols, grid_rows = get_current_grid_size()
    try:
        preset_cells = get_map_preset_cells(preset_key, grid_cols, grid_rows)
    except KeyError:
        try:
            preset_cells = _get_custom_map_preset_cells(preset_key, grid_cols, grid_rows)
        except KeyError:
            raise_api_error(404, "preset_not_found")

    filtered, skipped = _filter_occupied_cells(preset_cells)
    updated = set_blocked_cells(filtered, grid_cols, grid_rows)
    return {
        "message": "Map preset applied",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "preset_key": preset_key,
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


def save_map_layout_preset(payload):
    grid_cols = int(payload.grid_cols)
    grid_rows = int(payload.grid_rows)
    custom_name = payload.name.strip()
    if not custom_name:
        raise_api_error(400, "preset_name_required")

    requested = _normalize_requested_cells(payload.blocked_cells, grid_cols, grid_rows)
    filtered, skipped = _filter_occupied_cells(requested)
    preset = MapPreset(
        key=_build_custom_preset_key(custom_name),
        custom_name=custom_name,
        description=(payload.description or "").strip() or None,
        blocked_cells=[MapPresetCell(x=x, y=y) for x, y in sorted(filtered)],
        custom=True,
    )
    upsert_map_preset(preset)
    return {
        "message": "Map preset saved",
        "preset": build_map_preset_payload(
            key=preset.key,
            name=preset.custom_name,
            description=preset.description,
            cells=filtered,
            custom=True,
            deletable=True,
        ),
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


def delete_map_layout_preset(preset_key: str):
    if preset_key in DEFAULT_MAP_PRESETS:
        raise_api_error(400, "builtin_preset_cannot_be_deleted")

    preset = get_map_preset_by_key(preset_key)
    if preset is None:
        raise_api_error(404, "preset_not_found")

    remove_map_preset(preset_key)
    return {
        "message": "Map preset deleted",
        "preset_key": preset_key,
    }


def reset_map_layout():
    grid_cols, grid_rows = get_current_grid_size()
    default_cells = get_default_blocked_cells(grid_cols, grid_rows)
    filtered, skipped = _filter_occupied_cells(default_cells)
    updated = set_blocked_cells(filtered, grid_cols, grid_rows)
    return {
        "message": "Map layout reset",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }
