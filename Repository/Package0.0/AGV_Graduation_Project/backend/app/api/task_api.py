from fastapi import APIRouter

from app.schemas.task import TaskCreateRequest, TaskImportRequest
from app.services import task_service


router = APIRouter(prefix="/task", tags=["Task"])


# Keep compatibility for modules importing task_list from api.task_api.
task_list = task_service.task_list


@router.get("/list")
def get_tasks():
    return task_service.get_tasks()


@router.post("/create")
def create_task(req: TaskCreateRequest):
    return task_service.create_task(req)


@router.post("/finish/{task_id}")
def finish_task(task_id: int):
    return task_service.finish_task(task_id)


@router.post("/import_json")
def import_tasks(req: TaskImportRequest):
    return task_service.import_tasks(req.tasks)


@router.get("/export_json")
def export_tasks():
    return task_service.export_tasks()


@router.delete("/{task_id}")
def delete_task(task_id: int):
    return task_service.delete_task(task_id)
