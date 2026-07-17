from fastapi import APIRouter, Header, Request

from app.core.data_scope import build_scope_key_from_actor
from app.repositories import runtime_repository
from app.schemas.task import TaskCreateRequest, TaskImportRequest
from app.services import auth_service, task_service


router = APIRouter(prefix="/task", tags=["Task"])


# Keep compatibility for modules importing task_list from api.task_api.
task_list = task_service.task_list


@router.get("/list")
def get_tasks():
    return task_service.get_tasks()


@router.post("/create", status_code=201)
def create_task(
    req: TaskCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    actor = auth_service.require_actor_capability(request, "dispatch.write")
    if idempotency_key is not None and not (8 <= len(idempotency_key) <= 128):
        from app.utils.api_error import raise_api_error

        raise_api_error(422, "invalid_idempotency_key")
    if not idempotency_key:
        return task_service.create_task(req, actor)
    scope_key = f"{build_scope_key_from_actor(actor)}:task.create"
    payload = req.model_dump(mode="json")
    try:
        cached = runtime_repository.get_idempotent_response(
            scope_key=scope_key,
            idempotency_key=idempotency_key,
            request_payload=payload,
        )
        if cached is not None:
            return cached[1]
        result = task_service.create_task(req, actor)
        _status, body = runtime_repository.save_idempotent_response(
            scope_key=scope_key,
            idempotency_key=idempotency_key,
            request_payload=payload,
            response_status=201,
            response_body=result,
        )
        return body
    except ValueError as exc:
        if str(exc) == "idempotency_key_payload_mismatch":
            from app.utils.api_error import raise_api_error

            raise_api_error(409, "idempotency_key_payload_mismatch")
        raise


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
