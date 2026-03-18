from pydantic import BaseModel

from app.utils.warehouse_map import DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS


class BlockedCellPayload(BaseModel):
    x: int
    y: int


class MapLayoutUpdateRequest(BaseModel):
    blocked_cells: list[BlockedCellPayload]
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


class MapPresetCreateRequest(BaseModel):
    name: str
    description: str | None = None
    blocked_cells: list[BlockedCellPayload]
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS

