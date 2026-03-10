from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR
from app.utils.warehouse_map import (
    apply_map_preset,
    DEFAULT_GRID_COLS,
    DEFAULT_GRID_ROWS,
    get_blocked_cell_payload,
    get_map_presets_payload,
    reset_blocked_cells,
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
    updated = set_blocked_cells(
        {(cell.x, cell.y) for cell in req.blocked_cells},
        req.grid_cols,
        req.grid_rows,
    )
    return {
        "message": "Map layout updated",
        "grid_cols": req.grid_cols,
        "grid_rows": req.grid_rows,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
    }


@router.post("/map/preset/{preset_key}")
def apply_map_layout_preset(preset_key: str):
    try:
        updated = apply_map_preset(preset_key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Preset not found")

    return {
        "message": "Map preset applied",
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
        "preset_key": preset_key,
    }


@router.post("/map/reset")
def reset_map_layout():
    updated = reset_blocked_cells()
    return {
        "message": "Map layout reset",
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(updated)],
    }
