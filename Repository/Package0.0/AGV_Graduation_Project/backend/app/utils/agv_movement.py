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


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


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
            stage = sync_task_stage_fields(task)
            path_to_start = stage.path_to_start or plan_path(
                algorithm,
                agv.x,
                agv.y,
                stage.start_x,
                stage.start_y,
                grid_cols,
                grid_rows,
            )
            path_to_end = stage.path_to_end or plan_path(
                algorithm,
                stage.start_x,
                stage.start_y,
                stage.end_x,
                stage.end_y,
                grid_cols,
                grid_rows,
            )
            if not path_to_start or not path_to_end:
                mark_task_blocked(task, f"当前算法 {algorithm} 下，任务路径不可达，请切换算法或修改点位", algorithm)
                agv.status = "idle"
                agv.task_id = None
                return

            set_stage_paths(task, path_to_start, path_to_end)

            if len(path_to_start) > 1:
                agv.status = "relocating"
                for point in path_to_start:
                    agv.x = int(point["x"])
                    agv.y = int(point["y"])
                    time.sleep(1)

            task.status = "running"
            if task.started_at is None:
                task.started_at = now_iso()
            if stage.started_at is None:
                stage.started_at = now_iso()
            agv.status = "running"

            start_index = 0
            if path_to_start and path_to_end and path_to_end[0] == path_to_start[-1]:
                start_index = 1

            for point in path_to_end[start_index:]:
                agv.x = int(point["x"])
                agv.y = int(point["y"])
                time.sleep(1)

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
                mark_task_blocked(task, f"当前算法 {algorithm} 下，下一阶段路径不可达，请切换算法或修改点位", algorithm)
                agv.status = "idle"
                agv.task_id = None
                return

            set_stage_paths(task, next_path_to_start, next_path_to_end)
            task.status = "assigned" if len(next_path_to_start) > 1 else "running"
            agv.status = "relocating" if len(next_path_to_start) > 1 else "running"

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
