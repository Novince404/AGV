from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.agv_api import agv_list
from app.api.task_api import task_list
from app.utils.agv_movement import move_agv
from app.utils.path_planner import plan_path


router = APIRouter(prefix="/schedule", tags=["Schedule"])


class ScheduleWithPathRequest(BaseModel):
    task_id: int | None = None
    agv_id: int | None = None
    algorithm: str = "simple"
    grid_cols: int = 10
    grid_rows: int = 8


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _select_pending_task(task_id: int | None):
    if task_id is not None:
        task = next((t for t in task_list if t.id == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status != "pending":
            raise HTTPException(status_code=400, detail="Task is not pending")
        return task
    return None


def _select_idle_agv(agv_id: int | None):
    if agv_id is not None:
        agv = next((a for a in agv_list if a.id == agv_id), None)
        if not agv:
            raise HTTPException(status_code=404, detail="AGV not found")
        if agv.status != "idle":
            raise HTTPException(status_code=400, detail="AGV is not idle")
        return agv

    idle_agv = next((a for a in agv_list if a.status == "idle"), None)
    if not idle_agv:
        raise HTTPException(status_code=400, detail="No idle AGV")
    return idle_agv


def _get_pending_tasks():
    return [t for t in task_list if t.status == "pending"]


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
    task = _select_pending_task(task_id)
    if task is not None:
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
            raise HTTPException(status_code=400, detail="Path not found")
        return task, agv, distance

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
        for a in idle_agvs:
            dist = _path_length(algorithm, a.x, a.y, t.start_x, t.start_y, grid_cols, grid_rows)
            if dist is None:
                continue
            key = (-t.priority, dist, t.id, a.id)
            if best_key is None or key < best_key:
                best_key = key
                best_pair = (t, a)
                best_distance = dist

    if best_pair is None:
        raise HTTPException(status_code=400, detail="No reachable tasks")
    return best_pair[0], best_pair[1], best_distance


def _schedule_task(
    task_id: int | None,
    agv_id: int | None,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
):
    algorithm = algorithm.lower().strip()
    if algorithm not in {"simple", "astar"}:
        raise HTTPException(status_code=400, detail="Unsupported algorithm")
    schedule_mode = "manual" if task_id is not None or agv_id is not None else "auto"

    task, agv, dispatch_distance = _pick_task_and_agv(
        task_id,
        agv_id,
        algorithm,
        grid_cols,
        grid_rows,
    )

    if task.created_at is None:
        task.created_at = now_iso()
    task.status = "assigned"
    task.agv_id = agv.id
    task.assigned_at = now_iso()

    agv.task_id = task.id

    path_to_start = plan_path(
        algorithm,
        agv.x,
        agv.y,
        task.start_x,
        task.start_y,
        grid_cols,
        grid_rows,
    )
    path_to_end = plan_path(
        algorithm,
        task.start_x,
        task.start_y,
        task.end_x,
        task.end_y,
        grid_cols,
        grid_rows,
    )
    if not path_to_start or not path_to_end:
        raise HTTPException(status_code=400, detail="Path not found")

    task.path_to_start = path_to_start
    task.path_to_end = path_to_end
    task.path_length_to_start = max(len(path_to_start) - 1, 0)
    task.path_length_to_end = max(len(path_to_end) - 1, 0)
    task.dispatch_mode = schedule_mode
    task.dispatch_distance = dispatch_distance
    task.dispatch_algorithm = algorithm
    task.dispatch_reason = (
        f"mode={schedule_mode}, priority={task.priority}, distance={dispatch_distance}, agv={agv.id}, algorithm={algorithm}"
    )

    if len(path_to_start) > 1:
        agv.status = "relocating"
    else:
        agv.status = "running"
        task.status = "running"
        task.started_at = now_iso()

    move_agv(agv.id, task.id, path_to_start, path_to_end)

    full_path = path_to_start[:]
    if path_to_end:
        if full_path and path_to_end[0] == full_path[-1]:
            full_path.extend(path_to_end[1:])
        else:
            full_path.extend(path_to_end)

    return {
        "message": "Task scheduled",
        "algorithm": algorithm,
        "task": {
            "id": task.id,
            "status": task.status,
            "start_x": task.start_x,
            "start_y": task.start_y,
            "end_x": task.end_x,
            "end_y": task.end_y,
            "priority": task.priority,
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
