from pydantic import BaseModel, Field


class PointUpsertRequest(BaseModel):
    id: str = Field(min_length=1)
    x: int
    y: int
    name_key: str | None = None
    zone_key: str | None = None
    custom_name: str | None = None
    aliases: list[str] = []
    custom: bool = True
