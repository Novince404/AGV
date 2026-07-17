from __future__ import annotations

from app.models.tracked_model import TrackedModel


class PointLibraryItem(TrackedModel):
    id: str
    x: int
    y: int
    name_key: str | None = None
    zone_key: str | None = None
    custom_name: str | None = None
    aliases: list[str] = []
    custom: bool = False
