from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.agv_api import agv_list
from app.api.task_api import task_list
from app.utils.agv_movement import move_agv
from app.utils.api_error import raise_api_error
from app.utils.path_planner import plan_path
from app.utils.task_chain import (
    get_current_stage,
    mark_task_blocked,
    mark_task_pending,
    set_stage_paths,
    sync_task_stage_fields,
)
from app.utils.warehouse_map import get_blocked_cell_payload


router = APIRouter(prefix="/schedule", tags=["Schedule"])


class ScheduleWithPathRequest(BaseModel):
    task_id: int | None = None
    agv_id: int | None = None
    algorithm: str = "simple"
    grid_cols: int = 10
    grid_rows: int = 8


class CompareStagePayload(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None


class PathCompareRequest(BaseModel):
    start_x: int | None = None
    start_y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    stages: list[CompareStagePayload] | None = None
    grid_cols: int = 10
    grid_rows: int = 8


class RetryBlockedTaskRequest(BaseModel):
    algorithm: str = "astar"
    grid_cols: int = 10
    grid_rows: int = 8


class RecoverBlockedTaskRequest(BaseModel):
    mode: str = "reassign"  # bound / reassign
    algorithm: str | None = None
    grid_cols: int = 10
    grid_rows: int = 8


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _is_valid_grid_coordinate(value: int, max_value: int):
    return isinstance(value, int) and 0 <= value < max_value


def _validate_stage_bounds(stages: list[dict], grid_cols: int, grid_rows: int):
    for stage in stages:
        if (
            not _is_valid_grid_coordinate(stage["start_x"], grid_cols)
            or not _is_valid_grid_coordinate(stage["start_y"], grid_rows)
            or not _is_valid_grid_coordinate(stage["end_x"], grid_cols)
            or not _is_valid_grid_coordinate(stage["end_y"], grid_rows)
        ):
            raise_api_error(400, "stage_out_of_grid", stage_index=stage["index"] + 1)


def _mark_task_unreachable(task, algorithm: str, reason: str):
    mark_task_blocked(task, reason=reason, algorithm=algorithm)


def _normalize_algorithm_name(algorithm: str | None):
    normalized = (algorithm or "simple").lower().strip()
    if normalized not in {"simple", "astar"}:
        raise_api_error(400, "unsupported_algorithm")
    return normalized


def _normalize_recover_mode(mode: str | None):
    normalized = (mode or "reassign").lower().strip()
    if normalized not in {"bound", "reassign"}:
        raise_api_error(400, "unsupported_recover_mode")
    return normalized


def _resolve_task_algorithm(task, fallback_algorithm: str):
    preferred_algorithm = (getattr(task, "dispatch_algorithm", None) or "").lower().strip()
    if preferred_algorithm in {"simple", "astar"} and task.status in {"pending", "blocked"}:
        return preferred_algorithm
    return fallback_algorithm


def _reason_requires_bound_agv(reason: str):
    return reason.startswith("retry_from_current_waiting_for_bound_agv:")


def _task_requires_bound_agv(task):
    preferred_agv_id = getattr(task, "preferred_agv_id", None)
    if preferred_agv_id is None:
        return False
    reason = str(getattr(task, "dispatch_reason", "") or "")
    return task.dispatch_mode == "manual" or _reason_requires_bound_agv(reason)


def _select_schedulable_task(task_id: int | None):
    if task_id is not None:
        task = next((t for t in task_list if t.id == task_id), None)
        if not task:
            raise_api_error(404, "task_not_found")
        sync_task_stage_fields(task)
        if task.status not in {"pending", "blocked"}:
            raise_api_error(400, "task_not_schedulable")
        return task
    return None


def _select_idle_agv(agv_id: int | None):
    if agv_id is not None:
        agv = next((a for a in agv_list if a.id == agv_id), None)
        if not agv:
            raise_api_error(404, "agv_not_found")
        if agv.status != "idle":
            raise_api_error(400, "agv_not_idle")
        return agv

    idle_agv = next((a for a in agv_list if a.status == "idle"), None)
    if not idle_agv:
        raise_api_error(400, "no_idle_agv")
    return idle_agv


def _get_pending_tasks():
    pending_tasks = [t for t in task_list if t.status in {"pending", "blocked"}]
    schedulable_tasks = []
    for task in pending_tasks:
        sync_task_stage_fields(task)
        reason = str(getattr(task, "dispatch_reason", "") or "")
        # Recovery-required blocked tasks must be explicitly resumed/reassigned by user action.
        if task.status == "blocked" and (
            reason in {"recover_required_fault", "recover_required_emergency_stop", "cell_occupied_timeout"}
            or reason.startswith("cell_occupied_timeout:")
        ):
            continue
        schedulable_tasks.append(task)
    return schedulable_tasks


def _get_idle_agvs():
    return [a for a in agv_list if a.status == "idle"]


def _path_length(
    algorithm: str,
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
):
    path = plan_path(algorithm, sx, sy, ex, ey, grid_cols, grid_rows)
    if not path:
        return None
    return max(len(path) - 1, 0)


def _pick_task_and_agv(
    task_id: int | None,
    agv_id: int | None,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
):
    task = _select_schedulable_task(task_id)
    if task is not None:
        if agv_id is not None:
            agv = _select_idle_agv(agv_id)
            distance = _path_length(
                algorithm,
                agv.x,
                agv.y,
                task.start_x,
                task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                _mark_task_unreachable(
                    task,
                    algorithm,
                    f"当前算法 {algorithm} 下，AGV 无法到达任务起点",
                )
                raise HTTPException(status_code=400, detail="Task unreachable with current algorithm")
            return task, agv, distance

        idle_agvs = _get_idle_agvs()
        if not idle_agvs:
            raise HTTPException(status_code=400, detail="No idle AGV")

        best_agv = None
        best_distance = None
        for agv in idle_agvs:
            distance = _path_length(
                algorithm,
                agv.x,
                agv.y,
                task.start_x,
                task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                continue
            if best_distance is None or (distance, agv.id) < (best_distance, best_agv.id):
                best_distance = distance
                best_agv = agv

        if best_agv is None or best_distance is None:
            _mark_task_unreachable(
                task,
                algorithm,
                f"当前算法 {algorithm} 下，没有空闲 AGV 可到达任务起点",
            )
            raise HTTPException(status_code=400, detail="Task unreachable with current algorithm")
        return task, best_agv, best_distance

    pending_tasks = _get_pending_tasks()
    if not pending_tasks:
        raise HTTPException(status_code=400, detail="No pending tasks")

    idle_agvs = _get_idle_agvs()
    if not idle_agvs:
        raise HTTPException(status_code=400, detail="No idle AGV")

    if agv_id is not None:
        agv = _select_idle_agv(agv_id)
        best_task = None
        best_key = None
        best_distance = None
        for t in pending_tasks:
            dist = _path_length(algorithm, agv.x, agv.y, t.start_x, t.start_y, grid_cols, grid_rows)
            if dist is None:
                continue
            key = (-t.priority, dist, t.id)
            if best_key is None or key < best_key:
                best_key = key
                best_task = t
                best_distance = dist
        if best_task is None:
            raise HTTPException(status_code=400, detail="No reachable tasks")
        return best_task, agv, best_distance

    best_pair = None
    best_key = None
    best_distance = None
    for t in pending_tasks:
        reachable = False
        for a in idle_agvs:
            dist = _path_length(algorithm, a.x, a.y, t.start_x, t.start_y, grid_cols, grid_rows)
            if dist is None:
                continue
            reachable = True
            key = (-t.priority, dist, t.id, a.id)
            if best_key is None or key < best_key:
                best_key = key
                best_pair = (t, a)
                best_distance = dist
        if reachable:
            if t.status == "blocked":
                mark_task_pending(t)
        else:
            _mark_task_unreachable(
                t,
                algorithm,
                f"当前算法 {algorithm} 下，没有空闲 AGV 可到达任务起点",
            )

    if best_pair is None:
        raise HTTPException(status_code=400, detail="No reachable tasks")
    return best_pair[0], best_pair[1], best_distance


def _pick_task_and_agv_resolved(
    task_id: int | None,
    agv_id: int | None,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
):
    task = _select_schedulable_task(task_id)
    if task is not None:
        task_algorithm = algorithm
        if agv_id is not None:
            agv = _select_idle_agv(agv_id)
            distance = _path_length(
                task_algorithm,
                agv.x,
                agv.y,
                task.start_x,
                task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                _mark_task_unreachable(
                    task,
                    task_algorithm,
                    f"task_start_unreachable:{task_algorithm}",
                )
                raise_api_error(400, "task_start_unreachable", algorithm=task_algorithm)
            return task, agv, distance, task_algorithm

        idle_agvs = _get_idle_agvs()
        if not idle_agvs:
            raise_api_error(400, "no_idle_agv")

        best_agv = None
        best_distance = None
        for agv in idle_agvs:
            distance = _path_length(
                task_algorithm,
                agv.x,
                agv.y,
                task.start_x,
                task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                continue
            if best_distance is None or (distance, agv.id) < (best_distance, best_agv.id):
                best_distance = distance
                best_agv = agv

        if best_agv is None or best_distance is None:
            _mark_task_unreachable(
                task,
                task_algorithm,
                f"task_start_unreachable:{task_algorithm}",
            )
            raise_api_error(400, "task_start_unreachable", algorithm=task_algorithm)
        return task, best_agv, best_distance, task_algorithm

    pending_tasks = _get_pending_tasks()
    if not pending_tasks:
        raise_api_error(400, "no_pending_tasks")

    idle_agvs = _get_idle_agvs()
    if not idle_agvs:
        raise_api_error(400, "no_idle_agv")

    if agv_id is not None:
        agv = _select_idle_agv(agv_id)
        best_task = None
        best_key = None
        best_distance = None
        best_algorithm = algorithm
        for pending_task in pending_tasks:
            task_algorithm = _resolve_task_algorithm(pending_task, algorithm)
            distance = _path_length(
                task_algorithm,
                agv.x,
                agv.y,
                pending_task.start_x,
                pending_task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                continue
            key = (-pending_task.priority, distance, pending_task.id)
            if best_key is None or key < best_key:
                best_key = key
                best_task = pending_task
                best_distance = distance
                best_algorithm = task_algorithm
        if best_task is None:
            raise_api_error(400, "no_reachable_tasks")
        return best_task, agv, best_distance, best_algorithm

    best_pair = None
    best_key = None
    best_distance = None
    best_algorithm = algorithm
    for pending_task in pending_tasks:
        reachable = False
        task_algorithm = _resolve_task_algorithm(pending_task, algorithm)
        preferred_agv_id = getattr(pending_task, "preferred_agv_id", None)
        if _task_requires_bound_agv(pending_task):
            preferred_agv = next((agv for agv in idle_agvs if agv.id == preferred_agv_id), None)
            if preferred_agv is None:
                continue
            distance = _path_length(
                task_algorithm,
                preferred_agv.x,
                preferred_agv.y,
                pending_task.start_x,
                pending_task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                continue
            reachable = True
            key = (-pending_task.priority, distance, pending_task.id, preferred_agv.id)
            if best_key is None or key < best_key:
                best_key = key
                best_pair = (pending_task, preferred_agv)
                best_distance = distance
                best_algorithm = task_algorithm
            if reachable and pending_task.status == "blocked":
                mark_task_pending(pending_task)
            continue
        for agv in idle_agvs:
            distance = _path_length(
                task_algorithm,
                agv.x,
                agv.y,
                pending_task.start_x,
                pending_task.start_y,
                grid_cols,
                grid_rows,
            )
            if distance is None:
                continue
            reachable = True
            key = (-pending_task.priority, distance, pending_task.id, agv.id)
            if best_key is None or key < best_key:
                best_key = key
                best_pair = (pending_task, agv)
                best_distance = distance
                best_algorithm = task_algorithm
        if reachable:
            if pending_task.status == "blocked":
                mark_task_pending(pending_task)
        else:
            _mark_task_unreachable(
                pending_task,
                task_algorithm,
                f"task_start_unreachable:{task_algorithm}",
            )

    if best_pair is None:
        raise_api_error(400, "no_reachable_tasks")
    return best_pair[0], best_pair[1], best_distance, best_algorithm


def _build_compare_stages(req: PathCompareRequest):
    if req.stages:
        stages = [
            {
                "index": index,
                "label": stage.label,
                "start_x": stage.start_x,
                "start_y": stage.start_y,
                "end_x": stage.end_x,
                "end_y": stage.end_y,
            }
            for index, stage in enumerate(req.stages)
        ]
        _validate_stage_bounds(stages, req.grid_cols, req.grid_rows)
        return stages

    if None in {req.start_x, req.start_y, req.end_x, req.end_y}:
        raise_api_error(400, "task_coordinates_required")

    stages = [
        {
            "index": 0,
            "label": None,
            "start_x": req.start_x,
            "start_y": req.start_y,
            "end_x": req.end_x,
            "end_y": req.end_y,
        }
    ]
    _validate_stage_bounds(stages, req.grid_cols, req.grid_rows)
    return stages


def _compare_algorithm(
    algorithm: str,
    stages: list[dict],
    grid_cols: int,
    grid_rows: int,
):
    stage_results = []
    total_length = 0

    for stage in stages:
        path = plan_path(
            algorithm,
            stage["start_x"],
            stage["start_y"],
            stage["end_x"],
            stage["end_y"],
            grid_cols,
            grid_rows,
        )

        if not path:
            return {
                "algorithm": algorithm,
                "reachable": False,
                "total_length": None,
                "failed_stage_index": stage["index"],
                "stage_results": [
                    *stage_results,
                    {
                        "index": stage["index"],
                        "label": stage["label"],
                        "reachable": False,
                        "path_length": None,
                    },
                ],
            }

        path_length = max(len(path) - 1, 0)
        total_length += path_length
        stage_results.append(
            {
                "index": stage["index"],
                "label": stage["label"],
                "reachable": True,
                "path_length": path_length,
            }
        )

    return {
        "algorithm": algorithm,
        "reachable": True,
        "total_length": total_length,
        "failed_stage_index": None,
        "stage_results": stage_results,
    }


def _schedule_task(
    task_id: int | None,
    agv_id: int | None,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
    schedule_mode_override: str | None = None,
    resume_from_current: bool = False,
):
    algorithm = _normalize_algorithm_name(algorithm)
    schedule_mode = (
        schedule_mode_override
        if schedule_mode_override in {"auto", "manual"}
        else ("manual" if task_id is not None or agv_id is not None else "auto")
    )

    task, agv, dispatch_distance, task_algorithm = _pick_task_and_agv_resolved(
        task_id,
        agv_id,
        algorithm,
        grid_cols,
        grid_rows,
    )
    if (
        schedule_mode_override not in {"auto", "manual"}
        and task_id is None
        and agv_id is None
        and task.dispatch_mode == "manual"
        and task.preferred_agv_id == agv.id
    ):
        # Preserve manual semantics when auto poll schedules a bound manual task.
        schedule_mode = "manual"
    stage = get_current_stage(task)

    if task.created_at is None:
        task.created_at = now_iso()
    reason_text = str(task.dispatch_reason or "")
    should_resume_from_current = resume_from_current or (
        task.preferred_agv_id == agv.id
        and (
            reason_text in {"recover_required_fault", "recover_required_emergency_stop", "cell_occupied_timeout"}
            or reason_text.startswith("recover_waiting_for_bound_agv:")
            or reason_text.startswith("cell_occupied_timeout:")
            or reason_text.startswith("retry_from_current_waiting_for_bound_agv:")
        )
    )

    if should_resume_from_current:
        path_to_start = [{"x": agv.x, "y": agv.y}]
        path_to_end = plan_path(
            task_algorithm,
            agv.x,
            agv.y,
            stage.end_x,
            stage.end_y,
            grid_cols,
            grid_rows,
        )
    else:
        path_to_start = plan_path(
            task_algorithm,
            agv.x,
            agv.y,
            stage.start_x,
            stage.start_y,
            grid_cols,
            grid_rows,
        )
        path_to_end = plan_path(
            task_algorithm,
            stage.start_x,
            stage.start_y,
            stage.end_x,
            stage.end_y,
            grid_cols,
            grid_rows,
        )
    if not path_to_start or not path_to_end:
        _mark_task_unreachable(
            task,
            task_algorithm,
            f"task_route_unreachable:{task_algorithm}",
        )
        task.dispatch_reason = f"task_route_unreachable:{task_algorithm}"
        raise_api_error(400, "task_route_unreachable", algorithm=task_algorithm)

    task.status = "assigned"
    task.agv_id = agv.id
    task.preferred_agv_id = agv.id if schedule_mode == "manual" else None
    if schedule_mode == "manual" and task.dispatch_origin_x is None and task.dispatch_origin_y is None:
        task.dispatch_origin_x = agv.x
        task.dispatch_origin_y = agv.y
    task.assigned_at = now_iso()

    agv.task_id = task.id

    set_stage_paths(task, path_to_start, path_to_end)
    task.dispatch_mode = schedule_mode
    task.dispatch_distance = dispatch_distance
    task.dispatch_algorithm = task_algorithm
    task.cell_wait_retry_count = 0
    task.dispatch_reason = (
        f"mode={schedule_mode}, priority={task.priority}, distance={dispatch_distance}, agv={agv.id}, algorithm={task_algorithm}, stage={task.current_stage_index + 1}/{task.total_stages}"
    )

    if len(path_to_start) > 1:
        agv.status = "relocating"
    else:
        agv.status = "running"
        task.status = "running"
        task.started_at = now_iso()
        if stage.started_at is None:
            stage.started_at = task.started_at

    move_agv(agv.id, task.id, task_algorithm, grid_cols, grid_rows)

    full_path = path_to_start[:]
    if path_to_end:
        if full_path and path_to_end[0] == full_path[-1]:
            full_path.extend(path_to_end[1:])
        else:
            full_path.extend(path_to_end)

    path_stats = {
        "to_start": max(len(path_to_start) - 1, 0),
        "to_end": max(len(path_to_end) - 1, 0),
        "total": max(len(full_path) - 1, 0),
    }

    return {
        "message": "Task scheduled",
        "algorithm": task_algorithm,
        "task": {
            "id": task.id,
            "status": task.status,
            "start_x": stage.start_x,
            "start_y": stage.start_y,
            "end_x": stage.end_x,
            "end_y": stage.end_y,
            "priority": task.priority,
            "current_stage_index": task.current_stage_index,
            "total_stages": task.total_stages,
        },
        "agv": {
            "id": agv.id,
            "status": agv.status,
            "x": agv.x,
            "y": agv.y,
        },
        "path": full_path,
        "path_to_start": path_to_start,
        "path_to_end": path_to_end,
        "path_stats": path_stats,
        "blocked_cells": get_blocked_cell_payload(grid_cols, grid_rows),
    }


@router.post("/")
def schedule_task():
    return _schedule_task(None, None, "simple", 10, 8)


@router.post("/with_path")
def schedule_task_with_path(req: ScheduleWithPathRequest):
    return _schedule_task(
        req.task_id,
        req.agv_id,
        req.algorithm,
        req.grid_cols,
        req.grid_rows,
    )


@router.post("/compare_path")
def compare_path(req: PathCompareRequest):
    stages = _build_compare_stages(req)
    return {
        "grid_cols": req.grid_cols,
        "grid_rows": req.grid_rows,
        "stage_count": len(stages),
        "blocked_cells": get_blocked_cell_payload(req.grid_cols, req.grid_rows),
        "results": {
            "simple": _compare_algorithm("simple", stages, req.grid_cols, req.grid_rows),
            "astar": _compare_algorithm("astar", stages, req.grid_cols, req.grid_rows),
        },
    }


@router.post("/retry_blocked/{task_id}")
def retry_blocked_task(task_id: int, req: RetryBlockedTaskRequest):
    algorithm = _normalize_algorithm_name(req.algorithm)
    if algorithm != "astar":
        raise_api_error(400, "blocked_retry_requires_astar")

    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise_api_error(404, "task_not_found")

    sync_task_stage_fields(task)
    if task.status != "blocked":
        raise_api_error(400, "task_not_blocked")

    task.dispatch_algorithm = algorithm

    preferred_agv_id = getattr(task, "preferred_agv_id", None)
    if task.dispatch_mode == "manual" and preferred_agv_id is not None:
        preferred_agv = next((agv for agv in agv_list if agv.id == preferred_agv_id), None)
        if preferred_agv is None:
            raise_api_error(404, "agv_not_found")
        if preferred_agv.status != "idle":
            mark_task_pending(task)
            task.dispatch_algorithm = algorithm
            task.dispatch_mode = "manual"
            task.dispatch_reason = "retry_waiting_for_bound_agv:astar"
            return {
                "message": "Task queued for A* retry on bound AGV",
                "queued": True,
                "algorithm": algorithm,
                "task": {
                    "id": task.id,
                    "status": task.status,
                    "dispatch_algorithm": task.dispatch_algorithm,
                    "dispatch_reason": task.dispatch_reason,
                    "preferred_agv_id": task.preferred_agv_id,
                },
                "blocked_cells": get_blocked_cell_payload(req.grid_cols, req.grid_rows),
            }
        result = _schedule_task(task_id, preferred_agv_id, algorithm, req.grid_cols, req.grid_rows)
        result["queued"] = False
        return result

    if not _get_idle_agvs():
        mark_task_pending(task)
        task.dispatch_algorithm = algorithm
        task.dispatch_mode = "auto"
        task.preferred_agv_id = None
        task.dispatch_reason = "retry_waiting_for_idle_agv:astar"
        return {
            "message": "Task queued for A* retry",
            "queued": True,
            "algorithm": algorithm,
            "task": {
                "id": task.id,
                "status": task.status,
                "dispatch_algorithm": task.dispatch_algorithm,
                "dispatch_reason": task.dispatch_reason,
            },
            "blocked_cells": get_blocked_cell_payload(req.grid_cols, req.grid_rows),
        }

    result = _schedule_task(
        task_id,
        None,
        algorithm,
        req.grid_cols,
        req.grid_rows,
        schedule_mode_override="auto",
    )
    result["queued"] = False
    return result


@router.post("/retry_blocked_from_current/{task_id}")
def retry_blocked_task_from_current(task_id: int, req: RetryBlockedTaskRequest):
    algorithm = _normalize_algorithm_name(req.algorithm)

    task = next((t for t in task_list if t.id == task_id), None)
    if not task:
        raise_api_error(404, "task_not_found")

    sync_task_stage_fields(task)
    if task.status != "blocked":
        raise_api_error(400, "task_not_blocked")

    bound_agv_id = getattr(task, "preferred_agv_id", None)
    if bound_agv_id is None:
        raise_api_error(400, "task_has_no_bound_agv")

    bound_agv = next((agv for agv in agv_list if agv.id == bound_agv_id), None)
    if not bound_agv:
        raise_api_error(404, "agv_not_found")

    original_mode = task.dispatch_mode if task.dispatch_mode in {"auto", "manual"} else "auto"
    task.dispatch_algorithm = algorithm

    if bound_agv.status != "idle":
        mark_task_pending(task)
        task.dispatch_mode = original_mode
        task.preferred_agv_id = bound_agv_id
        task.dispatch_algorithm = algorithm
        task.dispatch_reason = f"retry_from_current_waiting_for_bound_agv:{algorithm}"
        return {
            "message": "Task queued for retry from current position on bound AGV",
            "queued": True,
            "algorithm": algorithm,
            "task": {
                "id": task.id,
                "status": task.status,
                "dispatch_mode": task.dispatch_mode,
                "dispatch_algorithm": task.dispatch_algorithm,
                "dispatch_reason": task.dispatch_reason,
                "preferred_agv_id": task.preferred_agv_id,
            },
            "blocked_cells": get_blocked_cell_payload(req.grid_cols, req.grid_rows),
        }

    result = _schedule_task(
        task_id,
        bound_agv_id,
        algorithm,
        req.grid_cols,
        req.grid_rows,
        schedule_mode_override=original_mode,
        resume_from_current=True,
    )
    result["queued"] = False
    result["resume_from_current"] = True
    return result


@router.post("/recover_blocked/{task_id}")
def recover_blocked_task(task_id: int, req: RecoverBlockedTaskRequest):
    task = next((item for item in task_list if item.id == task_id), None)
    if not task:
        raise_api_error(404, "task_not_found")

    sync_task_stage_fields(task)
    if task.status not in {"blocked", "pending"}:
        raise_api_error(400, "task_not_recoverable")

    recover_mode = _normalize_recover_mode(req.mode)
    algorithm = _normalize_algorithm_name(req.algorithm or task.dispatch_algorithm or "simple")
    task.dispatch_algorithm = algorithm

    if recover_mode == "bound":
        bound_agv_id = task.preferred_agv_id
        if bound_agv_id is None:
            raise_api_error(400, "task_has_no_bound_agv")

        bound_agv = next((agv for agv in agv_list if agv.id == bound_agv_id), None)
        if not bound_agv:
            raise_api_error(404, "agv_not_found")

        task.dispatch_mode = "manual"
        if bound_agv.status != "idle":
            mark_task_pending(task)
            task.dispatch_mode = "manual"
            task.preferred_agv_id = bound_agv_id
            task.dispatch_algorithm = algorithm
            task.dispatch_reason = f"recover_waiting_for_bound_agv:{algorithm}"
            return {
                "message": "Task queued for recovery on bound AGV",
                "queued": True,
                "recover_mode": recover_mode,
                "algorithm": algorithm,
                "task": {
                    "id": task.id,
                    "status": task.status,
                    "dispatch_algorithm": task.dispatch_algorithm,
                    "dispatch_reason": task.dispatch_reason,
                    "preferred_agv_id": task.preferred_agv_id,
                },
                "blocked_cells": get_blocked_cell_payload(req.grid_cols, req.grid_rows),
            }

        result = _schedule_task(task_id, bound_agv_id, algorithm, req.grid_cols, req.grid_rows)
        result["queued"] = False
        result["recover_mode"] = recover_mode
        return result

    # recover_mode == "reassign"
    task.dispatch_mode = "auto"
    task.preferred_agv_id = None
    if not _get_idle_agvs():
        mark_task_pending(task)
        task.dispatch_mode = "auto"
        task.preferred_agv_id = None
        task.dispatch_algorithm = algorithm
        task.dispatch_reason = f"recover_waiting_for_idle_agv:{algorithm}"
        return {
            "message": "Task queued for recovery on any idle AGV",
            "queued": True,
            "recover_mode": recover_mode,
            "algorithm": algorithm,
            "task": {
                "id": task.id,
                "status": task.status,
                "dispatch_algorithm": task.dispatch_algorithm,
                "dispatch_reason": task.dispatch_reason,
                "preferred_agv_id": task.preferred_agv_id,
            },
            "blocked_cells": get_blocked_cell_payload(req.grid_cols, req.grid_rows),
        }

    result = _schedule_task(
        task_id,
        None,
        algorithm,
        req.grid_cols,
        req.grid_rows,
        schedule_mode_override="auto",
    )
    result["queued"] = False
    result["recover_mode"] = recover_mode
    return result
