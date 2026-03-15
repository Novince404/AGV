from __future__ import annotations

from app.repositories.agv_repository import list_agvs
from app.utils.api_error import raise_api_error
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR
from app.utils.warehouse_map import (
    DEFAULT_GRID_COLS,
    DEFAULT_GRID_ROWS,
    get_blocked_cell_payload,
    get_default_blocked_cells,
    get_map_preset_cells,
    get_map_presets_payload,
    set_blocked_cells,
)


def _filter_occupied_cells(cells: set[tuple[int, int]]):
    occupied = {(agv.x, agv.y) for agv in list_agvs() if agv.status != "maintenance"}
    filtered = {cell for cell in cells if cell not in occupied}
    skipped = sorted(cell for cell in cells if cell in occupied)
    return filtered, skipped


def get_agv_status_map():
    return AGV_STATUS_COLOR


def get_task_status_map():
    return TASK_STATUS_COLOR


def get_map_layout():
    return {
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "blocked_cells": get_blocked_cell_payload(),
    }


def get_map_presets():
    return {
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "presets": get_map_presets_payload(),
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
    try:
        preset_cells = get_map_preset_cells(preset_key)
    except KeyError:
        raise_api_error(404, "preset_not_found")

    filtered, skipped = _filter_occupied_cells(preset_cells)
    updated = set_blocked_cells(filtered, DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS)
    return {
        "message": "Map preset applied",
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "preset_key": preset_key,
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


def reset_map_layout():
    default_cells = get_default_blocked_cells()
    filtered, skipped = _filter_occupied_cells(default_cells)
    updated = set_blocked_cells(filtered, DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS)
    return {
        "message": "Map layout reset",
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }
