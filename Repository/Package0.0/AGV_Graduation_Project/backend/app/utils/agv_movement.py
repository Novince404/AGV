import threading
import time
from datetime import datetime
from math import atan2, degrees

from app.core.data_scope import get_current_scope_key, use_scope
from app.repositories.agv_repository import get_agv_by_id, list_agvs
from app.repositories.task_repository import get_task_by_id
from app.repositories.ui_settings_repository import get_ui_settings as get_ui_settings_store
from app.utils.path_planner import (
    build_runtime_special_node_constraints,
    plan_path,
    resolve_topology_segment_metadata,
)
from app.utils.task_chain import (
    advance_task_stage,
    get_current_stage,
    mark_task_blocked,
    set_stage_paths,
    sync_task_stage_fields,
)
from app.utils.warehouse_map import (
    get_current_grid_size,
    get_map_layout_state,
    get_navigation_blocked_cells,
    get_topology_node_default_capacity,
    normalize_topology_node_capacity,
)
movement_lock = threading.Lock()
MOVE_WAIT_INTERVAL_SEC = 0.25
MOVE_WAIT_TIMEOUT_SEC = 12
TOPOLOGY_EDGE_REPLAN_INTERVAL_SEC = 1.2
TOPOLOGY_OCCUPIED_NODE_REPLAN_INTERVAL_SEC = 1.4
TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC = 4.5
TOPOLOGY_FOLLOW_LOOKAHEAD_CELLS = 1.65
TOPOLOGY_FOLLOW_MIN_GAP_CELLS = 0.75
CELL_TRAVEL_DURATION_SEC = 0.9
DEFAULT_CELL_SPEED = 1.0
DEFAULT_BASE_SPEED = round(DEFAULT_CELL_SPEED / CELL_TRAVEL_DURATION_SEC, 2)
RUNTIME_MOTION_UI_SETTINGS_DEFAULTS = {
    "base_speed": DEFAULT_BASE_SPEED,
    "follow_distance": TOPOLOGY_FOLLOW_MIN_GAP_CELLS,
    "deadlock_timeout_sec": TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC,
}


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


def _segment_direction(source_x: int, source_y: int, target_x: int, target_y: int) -> tuple[int, int]:
    dx = int(target_x) - int(source_x)
    dy = int(target_y) - int(source_y)
    if dx > 0:
        dx = 1
    elif dx < 0:
        dx = -1
    if dy > 0:
        dy = 1
    elif dy < 0:
        dy = -1
    return dx, dy


def _get_runtime_motion_settings() -> dict:
    payload = get_ui_settings_store(RUNTIME_MOTION_UI_SETTINGS_DEFAULTS)
    try:
        base_speed = max(0.2, min(6.0, float(payload.get("base_speed", DEFAULT_BASE_SPEED))))
    except Exception:
        base_speed = DEFAULT_BASE_SPEED
    try:
        follow_distance = max(0.25, min(3.0, float(payload.get("follow_distance", TOPOLOGY_FOLLOW_MIN_GAP_CELLS))))
    except Exception:
        follow_distance = TOPOLOGY_FOLLOW_MIN_GAP_CELLS
    try:
        deadlock_timeout_sec = max(1.0, min(20.0, float(payload.get("deadlock_timeout_sec", TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC))))
    except Exception:
        deadlock_timeout_sec = TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC
    return {
        "base_speed": base_speed,
        "follow_distance": follow_distance,
        "follow_lookahead_cells": max(1.65, follow_distance * 2.0, follow_distance + 0.9),
        "deadlock_timeout_sec": deadlock_timeout_sec,
    }


def _point_coordinates(point) -> tuple[int, int]:
    return int(point["x"]), int(point["y"])


def _same_point_coordinates(a, b) -> bool:
    if not a or not b:
        return False
    return int(a.get("x", -1)) == int(b.get("x", -2)) and int(a.get("y", -1)) == int(b.get("y", -2))


def _estimate_runtime_axis_position(agv, *, horizontal: bool) -> float:
    source_value = float(getattr(agv, "motion_source_x" if horizontal else "motion_source_y", getattr(agv, "x" if horizontal else "y", 0)) or 0)
    target_value = float(getattr(agv, "motion_target_x" if horizontal else "motion_target_y", getattr(agv, "x" if horizontal else "y", 0)) or 0)
    started_ms = None
    duration_ms = 0.0
    try:
        started_ms = datetime.fromisoformat(str(getattr(agv, "motion_started_at", "") or "")).timestamp() * 1000.0
    except Exception:
        started_ms = None
    try:
        duration_ms = max(float(getattr(agv, "motion_duration_ms", 0) or 0), 0.0)
    except Exception:
        duration_ms = 0.0
    if started_ms is None or duration_ms <= 0:
        return float(getattr(agv, "render_x" if horizontal else "render_y", getattr(agv, "x" if horizontal else "y", 0)) or 0)

    now_ms = time.time() * 1000.0
    progress = max(0.0, min(1.0, (now_ms - started_ms) / duration_ms))
    return source_value + (target_value - source_value) * progress


def _get_runtime_topology_node_key_at_position(x: int, y: int) -> str | None:
    state = get_map_layout_state()
    topology = state.get("topology") or {}
    for node in topology.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if int(node.get("x", -1)) != int(x) or int(node.get("y", -1)) != int(y):
            continue
        return str(node.get("key") or _build_grid_node_key(x, y))
    return None


def _build_autonomy_runtime_path_constraints(
    agv,
    *,
    target_key: str,
    target_x: int,
    target_y: int,
) -> tuple[set[tuple[int, int]], set[str]]:
    blocked_cells = set(get_navigation_blocked_cells(*get_current_grid_size()))
    constraints = build_runtime_special_node_constraints(
        exclude_agv_id=getattr(agv, "id", None),
        goal_node_key=target_key,
        allowed_node_keys={target_key},
    )
    blocked_cells |= set(constraints["blocked_positions"])
    blocked_cells.discard((int(agv.x), int(agv.y)))
    blocked_cells.discard((int(target_x), int(target_y)))
    return blocked_cells, set(constraints["avoid_node_keys"])


def _get_special_topology_node_at_position(x: int, y: int) -> dict | None:
    state = get_map_layout_state()
    topology = state.get("topology") or {}
    for node in topology.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if int(node.get("x", -1)) != int(x) or int(node.get("y", -1)) != int(y):
            continue
        node_type = str(node.get("node_type") or "waypoint")
        if node_type not in {"station", "parking", "charge"}:
            continue
        return {
            "key": str(node.get("key") or _build_grid_node_key(x, y)),
            "node_type": node_type,
            "capacity": normalize_topology_node_capacity(node_type, node.get("capacity")),
        }
    return None


def _special_topology_node_has_spare_capacity(x: int, y: int, *, exclude_agv_id: int | None = None) -> dict | None:
    special_node = _get_special_topology_node_at_position(x, y)
    if special_node is None:
        return None

    occupancy = 0
    for other in list_agvs():
        try:
            other_id = int(other.id)
        except Exception:
            continue
        if exclude_agv_id is not None and other_id == int(exclude_agv_id):
            continue
        if getattr(other, "status", None) == "maintenance":
            continue
        if int(other.x) == int(x) and int(other.y) == int(y):
            occupancy += 1

    if occupancy < int(special_node["capacity"]):
        return special_node
    return None


def _detect_same_corridor_follow_conflict(
    agv_id: int,
    source_x: int,
    source_y: int,
    point: dict,
    *,
    motion_settings: dict | None = None,
):
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

    direction_x, direction_y = _segment_direction(source_x, source_y, target_x, target_y)
    if direction_x == 0 and direction_y == 0:
        return None

    horizontal = direction_y == 0
    axis_sign = direction_x if horizontal else direction_y
    source_axis = float(source_x if horizontal else source_y)
    target_axis = float(target_x if horizontal else target_y)
    settings = motion_settings or _get_runtime_motion_settings()
    follow_distance = float(settings.get("follow_distance", TOPOLOGY_FOLLOW_MIN_GAP_CELLS))
    follow_lookahead = float(settings.get("follow_lookahead_cells", TOPOLOGY_FOLLOW_LOOKAHEAD_CELLS))
    candidate_front_axis = target_axis + follow_distance * axis_sign

    for other in list_agvs():
        if int(other.id) == int(agv_id) or getattr(other, "status", None) == "maintenance":
            continue

        other_source_x = int(getattr(other, "motion_source_x", getattr(other, "x", 0)) or getattr(other, "x", 0))
        other_source_y = int(getattr(other, "motion_source_y", getattr(other, "y", 0)) or getattr(other, "y", 0))
        other_target_x = int(getattr(other, "motion_target_x", getattr(other, "x", 0)) or getattr(other, "x", 0))
        other_target_y = int(getattr(other, "motion_target_y", getattr(other, "y", 0)) or getattr(other, "y", 0))
        other_direction_x, other_direction_y = _segment_direction(other_source_x, other_source_y, other_target_x, other_target_y)
        if (other_direction_x, other_direction_y) != (direction_x, direction_y):
            continue

        if horizontal:
            if not (other_source_y == source_y and other_target_y == target_y):
                continue
        else:
            if not (other_source_x == source_x and other_target_x == target_x):
                continue

        other_axis = _estimate_runtime_axis_position(other, horizontal=horizontal)
        relative_axis = (other_axis - source_axis) * axis_sign
        if relative_axis < 0:
            continue
        if relative_axis > follow_lookahead:
            continue

        blocker_front_relative = (candidate_front_axis - source_axis) * axis_sign
        if relative_axis <= blocker_front_relative:
            blocker_task = get_task_by_id(other.task_id) if getattr(other, "task_id", None) is not None else None
            return {
                "edge_key": edge_key,
                "lane_type": str(segment.get("lane_type") or "main"),
                "speed_multiplier": float(segment.get("speed_multiplier") or 1.0),
                "target_node": str(segment.get("target_node") or _build_grid_node_key(target_x, target_y)),
                "blocker_node": str(getattr(other, "current_node", "") or _build_grid_node_key(int(other.x), int(other.y))),
                "blocker_agv_id": int(other.id),
                "blocker_task_id": int(other.task_id) if getattr(other, "task_id", None) is not None else None,
                "blocker_priority": int(getattr(blocker_task, "priority", 0) or 0) if blocker_task else 0,
                "blocker_motion_state": str(getattr(other, "motion_state", "") or getattr(other, "status", "") or "idle"),
            }
    return None


def _can_directly_enter_special_target(
    agv_id: int,
    next_x: int,
    next_y: int,
    *,
    final_target_x: int,
    final_target_y: int,
    target_type: str,
) -> bool:
    if str(target_type or "") not in {"charge", "parking"}:
        return False
    if int(next_x) != int(final_target_x) or int(next_y) != int(final_target_y):
        return False
    return _special_topology_node_has_spare_capacity(next_x, next_y, exclude_agv_id=agv_id) is not None


def _build_topology_wait_reason(conflict: dict) -> str:
    edge_key = str(conflict.get("edge_key") or "topology")
    target_node = str(conflict.get("target_node") or "")
    blocker_node = str(conflict.get("blocker_node") or "")
    blocker_agv_id = conflict.get("blocker_agv_id")
    parts = [f"edge={edge_key}"]
    if target_node:
        parts.append(f"node={target_node}")
    if blocker_node and blocker_node != target_node:
        parts.append(f"node={blocker_node}")
    if blocker_agv_id is not None:
        parts.append(f"agv={int(blocker_agv_id)}")
    return f"topology_edge_waiting:{';'.join(parts)}"


def _build_topology_retry_reason(conflict: dict) -> str:
    edge_key = str(conflict.get("edge_key") or "topology")
    target_node = str(conflict.get("target_node") or "")
    blocker_node = str(conflict.get("blocker_node") or "")
    blocker_agv_id = conflict.get("blocker_agv_id")
    parts = [f"edge={edge_key}"]
    if target_node:
        parts.append(f"node={target_node}")
    if blocker_node and blocker_node != target_node:
        parts.append(f"node={blocker_node}")
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
    special_target = _special_topology_node_has_spare_capacity(target_x, target_y, exclude_agv_id=agv_id)

    for other in list_agvs():
        if int(other.id) == int(agv_id) or other.status == "maintenance":
            continue
        other_edge = str(getattr(other, "current_edge", "") or "").strip()
        if other_edge != edge_key:
            continue
        if special_target is not None:
            blocker_target_key = str(
                getattr(other, "auto_target_node", "") or getattr(other, "current_node", "") or ""
            ).strip()
            if blocker_target_key == str(special_target["key"]):
                continue
        blocker_task = get_task_by_id(other.task_id) if getattr(other, "task_id", None) is not None else None
        return {
            "edge_key": edge_key,
            "lane_type": str(segment.get("lane_type") or "main"),
            "speed_multiplier": float(segment.get("speed_multiplier") or 1.0),
            "target_node": str(segment.get("target_node") or _build_grid_node_key(target_x, target_y)),
            "blocker_node": str(getattr(other, "current_node", "") or _build_grid_node_key(int(other.x), int(other.y))),
            "blocker_agv_id": int(other.id),
            "blocker_task_id": int(other.task_id) if getattr(other, "task_id", None) is not None else None,
            "blocker_priority": int(getattr(blocker_task, "priority", 0) or 0) if blocker_task else 0,
            "blocker_motion_state": str(getattr(other, "motion_state", "") or getattr(other, "status", "") or "idle"),
        }
    return None


def _find_blocking_agv_at_position(agv_id: int, x: int, y: int):
    matching_agvs = []
    for other in list_agvs():
        if int(other.id) == int(agv_id) or other.status == "maintenance":
            continue
        if int(other.x) == int(x) and int(other.y) == int(y):
            matching_agvs.append(other)
    if not matching_agvs:
        return None

    special_node = _get_special_topology_node_at_position(x, y)
    if special_node is not None:
        if len(matching_agvs) < int(special_node["capacity"]):
            return None
    return matching_agvs[0]


def _get_task_priority(task) -> int:
    try:
        return max(int(getattr(task, "priority", 0) or 0), 0)
    except Exception:
        return 0


def _task_order_timestamp(task) -> float:
    for field_name in ("started_at", "assigned_at", "created_at"):
        raw_value = str(getattr(task, field_name, "") or "").strip()
        if not raw_value:
            continue
        try:
            return datetime.fromisoformat(raw_value).timestamp()
        except Exception:
            continue
    return float("inf")


def _path_cost(path) -> int:
    if not path:
        return 0
    return max(len(path) - 1, 0)


def _estimate_remaining_task_path_cost(agv, task, avoid_edge_keys: set[str] | None = None, avoid_node_keys: set[str] | None = None) -> float:
    if agv is None or task is None:
        return float("inf")

    state = get_map_layout_state()
    grid_cols = int(state.get("grid_cols") or 0)
    grid_rows = int(state.get("grid_rows") or 0)
    if grid_cols <= 0 or grid_rows <= 0:
        return float("inf")

    blocked = get_navigation_blocked_cells(grid_cols, grid_rows)
    topology = state.get("topology")
    priority = _get_task_priority(task)
    stage = sync_task_stage_fields(task)
    running_from_current = getattr(task, "status", None) == "running" or getattr(agv, "status", None) == "running"

    if running_from_current:
        path_to_end = plan_path(
            "astar",
            int(agv.x),
            int(agv.y),
            int(stage.end_x),
            int(stage.end_y),
            grid_cols,
            grid_rows,
            blocked,
            topology=topology,
            request_priority=priority,
            agv_id=int(agv.id),
            avoid_edge_keys=avoid_edge_keys,
            avoid_node_keys=avoid_node_keys,
        )
        return float("inf") if not path_to_end else float(_path_cost(path_to_end))

    path_to_start = plan_path(
        "astar",
        int(agv.x),
        int(agv.y),
        int(stage.start_x),
        int(stage.start_y),
        grid_cols,
        grid_rows,
        blocked,
        topology=topology,
        request_priority=priority,
        agv_id=int(agv.id),
        avoid_edge_keys=avoid_edge_keys,
        avoid_node_keys=avoid_node_keys,
    )
    path_to_end = plan_path(
        "astar",
        int(stage.start_x),
        int(stage.start_y),
        int(stage.end_x),
        int(stage.end_y),
        grid_cols,
        grid_rows,
        blocked,
        topology=topology,
        request_priority=priority,
        agv_id=int(agv.id),
        avoid_edge_keys=avoid_edge_keys,
        avoid_node_keys=avoid_node_keys,
    )
    if not path_to_start or not path_to_end:
        return float("inf")
    return float(_path_cost(path_to_start) + _path_cost(path_to_end))


def _should_current_agv_reroute(agv, task, conflict: dict | None) -> bool:
    if conflict is None:
        return True

    blocker_agv_id = conflict.get("blocker_agv_id")
    blocker_task_id = conflict.get("blocker_task_id")
    if blocker_agv_id is None:
        return True

    current_priority = _get_task_priority(task)
    blocker_task = get_task_by_id(blocker_task_id) if blocker_task_id is not None else None
    blocker_priority = _get_task_priority(blocker_task)

    if blocker_priority != current_priority:
        return blocker_priority > current_priority

    avoid_edge_keys = {str(conflict.get("edge_key") or "").strip()} if str(conflict.get("edge_key") or "").strip() else set()
    avoid_node_keys = {
        str(item).strip()
        for item in {conflict.get("target_node"), conflict.get("blocker_node")}
        if str(item or "").strip()
    }

    current_detour_cost = _estimate_remaining_task_path_cost(
        agv,
        task,
        avoid_edge_keys=avoid_edge_keys,
        avoid_node_keys=avoid_node_keys,
    )
    blocker_agv = get_agv_by_id(int(blocker_agv_id))
    blocker_detour_cost = _estimate_remaining_task_path_cost(
        blocker_agv,
        blocker_task,
        avoid_edge_keys=avoid_edge_keys,
        avoid_node_keys=avoid_node_keys,
    )

    current_has_detour = current_detour_cost != float("inf")
    blocker_has_detour = blocker_detour_cost != float("inf")
    if current_has_detour != blocker_has_detour:
        return current_has_detour
    if current_has_detour and blocker_has_detour:
        if abs(current_detour_cost - blocker_detour_cost) >= 1:
            return current_detour_cost < blocker_detour_cost

    current_order = _task_order_timestamp(task)
    blocker_order = _task_order_timestamp(blocker_task)
    if current_order != blocker_order:
        return current_order > blocker_order
    return int(getattr(agv, "id", 0) or 0) > int(blocker_agv_id)


def _should_reroute_for_blocker(agv, task, blocker_agv_id: int | None, blocker_task_id: int | None = None) -> bool:
    if blocker_agv_id is None:
        return True
    if task is not None:
        return _should_current_agv_reroute(
            agv,
            task,
            {
                "edge_key": "",
                "target_node": "",
                "blocker_agv_id": blocker_agv_id,
                "blocker_task_id": blocker_task_id,
            },
        )

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
        "blocker_node": str(getattr(blocker_agv, "current_node", "") or _build_grid_node_key(int(blocker_agv.x), int(blocker_agv.y))),
        "blocker_agv_id": int(blocker_agv.id),
        "blocker_task_id": blocker_task_id,
        "blocker_priority": _get_task_priority(blocker_task),
        "blocker_motion_state": str(getattr(blocker_agv, "motion_state", "") or getattr(blocker_agv, "status", "") or "idle"),
    }


def _begin_motion_segment(agv, point: dict, active_status: str, *, motion_settings: dict | None = None):
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
    segment_mode = "topology" if not edge_key.startswith("grid:") and str(segment.get("lane_type") or "grid") != "grid" else "grid"
    lane_type = str(segment.get("lane_type") or "grid")
    topology_speed_multiplier = max(float(point.get("topology_speed_multiplier") or segment.get("speed_multiplier") or 1.0), 0.1)
    speed_multiplier = topology_speed_multiplier if segment_mode == "topology" else 1.0
    settings = motion_settings or _get_runtime_motion_settings()
    base_speed = float(settings.get("base_speed", DEFAULT_BASE_SPEED))
    segment_distance = max(abs(target_x - source_x), abs(target_y - source_y), 1)
    target_speed = max(base_speed * speed_multiplier, 0.05)
    travel_duration_sec = segment_distance / target_speed
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
        segment_mode=segment_mode,
        current_lane_type=lane_type if segment_mode == "topology" else None,
        current_speed_multiplier=speed_multiplier,
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
    current_node_key = _get_runtime_topology_node_key_at_position(int(agv.x), int(agv.y)) or _build_grid_node_key(int(agv.x), int(agv.y))
    agv.apply_motion_fields(
        status=active_status,
        render_x=float(agv.x),
        render_y=float(agv.y),
        current_node=current_node_key,
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
            runtime_motion_settings = _get_runtime_motion_settings()
            topology_conflict = _detect_topology_edge_conflict(agv.id, source_x, source_y, point)
            if topology_conflict is None:
                topology_conflict = _detect_same_corridor_follow_conflict(
                    agv.id,
                    source_x,
                    source_y,
                    point,
                    motion_settings=runtime_motion_settings,
                )
            if topology_conflict is None:
                blocking_agv = _find_blocking_agv_at_position(agv.id, target_x, target_y)
            if topology_conflict is None and blocking_agv is None:
                target_node, target_speed, travel_duration_sec = _begin_motion_segment(
                    agv,
                    point,
                    active_status,
                    motion_settings=runtime_motion_settings,
                )
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
            if waited_sec >= TOPOLOGY_EDGE_REPLAN_INTERVAL_SEC and _should_current_agv_reroute(
                agv,
                task,
                topology_conflict,
            ):
                time.sleep(_topology_retry_backoff(agv, task, topology_conflict.get("blocker_agv_id"), topology_conflict.get("blocker_task_id")))
                task.dispatch_reason = _build_topology_retry_reason(topology_conflict)
                agv.clear_motion(motion_state=active_status)
                return "retry"
            if waited_sec >= float(runtime_motion_settings.get("deadlock_timeout_sec", TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC)):
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

                reroute_preferred = _should_current_agv_reroute(
                    agv,
                    task,
                    topology_cell_conflict,
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
                if waited_sec >= float(runtime_motion_settings.get("deadlock_timeout_sec", TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC)):
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
    scope_key = get_current_scope_key()

    def run():
        with use_scope(scope_key):
            run_in_scope()

    def run_in_scope():
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

    scope_key = get_current_scope_key()

    def run():
        with use_scope(scope_key):
            run_in_scope()

    def run_in_scope():
        while True:
            agv = get_agv_by_id(agv_id)
            if should_cancel_autonomy(agv):
                if agv is not None:
                    agv.clear_motion(motion_state=agv.status)
                return

            runtime_blocked_cells, runtime_avoid_node_keys = _build_autonomy_runtime_path_constraints(
                agv,
                target_key=target_key,
                target_x=target_x,
                target_y=target_y,
            )

            path = plan_path(
                algorithm,
                agv.x,
                agv.y,
                target_x,
                target_y,
                grid_cols,
                grid_rows,
                blocked=runtime_blocked_cells,
                request_priority=0,
                agv_id=agv.id,
                avoid_node_keys=runtime_avoid_node_keys,
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
                    next_x, next_y = _point_coordinates(point)
                    topology_conflict = None
                    blocking_agv = None
                    moved = False
                    target_node = _build_grid_node_key(next_x, next_y)
                    target_speed = 0.0
                    travel_duration_sec = CELL_TRAVEL_DURATION_SEC

                    with movement_lock:
                        runtime_motion_settings = _get_runtime_motion_settings()
                        allow_direct_special_entry = _can_directly_enter_special_target(
                            agv.id,
                            next_x,
                            next_y,
                            final_target_x=target_x,
                            final_target_y=target_y,
                            target_type=target_type,
                        )
                        if not allow_direct_special_entry:
                            topology_conflict = _detect_topology_edge_conflict(agv.id, source_x, source_y, point)
                            if topology_conflict is None:
                                topology_conflict = _detect_same_corridor_follow_conflict(
                                    agv.id,
                                    source_x,
                                    source_y,
                                    point,
                                    motion_settings=runtime_motion_settings,
                                )
                            if topology_conflict is None:
                                blocking_agv = _find_blocking_agv_at_position(agv.id, next_x, next_y)
                        if topology_conflict is None and blocking_agv is None:
                            target_node, target_speed, travel_duration_sec = _begin_motion_segment(
                                agv,
                                point,
                                active_status,
                                motion_settings=runtime_motion_settings,
                            )
                            moved = True

                    waited_sec = max(time.monotonic() - wait_started_at, 0.0)
                    if moved:
                        time.sleep(travel_duration_sec)
                        _finish_motion_segment(agv, next_x, next_y, target_node, active_status, target_speed)
                        break

                    if topology_conflict is not None:
                        reroute_preferred = _should_reroute_for_blocker(
                            agv,
                            None,
                            topology_conflict.get("blocker_agv_id"),
                            topology_conflict.get("blocker_task_id"),
                        )
                        _set_waiting_motion_state(agv, active_status, motion_state="yielding" if reroute_preferred else "waiting")
                        if waited_sec >= TOPOLOGY_EDGE_REPLAN_INTERVAL_SEC and reroute_preferred:
                            time.sleep(
                                _topology_retry_backoff(
                                    agv,
                                    None,
                                    topology_conflict.get("blocker_agv_id"),
                                    topology_conflict.get("blocker_task_id"),
                                )
                            )
                            should_replan = True
                            break
                        if waited_sec >= float(runtime_motion_settings.get("deadlock_timeout_sec", TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC)):
                            should_replan = True
                            break
                        if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
                            should_replan = True
                            break
                        time.sleep(MOVE_WAIT_INTERVAL_SEC)
                        continue

                    if blocking_agv is not None:
                        topology_cell_conflict = _build_topology_segment_conflict(source_x, source_y, point, blocking_agv)
                        if topology_cell_conflict is not None:
                            reroute_preferred = _should_reroute_for_blocker(
                                agv,
                                None,
                                topology_cell_conflict.get("blocker_agv_id"),
                                topology_cell_conflict.get("blocker_task_id"),
                            )
                            _set_waiting_motion_state(agv, active_status, motion_state="yielding" if reroute_preferred else "waiting")
                            if waited_sec >= TOPOLOGY_OCCUPIED_NODE_REPLAN_INTERVAL_SEC and reroute_preferred:
                                time.sleep(
                                    _topology_retry_backoff(
                                        agv,
                                        None,
                                        topology_cell_conflict.get("blocker_agv_id"),
                                        topology_cell_conflict.get("blocker_task_id"),
                                    )
                                )
                                should_replan = True
                                break
                            if waited_sec >= float(runtime_motion_settings.get("deadlock_timeout_sec", TOPOLOGY_DEADLOCK_BREAK_TIMEOUT_SEC)):
                                should_replan = True
                                break
                            if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
                                should_replan = True
                                break
                            time.sleep(MOVE_WAIT_INTERVAL_SEC)
                            continue

                        _set_waiting_motion_state(agv, active_status, motion_state="waiting")
                        if waited_sec >= MOVE_WAIT_TIMEOUT_SEC:
                            should_replan = True
                            break
                        time.sleep(MOVE_WAIT_INTERVAL_SEC)
                        continue

                if should_replan:
                    break

            if should_replan:
                continue

            finalize_target(agv)
            return

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return True
