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


def list_tasks() -> list[Task]:
    return task_list


def get_task_by_id(task_id: int) -> Task | None:
    return next((task for task in task_list if task.id == task_id), None)


def get_next_task_id() -> int:
    return max((task.id for task in task_list), default=0) + 1


def get_existing_task_ids() -> set[int]:
    return {task.id for task in task_list}


def add_task(task: Task) -> Task:
    task_list.append(task)
    return task


def remove_task(task: Task) -> None:
    task_list.remove(task)
