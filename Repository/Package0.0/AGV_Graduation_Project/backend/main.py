from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agv_api import router as agv_router
from app.api.fault_api import router as fault_router
from app.api.schedule_api import router as schedule_router
from app.api.status_api import router as status_router
from app.api.task_api import router as task_router
from app.core.lifecycle import initialize_runtime
from app.core.settings import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_title)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agv_router)
app.include_router(fault_router)
app.include_router(task_router)
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
    return {"message": settings.root_message}
