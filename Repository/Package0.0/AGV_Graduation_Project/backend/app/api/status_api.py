from fastapi import APIRouter, Request

from app.schemas.status import (
    MapLayoutUpdateRequest,
    MapProfileCreateRequest,
    MapPresetCreateRequest,
    MapResizeRequest,
    UiSettingsUpdateRequest,
)
from app.services import auth_service, status_service


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


@router.get("/map/profile/{profile_key}")
def get_map_profile_detail(profile_key: str):
    return status_service.get_map_profile_detail(profile_key)


@router.get("/map/resize-precheck")
def get_map_resize_precheck(grid_cols: int, grid_rows: int):
    return status_service.get_map_resize_precheck(grid_cols, grid_rows)


@router.post("/map/resize")
def resize_map_layout(req: MapResizeRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    return status_service.resize_map_layout(req.grid_cols, req.grid_rows, actor=actor)


@router.post("/map/profile/{profile_key}")
def apply_map_profile(profile_key: str, request: Request, force: bool = False):
    actor = auth_service.require_actor_capability(request, "map.write")
    if force:
        auth_service.require_actor_capability(request, "map.force_apply")
    return status_service.apply_map_profile(profile_key, force=force, actor=actor)


@router.post("/map/profile")
def save_map_profile(req: MapProfileCreateRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    return status_service.save_map_profile(req, actor)


@router.delete("/map/profile/{profile_key}")
def delete_map_profile(profile_key: str, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    return status_service.delete_map_profile(profile_key, actor)


@router.put("/map")
def update_map_layout(req: MapLayoutUpdateRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    if req.force_apply:
        auth_service.require_actor_capability(request, "map.force_apply")
    return status_service.update_map_layout(
        blocked_cells=req.blocked_cells,
        valid_cells=req.valid_cells,
        grid_cols=req.grid_cols,
        grid_rows=req.grid_rows,
        topology=req.topology,
        force_apply=req.force_apply,
        actor=actor,
    )


@router.post("/map/preset/{preset_key}")
def apply_map_layout_preset(preset_key: str, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    return status_service.apply_map_layout_preset(preset_key, actor=actor)


@router.post("/map/preset")
def save_map_layout_preset(req: MapPresetCreateRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    return status_service.save_map_layout_preset(req, actor=actor)


@router.delete("/map/preset/{preset_key}")
def delete_map_layout_preset(preset_key: str, request: Request):
    actor = auth_service.require_actor_capability(request, "map.write")
    return status_service.delete_map_layout_preset(preset_key, actor=actor)


@router.post("/map/reset")
def reset_map_layout(request: Request):
    actor = auth_service.require_authenticated_actor(request)
    return status_service.reset_map_layout(actor=actor)
