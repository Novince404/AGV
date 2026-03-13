from datetime import datetime

from app.models.task import Task


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


task_list = [
    Task(
        id=1,
        start_x=1,
        start_y=1,
        end_x=5,
        end_y=5,
        priority=3,
        status="pending",
        created_at=now_iso(),
    ),
    Task(
        id=2,
        start_x=2,
        start_y=3,
        end_x=6,
        end_y=2,
        priority=2,
        status="pending",
        created_at=now_iso(),
    ),
]

