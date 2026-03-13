from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.models.task import Task
from app.repositories.agv_repository import agv_list
from app.repositories.task_repository import task_list
from app.utils.api_error import raise_api_error
from app.utils.task_chain import build_stage_models, sync_task_stage_fields
from app.utils.warehouse_map import DEFAULT_GRID_COLS, DEFAULT_GRID_ROWS, get_blocked_cells


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


def _build_task_stages(item: Any):
    stages = _get_field(item, "stages")
    if stages:
        normalized_stages = [
            SimpleNamespace(**stage) if isinstance(stage, dict) else stage
            for stage in stages
        ]
        stage_models = build_stage_models(normalized_stages)
        _validate_task_stages(stage_models)
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
    _validate_task_stages(stage_models)
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


def get_tasks():
    return task_list


def create_task(payload: Any):
    next_id = max((t.id for t in task_list), default=0) + 1
    stages = _build_task_stages(payload)
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
    task_list.append(task)
    return {"message": "Task created", "task": task}


def finish_task(task_id: int):
    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise_api_error(404, "task_not_found")
    if task.status != "running":
        raise_api_error(400, "task_not_running")

    agv = next((a for a in agv_list if a.id == task.agv_id), None)
    if not agv:
        raise_api_error(404, "related_agv_not_found")

    task.status = "finished"
    task.finished_at = now_iso()
    agv.status = "idle"
    agv.task_id = None
    return {"message": "Task finished", "task": task, "agv": agv}


def import_tasks(items: list[Any]):
    existing_ids = {t.id for t in task_list}
    next_id = max(existing_ids, default=0) + 1
    created_ids = []

    for item in items:
        task_id = _get_field(item, "id")
        if task_id is None or task_id in existing_ids or task_id < 1:
            task_id = next_id
            next_id += 1
        existing_ids.add(task_id)

        stages = _build_task_stages(item)
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
        task_list.append(task)
        created_ids.append(task_id)

    return {"message": "Tasks imported", "count": len(created_ids), "task_ids": created_ids}


def export_tasks():
    return {
        "version": 2,
        "exported_at": now_iso(),
        "tasks": [serialize_task_for_json(task) for task in task_list],
    }


def delete_task(task_id: int):
    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise_api_error(404, "task_not_found")
    if task.status not in {"pending", "blocked"}:
        raise_api_error(400, "task_delete_not_allowed")

    task_list.remove(task)
    return {"message": "Task deleted", "task_id": task_id}
