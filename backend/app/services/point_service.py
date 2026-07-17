from __future__ import annotations

from app.models.point_library import PointLibraryItem
from app.repositories.point_repository import get_point_by_id, list_points, remove_point, upsert_point
from app.utils.map_validity import build_map_validity_context, build_point_validity_payload
from app.utils.api_error import raise_api_error


def get_point_list():
    context = build_map_validity_context()
    return [build_point_validity_payload(point, context) for point in list_points()]


def create_or_update_point(payload):
    point = PointLibraryItem(
        id=payload.id,
        x=payload.x,
        y=payload.y,
        name_key=payload.name_key,
        zone_key=payload.zone_key,
        custom_name=payload.custom_name,
        aliases=list(payload.aliases or []),
        custom=payload.custom,
    )
    upsert_point(point)
    return {"message": "Point saved", "point": point}


def delete_point(point_id: str):
    point = get_point_by_id(point_id)
    if point is None:
        raise_api_error(404, "point_not_found")
    remove_point(point_id)
    return {"message": "Point deleted", "point_id": point_id}
