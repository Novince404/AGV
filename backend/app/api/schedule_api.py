from fastapi import APIRouter, Request

from app.schemas.schedule import (
    PathCompareRequest,
    RecoverBlockedTaskRequest,
    RetryBlockedTaskRequest,
    ScheduleWithPathRequest,
)
from app.services import auth_service, schedule_service


router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.post("/")
def schedule_task(request: Request):
    auth_service.require_actor_capability(request, "dispatch.write")
    return schedule_service.schedule_task_default()


@router.post("/with_path")
def schedule_task_with_path(req: ScheduleWithPathRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return schedule_service.schedule_task_with_path(
        req.task_id,
        req.agv_id,
        req.schedule_mode,
        req.algorithm,
        req.grid_cols,
        req.grid_rows,
        actor,
    )


@router.post("/compare_path")
def compare_path(req: PathCompareRequest):
    return schedule_service.compare_path(
        req.start_x,
        req.start_y,
        req.end_x,
        req.end_y,
        req.stages,
        req.grid_cols,
        req.grid_rows,
    )


@router.post("/retry_blocked/{task_id}")
def retry_blocked_task(task_id: int, req: RetryBlockedTaskRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return schedule_service.retry_blocked_task(
        task_id,
        req.algorithm,
        req.grid_cols,
        req.grid_rows,
        actor,
    )


@router.post("/retry_blocked_from_current/{task_id}")
def retry_blocked_task_from_current(task_id: int, req: RetryBlockedTaskRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return schedule_service.retry_blocked_task_from_current(
        task_id,
        req.algorithm,
        req.grid_cols,
        req.grid_rows,
        actor,
    )


@router.post("/recover_blocked/{task_id}")
def recover_blocked_task(task_id: int, req: RecoverBlockedTaskRequest, request: Request):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    return schedule_service.recover_blocked_task(
        task_id,
        req.mode,
        req.algorithm,
        req.grid_cols,
        req.grid_rows,
        actor,
    )
