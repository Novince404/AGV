from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.agv_api import router as agv_router
from app.api.ai_api import router as ai_router
from app.api.auth_api import router as auth_router
from app.api.fault_api import router as fault_router
from app.api.point_api import router as point_router
from app.api.schedule_api import router as schedule_router
from app.api.status_api import router as status_router
from app.api.task_api import router as task_router
from app.api.template_api import router as template_router
from app.core.lifecycle import initialize_runtime
from app.core.settings import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_title)
frontend_dist_dir = Path(settings.frontend_dist_dir).expanduser().resolve()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agv_router)
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(fault_router)
app.include_router(point_router)
app.include_router(task_router)
app.include_router(template_router)
app.include_router(schedule_router)
app.include_router(status_router)


@app.on_event("startup")
def on_startup():
    try:
        summary = initialize_runtime()
        if summary["database_status"] == "memory":
            print("[startup] running with memory backend")
            return
        if summary["database_status"] == "connected":
            if summary.get("tables_ready"):
                print(f"[startup] SQL backend ready ({summary['data_backend']})")
            else:
                print(f"[startup] SQL backend connected without auto-create ({summary['data_backend']})")
            return
        error_text = summary.get("database_error", "unknown error")
        print(f"[startup] SQL backend unavailable: {error_text}")
    except Exception as exc:
        # Keep startup alive in A3 transition stage; SQL backend can be fixed without blocking demo mode.
        print(f"[startup] SQL init skipped due to error: {exc}")


@app.get("/")
def root():
    if settings.serve_frontend_dist:
        index_file = frontend_dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return {"message": settings.root_message}


def _resolve_frontend_file(relative_path: str) -> Path | None:
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

    requested_file = _resolve_frontend_file(frontend_path)
    if requested_file:
        return FileResponse(requested_file)

    index_file = _resolve_frontend_file("index.html")
    if index_file:
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend bundle not found")
