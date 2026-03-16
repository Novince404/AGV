from fastapi import APIRouter

from app.schemas.point import PointUpsertRequest
from app.services import point_service


router = APIRouter(prefix="/point", tags=["Point"])


@router.get("/list")
def get_points():
    return point_service.get_point_list()


@router.post("/upsert")
def upsert_point(req: PointUpsertRequest):
    return point_service.create_or_update_point(req)


@router.delete("/{point_id}")
def delete_point(point_id: str):
    return point_service.delete_point(point_id)
