from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.core.data_scope import build_scope_key_from_actor
from app.repositories import runtime_repository
from app.schemas.device import DeviceCommandRequest
from app.scheduler.coordinator import coordinator
from app.services import auth_service
from app.utils.api_error import raise_api_error


router = APIRouter(tags=["Device adapter"])


@router.get("/system/device-adapter")
async def device_adapter_health(request: Request) -> dict:
    auth_service.require_authenticated_actor(request)
    health = await coordinator.adapter.health()
    lease = runtime_repository.get_lease(coordinator.lease_key)
    return {
        **health.model_dump(),
        "leader": bool(lease),
        "lease": lease,
        "runtime": "deterministic-single-tick",
        "real_device_io": False,
    }


@router.post("/agvs/{agv_id}/commands", status_code=202)
def enqueue_device_command(
    agv_id: str,
    body: DeviceCommandRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    if idempotency_key is not None and not (8 <= len(idempotency_key) <= 128):
        raise_api_error(422, "invalid_idempotency_key")
    scope_key = build_scope_key_from_actor(actor)
    payload = {
        "agv_id": agv_id,
        "parameters": body.parameters,
        "requested_by": actor.get("id"),
    }
    try:
        command, created = runtime_repository.enqueue_command(
            command_type=body.command_type,
            scope_key=scope_key,
            entity_id=agv_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        if str(exc) == "idempotency_key_payload_mismatch":
            raise_api_error(409, "idempotency_key_payload_mismatch")
        raise
    return {"created": created, "command": command.to_dict()}
