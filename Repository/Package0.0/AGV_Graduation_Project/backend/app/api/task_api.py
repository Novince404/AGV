from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.task import Task
from app.api.agv_api import agv_list


router = APIRouter(prefix="/task", tags=["Task"])


class TaskCreateRequest(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    priority: int = 1


class TaskImportItem(BaseModel):
    id: int | None = None
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    priority: int = 1


class TaskImportRequest(BaseModel):
    tasks: list[TaskImportItem]


def now_iso():
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


@router.get("/list")
def get_tasks():
    return task_list


@router.post("/create")
def create_task(req: TaskCreateRequest):
    next_id = max((t.id for t in task_list), default=0) + 1
    task = Task(
        id=next_id,
        start_x=req.start_x,
        start_y=req.start_y,
        end_x=req.end_x,
        end_y=req.end_y,
        priority=req.priority,
        status="pending",
        created_at=now_iso(),
    )
    task_list.append(task)
    return {"message": "Task created", "task": task}


@router.post("/finish/{task_id}")
def finish_task(task_id: int):
    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "running":
        raise HTTPException(status_code=400, detail="Task is not running")

    agv = next((a for a in agv_list if a.id == task.agv_id), None)
    if not agv:
        raise HTTPException(status_code=404, detail="Related AGV not found")

    task.status = "finished"
    task.finished_at = now_iso()
    agv.status = "idle"
    agv.task_id = None

    return {"message": "Task finished", "task": task, "agv": agv}


@router.post("/import_json")
def import_tasks(req: TaskImportRequest):
    existing_ids = {t.id for t in task_list}
    next_id = max(existing_ids, default=0) + 1
    created_ids = []

    for item in req.tasks:
        task_id = item.id
        if task_id is None or task_id in existing_ids or task_id < 1:
            task_id = next_id
            next_id += 1
        existing_ids.add(task_id)

        task = Task(
            id=task_id,
            start_x=item.start_x,
            start_y=item.start_y,
            end_x=item.end_x,
            end_y=item.end_y,
            priority=item.priority,
            status="pending",
            created_at=now_iso(),
        )
        task_list.append(task)
        created_ids.append(task_id)

    return {"message": "Tasks imported", "count": len(created_ids), "task_ids": created_ids}


@router.get("/export_json")
def export_tasks():
    return {"exported_at": now_iso(), "tasks": task_list}


@router.delete("/{task_id}")
def delete_task(task_id: int):
    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending tasks can be deleted")

    task_list.remove(task)
    return {"message": "Task deleted", "task_id": task_id}
