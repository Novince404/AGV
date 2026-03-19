from fastapi import APIRouter

from app.schemas.status import MapLayoutUpdateRequest, MapPresetCreateRequest, UiSettingsUpdateRequest
from app.services import status_service


router = APIRouter(prefix="/status", tags=["Status"])


@router.get("/agv")
def get_agv_status_map():
    return status_service.get_agv_status_map()


@router.get("/task")
def get_task_status_map():
    return status_service.get_task_status_map()


@router.get("/map")
def get_map_layout():
    return status_service.get_map_layout()


@router.get("/ui-settings")
def get_ui_settings():
    return status_service.get_ui_settings()


@router.put("/ui-settings")
def update_ui_settings(req: UiSettingsUpdateRequest):
    return status_service.update_ui_settings(req)


@router.get("/map/presets")
def get_map_presets():
    return status_service.get_map_presets()


@router.get("/map/profiles")
def get_map_profiles():
    return status_service.get_map_profiles()


@router.put("/map")
def update_map_layout(req: MapLayoutUpdateRequest):
    return status_service.update_map_layout(req.blocked_cells, req.grid_cols, req.grid_rows)


@router.post("/map/preset/{preset_key}")
def apply_map_layout_preset(preset_key: str):
    return status_service.apply_map_layout_preset(preset_key)


@router.post("/map/preset")
def save_map_layout_preset(req: MapPresetCreateRequest):
    return status_service.save_map_layout_preset(req)


@router.delete("/map/preset/{preset_key}")
def delete_map_layout_preset(preset_key: str):
    return status_service.delete_map_layout_preset(preset_key)


@router.post("/map/reset")
def reset_map_layout():
    return status_service.reset_map_layout()
