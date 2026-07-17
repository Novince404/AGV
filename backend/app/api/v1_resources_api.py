"""Stable resource-oriented v1 API.

The original route modules remain mounted for one major-version compatibility
window. New browser and integration work should use these plural resources.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.status import MapLayoutUpdateRequest
from app.services import agv_service, auth_service, fault_service, schedule_service, status_service, task_service


router = APIRouter(tags=["v1 resources"])


@router.get("/agvs")
def list_agvs(request: Request) -> dict:
    auth_service.require_authenticated_actor(request)
    return {"items": agv_service.get_agvs()}


@router.get("/tasks")
def list_tasks(request: Request) -> dict:
    auth_service.require_authenticated_actor(request)
    return {"items": task_service.get_tasks()}


@router.get("/maps")
def get_map(request: Request) -> dict:
    auth_service.require_authenticated_actor(request)
    return status_service.get_map_layout()


@router.put("/maps")
def update_map(req: MapLayoutUpdateRequest, request: Request) -> dict:
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


@router.get("/topologies")
def get_topology(request: Request) -> dict:
    auth_service.require_authenticated_actor(request)
    map_layout = status_service.get_map_layout()
    return {"topology": map_layout.get("topology") or {}, "map_id": map_layout.get("profile_key")}


@router.get("/faults")
def list_faults(request: Request, status: str | None = None) -> dict:
    auth_service.require_authenticated_actor(request)
    return {"items": fault_service.get_fault_list(status)}


@router.post("/dispatches", status_code=202)
def create_dispatch(request: Request) -> dict:
    auth_service.require_actor_capability(request, "dispatch.write")
    return schedule_service.schedule_task_default()


@router.get("/audit-events")
def list_audit_events(request: Request, limit: int = 60, resource_type: str | None = None, action: str | None = None) -> dict:
    auth_service.require_actor_capability(request, "audit.view")
    return auth_service.list_operation_feed(limit=limit, resource_type=resource_type, action=action)
