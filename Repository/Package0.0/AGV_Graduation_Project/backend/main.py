from fastapi import FastAPI
from app.api.agv_api import router as agv_router
from app.api.fault_api import router as fault_router
from app.api.task_api import router as task_router
from app.api.schedule_api import router as schedule_router
from app.api.status_api import router as status_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AGV 调度系统后端")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agv_router)
app.include_router(fault_router)
app.include_router(task_router)
app.include_router(schedule_router)
app.include_router(status_router)

@app.get("/")
def root():
    return {"message": "AGV 调度系统后端已启动"}

