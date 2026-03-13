import threading
import time
from datetime import datetime

from app.api.agv_api import agv_list
from app.api.task_api import task_list
from app.utils.path_planner import plan_path
from app.utils.task_chain import (
    advance_task_stage,
    get_current_stage,
    mark_task_blocked,
    set_stage_paths,
    sync_task_stage_fields,
)

movement_lock = threading.Lock()
MOVE_WAIT_INTERVAL_SEC = 0.25
MOVE_WAIT_TIMEOUT_SEC = 12


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def interrupt_reason_for_status(status: str):
    if status == "fault":
        return "agv_fault_stop"
    if status == "emergency_stop":
        return "agv_emergency_stop"
    return None


def should_interrupt_agv(agv, task, algorithm: str):
    reason = interrupt_reason_for_status(agv.status)
    if not reason:
        return False

    if task.status not in {"blocked", "finished"}:
        # Preserve AGV binding for later recovery actions.
        task.preferred_agv_id = task.preferred_agv_id or agv.id
        if reason == "agv_fault_stop":
            mark_task_blocked(task, "recover_required_fault", algorithm)
        elif reason == "agv_emergency_stop":
            mark_task_blocked(task, "recover_required_emergency_stop", algorithm)
        else:
            mark_task_blocked(task, reason, algorithm)
    agv.task_id = None
    return True


def is_cell_occupied_by_other_agv(agv_id: int, x: int, y: int):
    return any(other.id != agv_id and other.x == x and other.y == y for other in agv_list)


def move_to_point_with_collision_guard(agv, task, point, algorithm: str, active_status: str):
    target_x = int(point["x"])
    target_y = int(point["y"])
    previous_reason = task.dispatch_reason
    waiting_noted = False
    wait_started_at = time.monotonic()

    while True:
        if should_interrupt_agv(agv, task, algorithm):
            return "interrupted"

        moved = False
        with movement_lock:
            if not is_cell_occupied_by_other_agv(agv.id, target_x, target_y):
                agv.x = target_x
                agv.y = target_y
                moved = True

        if moved:
            agv.status = active_status
            if waiting_noted:
                task.dispatch_reason = previous_reason
            time.sleep(1)
            return "moved"

        waited_sec = time.monotonic() - wait_started_at
        if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
            retry_budget = max(int(getattr(task, "cell_wait_retry_budget", 1)), 0)
            retry_count = max(int(getattr(task, "cell_wait_retry_count", 0)), 0)
            if retry_count < retry_budget:
                task.cell_wait_retry_count = retry_count + 1
                task.dispatch_reason = f"cell_occupied_retrying:{task.cell_wait_retry_count}"
                return "retry"

            task.preferred_agv_id = task.preferred_agv_id or agv.id
            mark_task_blocked(task, "cell_occupied_timeout", algorithm)
            agv.status = "idle"
            agv.task_id = None
            return "blocked"

        if not waiting_noted:
            task.dispatch_reason = "cell_occupied_waiting"
            waiting_noted = True

        agv.status = active_status

        time.sleep(MOVE_WAIT_INTERVAL_SEC)


def move_agv(
    agv_id: int,
    task_id: int,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
):
    def run():
        agv = next((a for a in agv_list if a.id == agv_id), None)
        task = next((t for t in task_list if t.id == task_id), None)
        if not agv or not task:
            return

        while True:
            if should_interrupt_agv(agv, task, algorithm):
                return

            stage = sync_task_stage_fields(task)
            running_from_current = task.status == "running" or agv.status == "running"
            if running_from_current:
                path_to_start = [{"x": agv.x, "y": agv.y}]
                path_to_end = plan_path(
                    algorithm,
                    agv.x,
                    agv.y,
                    stage.end_x,
                    stage.end_y,
                    grid_cols,
                    grid_rows,
                )
            else:
                path_to_start = plan_path(
                    algorithm,
                    agv.x,
                    agv.y,
                    stage.start_x,
                    stage.start_y,
                    grid_cols,
                    grid_rows,
                )
                path_to_end = plan_path(
                    algorithm,
                    stage.start_x,
                    stage.start_y,
                    stage.end_x,
                    stage.end_y,
                    grid_cols,
                    grid_rows,
                )
            if not path_to_start or not path_to_end:
                mark_task_blocked(task, f"task_route_unreachable:{algorithm}", algorithm)
                agv.status = "idle"
                agv.task_id = None
                return

            set_stage_paths(task, path_to_start, path_to_end)

            should_retry_stage = False
            if len(path_to_start) > 1:
                agv.status = "relocating"
                for point in path_to_start:
                    move_result = move_to_point_with_collision_guard(agv, task, point, algorithm, "relocating")
                    if move_result == "moved":
                        continue
                    if move_result == "retry":
                        should_retry_stage = True
                        break
                    return
            if should_retry_stage:
                continue

            task.status = "running"
            if task.started_at is None:
                task.started_at = now_iso()
            if stage.started_at is None:
                stage.started_at = now_iso()
            agv.status = "running"

            start_index = 0
            if path_to_start and path_to_end and path_to_end[0] == path_to_start[-1]:
                # Keep one visible "idle tick" before the first real move when
                # AGV starts directly from current cell (no relocation path).
                # This avoids the first step looking faster than later steps.
                start_index = 1 if len(path_to_start) > 1 else 0

            for point in path_to_end[start_index:]:
                move_result = move_to_point_with_collision_guard(agv, task, point, algorithm, "running")
                if move_result == "moved":
                    continue
                if move_result == "retry":
                    should_retry_stage = True
                    break
                return
            if should_retry_stage:
                continue

            stage.finished_at = now_iso()

            if not advance_task_stage(task):
                task.status = "finished"
                task.finished_at = now_iso()
                agv.status = "idle"
                agv.task_id = None
                return

            next_stage = get_current_stage(task)
            next_path_to_start = plan_path(
                algorithm,
                agv.x,
                agv.y,
                next_stage.start_x,
                next_stage.start_y,
                grid_cols,
                grid_rows,
            )
            next_path_to_end = plan_path(
                algorithm,
                next_stage.start_x,
                next_stage.start_y,
                next_stage.end_x,
                next_stage.end_y,
                grid_cols,
                grid_rows,
            )
            if not next_path_to_start or not next_path_to_end:
                mark_task_blocked(task, f"task_route_unreachable:{algorithm}", algorithm)
                agv.status = "idle"
                agv.task_id = None
                return

            set_stage_paths(task, next_path_to_start, next_path_to_end)
            task.status = "assigned" if len(next_path_to_start) > 1 else "running"
            agv.status = "relocating" if len(next_path_to_start) > 1 else "running"

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

