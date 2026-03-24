from fastapi import APIRouter, Request

from app.services import agv_service, auth_service
from app.schemas.agv import EmergencyStopRequest


router = APIRouter(prefix="/agv", tags=["AGV"])


# Keep compatibility for modules importing agv_list from api.agv_api.
agv_list = agv_service.agv_list


@router.get("/list")
def get_agvs():
    return agv_service.get_agvs()


@router.post("/{agv_id}/emergency-stop")
def emergency_stop_agv(agv_id: int, req: EmergencyStopRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "fault.write")
    return agv_service.emergency_stop_agv(
        agv_id,
        req.message,
        actor.get("display_name") or req.reported_by,
        actor=actor,
    )


@router.post("/{agv_id}/resume")
def resume_agv(agv_id: int, request: Request):
    actor = auth_service.require_actor_capability(request, "fault.write")
    return agv_service.resume_agv(agv_id, actor=actor)


@router.post("/{agv_id}/to-maintenance")
def move_agv_to_maintenance(agv_id: int, request: Request):
    actor = auth_service.require_actor_capability(request, "fault.write")
    return agv_service.move_agv_to_maintenance(agv_id, actor=actor)


@router.post("/{agv_id}/return-to-service")
def return_agv_to_service(agv_id: int, request: Request):
    actor = auth_service.require_actor_capability(request, "fault.write")
    return agv_service.return_agv_to_service(agv_id, actor=actor)
