from __future__ import annotations

import asyncio

from fastapi import APIRouter, Header, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.core.database import check_database_connection
from app.core.data_scope import build_scope_key_from_actor
from app.core.events import event_broker
from app.core.settings import get_settings
from app.core.version import get_version
from app.repositories.runtime import is_sql_backend
from app.repositories import runtime_repository
from app.scheduler.coordinator import coordinator
from app.services import auth_service


router = APIRouter(tags=["System"])


def readiness_payload() -> tuple[dict, int]:
    settings = get_settings()
    if not is_sql_backend():
        return {
            "status": "ready",
            "database": "memory",
            "environment": settings.app_environment,
        }, 200
    connected, error_text = check_database_connection()
    payload = {
        "status": "ready" if connected else "not_ready",
        "database": settings.data_backend,
        "environment": settings.app_environment,
    }
    if error_text:
        payload["database_error"] = error_text
    return payload, 200 if connected else 503


@router.get("/health/live", summary="Process liveness")
def liveness() -> dict:
    return {"status": "alive", "version": get_version()}


@router.get("/health/ready", summary="Dependency readiness")
def readiness():
    payload, status_code = readiness_payload()
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=payload)


@router.get("/version", summary="Build version")
def version() -> dict:
    settings = get_settings()
    return {
        "version": get_version(),
        "environment": settings.app_environment,
        "api_version": "v1",
    }


@router.get("/api/v1/system/info", summary="System information")
def system_info(request: Request) -> dict:
    settings = get_settings()
    return {
        "version": get_version(),
        "api_version": "v1",
        "environment": settings.app_environment,
        "data_backend": settings.data_backend,
        "demo_users_enabled": settings.auth_demo_users_enabled,
        "request_id": getattr(request.state, "request_id", None),
    }


@router.get("/api/v1/events/stream", summary="Runtime event stream")
async def event_stream(request: Request, last_event_id: str | None = Header(default=None, alias="Last-Event-ID")):
    actor = auth_service.require_authenticated_actor(request)
    scope_key = build_scope_key_from_actor(actor)

    async def generate():
        if is_sql_backend():
            marker = last_event_id
            idle_cycles = 0
            while True:
                if await request.is_disconnected():
                    return
                events = await asyncio.to_thread(
                    runtime_repository.list_events_after,
                    marker,
                    scope_key=scope_key,
                    limit=200,
                )
                if events:
                    idle_cycles = 0
                    for event in events:
                        marker = event.id
                        yield event.to_sse()
                    continue
                idle_cycles += 1
                if idle_cycles >= 15:
                    yield ": keep-alive\n\n"
                    idle_cycles = 0
                await asyncio.sleep(1)
            return
        async for event in event_broker.subscribe(last_event_id):
            if event is None:
                yield ": keep-alive\n\n"
            elif event.scope_key == scope_key:
                yield event.to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/v1/system/metrics", response_class=PlainTextResponse, summary="Prometheus metrics")
def metrics() -> str:
    lease = runtime_repository.get_lease(coordinator.lease_key)
    return (
        "# HELP agv_sse_subscribers Active server-sent event subscribers.\n"
        "# TYPE agv_sse_subscribers gauge\n"
        f"agv_sse_subscribers {event_broker.subscriber_count}\n"
        "# HELP agv_scheduler_leader Whether a scheduler lease is currently present.\n"
        "# TYPE agv_scheduler_leader gauge\n"
        f"agv_scheduler_leader {1 if lease else 0}\n"
        "# HELP agv_scheduler_ticks_total Fixed-duration scheduler ticks in this process.\n"
        "# TYPE agv_scheduler_ticks_total counter\n"
        f"agv_scheduler_ticks_total {coordinator.tick_count}\n"
    )
