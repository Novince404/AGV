from fastapi import APIRouter
from pydantic import BaseModel
from app.api.agv_api import agv_list
from app.utils.api_error import raise_api_error
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR
from app.utils.warehouse_map import (
    DEFAULT_GRID_COLS,
    DEFAULT_GRID_ROWS,
    get_default_blocked_cells,
    get_blocked_cell_payload,
    get_map_preset_cells,
    get_map_presets_payload,
    set_blocked_cells,
)

router = APIRouter(prefix="/status", tags=["Status"])


class BlockedCellPayload(BaseModel):
    x: int
    y: int


class MapLayoutUpdateRequest(BaseModel):
    blocked_cells: list[BlockedCellPayload]
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


def _filter_occupied_cells(cells: set[tuple[int, int]]):
    occupied = {(agv.x, agv.y) for agv in agv_list}
    filtered = {cell for cell in cells if cell not in occupied}
    skipped = sorted(cell for cell in cells if cell in occupied)
    return filtered, skipped

@router.get("/agv")
def get_agv_status_map():
    return AGV_STATUS_COLOR

@router.get("/task")
def get_task_status_map():
    return TASK_STATUS_COLOR


@router.get("/map")
def get_map_layout():
    return {
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "blocked_cells": get_blocked_cell_payload(),
    }


@router.get("/map/presets")
def get_map_presets():
    return {
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "presets": get_map_presets_payload(),
    }


@router.put("/map")
def update_map_layout(req: MapLayoutUpdateRequest):
    requested = {(cell.x, cell.y) for cell in req.blocked_cells}
    filtered, skipped = _filter_occupied_cells(requested)
    updated = set_blocked_cells(
        filtered,
        req.grid_cols,
        req.grid_rows,
    )
    return {
        "message": "Map layout updated",
        "grid_cols": req.grid_cols,
        "grid_rows": req.grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "skipped_occupied_cells": [{"x": x, "y": y} for x, y in skipped],
        "skipped_occupied_count": len(skipped),
    }


@router.post("/map/preset/{preset_key}")
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


@router.post("/map/reset")
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
