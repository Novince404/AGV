import threading
import time
from datetime import datetime
from math import atan2, degrees

from app.repositories.agv_repository import get_agv_by_id, list_agvs
from app.repositories.task_repository import get_task_by_id
from app.utils.path_planner import plan_path, resolve_topology_segment_metadata
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
TOPOLOGY_EDGE_REPLAN_INTERVAL_SEC = 1.2
TOPOLOGY_OCCUPIED_NODE_REPLAN_INTERVAL_SEC = 1.4
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


def _point_coordinates(point) -> tuple[int, int]:
    return int(point["x"]), int(point["y"])


def _same_point_coordinates(a, b) -> bool:
    if not a or not b:
        return False
    return int(a.get("x", -1)) == int(b.get("x", -2)) and int(a.get("y", -1)) == int(b.get("y", -2))


def _build_topology_wait_reason(conflict: dict) -> str:
    edge_key = str(conflict.get("edge_key") or "topology")
    target_node = str(conflict.get("target_node") or "")
    blocker_agv_id = conflict.get("blocker_agv_id")
    parts = [f"edge={edge_key}"]
    if target_node:
        parts.append(f"node={target_node}")
    if blocker_agv_id is not None:
        parts.append(f"agv={int(blocker_agv_id)}")
    return f"topology_edge_waiting:{';'.join(parts)}"


def _build_topology_retry_reason(conflict: dict) -> str:
    edge_key = str(conflict.get("edge_key") or "topology")
    target_node = str(conflict.get("target_node") or "")
    blocker_agv_id = conflict.get("blocker_agv_id")
    parts = [f"edge={edge_key}"]
    if target_node:
        parts.append(f"node={target_node}")
    if blocker_agv_id is not None:
        parts.append(f"agv={int(blocker_agv_id)}")
    return f"topology_edge_reroute:{';'.join(parts)}"


def _extract_topology_avoidance(reason: str | None) -> tuple[set[str], set[str]]:
    text = str(reason or "").strip()
    if not text.startswith("topology_edge_reroute:"):
        return set(), set()

    payload = text.split(":", 1)[1] if ":" in text else ""
    avoid_edge_keys: set[str] = set()
    avoid_node_keys: set[str] = set()
    for part in payload.split(";"):
        key, _, value = part.partition("=")
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if not normalized_value:
            continue
        if normalized_key == "edge":
            avoid_edge_keys.add(normalized_value)
        elif normalized_key == "node":
            avoid_node_keys.add(normalized_value)
    return avoid_edge_keys, avoid_node_keys


def _detect_topology_edge_conflict(agv_id: int, source_x: int, source_y: int, point: dict):
    target_x, target_y = _point_coordinates(point)
    segment = resolve_topology_segment_metadata(
        source_x,
        source_y,
        target_x,
        target_y,
        edge_key=point.get("topology_edge_key"),
    )
    edge_key = str(segment.get("edge_key") or "").strip()
    if not edge_key or edge_key.startswith("grid:"):
        return None

    for other in list_agvs():
        if int(other.id) == int(agv_id) or other.status == "maintenance":
            continue
        other_edge = str(getattr(other, "current_edge", "") or "").strip()
        if other_edge != edge_key:
            continue
        blocker_task = get_task_by_id(other.task_id) if getattr(other, "task_id", None) is not None else None
        return {
            "edge_key": edge_key,
            "lane_type": str(segment.get("lane_type") or "main"),
            "speed_multiplier": float(segment.get("speed_multiplier") or 1.0),
            "target_node": str(segment.get("target_node") or _build_grid_node_key(target_x, target_y)),
            "blocker_agv_id": int(other.id),
            "blocker_task_id": int(other.task_id) if getattr(other, "task_id", None) is not None else None,
            "blocker_priority": int(getattr(blocker_task, "priority", 0) or 0) if blocker_task else 0,
            "blocker_motion_state": str(getattr(other, "motion_state", "") or getattr(other, "status", "") or "idle"),
        }
    return None


def _find_blocking_agv_at_position(agv_id: int, x: int, y: int):
    for other in list_agvs():
        if int(other.id) == int(agv_id) or other.status == "maintenance":
            continue
        if int(other.x) == int(x) and int(other.y) == int(y):
            return other
    return None


def _get_task_priority(task) -> int:
    try:
        return max(int(getattr(task, "priority", 0) or 0), 0)
    except Exception:
        return 0


def _should_reroute_for_blocker(agv, task, blocker_agv_id: int | None, blocker_task_id: int | None = None) -> bool:
    if blocker_agv_id is None:
        return True

    current_priority = _get_task_priority(task)
    blocker_task = get_task_by_id(blocker_task_id) if blocker_task_id is not None else None
    blocker_priority = _get_task_priority(blocker_task)
    if blocker_priority != current_priority:
        return blocker_priority > current_priority
    return int(blocker_agv_id) < int(agv.id)


def _topology_retry_backoff(agv, task, blocker_agv_id: int | None, blocker_task_id: int | None = None) -> float:
    if blocker_agv_id is None:
        return 0.0
    current_priority = _get_task_priority(task)
    blocker_task = get_task_by_id(blocker_task_id) if blocker_task_id is not None else None
    blocker_priority = _get_task_priority(blocker_task)
    if blocker_priority > current_priority:
        return 0.55
    if blocker_priority < current_priority:
        return 0.0
    return 0.35 if int(blocker_agv_id) < int(agv.id) else 0.0


def _build_topology_segment_conflict(source_x: int, source_y: int, point: dict, blocker_agv) -> dict | None:
    target_x, target_y = _point_coordinates(point)
    segment = resolve_topology_segment_metadata(
        source_x,
        source_y,
        target_x,
        target_y,
        edge_key=point.get("topology_edge_key"),
    )
    edge_key = str(segment.get("edge_key") or "").strip()
    if not edge_key or edge_key.startswith("grid:"):
        return None
    blocker_task_id = int(blocker_agv.task_id) if getattr(blocker_agv, "task_id", None) is not None else None
    blocker_task = get_task_by_id(blocker_task_id) if blocker_task_id is not None else None
    return {
        "edge_key": edge_key,
        "lane_type": str(segment.get("lane_type") or "main"),
        "speed_multiplier": float(segment.get("speed_multiplier") or 1.0),
        "target_node": str(segment.get("target_node") or _build_grid_node_key(target_x, target_y)),
        "blocker_agv_id": int(blocker_agv.id),
        "blocker_task_id": blocker_task_id,
        "blocker_priority": _get_task_priority(blocker_task),
        "blocker_motion_state": str(getattr(blocker_agv, "motion_state", "") or getattr(blocker_agv, "status", "") or "idle"),
    }


def _begin_motion_segment(agv, point: dict, active_status: str):
    source_x = int(agv.x)
    source_y = int(agv.y)
    target_x, target_y = _point_coordinates(point)
    segment = resolve_topology_segment_metadata(
        source_x,
        source_y,
        target_x,
        target_y,
        edge_key=point.get("topology_edge_key"),
    )
    start_node = str(segment.get("source_node") or _build_grid_node_key(source_x, source_y))
    edge_key = str(segment.get("edge_key") or f"{start_node}->{_build_grid_node_key(target_x, target_y)}")
    target_node = str(segment.get("target_node") or _build_grid_node_key(target_x, target_y))
    started_at = now_iso_ms()
    speed_multiplier = max(float(point.get("topology_speed_multiplier") or segment.get("speed_multiplier") or 1.0), 0.1)
    travel_duration_sec = CELL_TRAVEL_DURATION_SEC / speed_multiplier
    target_speed = DEFAULT_CELL_SPEED / max(travel_duration_sec, 0.1)
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
        motion_duration_ms=int(travel_duration_sec * 1000),
        motion_source_x=float(source_x),
        motion_source_y=float(source_y),
        motion_target_x=float(target_x),
        motion_target_y=float(target_y),
    )
    return target_node, target_speed, travel_duration_sec


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


def _set_waiting_motion_state(agv, active_status: str, motion_state: str = "waiting"):
    agv.apply_motion_fields(
        status=active_status,
        render_x=float(agv.x),
        render_y=float(agv.y),
        current_node=_build_grid_node_key(int(agv.x), int(agv.y)),
        current_edge=None,
        edge_progress=0.0,
        motion_state=motion_state,
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
    target_x, target_y = _point_coordinates(point)
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
        travel_duration_sec = CELL_TRAVEL_DURATION_SEC
        source_x = int(agv.x)
        source_y = int(agv.y)
        topology_conflict = None
        blocking_agv = None
        with movement_lock:
            topology_conflict = _detect_topology_edge_conflict(agv.id, source_x, source_y, point)
            if topology_conflict is None:
                blocking_agv = _find_blocking_agv_at_position(agv.id, target_x, target_y)
            if topology_conflict is None and blocking_agv is None:
                target_node, target_speed, travel_duration_sec = _begin_motion_segment(agv, point, active_status)
                moved = True

        if moved:
            if waiting_noted:
                task.dispatch_reason = previous_reason
            if source_x != target_x or source_y != target_y:
                time.sleep(travel_duration_sec)
            _finish_motion_segment(agv, target_x, target_y, target_node, active_status, target_speed)
            return "moved"

        waited_sec = time.monotonic() - wait_started_at
        if topology_conflict is not None:
            if not waiting_noted:
                task.dispatch_reason = _build_topology_wait_reason(topology_conflict)
                waiting_noted = True

            _set_waiting_motion_state(agv, active_status, motion_state="yielding")
            if waited_sec >= TOPOLOGY_EDGE_REPLAN_INTERVAL_SEC and _should_reroute_for_blocker(
                agv,
                task,
                topology_conflict.get("blocker_agv_id"),
                topology_conflict.get("blocker_task_id"),
            ):
                time.sleep(_topology_retry_backoff(agv, task, topology_conflict.get("blocker_agv_id"), topology_conflict.get("blocker_task_id")))
                task.dispatch_reason = _build_topology_retry_reason(topology_conflict)
                agv.clear_motion(motion_state=active_status)
                return "retry"
            if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
                task.dispatch_reason = _build_topology_retry_reason(topology_conflict)
                agv.clear_motion(motion_state=active_status)
                return "retry"

            time.sleep(MOVE_WAIT_INTERVAL_SEC)
            continue

        if blocking_agv is not None:
            topology_cell_conflict = _build_topology_segment_conflict(source_x, source_y, point, blocking_agv)
            if topology_cell_conflict is not None:
                if not waiting_noted:
                    task.dispatch_reason = _build_topology_wait_reason(topology_cell_conflict)
                    waiting_noted = True

                reroute_preferred = _should_reroute_for_blocker(
                    agv,
                    task,
                    topology_cell_conflict.get("blocker_agv_id"),
                    topology_cell_conflict.get("blocker_task_id"),
                )
                _set_waiting_motion_state(agv, active_status, motion_state="yielding" if reroute_preferred else "waiting")
                if waited_sec >= TOPOLOGY_OCCUPIED_NODE_REPLAN_INTERVAL_SEC and reroute_preferred:
                    time.sleep(
                        _topology_retry_backoff(
                            agv,
                            task,
                            topology_cell_conflict.get("blocker_agv_id"),
                            topology_cell_conflict.get("blocker_task_id"),
                        )
                    )
                    task.dispatch_reason = _build_topology_retry_reason(topology_cell_conflict)
                    agv.clear_motion(motion_state=active_status)
                    return "retry"
                if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
                    task.dispatch_reason = _build_topology_retry_reason(topology_cell_conflict)
                    agv.clear_motion(motion_state=active_status)
                    return "retry"
                time.sleep(MOVE_WAIT_INTERVAL_SEC)
                continue

        if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
            retry_budget = max(int(getattr(task, "cell_wait_retry_budget", 1)), 0)
            retry_count = max(int(getattr(task, "cell_wait_retry_count", 0)), 0)
            if retry_count < retry_budget:
                task.cell_wait_retry_count = retry_count + 1
                task.dispatch_reason = f"cell_occupied_retrying:{task.cell_wait_retry_count}"
                _set_waiting_motion_state(agv, active_status, motion_state="waiting")
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

        _set_waiting_motion_state(agv, active_status, motion_state="waiting")

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
            avoid_edge_keys, avoid_node_keys = _extract_topology_avoidance(getattr(task, "dispatch_reason", None))
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
                    request_priority=int(getattr(task, "priority", 0) or 0),
                    agv_id=agv.id,
                    avoid_edge_keys=avoid_edge_keys,
                    avoid_node_keys=avoid_node_keys,
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
                    request_priority=int(getattr(task, "priority", 0) or 0),
                    agv_id=agv.id,
                    avoid_edge_keys=avoid_edge_keys,
                    avoid_node_keys=avoid_node_keys,
                )
                path_to_end = plan_path(
                    algorithm,
                    stage.start_x,
                    stage.start_y,
                    stage.end_x,
                    stage.end_y,
                    grid_cols,
                    grid_rows,
                    request_priority=int(getattr(task, "priority", 0) or 0),
                    agv_id=agv.id,
                    avoid_edge_keys=avoid_edge_keys,
                    avoid_node_keys=avoid_node_keys,
                )
            if not path_to_start or not path_to_end:
                mark_task_blocked(task, f"task_route_unreachable:{algorithm}", algorithm)
                agv.status = "idle"
                agv.task_id = None
                agv.clear_motion()
                return

            set_stage_paths(task, path_to_start, path_to_end)
            if str(getattr(task, "dispatch_reason", "") or "").startswith("topology_edge_"):
                task.dispatch_reason = None

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
            if path_to_start and path_to_end and _same_point_coordinates(path_to_end[0], path_to_start[-1]):
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
            next_avoid_edge_keys, next_avoid_node_keys = _extract_topology_avoidance(getattr(task, "dispatch_reason", None))
            next_path_to_start = plan_path(
                algorithm,
                agv.x,
                agv.y,
                next_stage.start_x,
                next_stage.start_y,
                grid_cols,
                grid_rows,
                request_priority=int(getattr(task, "priority", 0) or 0),
                agv_id=agv.id,
                avoid_edge_keys=next_avoid_edge_keys,
                avoid_node_keys=next_avoid_node_keys,
            )
            next_path_to_end = plan_path(
                algorithm,
                next_stage.start_x,
                next_stage.start_y,
                next_stage.end_x,
                next_stage.end_y,
                grid_cols,
                grid_rows,
                request_priority=int(getattr(task, "priority", 0) or 0),
                agv_id=agv.id,
                avoid_edge_keys=next_avoid_edge_keys,
                avoid_node_keys=next_avoid_node_keys,
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


def move_agv_to_autonomy_target(
    agv_id: int,
    target_x: int,
    target_y: int,
    *,
    target_key: str,
    target_type: str,
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
):
    active_status = "waiting_for_charge" if target_type == "charge" else "idle_returning"

    def should_cancel_autonomy(agv) -> bool:
        if agv is None:
            return True
        if agv.task_id is not None:
            return True
        if agv.status in {"fault", "emergency_stop", "maintenance"}:
            return True
        if str(getattr(agv, "auto_target_type", "") or "") != target_type:
            return True
        if str(getattr(agv, "auto_target_node", "") or "") != target_key:
            return True
        return False

    def finalize_target(agv):
        if target_type == "charge":
            agv.status = "charging"
            agv.charge_started_at = now_iso()
            agv.idle_since_at = None
            agv.clear_motion(motion_state="charging")
            return
        agv.status = "idle"
        agv.auto_target_node = None
        agv.auto_target_type = None
        agv.idle_since_at = now_iso()
        agv.clear_motion()

    agv = get_agv_by_id(agv_id)
    if not agv or agv.task_id is not None or agv.status in {"fault", "emergency_stop", "maintenance"}:
        return False

    agv.auto_target_node = target_key
    agv.auto_target_type = target_type
    agv.charge_started_at = None
    agv.idle_since_at = None
    agv.status = active_status
    agv.clear_motion(motion_state=active_status)

    def run():
        with movement_lock:
            while True:
                agv = get_agv_by_id(agv_id)
                if should_cancel_autonomy(agv):
                    if agv is not None:
                        agv.clear_motion(motion_state=agv.status)
                    return

                path = plan_path(
                    algorithm,
                    agv.x,
                    agv.y,
                    target_x,
                    target_y,
                    grid_cols,
                    grid_rows,
                    request_priority=0,
                    agv_id=agv.id,
                )
                if not path:
                    agv.status = "idle"
                    agv.auto_target_node = None
                    agv.auto_target_type = None
                    agv.clear_motion()
                    return

                if len(path) <= 1:
                    finalize_target(agv)
                    return

                should_replan = False
                for point in path[1:]:
                    wait_started_at = time.monotonic()
                    while True:
                        agv = get_agv_by_id(agv_id)
                        if should_cancel_autonomy(agv):
                            if agv is not None:
                                agv.clear_motion(motion_state=agv.status)
                            return

                        source_x = int(agv.x)
                        source_y = int(agv.y)
                        topology_conflict = _detect_topology_edge_conflict(agv.id, source_x, source_y, point)
                        waited_sec = max(time.monotonic() - wait_started_at, 0.0)
                        if topology_conflict:
                            _set_waiting_motion_state(agv, active_status, motion_state="yielding")
                            if waited_sec >= TOPOLOGY_EDGE_REPLAN_INTERVAL_SEC:
                                should_replan = True
                                break
                            time.sleep(MOVE_WAIT_INTERVAL_SEC)
                            continue

                        next_x, next_y = _point_coordinates(point)
                        if is_cell_occupied_by_other_agv(agv.id, next_x, next_y):
                            _set_waiting_motion_state(agv, active_status, motion_state="waiting")
                            if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
                                should_replan = True
                                break
                            time.sleep(MOVE_WAIT_INTERVAL_SEC)
                            continue

                        target_node, target_speed, travel_duration_sec = _begin_motion_segment(agv, point, active_status)
                        time.sleep(travel_duration_sec)
                        _finish_motion_segment(agv, next_x, next_y, target_node, active_status, target_speed)
                        break

                    if should_replan:
                        break

                if should_replan:
                    continue

                finalize_target(agv)
                return

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return True
