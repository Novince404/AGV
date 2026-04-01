import threading
import time
from datetime import datetime
from math import atan2, degrees

from app.repositories.agv_repository import get_agv_by_id, list_agvs
from app.repositories.task_repository import get_task_by_id
from app.utils.path_planner import plan_path
from app.utils.task_chain import (
    advance_task_stage,
    get_current_stage,
    mark_task_blocked,
    set_stage_paths,
    sync_task_stage_fields,
)
from app.utils.warehouse_map import get_map_layout_state

movement_lock = threading.Lock()
MOVE_WAIT_INTERVAL_SEC = 0.25
MOVE_WAIT_TIMEOUT_SEC = 12
CELL_TRAVEL_DURATION_SEC = 0.9
DEFAULT_CELL_SPEED = 1.0


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def now_iso_ms():
    return datetime.now().isoformat(timespec="milliseconds")


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
    agv.clear_motion(motion_state=agv.status)
    return True


def should_cancel_task(agv, task):
    return getattr(task, "status", None) == "cancelled" or agv.task_id != task.id


def is_cell_occupied_by_other_agv(agv_id: int, x: int, y: int):
    return any(
        other.id != agv_id
        and other.status != "maintenance"
        and other.x == x
        and other.y == y
        for other in list_agvs()
    )


def _build_grid_node_key(x: int, y: int) -> str:
    return f"grid:{int(x)}:{int(y)}"


def _segment_heading(source_x: int, source_y: int, target_x: int, target_y: int) -> float:
    dx = float(target_x) - float(source_x)
    dy = float(target_y) - float(source_y)
    if dx == 0 and dy == 0:
        return 0.0
    return round(degrees(atan2(dy, dx)), 2)


def _resolve_motion_context(source_x: int, source_y: int, target_x: int, target_y: int):
    source_key = _build_grid_node_key(source_x, source_y)
    target_key = _build_grid_node_key(target_x, target_y)
    fallback_edge = f"{source_key}->{target_key}"

    try:
        topology = get_map_layout_state().get("topology") or {}
    except Exception:
        topology = {}

    nodes = topology.get("nodes") if isinstance(topology, dict) else []
    edges = topology.get("edges") if isinstance(topology, dict) else []
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return source_key, fallback_edge, target_key

    node_by_position: dict[tuple[int, int], str] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        try:
            x = int(node.get("x"))
            y = int(node.get("y"))
        except Exception:
            continue
        node_by_position[(x, y)] = str(node.get("key") or _build_grid_node_key(x, y))

    source_node = node_by_position.get((int(source_x), int(source_y))) or source_key
    target_node = node_by_position.get((int(target_x), int(target_y))) or target_key

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        edge_key = str(edge.get("key") or "") or fallback_edge
        edge_source = str(edge.get("source") or "")
        edge_target = str(edge.get("target") or "")
        direction = str(edge.get("direction") or "bidirectional")
        if edge_source == source_node and edge_target == target_node:
            return source_node, edge_key, target_node
        if direction == "bidirectional" and edge_source == target_node and edge_target == source_node:
            return source_node, edge_key, target_node

    return source_node, fallback_edge, target_node


def _begin_motion_segment(agv, source_x: int, source_y: int, target_x: int, target_y: int, active_status: str):
    start_node, edge_key, target_node = _resolve_motion_context(source_x, source_y, target_x, target_y)
    started_at = now_iso_ms()
    target_speed = DEFAULT_CELL_SPEED / max(CELL_TRAVEL_DURATION_SEC, 0.1)
    heading = _segment_heading(source_x, source_y, target_x, target_y)

    agv.apply_motion_fields(
        x=target_x,
        y=target_y,
        status=active_status,
        render_x=float(source_x),
        render_y=float(source_y),
        current_node=start_node,
        current_edge=edge_key,
        edge_progress=0.0,
        motion_state=active_status,
        current_speed=target_speed,
        target_speed=target_speed,
        heading=heading,
        motion_started_at=started_at,
        motion_updated_at=started_at,
        motion_duration_ms=int(CELL_TRAVEL_DURATION_SEC * 1000),
        motion_source_x=float(source_x),
        motion_source_y=float(source_y),
        motion_target_x=float(target_x),
        motion_target_y=float(target_y),
    )
    return target_node, target_speed


def _finish_motion_segment(agv, target_x: int, target_y: int, target_node: str, active_status: str, target_speed: float):
    agv.apply_motion_fields(
        render_x=float(target_x),
        render_y=float(target_y),
        current_node=target_node,
        edge_progress=1.0,
        motion_state=active_status,
        current_speed=0.0,
        target_speed=target_speed,
        motion_updated_at=now_iso_ms(),
    )


def _set_waiting_motion_state(agv, active_status: str):
    agv.apply_motion_fields(
        status=active_status,
        render_x=float(agv.x),
        render_y=float(agv.y),
        current_node=_build_grid_node_key(int(agv.x), int(agv.y)),
        current_edge=None,
        edge_progress=0.0,
        motion_state="waiting",
        current_speed=0.0,
        target_speed=0.0,
        heading=0.0,
        motion_started_at=None,
        motion_updated_at=now_iso_ms(),
        motion_duration_ms=0,
        motion_source_x=float(agv.x),
        motion_source_y=float(agv.y),
        motion_target_x=float(agv.x),
        motion_target_y=float(agv.y),
    )


def move_to_point_with_collision_guard(agv, task, point, algorithm: str, active_status: str):
    target_x = int(point["x"])
    target_y = int(point["y"])
    previous_reason = task.dispatch_reason
    waiting_noted = False
    wait_started_at = time.monotonic()

    while True:
        if should_cancel_task(agv, task):
            return "cancelled"
        if should_interrupt_agv(agv, task, algorithm):
            return "interrupted"

        moved = False
        target_node = _build_grid_node_key(target_x, target_y)
        target_speed = 0.0
        source_x = int(agv.x)
        source_y = int(agv.y)
        with movement_lock:
            if not is_cell_occupied_by_other_agv(agv.id, target_x, target_y):
                target_node, target_speed = _begin_motion_segment(agv, source_x, source_y, target_x, target_y, active_status)
                moved = True

        if moved:
            if waiting_noted:
                task.dispatch_reason = previous_reason
            if source_x != target_x or source_y != target_y:
                time.sleep(CELL_TRAVEL_DURATION_SEC)
            _finish_motion_segment(agv, target_x, target_y, target_node, active_status, target_speed)
            return "moved"

        waited_sec = time.monotonic() - wait_started_at
        if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
            retry_budget = max(int(getattr(task, "cell_wait_retry_budget", 1)), 0)
            retry_count = max(int(getattr(task, "cell_wait_retry_count", 0)), 0)
            if retry_count < retry_budget:
                task.cell_wait_retry_count = retry_count + 1
                task.dispatch_reason = f"cell_occupied_retrying:{task.cell_wait_retry_count}"
                _set_waiting_motion_state(agv, active_status)
                return "retry"

            task.preferred_agv_id = task.preferred_agv_id or agv.id
            mark_task_blocked(task, "cell_occupied_timeout", algorithm)
            agv.status = "idle"
            agv.task_id = None
            agv.clear_motion()
            return "blocked"

        if not waiting_noted:
            task.dispatch_reason = "cell_occupied_waiting"
            waiting_noted = True

        _set_waiting_motion_state(agv, active_status)

        time.sleep(MOVE_WAIT_INTERVAL_SEC)


def move_agv(
    agv_id: int,
    task_id: int,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
):
    def run():
        agv = get_agv_by_id(agv_id)
        task = get_task_by_id(task_id)
        if not agv or not task:
            return

        agv.clear_motion(motion_state=agv.status)

        while True:
            if should_cancel_task(agv, task):
                agv.clear_motion(motion_state=agv.status)
                return
            if should_interrupt_agv(agv, task, algorithm):
                agv.clear_motion(motion_state=agv.status)
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
                agv.clear_motion()
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
                    if move_result == "cancelled":
                        agv.clear_motion(motion_state=agv.status)
                        return
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
                start_index = 1 if len(path_to_start) > 1 else 0

            for point in path_to_end[start_index:]:
                move_result = move_to_point_with_collision_guard(agv, task, point, algorithm, "running")
                if move_result == "moved":
                    continue
                if move_result == "retry":
                    should_retry_stage = True
                    break
                if move_result == "cancelled":
                    agv.clear_motion(motion_state=agv.status)
                    return
                return
            if should_retry_stage:
                continue

            stage.finished_at = now_iso()

            if not advance_task_stage(task):
                task.status = "finished"
                task.finished_at = now_iso()
                agv.status = "idle"
                agv.task_id = None
                agv.clear_motion()
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
                agv.clear_motion()
                return

            set_stage_paths(task, next_path_to_start, next_path_to_end)
            task.status = "assigned" if len(next_path_to_start) > 1 else "running"
            agv.status = "relocating" if len(next_path_to_start) > 1 else "running"
            agv.clear_motion(motion_state=agv.status)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
