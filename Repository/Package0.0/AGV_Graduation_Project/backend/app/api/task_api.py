from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.task import Task
from app.api.agv_api import agv_list
from app.utils.task_chain import build_stage_models, sync_task_stage_fields


router = APIRouter(prefix="/task", tags=["Task"])


class TaskStagePayload(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None


class TaskCreateRequest(BaseModel):
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    priority: int = 1
    stages: list[TaskStagePayload] | None = None


class TaskImportItem(BaseModel):
    id: int | None = None
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    priority: int = 1
    stages: list[TaskStagePayload] | None = None


class TaskImportRequest(BaseModel):
    tasks: list[TaskImportItem]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def serialize_task_for_json(task: Task):
    payload = {
        "id": task.id,
        "start_x": task.overall_start_x if task.overall_start_x is not None else task.start_x,
        "start_y": task.overall_start_y if task.overall_start_y is not None else task.start_y,
        "end_x": task.overall_end_x if task.overall_end_x is not None else task.end_x,
        "end_y": task.overall_end_y if task.overall_end_y is not None else task.end_y,
        "priority": task.priority,
    }

    if task.stages and len(task.stages) > 1:
        payload["stages"] = [
            {
                "label": stage.label,
                "start_x": stage.start_x,
                "start_y": stage.start_y,
                "end_x": stage.end_x,
                "end_y": stage.end_y,
            }
            for stage in task.stages
        ]

    return payload


def build_task_stages(item: TaskCreateRequest | TaskImportItem):
    if item.stages:
        return build_stage_models(item.stages)

    if None in {item.start_x, item.start_y, item.end_x, item.end_y}:
        raise HTTPException(status_code=400, detail="Task coordinates are required")

    return build_stage_models(
        [
            TaskStagePayload(
                start_x=item.start_x,
                start_y=item.start_y,
                end_x=item.end_x,
                end_y=item.end_y,
            )
        ]
    )


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
    stages = build_task_stages(req)
    first_stage = stages[0]
    last_stage = stages[-1]
    task = Task(
        id=next_id,
        start_x=first_stage.start_x,
        start_y=first_stage.start_y,
        end_x=first_stage.end_x,
        end_y=first_stage.end_y,
        priority=req.priority,
        status="pending",
        created_at=now_iso(),
        current_stage_index=0,
        total_stages=len(stages),
        overall_start_x=first_stage.start_x,
        overall_start_y=first_stage.start_y,
        overall_end_x=last_stage.end_x,
        overall_end_y=last_stage.end_y,
        stages=stages,
    )
    sync_task_stage_fields(task)
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
        stages = build_task_stages(item)
        first_stage = stages[0]
        last_stage = stages[-1]

        task = Task(
            id=task_id,
            start_x=first_stage.start_x,
            start_y=first_stage.start_y,
            end_x=first_stage.end_x,
            end_y=first_stage.end_y,
            priority=item.priority,
            status="pending",
            created_at=now_iso(),
            current_stage_index=0,
            total_stages=len(stages),
            overall_start_x=first_stage.start_x,
            overall_start_y=first_stage.start_y,
            overall_end_x=last_stage.end_x,
            overall_end_y=last_stage.end_y,
            stages=stages,
        )
        sync_task_stage_fields(task)
        task_list.append(task)
        created_ids.append(task_id)

    return {"message": "Tasks imported", "count": len(created_ids), "task_ids": created_ids}


@router.get("/export_json")
def export_tasks():
    return {
        "version": 2,
        "exported_at": now_iso(),
        "tasks": [serialize_task_for_json(task) for task in task_list],
    }


@router.delete("/{task_id}")
def delete_task(task_id: int):
    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending tasks can be deleted")

    task_list.remove(task)
    return {"message": "Task deleted", "task_id": task_id}
