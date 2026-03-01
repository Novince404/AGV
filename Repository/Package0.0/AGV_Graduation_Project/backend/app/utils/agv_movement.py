import time
import threading
from datetime import datetime
from app.api.agv_api import agv_list
from app.api.task_api import task_list


def move_agv(
    agv_id: int,
    task_id: int,
    path_to_start: list[dict],
    path_to_end: list[dict],
):
    def now_iso():
        return datetime.now().isoformat(timespec="seconds")

    def run():
        agv = next((a for a in agv_list if a.id == agv_id), None)
        task = next((t for t in task_list if t.id == task_id), None)

        if not agv or not task:
            return

        if path_to_start and len(path_to_start) > 1:
            agv.status = "relocating"
            for point in path_to_start:
                agv.x = int(point["x"])
                agv.y = int(point["y"])
                time.sleep(1)

        task.status = "running"
        if task.started_at is None:
            task.started_at = now_iso()
        agv.status = "running"

        start_index = 0
        if path_to_start and path_to_end:
            if path_to_end[0] == path_to_start[-1]:
                start_index = 1

        for point in path_to_end[start_index:]:
            agv.x = int(point["x"])
            agv.y = int(point["y"])
            time.sleep(1)

        task.status = "finished"
        task.finished_at = now_iso()
        agv.status = "idle"
        agv.task_id = None

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
