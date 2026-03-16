from __future__ import annotations

from app.models.point_library import PointLibraryItem


point_library: list[PointLibraryItem] = [
    PointLibraryItem(
        id="inbound_a",
        x=0,
        y=1,
        name_key="point_name_inbound_a",
        zone_key="point_zone_inbound",
        aliases=["dock", "receiving", "0,1"],
        custom=False,
    ),
    PointLibraryItem(
        id="inbound_b",
        x=0,
        y=6,
        name_key="point_name_inbound_b",
        zone_key="point_zone_inbound",
        aliases=["dock", "receiving", "0,6"],
        custom=False,
    ),
    PointLibraryItem(
        id="outbound_a",
        x=9,
        y=1,
        name_key="point_name_outbound_a",
        zone_key="point_zone_outbound",
        aliases=["shipping", "delivery", "9,1"],
        custom=False,
    ),
    PointLibraryItem(
        id="outbound_b",
        x=9,
        y=6,
        name_key="point_name_outbound_b",
        zone_key="point_zone_outbound",
        aliases=["shipping", "delivery", "9,6"],
        custom=False,
    ),
    PointLibraryItem(
        id="storage_c1",
        x=3,
        y=2,
        name_key="point_name_storage_c1",
        zone_key="point_zone_storage",
        aliases=["rack", "buffer", "3,2"],
        custom=False,
    ),
    PointLibraryItem(
        id="storage_c2",
        x=3,
        y=5,
        name_key="point_name_storage_c2",
        zone_key="point_zone_storage",
        aliases=["rack", "buffer", "3,5"],
        custom=False,
    ),
    PointLibraryItem(
        id="assembly_1",
        x=6,
        y=2,
        name_key="point_name_assembly_1",
        zone_key="point_zone_assembly",
        aliases=["station", "line", "6,2"],
        custom=False,
    ),
    PointLibraryItem(
        id="assembly_2",
        x=6,
        y=5,
        name_key="point_name_assembly_2",
        zone_key="point_zone_assembly",
        aliases=["station", "line", "6,5"],
        custom=False,
    ),
    PointLibraryItem(
        id="charge",
        x=1,
        y=7,
        name_key="point_name_charge",
        zone_key="point_zone_service",
        aliases=["charger", "battery", "1,7"],
        custom=False,
    ),
    PointLibraryItem(
        id="maintenance",
        x=8,
        y=7,
        name_key="point_name_maintenance",
        zone_key="point_zone_service",
        aliases=["repair", "service", "8,7"],
        custom=False,
    ),
]


def list_points() -> list[PointLibraryItem]:
    return point_library


def get_point_by_id(point_id: str) -> PointLibraryItem | None:
    return next((point for point in point_library if point.id == point_id), None)


def upsert_point(point: PointLibraryItem) -> PointLibraryItem:
    existing = get_point_by_id(point.id)
    if existing is None:
        point_library.append(point)
        return point

    index = point_library.index(existing)
    point_library[index] = point
    return point


def remove_point(point_id: str) -> None:
    existing = get_point_by_id(point_id)
    if existing is not None:
        point_library.remove(existing)
