from __future__ import annotations

import re
import time

from app.models.map_profile import MapProfile, MapProfileCell
from app.models.map_preset import MapPreset, MapPresetCell
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
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR
from app.utils.warehouse_map import (
    DEFAULT_MAP_PRESETS,
    build_map_profile_payload,
    build_map_preset_payload,
    get_current_map_profile_payload,
    get_blocked_cell_payload,
    get_blocked_cells,
    get_current_grid_size,
    get_default_blocked_cells,
    get_map_layout_state,
    get_map_profile_cells,
    get_map_profile_definition,
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


def _get_custom_map_profile_cells(profile_key: str) -> set[tuple[int, int]]:
    profile = get_map_profile_by_key(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    return {(int(cell.x), int(cell.y)) for cell in profile.blocked_cells}


def _normalize_cells_signature(cells: set[tuple[int, int]] | list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((int(x), int(y)) for x, y in cells))


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
    payload = build_map_profile_payload(
        key=profile.key,
        name=profile.custom_name,
        description=profile.description,
        grid_cols=int(profile.grid_cols),
        grid_rows=int(profile.grid_rows),
        custom=True,
        editable=True,
        deletable=True,
    ) | {
        "blocked_count": len(cells),
    }
    return _attach_map_profile_audit(payload)


def _resolve_current_profile_payload(
    grid_cols: int,
    grid_rows: int,
    blocked_cells: set[tuple[int, int]] | None = None,
) -> dict:
    normalized_cells = _normalize_cells_signature(blocked_cells or get_blocked_cells(grid_cols, grid_rows))

    for profile in list_map_profiles():
        profile_cells = {(int(cell.x), int(cell.y)) for cell in profile.blocked_cells}
        if (
            int(profile.grid_cols) == int(grid_cols)
            and int(profile.grid_rows) == int(grid_rows)
            and _normalize_cells_signature(profile_cells) == normalized_cells
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
        ):
            return profile_payload

    return get_current_map_profile_payload(grid_cols, grid_rows)


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
    current_profile = _resolve_current_profile_payload(grid_cols, grid_rows)
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
        "current_profile": _attach_map_profile_audit(_resolve_current_profile_payload(grid_cols, grid_rows, blocked_cells)),
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
        return _attach_map_profile_audit(build_map_profile_payload(
            key=custom_profile.key,
            name=custom_profile.custom_name,
            description=custom_profile.description,
            grid_cols=int(custom_profile.grid_cols),
            grid_rows=int(custom_profile.grid_rows),
            custom=True,
            editable=True,
            deletable=True,
        ) | {
            "blocked_count": len(cells),
            "blocked_cells": [{"x": x, "y": y} for x, y in sorted(cells)],
        })

    profile_definition = get_map_profile_definition(profile_key)
    if profile_definition is None:
        raise_api_error(404, "profile_not_found")

    cells = {(int(x), int(y)) for x, y in profile_definition["cells"]}
    return _attach_map_profile_audit(build_map_profile_payload(
        key=profile_definition["key"],
        name=profile_definition["name"],
        description=profile_definition["description"],
        grid_cols=int(profile_definition["grid_cols"]),
        grid_rows=int(profile_definition["grid_rows"]),
        custom=bool(profile_definition.get("custom", False)),
        editable=False,
        deletable=False,
    ) | {
        "blocked_count": len(cells),
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(cells)],
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
    updated = set_blocked_cells(current_cells, requested_grid_cols, requested_grid_rows)
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
        },
    )
    return {
        "message": "Map size updated",
        "grid_cols": int(requested_grid_cols),
        "grid_rows": int(requested_grid_rows),
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "current_profile": _resolve_current_profile_payload(requested_grid_cols, requested_grid_rows, updated),
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
            else:
                raw_profile_cells = get_map_profile_cells(profile_key)
            in_bounds_profile_cells = {
                (int(x), int(y))
                for x, y in raw_profile_cells
                if _is_within_grid(x, y, target_cols, target_rows)
            }
            trimmed_blocked_cells = sorted(raw_profile_cells - in_bounds_profile_cells)
            relocated_agvs = _relocate_out_of_bounds_agvs_for_force_apply(
                requested_grid_cols=target_cols,
                requested_grid_rows=target_rows,
                blocked_cells=in_bounds_profile_cells,
            )
            filtered, skipped = _filter_occupied_cells(in_bounds_profile_cells)
            updated = set_blocked_cells(filtered, target_cols, target_rows)
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
                },
            )
            return {
                "message": "Map profile force applied",
                "profile_key": profile_key,
                "grid_cols": target_cols,
                "grid_rows": target_rows,
                "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
                "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
                "skipped_occupied_count": len(skipped),
                "current_profile": _attach_map_profile_audit(_resolve_current_profile_payload(target_cols, target_rows, updated)),
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
    else:
        profile_cells = get_map_profile_cells(profile_key)
    filtered, skipped = _filter_occupied_cells(profile_cells)
    updated = set_blocked_cells(filtered, target_cols, target_rows)
    record_operation_audit(
        "map_profile",
        profile_key,
        "apply",
        actor,
        {
            "grid_cols": target_cols,
            "grid_rows": target_rows,
            "skipped_occupied_count": len(skipped),
        },
    )
    return {
        "message": "Map profile applied",
        "profile_key": profile_key,
        "grid_cols": target_cols,
        "grid_rows": target_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
        "current_profile": _attach_map_profile_audit(_resolve_current_profile_payload(target_cols, target_rows, updated)),
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
    profile = MapProfile(
        key=_build_custom_profile_key(resolved_name),
        custom_name=resolved_name,
        description=(payload.description or "").strip() or None,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        blocked_cells=[MapProfileCell(x=x, y=y) for x, y in sorted(requested)],
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


def update_map_layout(blocked_cells: list, grid_cols: int, grid_rows: int, actor: dict | None = None):
    requested = {(cell.x, cell.y) for cell in blocked_cells}
    filtered, skipped = _filter_occupied_cells(requested)
    updated = set_blocked_cells(filtered, grid_cols, grid_rows)
    record_operation_audit(
        "map_layout",
        "global",
        "save",
        actor,
        {
            "grid_cols": int(grid_cols),
            "grid_rows": int(grid_rows),
            "blocked_count": len(updated),
            "skipped_occupied_count": len(skipped),
        },
    )
    return {
        "message": "Map layout updated",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


def apply_map_layout_preset(preset_key: str, actor: dict | None = None):
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
    record_operation_audit(
        "map_preset",
        preset_key,
        "apply",
        actor,
        {
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "blocked_count": len(updated),
            "skipped_occupied_count": len(skipped),
        },
    )
    return {
        "message": "Map preset applied",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "preset_key": preset_key,
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


def save_map_layout_preset(payload, actor: dict | None = None):
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
            custom=True,
            deletable=True,
        ),
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
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
    filtered, skipped = _filter_occupied_cells(default_cells)
    updated = set_blocked_cells(filtered, grid_cols, grid_rows)
    record_operation_audit(
        "map_layout",
        "global",
        "reset",
        actor,
        {
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "blocked_count": len(updated),
            "skipped_occupied_count": len(skipped),
        },
    )
    return {
        "message": "Map layout reset",
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }
