from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.models.task import Task
from app.repositories.agv_repository import get_agv_by_id, list_agvs
from app.repositories.task_repository import (
    add_task,
    get_existing_task_ids,
    get_next_task_id,
    get_task_by_id,
    list_tasks,
    remove_task,
    task_list,
)
from app.utils.api_error import raise_api_error
from app.utils.task_chain import build_stage_models, sync_task_stage_fields
from app.utils.warehouse_map import DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS, get_blocked_cells, get_current_grid_size
from app.services.operation_audit_service import (
    build_first_audit_map,
    build_latest_audit_map,
    record_operation_audit,
    summarize_audit_entry,
)


#
# Keep compatibility for modules that still import `task_service.task_list`
# during the A3 transition. New code should prefer repository helpers.
#

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _is_valid_grid_coordinate(value: int, max_value: int) -> bool:
    return isinstance(value, int) and 0 <= value < max_value


def _get_field(item: Any, field_name: str):
    if isinstance(item, dict):
        return item.get(field_name)
    return getattr(item, field_name, None)


def _validate_task_stages(stages, grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS):
    blocked = get_blocked_cells(grid_cols, grid_rows)
    for index, stage in enumerate(stages):
        points = (
            (stage.start_x, stage.start_y, "start"),
            (stage.end_x, stage.end_y, "end"),
        )
        for x, y, point_type in points:
            if not _is_valid_grid_coordinate(x, grid_cols) or not _is_valid_grid_coordinate(y, grid_rows):
                raise_api_error(400, "stage_out_of_grid", stage_index=index + 1, point_type=point_type)
            if (x, y) in blocked:
                raise_api_error(400, "stage_blocked", stage_index=index + 1, point_type=point_type)


def _resolve_payload_grid_size(item: Any) -> tuple[int, int]:
    requested_cols = _get_field(item, "grid_cols")
    requested_rows = _get_field(item, "grid_rows")
    if isinstance(requested_cols, int) and isinstance(requested_rows, int) and requested_cols > 0 and requested_rows > 0:
        return requested_cols, requested_rows
    return get_current_grid_size()


def _build_task_stages(item: Any, grid_cols: int, grid_rows: int):
    stages = _get_field(item, "stages")
    if stages:
        normalized_stages = [
            SimpleNamespace(**stage) if isinstance(stage, dict) else stage
            for stage in stages
        ]
        stage_models = build_stage_models(normalized_stages)
        _validate_task_stages(stage_models, grid_cols, grid_rows)
        return stage_models

    start_x = _get_field(item, "start_x")
    start_y = _get_field(item, "start_y")
    end_x = _get_field(item, "end_x")
    end_y = _get_field(item, "end_y")
    if None in {start_x, start_y, end_x, end_y}:
        raise_api_error(400, "task_coordinates_required")

    stage_models = build_stage_models(
        [
            SimpleNamespace(
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                label=None,
            )
        ]
    )
    _validate_task_stages(stage_models, grid_cols, grid_rows)
    return stage_models


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


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _serialize_task_with_audit(task: Task, created_entry=None, latest_entry=None):
    payload = _model_dump(task)
    if created_entry is not None:
        payload["created_by"] = created_entry.operator_display_name
        payload["created_by_role"] = created_entry.operator_role
        payload["created_by_at"] = created_entry.performed_at
    if latest_entry is not None:
        payload["last_operator"] = latest_entry.operator_display_name
        payload["last_operator_role"] = latest_entry.operator_role
        payload["last_operator_at"] = latest_entry.performed_at
        payload["last_operator_action"] = latest_entry.action
    return payload


def _attach_task_audit(task: Task):
    task_id = str(task.id)
    created_map = build_first_audit_map("task", [task_id])
    latest_map = build_latest_audit_map("task", [task_id])
    return _serialize_task_with_audit(task, created_map.get(task_id), latest_map.get(task_id))


def _attach_task_audits(tasks: list[Task]):
    task_ids = [str(task.id) for task in tasks]
    created_map = build_first_audit_map("task", task_ids)
    latest_map = build_latest_audit_map("task", task_ids)
    return [
        _serialize_task_with_audit(
            task,
            created_map.get(str(task.id)),
            latest_map.get(str(task.id)),
        )
        for task in tasks
    ]


def serialize_task_response(task: Task):
    return _attach_task_audit(task)


def _find_related_agv(task: Task):
    if task.agv_id is not None:
        agv = get_agv_by_id(task.agv_id)
        if agv is not None:
            return agv
    return next((agv for agv in list_agvs() if agv.task_id == task.id), None)


def _can_delete_task(task: Task) -> bool:
    return task.status in {"pending", "blocked", "finished", "assigned", "running"}


def _cleanup_related_agv(task: Task):
    agv = _find_related_agv(task)
    if agv is None:
        return None

    if agv.task_id == task.id:
        agv.task_id = None
    if agv.status not in {"maintenance", "fault"}:
        agv.status = "idle"
    return agv


def _is_orphaned_task(task: Task) -> bool:
    return task.status in {"assigned", "running"} and _find_related_agv(task) is None


def get_tasks():
    return _attach_task_audits(list_tasks())


def create_task(payload: Any, actor: dict | None = None):
    next_id = get_next_task_id()
    grid_cols, grid_rows = _resolve_payload_grid_size(payload)
    stages = _build_task_stages(payload, grid_cols, grid_rows)
    first_stage = stages[0]
    last_stage = stages[-1]
    task = Task(
        id=next_id,
        start_x=first_stage.start_x,
        start_y=first_stage.start_y,
        end_x=first_stage.end_x,
        end_y=first_stage.end_y,
        priority=_get_field(payload, "priority") or 1,
        status="pending",
        created_at=now_iso(),
        current_stage_index=0,
        total_stages=len(stages),
        overall_start_x=first_stage.start_x,
        overall_start_y=first_stage.start_y,
        overall_end_x=last_stage.end_x,
        overall_end_y=last_stage.end_y,
        stages=stages,
        dispatch_mode=_get_field(payload, "dispatch_mode"),
        preferred_agv_id=_get_field(payload, "preferred_agv_id"),
        dispatch_origin_x=_get_field(payload, "dispatch_origin_x"),
        dispatch_origin_y=_get_field(payload, "dispatch_origin_y"),
        dispatch_algorithm=_get_field(payload, "dispatch_algorithm"),
        dispatch_reason=_get_field(payload, "dispatch_reason"),
    )
    sync_task_stage_fields(task)
    add_task(task)
    audit = record_operation_audit("task", task.id, "create", actor)
    return {"message": "Task created", "task": _serialize_task_with_audit(task, audit, audit)}


def finish_task(task_id: int, actor: dict | None = None):
    task = get_task_by_id(task_id)
    if not task:
        raise_api_error(404, "task_not_found")
    if task.status != "running":
        raise_api_error(400, "task_not_running")

    agv = get_agv_by_id(task.agv_id) if task.agv_id is not None else None
    if not agv:
        raise_api_error(404, "related_agv_not_found")

    task.status = "finished"
    task.finished_at = now_iso()
    agv.status = "idle"
    agv.task_id = None
    latest = record_operation_audit("task", task.id, "finish", actor)
    created = build_first_audit_map("task", [str(task.id)]).get(str(task.id))
    return {"message": "Task finished", "task": _serialize_task_with_audit(task, created, latest), "agv": agv}


def import_tasks(items: list[Any], actor: dict | None = None):
    existing_ids = get_existing_task_ids()
    next_id = max(existing_ids, default=0) + 1
    created_ids = []

    for item in items:
        task_id = _get_field(item, "id")
        if task_id is None or task_id in existing_ids or task_id < 1:
            task_id = next_id
            next_id += 1
        existing_ids.add(task_id)

        grid_cols, grid_rows = _resolve_payload_grid_size(item)
        stages = _build_task_stages(item, grid_cols, grid_rows)
        first_stage = stages[0]
        last_stage = stages[-1]

        task = Task(
            id=task_id,
            start_x=first_stage.start_x,
            start_y=first_stage.start_y,
            end_x=first_stage.end_x,
            end_y=first_stage.end_y,
            priority=_get_field(item, "priority") or 1,
            status="pending",
            created_at=now_iso(),
            current_stage_index=0,
            total_stages=len(stages),
            overall_start_x=first_stage.start_x,
            overall_start_y=first_stage.start_y,
            overall_end_x=last_stage.end_x,
            overall_end_y=last_stage.end_y,
            stages=stages,
            dispatch_mode=_get_field(item, "dispatch_mode"),
            preferred_agv_id=_get_field(item, "preferred_agv_id"),
            dispatch_origin_x=_get_field(item, "dispatch_origin_x"),
            dispatch_origin_y=_get_field(item, "dispatch_origin_y"),
            dispatch_algorithm=_get_field(item, "dispatch_algorithm"),
            dispatch_reason=_get_field(item, "dispatch_reason"),
        )
        sync_task_stage_fields(task)
        add_task(task)
        record_operation_audit("task", task.id, "import", actor)
        created_ids.append(task_id)

    return {"message": "Tasks imported", "count": len(created_ids), "task_ids": created_ids}


def export_tasks(status: str | None = None):
    exported_tasks = list_tasks()
    if status:
        exported_tasks = [task for task in exported_tasks if task.status == status]
    return {
        "version": 2,
        "exported_at": now_iso(),
        "status_filter": status,
        "tasks": [serialize_task_for_json(task) for task in exported_tasks],
    }


def delete_task(task_id: int, actor: dict | None = None):
    task = get_task_by_id(task_id)
    if not task:
        raise_api_error(404, "task_not_found")
    if not _can_delete_task(task):
        raise_api_error(400, "task_delete_not_allowed")

    if task.status in {"assigned", "running"}:
        task.status = "cancelled"
        task.agv_id = None
    _cleanup_related_agv(task)
    record_operation_audit("task", task.id, "delete", actor)
    remove_task(task)
    return {
        "message": "Task deleted",
        "task_id": task_id,
        "operator": summarize_audit_entry(build_latest_audit_map("task", [str(task_id)]).get(str(task_id))),
    }


def delete_finished_tasks(actor: dict | None = None):
    finished_tasks = [task for task in list_tasks() if task.status == "finished"]
    removed_ids = []
    for task in finished_tasks:
        _cleanup_related_agv(task)
        record_operation_audit("task", task.id, "delete_finished", actor)
        remove_task(task)
        removed_ids.append(task.id)

    return {
        "message": "Finished tasks deleted",
        "count": len(removed_ids),
        "task_ids": removed_ids,
    }


def delete_orphaned_tasks(actor: dict | None = None):
    orphaned_tasks = [task for task in list_tasks() if _is_orphaned_task(task)]
    removed_ids = []
    for task in orphaned_tasks:
        record_operation_audit("task", task.id, "delete_orphaned", actor)
        remove_task(task)
        removed_ids.append(task.id)

    return {
        "message": "Orphaned tasks deleted",
        "count": len(removed_ids),
        "task_ids": removed_ids,
    }
