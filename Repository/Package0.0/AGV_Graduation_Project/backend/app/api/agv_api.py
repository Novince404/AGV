from fastapi import APIRouter
from app.models.agv import AGV

router = APIRouter(prefix="/agv", tags=["AGV"])

# 模拟 AGV 数据（后面会接数据库）
agv_list = [
    AGV(id=1, x=2, y=3, status="idle"),
    AGV(id=2, x=5, y=7, status="running"),
    AGV(id=3, x=1, y=4, status="fault"),
]

@router.get("/list")
def get_agvs():
    return agv_list
