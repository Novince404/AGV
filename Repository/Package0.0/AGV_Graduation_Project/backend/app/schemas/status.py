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
    force_apply: bool = False


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
    show_topology_edge_speed: bool = False
    show_runtime_segment_type: bool = False
    show_runtime_conflict_reason: bool = False
    show_selected_agv_runtime_overlay: bool = False
    status_legend_layout: Literal["horizontal", "vertical"] = "horizontal"
    status_legend_opacity: float = 0.55
    base_speed: float = 1.11
    follow_distance: float = 0.75
    deadlock_timeout_sec: float = 4.5
    idle_return_timeout_sec: float = 12.0
    idle_charge_timeout_sec: float = 45.0
    idle_charge_battery_threshold: float = 60.0
    battery_active_drain_per_sec: float = 0.16
    battery_waiting_drain_per_sec: float = 0.05
    battery_idle_drain_per_sec: float = 0.01
    battery_parking_idle_drain_per_sec: float = 0.003
    battery_charge_per_sec: float = 6.0
    compare_display_mode: Literal["panel", "floating"] = "panel"
    panel_sections: UiPanelSectionsPayload = UiPanelSectionsPayload()

