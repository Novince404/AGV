from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import secrets
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.agv_api import router as agv_router
from app.api.ai_api import router as ai_router
from app.api.auth_api import router as auth_router
from app.api.device_api import router as device_router
from app.api.fault_api import router as fault_router
from app.api.feedback_api import router as feedback_router
from app.api.point_api import router as point_router
from app.api.schedule_api import router as schedule_router
from app.api.status_api import router as status_router
from app.api.system_api import router as system_router
from app.api.task_api import router as task_router
from app.api.template_api import router as template_router
from app.api.v1_resources_api import router as v1_resources_router
from app.core.data_scope import build_scope_key_from_actor, use_scope
from app.core.database import dispose_engine
from app.core.events import event_broker
from app.core.lifecycle import initialize_runtime
from app.core.problem_details import http_exception_handler, problem_response, validation_exception_handler
from app.core.settings import get_settings
from app.core.version import get_version
from app.scheduler.coordinator import coordinator


BUSINESS_ROUTERS = (
    agv_router,
    ai_router,
    auth_router,
    fault_router,
    feedback_router,
    point_router,
    task_router,
    template_router,
    schedule_router,
    status_router,
)
LEGACY_PREFIXES = tuple(f"/{name}" for name in ("agv", "ai", "auth", "fault", "feedback", "point", "task", "template", "schedule", "status"))


def _log_startup(summary: dict[str, object]) -> None:
    if summary.get("database_status") == "memory":
        print("[startup] running with memory backend")
    elif summary.get("database_status") == "connected":
        print(f"[startup] SQL backend ready ({summary.get('data_backend')})")
    else:
        print(f"[startup] SQL backend unavailable: {summary.get('database_error', 'unknown error')}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    summary = initialize_runtime()
    _log_startup(summary)
    event_broker.publish(
        "system.health.changed",
        data={"status": "started", "version": get_version(), **summary},
    )
    if settings.scheduler_v3_enabled:
        await coordinator.start()
    try:
        yield
    finally:
        if settings.scheduler_v3_enabled:
            await coordinator.stop()
        event_broker.publish("system.health.changed", data={"status": "stopping", "version": get_version()})
        dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_title, version=get_version(), lifespan=lifespan)
    frontend_dist_dir = Path(settings.frontend_dist_dir).expanduser().resolve()

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["Deprecation", "Sunset", "Link", "X-Request-ID"],
    )
    if settings.oidc_enabled and settings.oidc_state_secret:
        from starlette.middleware.sessions import SessionMiddleware

        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.oidc_state_secret,
            session_cookie="agv_oidc_flow",
            same_site="lax",
            https_only=settings.auth_cookie_secure,
            max_age=600,
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        from app.services import auth_service

        request.state.request_id = request.headers.get("X-Request-ID") or uuid4().hex
        unsafe_method = request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
        csrf_exempt = request.url.path.endswith(("/login", "/register-personal", "/register-enterprise"))
        session_cookie = request.cookies.get("agv_session")
        if settings.csrf_enabled and unsafe_method and session_cookie and not csrf_exempt:
            cookie_token = request.cookies.get("agv_csrf", "")
            header_token = request.headers.get("X-CSRF-Token", "")
            if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                return problem_response(
                    request,
                    status_code=403,
                    code="csrf_validation_failed",
                    detail="A valid CSRF token is required for this request.",
                )
        actor = auth_service.resolve_request_actor(request)
        with use_scope(build_scope_key_from_actor(actor)):
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith(LEGACY_PREFIXES):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "v4.0.0"
            response.headers["Link"] = '</docs>; rel="successor-version"'
        return response

    for router in BUSINESS_ROUTERS:
        app.include_router(router, prefix="/api/v1")
        if settings.legacy_api_enabled:
            app.include_router(router, include_in_schema=False)
    app.include_router(v1_resources_router, prefix="/api/v1")
    app.include_router(device_router, prefix="/api/v1")
    app.include_router(system_router)

    @app.get("/", include_in_schema=False)
    def root():
        if settings.serve_frontend_dist:
            index_file = frontend_dist_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        return {"message": settings.root_message, "version": get_version(), "api": "/api/v1"}

    def resolve_frontend_file(relative_path: str) -> Path | None:
        if not settings.serve_frontend_dist or not frontend_dist_dir.exists():
            return None
        target_path = (frontend_dist_dir / relative_path).resolve()
        try:
            target_path.relative_to(frontend_dist_dir)
        except ValueError:
            return None
        return target_path if target_path.is_file() else None

    @app.get("/{frontend_path:path}", include_in_schema=False)
    def frontend_spa(frontend_path: str):
        if not settings.serve_frontend_dist:
            raise HTTPException(status_code=404, detail="Not Found")
        requested_file = resolve_frontend_file(frontend_path)
        if requested_file:
            return FileResponse(requested_file)
        index_file = resolve_frontend_file("index.html")
        if index_file:
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend bundle not found")

    return app
