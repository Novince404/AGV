from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.warehouse_map import DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS


class BlockedCellPayload(BaseModel):
    x: int
    y: int


class MapLayoutUpdateRequest(BaseModel):
    blocked_cells: list[BlockedCellPayload]
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


class MapResizeRequest(BaseModel):
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


class MapPresetCreateRequest(BaseModel):
    name: str
    description: str | None = None
    blocked_cells: list[BlockedCellPayload]
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


class MapProfileCreateRequest(BaseModel):
    name: str
    description: str | None = None
    blocked_cells: list[BlockedCellPayload]
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS
    import_source: str | None = None


class UiPanelSectionsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    control: bool = True
    queue: bool = True
    templates: bool = False
    points: bool = False
    json_panel: bool = Field(default=False, alias="json")
    experiments: bool = False
    ai: bool = False
    operations: bool = False


class UiSettingsUpdateRequest(BaseModel):
    show_minimap: bool = True
    show_marker_icons: bool = True
    show_path_arrows: bool = False
    show_status_legend: bool = True
    status_legend_layout: Literal["horizontal", "vertical"] = "horizontal"
    status_legend_opacity: float = 0.55
    compare_display_mode: Literal["panel", "floating"] = "panel"
    panel_sections: UiPanelSectionsPayload = UiPanelSectionsPayload()

