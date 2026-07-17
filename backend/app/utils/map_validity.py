from __future__ import annotations

from typing import Any

from app.utils.path_planner import plan_path
from app.utils.task_chain import ensure_task_stages
from app.utils.warehouse_map import get_current_grid_size, get_map_layout_state


MAP_INVALID_OUT_OF_BOUNDS = "map_invalid:out_of_bounds"
MAP_INVALID_BLOCKED = "map_invalid:blocked"
MAP_INVALID_UNREACHABLE = "map_invalid:unreachable"
ACTIVE_TASK_INVALIDATION_STATUSES = {"pending", "assigned", "blocked", "running"}


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


def _coerce_cell(item: Any) -> tuple[int, int] | None:
    if isinstance(item, tuple) and len(item) == 2:
        x, y = item
    elif isinstance(item, dict):
        x, y = item.get("x"), item.get("y")
    else:
        x, y = getattr(item, "x", None), getattr(item, "y", None)
    try:
        return int(x), int(y)
    except (TypeError, ValueError):
        return None


def _normalize_cell_set(items: Any) -> set[tuple[int, int]]:
    normalized: set[tuple[int, int]] = set()
    for item in items or []:
        cell = _coerce_cell(item)
        if cell is not None:
            normalized.add(cell)
    return normalized


def _build_navigation_blocked(
    grid_cols: int,
    grid_rows: int,
    valid_cells: set[tuple[int, int]],
    blocked_cells: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    blocked = set(blocked_cells)
    for y in range(int(grid_rows)):
        for x in range(int(grid_cols)):
            if (x, y) not in valid_cells:
                blocked.add((x, y))
    return blocked


def build_map_validity_context(
    *,
    grid_cols: int | None = None,
    grid_rows: int | None = None,
    valid_cells: Any = None,
    blocked_cells: Any = None,
    topology: dict | None = None,
) -> dict[str, Any]:
    if grid_cols is None or grid_rows is None or valid_cells is None or blocked_cells is None:
        state = get_map_layout_state()
        resolved_grid_cols = int(grid_cols or state["grid_cols"] or get_current_grid_size()[0])
        resolved_grid_rows = int(grid_rows or state["grid_rows"] or get_current_grid_size()[1])
        resolved_valid_cells = _normalize_cell_set(
            state["valid_cells"] if valid_cells is None else valid_cells
        )
        resolved_blocked_cells = _normalize_cell_set(
            state["blocked_cells"] if blocked_cells is None else blocked_cells
        )
        resolved_topology = topology if topology is not None else state.get("topology")
    else:
        resolved_grid_cols = int(grid_cols)
        resolved_grid_rows = int(grid_rows)
        resolved_valid_cells = _normalize_cell_set(valid_cells)
        resolved_blocked_cells = _normalize_cell_set(blocked_cells)
        resolved_topology = topology

    resolved_blocked_cells &= resolved_valid_cells
    return {
        "grid_cols": resolved_grid_cols,
        "grid_rows": resolved_grid_rows,
        "valid_cells": resolved_valid_cells,
        "blocked_cells": resolved_blocked_cells,
        "navigation_blocked": _build_navigation_blocked(
            resolved_grid_cols,
            resolved_grid_rows,
            resolved_valid_cells,
            resolved_blocked_cells,
        ),
        "topology": resolved_topology or {},
    }


def _cell_invalid_reason(
    x: int,
    y: int,
    *,
    grid_cols: int,
    grid_rows: int,
    valid_cells: set[tuple[int, int]],
    blocked_cells: set[tuple[int, int]],
) -> str | None:
    if x < 0 or y < 0 or x >= grid_cols or y >= grid_rows:
        return MAP_INVALID_OUT_OF_BOUNDS
    if (x, y) not in valid_cells:
        return MAP_INVALID_OUT_OF_BOUNDS
    if (x, y) in blocked_cells:
        return MAP_INVALID_BLOCKED
    return None


def _stage_invalid_reason(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    *,
    context: dict[str, Any],
    priority: int = 0,
) -> str | None:
    grid_cols = int(context["grid_cols"])
    grid_rows = int(context["grid_rows"])
    valid_cells = context["valid_cells"]
    blocked_cells = context["blocked_cells"]
    navigation_blocked = context["navigation_blocked"]

    start_reason = _cell_invalid_reason(
        int(start_x),
        int(start_y),
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        valid_cells=valid_cells,
        blocked_cells=blocked_cells,
    )
    if start_reason:
        return start_reason

    end_reason = _cell_invalid_reason(
        int(end_x),
        int(end_y),
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        valid_cells=valid_cells,
        blocked_cells=blocked_cells,
    )
    if end_reason:
        return end_reason

    if int(start_x) == int(end_x) and int(start_y) == int(end_y):
        return None

    path = plan_path(
        "astar",
        int(start_x),
        int(start_y),
        int(end_x),
        int(end_y),
        grid_cols,
        grid_rows,
        blocked=set(navigation_blocked),
        topology=context.get("topology"),
        request_priority=int(priority or 0),
    )
    return None if path else MAP_INVALID_UNREACHABLE


def build_point_validity_payload(point, context: dict[str, Any]) -> dict[str, Any]:
    payload = _model_dump(point)
    reason = _cell_invalid_reason(
        int(getattr(point, "x", payload.get("x", 0))),
        int(getattr(point, "y", payload.get("y", 0))),
        grid_cols=int(context["grid_cols"]),
        grid_rows=int(context["grid_rows"]),
        valid_cells=context["valid_cells"],
        blocked_cells=context["blocked_cells"],
    )
    payload["is_invalid"] = bool(reason)
    payload["invalid_reason"] = reason
    return payload


def build_template_validity_payload(template, context: dict[str, Any]) -> dict[str, Any]:
    payload = _model_dump(template)
    stages = list(getattr(template, "stages", []) or payload.get("stages") or [])
    invalid_stage_indexes: list[int] = []
    invalid_reason = None

    for fallback_index, stage in enumerate(stages):
        stage_index = int(getattr(stage, "index", stage.get("index", fallback_index) if isinstance(stage, dict) else fallback_index))
        start_x = int(getattr(stage, "start_x", stage.get("start_x", 0) if isinstance(stage, dict) else 0))
        start_y = int(getattr(stage, "start_y", stage.get("start_y", 0) if isinstance(stage, dict) else 0))
        end_x = int(getattr(stage, "end_x", stage.get("end_x", 0) if isinstance(stage, dict) else 0))
        end_y = int(getattr(stage, "end_y", stage.get("end_y", 0) if isinstance(stage, dict) else 0))
        stage_reason = _stage_invalid_reason(
            start_x,
            start_y,
            end_x,
            end_y,
            context=context,
            priority=int(getattr(template, "priority", payload.get("priority", 1)) or 1),
        )
        if stage_reason:
            invalid_stage_indexes.append(stage_index)
            if invalid_reason is None:
                invalid_reason = stage_reason

    payload["is_invalid"] = bool(invalid_stage_indexes)
    payload["invalid_reason"] = invalid_reason
    payload["invalid_stage_indexes"] = invalid_stage_indexes
    return payload


def build_task_invalidity_payload(task, context: dict[str, Any], *, agv=None) -> dict[str, Any]:
    stages = ensure_task_stages(task)
    current_stage_index = max(0, int(getattr(task, "current_stage_index", 0) or 0))
    invalid_stage_indexes: list[int] = []
    invalid_reason = None
    priority = int(getattr(task, "priority", 1) or 1)

    if agv is not None:
        agv_cell_reason = _cell_invalid_reason(
            int(getattr(agv, "x", 0)),
            int(getattr(agv, "y", 0)),
            grid_cols=int(context["grid_cols"]),
            grid_rows=int(context["grid_rows"]),
            valid_cells=context["valid_cells"],
            blocked_cells=context["blocked_cells"],
        )
        if agv_cell_reason:
            invalid_reason = agv_cell_reason

    for stage in stages[current_stage_index:]:
        stage_index = int(getattr(stage, "index", 0))
        start_x = int(getattr(stage, "start_x", 0))
        start_y = int(getattr(stage, "start_y", 0))
        if (
            agv is not None
            and str(getattr(task, "status", "") or "") == "running"
            and stage_index == current_stage_index
        ):
            start_x = int(getattr(agv, "x", start_x))
            start_y = int(getattr(agv, "y", start_y))
        stage_reason = _stage_invalid_reason(
            start_x,
            start_y,
            int(getattr(stage, "end_x", 0)),
            int(getattr(stage, "end_y", 0)),
            context=context,
            priority=priority,
        )
        if stage_reason:
            invalid_stage_indexes.append(stage_index)
            if invalid_reason is None:
                invalid_reason = stage_reason

    return {
        "id": int(getattr(task, "id")),
        "status": str(getattr(task, "status", "") or ""),
        "agv_id": getattr(task, "agv_id", None),
        "invalid_reason": invalid_reason,
        "invalid_stage_indexes": invalid_stage_indexes,
        "is_invalid": bool(invalid_reason),
    }
