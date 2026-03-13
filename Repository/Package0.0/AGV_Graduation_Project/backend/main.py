from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agv_api import router as agv_router
from app.api.fault_api import router as fault_router
from app.api.schedule_api import router as schedule_router
from app.api.status_api import router as status_router
from app.api.task_api import router as task_router
from app.core.settings import get_settings
from app.repositories.db_init import create_all_tables
from app.repositories.runtime import is_sql_backend


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
    if not is_sql_backend():
        return
    if not settings.database_auto_create:
        return
    try:
        create_all_tables()
        print(f"[startup] SQL tables ready ({settings.data_backend})")
    except Exception as exc:
        # Keep startup alive in A3 transition stage; SQL backend can be fixed without blocking demo mode.
        print(f"[startup] SQL init skipped due to error: {exc}")


@app.get("/")
def root():
    return {"message": "AGV 调度系统后端已启动"}
