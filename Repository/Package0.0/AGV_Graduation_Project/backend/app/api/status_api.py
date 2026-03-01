from fastapi import APIRouter
from app.utils.status_map import AGV_STATUS_COLOR, TASK_STATUS_COLOR

router = APIRouter(prefix="/status", tags=["Status"])

@router.get("/agv")
def get_agv_status_map():
    return AGV_STATUS_COLOR

@router.get("/task")
def get_task_status_map():
    return TASK_STATUS_COLOR
