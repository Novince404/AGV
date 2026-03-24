from fastapi import APIRouter, Request

from app.schemas.task import TaskCreateRequest, TaskImportRequest
from app.services import auth_service, task_service


router = APIRouter(prefix="/task", tags=["Task"])


# Keep compatibility for modules importing task_list from api.task_api.
task_list = task_service.task_list


@router.get("/list")
def get_tasks():
    return task_service.get_tasks()


@router.post("/create")
def create_task(req: TaskCreateRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return task_service.create_task(req, actor)


@router.post("/finish/{task_id}")
def finish_task(task_id: int, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return task_service.finish_task(task_id, actor)


@router.post("/import_json")
def import_tasks(req: TaskImportRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return task_service.import_tasks(req.tasks, actor)


@router.get("/export_json")
def export_tasks(status: str | None = None):
    return task_service.export_tasks(status)


@router.delete("/finished")
def delete_finished_tasks(request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return task_service.delete_finished_tasks(actor)


@router.delete("/orphaned")
def delete_orphaned_tasks(request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return task_service.delete_orphaned_tasks(actor)


@router.delete("/{task_id}")
def delete_task(task_id: int, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return task_service.delete_task(task_id, actor)
