from pydantic import BaseModel

class AGV(BaseModel):
    id: int
    x: int
    y: int
    status: str
    task_id: int | None = None
