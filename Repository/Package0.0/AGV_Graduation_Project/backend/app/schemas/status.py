from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.warehouse_map import DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS


class BlockedCellPayload(BaseModel):
    x: int
    y: int


class MapTopologyNodePayload(BaseModel):
    key: str | None = None
    x: int
    y: int
    label: str | None = None
    node_type: Literal["waypoint", "station", "parking", "charge"] = "waypoint"
    capacity: int | None = None


class MapTopologyEdgePayload(BaseModel):
    key: str | None = None
    source: str
    target: str
    direction: Literal["bidirectional", "forward", "reverse"] = "bidirectional"
    lane_type: Literal["main", "branch", "service"] = "main"
    weight: float = 1.0
    speed_multiplier: float = 1.0


class MapTopologyPayload(BaseModel):
    topology_version: int = 1
    nodes: list[MapTopologyNodePayload] = []
    edges: list[MapTopologyEdgePayload] = []
    stations: list[str] = []
    parking_nodes: list[str] = []
    charge_nodes: list[str] = []


class MapLayoutUpdateRequest(BaseModel):
    blocked_cells: list[BlockedCellPayload]
    valid_cells: list[BlockedCellPayload] | None = None
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS
    topology: MapTopologyPayload | None = None


class MapResizeRequest(BaseModel):
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


class MapPresetCreateRequest(BaseModel):
    name: str
    description: str | None = None
    blocked_cells: list[BlockedCellPayload]
    valid_cells: list[BlockedCellPayload] | None = None
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS


class MapProfileCreateRequest(BaseModel):
    name: str
    description: str | None = None
    blocked_cells: list[BlockedCellPayload]
    valid_cells: list[BlockedCellPayload] | None = None
    grid_cols: int = DEFAULT_GRID_COLS
    grid_rows: int = DEFAULT_GRID_ROWS
    import_source: str | None = None
    topology: MapTopologyPayload | None = None


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
    idle_return_timeout_sec: float = 12.0
    idle_charge_timeout_sec: float = 45.0
    compare_display_mode: Literal["panel", "floating"] = "panel"
    panel_sections: UiPanelSectionsPayload = UiPanelSectionsPayload()

