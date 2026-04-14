from __future__ import annotations

from datetime import datetime

from app.repositories.agv_repository import list_agvs
from app.repositories.ui_settings_repository import get_ui_settings as get_ui_settings_store
from app.utils.agv_movement import move_agv_to_autonomy_target, now_iso
from app.utils.path_planner import build_runtime_special_node_constraints, plan_path
from app.utils.warehouse_map import (
    get_current_grid_size,
    get_map_layout_state,
    get_navigation_blocked_cells,
    get_topology_node_default_capacity,
    normalize_topology_node_capacity,
)


DEFAULT_IDLE_RETURN_TIMEOUT_SEC = 12.0
DEFAULT_IDLE_CHARGE_TIMEOUT_SEC = 45.0
DEFAULT_IDLE_CHARGE_BATTERY_THRESHOLD = 60.0
LOW_BATTERY_THRESHOLD = 24.0
CHARGE_RELEASE_THRESHOLD = 88.0
BATTERY_IDLE_DRAIN_PER_SEC = 0.01
BATTERY_ACTIVE_DRAIN_PER_SEC = 0.16
BATTERY_WAITING_DRAIN_PER_SEC = 0.05
BATTERY_PARKING_IDLE_DRAIN_PER_SEC = 0.003
BATTERY_CHARGE_PER_SEC = 6.0
AUTONOMY_ALGORITHM = "astar"
AUTONOMY_BLOCKING_STATUSES = {"fault", "emergency_stop", "maintenance"}
AUTONOMY_MOVING_STATUSES = {"running", "relocating", "idle_returning", "waiting_for_charge"}
AUTONOMY_STALLED_RECOVERY_SEC = 2.0


AUTONOMY_UI_SETTINGS_DEFAULTS = {
    "idle_return_timeout_sec": DEFAULT_IDLE_RETURN_TIMEOUT_SEC,
    "idle_charge_timeout_sec": DEFAULT_IDLE_CHARGE_TIMEOUT_SEC,
    "idle_charge_battery_threshold": DEFAULT_IDLE_CHARGE_BATTERY_THRESHOLD,
    "low_battery_threshold": LOW_BATTERY_THRESHOLD,
    "battery_active_drain_per_sec": BATTERY_ACTIVE_DRAIN_PER_SEC,
    "battery_waiting_drain_per_sec": BATTERY_WAITING_DRAIN_PER_SEC,
    "battery_idle_drain_per_sec": BATTERY_IDLE_DRAIN_PER_SEC,
    "battery_parking_idle_drain_per_sec": BATTERY_PARKING_IDLE_DRAIN_PER_SEC,
    "battery_charge_per_sec": BATTERY_CHARGE_PER_SEC,
}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _seconds_since(value: str | None, now: datetime) -> float:
    parsed = _parse_iso(value)
    if parsed is None:
        return 0.0
    return max((now - parsed).total_seconds(), 0.0)


def _clamp_battery(value: float) -> float:
    return round(min(max(float(value), 0.0), 100.0), 2)


def _get_autonomy_policy_settings() -> dict:
    payload = get_ui_settings_store(AUTONOMY_UI_SETTINGS_DEFAULTS)
    try:
        idle_return_timeout_sec = max(5.0, min(600.0, float(payload.get("idle_return_timeout_sec", DEFAULT_IDLE_RETURN_TIMEOUT_SEC))))
    except Exception:
        idle_return_timeout_sec = DEFAULT_IDLE_RETURN_TIMEOUT_SEC
    try:
        idle_charge_timeout_sec = max(5.0, min(600.0, float(payload.get("idle_charge_timeout_sec", DEFAULT_IDLE_CHARGE_TIMEOUT_SEC))))
    except Exception:
        idle_charge_timeout_sec = DEFAULT_IDLE_CHARGE_TIMEOUT_SEC
    try:
        low_battery_threshold = max(5.0, min(80.0, float(payload.get("low_battery_threshold", LOW_BATTERY_THRESHOLD))))
    except Exception:
        low_battery_threshold = LOW_BATTERY_THRESHOLD
    try:
        idle_charge_battery_threshold = max(
            low_battery_threshold,
            min(95.0, float(payload.get("idle_charge_battery_threshold", DEFAULT_IDLE_CHARGE_BATTERY_THRESHOLD))),
        )
    except Exception:
        idle_charge_battery_threshold = DEFAULT_IDLE_CHARGE_BATTERY_THRESHOLD
    try:
        battery_active_drain_per_sec = max(0.01, min(10.0, float(payload.get("battery_active_drain_per_sec", BATTERY_ACTIVE_DRAIN_PER_SEC))))
    except Exception:
        battery_active_drain_per_sec = BATTERY_ACTIVE_DRAIN_PER_SEC
    try:
        battery_waiting_drain_per_sec = max(0.0, min(5.0, float(payload.get("battery_waiting_drain_per_sec", BATTERY_WAITING_DRAIN_PER_SEC))))
    except Exception:
        battery_waiting_drain_per_sec = BATTERY_WAITING_DRAIN_PER_SEC
    try:
        battery_idle_drain_per_sec = max(0.0, min(2.0, float(payload.get("battery_idle_drain_per_sec", BATTERY_IDLE_DRAIN_PER_SEC))))
    except Exception:
        battery_idle_drain_per_sec = BATTERY_IDLE_DRAIN_PER_SEC
    try:
        battery_parking_idle_drain_per_sec = max(0.0, min(2.0, float(payload.get("battery_parking_idle_drain_per_sec", BATTERY_PARKING_IDLE_DRAIN_PER_SEC))))
    except Exception:
        battery_parking_idle_drain_per_sec = BATTERY_PARKING_IDLE_DRAIN_PER_SEC
    try:
        battery_charge_per_sec = max(0.1, min(20.0, float(payload.get("battery_charge_per_sec", BATTERY_CHARGE_PER_SEC))))
    except Exception:
        battery_charge_per_sec = BATTERY_CHARGE_PER_SEC
    return {
        "idle_return_timeout_sec": idle_return_timeout_sec,
        "idle_charge_timeout_sec": idle_charge_timeout_sec,
        "idle_charge_battery_threshold": idle_charge_battery_threshold,
        "low_battery_threshold": low_battery_threshold,
        "battery_active_drain_per_sec": battery_active_drain_per_sec,
        "battery_waiting_drain_per_sec": battery_waiting_drain_per_sec,
        "battery_idle_drain_per_sec": battery_idle_drain_per_sec,
        "battery_parking_idle_drain_per_sec": battery_parking_idle_drain_per_sec,
        "battery_charge_per_sec": battery_charge_per_sec,
    }


def _resolve_runtime_topology_nodes(*node_types: str) -> list[dict]:
    state = get_map_layout_state()
    topology = state.get("topology") or {}
    requested = {str(item).strip().lower() for item in node_types if str(item).strip()}
    nodes = []
    for node in topology.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("node_type") or "waypoint").strip().lower()
        if node_type in requested:
            nodes.append(
                {
                    **node,
                    "capacity": normalize_topology_node_capacity(node_type, node.get("capacity")),
                }
            )
    return nodes


def _build_runtime_topology_special_groups(*node_types: str) -> tuple[list[dict], dict[str, dict]]:
    nodes = _resolve_runtime_topology_nodes(*node_types)
    node_by_position = {
        (int(node.get("x") or 0), int(node.get("y") or 0)): node
        for node in nodes
    }
    visited: set[tuple[str, int, int]] = set()
    groups: list[dict] = []
    group_lookup: dict[str, dict] = {}
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    for node in nodes:
        node_key = str(node.get("key") or "").strip()
        node_type = str(node.get("node_type") or "").strip().lower()
        origin = (node_type, int(node.get("x") or 0), int(node.get("y") or 0))
        if not node_key or not node_type or origin in visited:
            continue

        queue = [node]
        group_nodes: list[dict] = []
        visited.add(origin)

        while queue:
            current = queue.pop(0)
            group_nodes.append(current)
            current_type = str(current.get("node_type") or "").strip().lower()
            current_x = int(current.get("x") or 0)
            current_y = int(current.get("y") or 0)
            for dx, dy in neighbors:
                next_node = node_by_position.get((current_x + dx, current_y + dy))
                if next_node is None:
                    continue
                next_type = str(next_node.get("node_type") or "").strip().lower()
                next_marker = (next_type, int(next_node.get("x") or 0), int(next_node.get("y") or 0))
                if next_type != current_type or next_marker in visited:
                    continue
                visited.add(next_marker)
                queue.append(next_node)

        group_nodes.sort(
            key=lambda item: (
                int(item.get("y") or 0),
                int(item.get("x") or 0),
                str(item.get("key") or ""),
            )
        )
        group = {
            "key": f"{node_type}:{'|'.join(str(item.get('key') or '') for item in group_nodes)}",
            "node_type": node_type,
            "nodes": group_nodes,
            "node_keys": [str(item.get("key") or "") for item in group_nodes],
        }
        groups.append(group)
        for group_node in group_nodes:
            group_lookup[str(group_node.get("key") or "")] = group

    return groups, group_lookup


def _resolve_runtime_topology_node_key_for_agv(
    agv,
    node_by_key: dict[str, dict],
    node_by_position: dict[tuple[int, int], dict],
) -> str:
    current_node = str(getattr(agv, "current_node", "") or "").strip()
    if current_node and current_node in node_by_key:
        return current_node
    try:
        matched_node = node_by_position.get((int(agv.x), int(agv.y)))
    except Exception:
        matched_node = None
    if matched_node is not None:
        return str(matched_node.get("key") or current_node or "").strip()
    return current_node


def _build_runtime_topology_occupancy_counts(
    *,
    exclude_agv_id: int | None = None,
    node_by_key: dict[str, dict] | None = None,
    node_by_position: dict[tuple[int, int], dict] | None = None,
) -> dict[str, int]:
    if node_by_key is None or node_by_position is None:
        node_by_key, node_by_position = _build_runtime_topology_node_indexes()
    counts: dict[str, int] = {}
    for agv in list_agvs():
        try:
            current_agv_id = int(agv.id)
        except Exception:
            current_agv_id = None
        if exclude_agv_id is not None and current_agv_id == int(exclude_agv_id):
            continue
        if getattr(agv, "status", None) == "maintenance":
            continue
        node_key = _resolve_runtime_topology_node_key_for_agv(agv, node_by_key, node_by_position)
        if not node_key:
            node_key = ""
        if node_key:
            counts[node_key] = counts.get(node_key, 0) + 1

        reserved_node_key = str(getattr(agv, "auto_target_node", "") or "").strip()
        reserved_target_type = str(getattr(agv, "auto_target_type", "") or "").strip().lower()
        motion_state = str(getattr(agv, "status", "") or "").strip().lower()
        if (
            reserved_node_key
            and reserved_node_key != node_key
            and reserved_target_type in {"parking", "charge"}
            and motion_state in {"idle_returning", "waiting_for_charge", "charging"}
        ):
            counts[reserved_node_key] = counts.get(reserved_node_key, 0) + 1
    return counts


def _build_autonomy_runtime_blocked_cells(
    agv,
    target_key: str,
    grid_cols: int,
    grid_rows: int,
    *,
    allowed_node_keys: set[str] | None = None,
) -> tuple[set[tuple[int, int]], set[str]]:
    base_blocked = set(get_navigation_blocked_cells(grid_cols, grid_rows))
    constraints = build_runtime_special_node_constraints(
        exclude_agv_id=getattr(agv, "id", None),
        goal_node_key=target_key,
        allowed_node_keys=allowed_node_keys,
    )
    blocked_cells = base_blocked | set(constraints["blocked_positions"])
    blocked_cells.discard((int(agv.x), int(agv.y)))
    blocked_cells.discard((int(getattr(agv, "motion_target_x", agv.x) or agv.x), int(getattr(agv, "motion_target_y", agv.y) or agv.y)))
    return blocked_cells, set(constraints["avoid_node_keys"])


def _resolve_nearest_autonomy_target(
    agv,
    target_type: str,
    grid_cols: int,
    grid_rows: int,
    *,
    node_candidates: list[dict] | None = None,
    exclude_agv_id: int | None = None,
) -> dict | None:
    candidate_types = ("charge",) if target_type == "charge" else ("parking",)
    node_by_key, node_by_position = _build_runtime_topology_node_indexes()
    occupancy_counts = _build_runtime_topology_occupancy_counts(
        exclude_agv_id=exclude_agv_id,
        node_by_key=node_by_key,
        node_by_position=node_by_position,
    )
    current_node_key = _resolve_runtime_topology_node_key_for_agv(agv, node_by_key, node_by_position)
    if node_candidates is None:
        groups, _ = _build_runtime_topology_special_groups(*candidate_types)
        if groups:
            best_group_target: dict | None = None
            for group in groups:
                group_target = _resolve_nearest_autonomy_target(
                    agv,
                    target_type,
                    grid_cols,
                    grid_rows,
                    node_candidates=group.get("nodes") or [],
                    exclude_agv_id=exclude_agv_id,
                )
                if not group_target:
                    continue
                group_occupancy = sum(max(int(occupancy_counts.get(node_key, 0) or 0), 0) for node_key in group.get("node_keys") or [])
                group_capacity = sum(
                    normalize_topology_node_capacity(node.get("node_type") or target_type, node.get("capacity"))
                    for node in group.get("nodes") or []
                )
                candidate = {
                    **group_target,
                    "group_key": str(group.get("key") or ""),
                    "group_count": len(group.get("nodes") or []),
                    "group_occupancy": group_occupancy,
                    "group_capacity": group_capacity,
                    "group_remaining_capacity": max(group_capacity - group_occupancy, 0),
                }
                if (
                    best_group_target is None
                    or (
                        float(candidate.get("distance", float("inf"))),
                        -int(candidate.get("group_remaining_capacity", 0) or 0),
                        int(candidate.get("occupancy", 0) or 0),
                        int(candidate.get("y", 0) or 0),
                        int(candidate.get("x", 0) or 0),
                        str(candidate.get("key") or ""),
                    )
                    < (
                        float(best_group_target.get("distance", float("inf"))),
                        -int(best_group_target.get("group_remaining_capacity", 0) or 0),
                        int(best_group_target.get("occupancy", 0) or 0),
                        int(best_group_target.get("y", 0) or 0),
                        int(best_group_target.get("x", 0) or 0),
                        str(best_group_target.get("key") or ""),
                    )
                ):
                    best_group_target = candidate
            if best_group_target is not None:
                return best_group_target
    best: tuple[int, dict] | None = None
    fallback: tuple[int, dict] | None = None
    for node in (node_candidates if node_candidates is not None else _resolve_runtime_topology_nodes(*candidate_types)):
        node_x = int(node.get("x") or 0)
        node_y = int(node.get("y") or 0)
        payload = {
            "key": str(node.get("key") or f"{target_type}:{node_x}:{node_y}"),
            "x": node_x,
            "y": node_y,
            "node_type": str(node.get("node_type") or target_type),
            "label": str(node.get("label") or ""),
            "capacity": normalize_topology_node_capacity(node.get("node_type") or target_type, node.get("capacity")),
        }
        manhattan = abs(node_x - int(agv.x)) + abs(node_y - int(agv.y))
        if fallback is None or manhattan < fallback[0]:
            fallback = (manhattan, payload)
        current_occupancy = max(int(occupancy_counts.get(payload["key"], 0) or 0), 0)
        remaining_capacity = max(int(payload["capacity"]) - current_occupancy, 0)
        payload["occupancy"] = current_occupancy
        payload["remaining_capacity"] = remaining_capacity
        if payload["key"] != current_node_key and current_occupancy >= payload["capacity"]:
            continue
        blocked_cells, avoid_node_keys = _build_autonomy_runtime_blocked_cells(
            agv,
            payload["key"],
            grid_cols,
            grid_rows,
            allowed_node_keys={payload["key"]},
        )
        path = plan_path(
            AUTONOMY_ALGORITHM,
            int(agv.x),
            int(agv.y),
            node_x,
            node_y,
            grid_cols,
            grid_rows,
            blocked=blocked_cells,
            request_priority=0,
            agv_id=agv.id,
            avoid_node_keys=avoid_node_keys,
        )
        if not path:
            continue
        distance = max(len(path) - 1, 0)
        payload["distance"] = distance
        if best is None or distance < best[0]:
            best = (distance, payload)
    return best[1] if best else (fallback[1] if fallback else None)


def _build_runtime_topology_node_indexes() -> tuple[dict[str, dict], dict[tuple[int, int], dict]]:
    state = get_map_layout_state()
    topology = state.get("topology") or {}
    node_by_key: dict[str, dict] = {}
    node_by_position: dict[tuple[int, int], dict] = {}
    for node in topology.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        key = str(node.get("key") or "").strip()
        if not key:
            continue
        payload = {
            **node,
            "node_type": str(node.get("node_type") or "waypoint").strip().lower(),
            "capacity": normalize_topology_node_capacity(node.get("node_type") or "waypoint", node.get("capacity")),
        }
        node_by_key[key] = payload
        node_by_position[(int(node.get("x") or 0), int(node.get("y") or 0))] = payload
    return node_by_key, node_by_position


def _resolve_runtime_topology_node_for_agv(agv, node_by_key: dict[str, dict], node_by_position: dict[tuple[int, int], dict]) -> dict | None:
    current_node = str(getattr(agv, "current_node", "") or "").strip()
    if current_node:
        by_key = node_by_key.get(current_node)
        if by_key is not None:
            return by_key
    try:
        return node_by_position.get((int(agv.x), int(agv.y)))
    except Exception:
        return None


def _resolve_active_autonomy_retarget(agv, target_type: str, grid_cols: int, grid_rows: int) -> dict | None:
    target_key = str(getattr(agv, "auto_target_node", "") or "").strip()
    if not target_key:
        return None

    node_by_key, node_by_position = _build_runtime_topology_node_indexes()
    active_target_nodes = _resolve_runtime_topology_nodes("charge" if target_type == "charge" else "parking")
    current_target = next(
        (node for node in active_target_nodes if str(node.get("key") or "").strip() == target_key),
        None,
    )
    if current_target is None:
        return _resolve_nearest_autonomy_target(
            agv,
            target_type,
            grid_cols,
            grid_rows,
            exclude_agv_id=agv.id,
        )

    runtime_node = _resolve_runtime_topology_node_for_agv(agv, node_by_key, node_by_position)
    if runtime_node is not None and str(runtime_node.get("key") or "").strip() == target_key:
        return None

    occupancy_counts = _build_runtime_topology_occupancy_counts(
        exclude_agv_id=agv.id,
        node_by_key=node_by_key,
        node_by_position=node_by_position,
    )
    if int(occupancy_counts.get(target_key, 0) or 0) < int(current_target.get("capacity") or 1):
        return None

    _, group_lookup = _build_runtime_topology_special_groups(target_type)
    target_group = group_lookup.get(target_key)
    if target_group is not None:
        next_in_group = _resolve_nearest_autonomy_target(
            agv,
            target_type,
            grid_cols,
            grid_rows,
            node_candidates=target_group.get("nodes") or [],
            exclude_agv_id=agv.id,
        )
        if next_in_group and str(next_in_group.get("key") or "").strip() != target_key:
            return next_in_group

    fallback_target = _resolve_nearest_autonomy_target(
        agv,
        target_type,
        grid_cols,
        grid_rows,
        exclude_agv_id=agv.id,
    )
    if fallback_target and str(fallback_target.get("key") or "").strip() != target_key:
        return fallback_target
    return None


def _retarget_active_autonomy_if_needed(agv, grid_cols: int, grid_rows: int) -> bool:
    target_type = str(getattr(agv, "auto_target_type", "") or "").strip().lower()
    if target_type not in {"parking", "charge"}:
        return False
    if target_type == "parking" and agv.status != "idle_returning":
        return False
    if target_type == "charge" and agv.status != "waiting_for_charge":
        return False
    motion_state = str(getattr(agv, "motion_state", "") or getattr(agv, "status", "") or "").strip().lower()
    if motion_state not in {"waiting", "yielding"}:
        return False

    next_target = _resolve_active_autonomy_retarget(agv, target_type, grid_cols, grid_rows)
    if not next_target:
        return False

    if move_agv_to_autonomy_target(
        agv.id,
        next_target["x"],
        next_target["y"],
        target_key=str(next_target["key"]),
        target_type=target_type,
        algorithm=AUTONOMY_ALGORITHM,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
    ):
        agv.idle_since_at = None
        return True
    return False


def _sync_battery_runtime(agv, now: datetime, policy_settings: dict, node_by_key: dict[str, dict], node_by_position: dict[tuple[int, int], dict]) -> None:
    elapsed = _seconds_since(getattr(agv, "energy_updated_at", None), now)
    battery_level = float(getattr(agv, "battery_level", 100.0) or 100.0)
    if elapsed <= 0:
        if not getattr(agv, "energy_updated_at", None):
            agv.energy_updated_at = now.isoformat(timespec="seconds")
        return

    motion_state = str(getattr(agv, "motion_state", "") or getattr(agv, "status", "") or "idle").strip().lower()
    runtime_node = _resolve_runtime_topology_node_for_agv(agv, node_by_key, node_by_position)
    runtime_node_type = str((runtime_node or {}).get("node_type") or "").strip().lower()

    if agv.status == "charging":
        battery_level += float(policy_settings.get("battery_charge_per_sec", BATTERY_CHARGE_PER_SEC)) * elapsed
    elif motion_state in {"waiting", "yielding"}:
        battery_level -= float(policy_settings.get("battery_waiting_drain_per_sec", BATTERY_WAITING_DRAIN_PER_SEC)) * elapsed
    elif agv.status in AUTONOMY_MOVING_STATUSES:
        battery_level -= float(policy_settings.get("battery_active_drain_per_sec", BATTERY_ACTIVE_DRAIN_PER_SEC)) * elapsed
    elif agv.status == "idle":
        if runtime_node_type == "parking":
            battery_level -= float(
                policy_settings.get("battery_parking_idle_drain_per_sec", BATTERY_PARKING_IDLE_DRAIN_PER_SEC)
            ) * elapsed
        else:
            battery_level -= float(policy_settings.get("battery_idle_drain_per_sec", BATTERY_IDLE_DRAIN_PER_SEC)) * elapsed

    agv.battery_level = _clamp_battery(battery_level)
    agv.energy_updated_at = now.isoformat(timespec="seconds")


def _release_from_charging_if_ready(agv, now: datetime) -> bool:
    if agv.status != "charging":
        return False
    if float(getattr(agv, "battery_level", 0.0) or 0.0) < CHARGE_RELEASE_THRESHOLD:
        return False
    agv.status = "idle"
    agv.charge_started_at = None
    agv.auto_target_node = None
    agv.auto_target_type = None
    agv.idle_since_at = now.isoformat(timespec="seconds")
    agv.clear_motion()
    return True


def _finalize_autonomy_target(agv, target_type: str, now: datetime) -> bool:
    if target_type == "charge":
        agv.status = "charging"
        agv.charge_started_at = now.isoformat(timespec="seconds")
        agv.idle_since_at = None
        agv.auto_target_type = "charge"
        agv.clear_motion(motion_state="charging")
        return True
    if target_type == "parking":
        agv.status = "idle"
        agv.charge_started_at = None
        agv.auto_target_node = None
        agv.auto_target_type = None
        agv.idle_since_at = now.isoformat(timespec="seconds")
        agv.clear_motion()
        return True
    return False


def _normalize_stalled_autonomy_motion_if_needed(agv, expected_status: str, now: datetime, node_by_position: dict) -> bool:
    current_edge = str(getattr(agv, "current_edge", "") or "").strip()
    if not current_edge:
        return True

    motion_updated_sec = _seconds_since(getattr(agv, "motion_updated_at", None), now)
    motion_started_at = _parse_iso(getattr(agv, "motion_started_at", None))
    try:
        motion_duration_ms = max(float(getattr(agv, "motion_duration_ms", 0) or 0), 0.0)
    except Exception:
        motion_duration_ms = 0.0
    motion_finished = False
    if motion_started_at is not None and motion_duration_ms > 0:
        motion_finished = (now - motion_started_at).total_seconds() * 1000.0 >= motion_duration_ms

    if motion_updated_sec < AUTONOMY_STALLED_RECOVERY_SEC and not motion_finished:
        return False

    position_key = (int(getattr(agv, "x", 0) or 0), int(getattr(agv, "y", 0) or 0))
    position_node = node_by_position.get(position_key)
    if position_node is not None:
        agv.current_node = str(position_node.get("key") or agv.current_node or "")
    elif not str(getattr(agv, "current_node", "") or "").strip():
        agv.current_node = f"grid:{position_key[0]}:{position_key[1]}"
    agv.clear_motion(motion_state=expected_status)
    return True


def _recover_stalled_autonomy_if_needed(agv, now: datetime, grid_cols: int, grid_rows: int) -> bool:
    if agv.task_id is not None:
        return False

    target_type = str(getattr(agv, "auto_target_type", "") or "").strip().lower()
    target_key = str(getattr(agv, "auto_target_node", "") or "").strip()
    if target_type not in {"parking", "charge"} or not target_key:
        return False

    expected_status = "waiting_for_charge" if target_type == "charge" else "idle_returning"
    if str(getattr(agv, "status", "") or "").strip().lower() != expected_status:
        return False

    motion_state = str(getattr(agv, "motion_state", "") or expected_status).strip().lower()
    if motion_state not in {"waiting", "yielding", expected_status}:
        return False

    had_current_edge = bool(str(getattr(agv, "current_edge", "") or "").strip())
    node_by_key, node_by_position = _build_runtime_topology_node_indexes()
    if not _normalize_stalled_autonomy_motion_if_needed(agv, expected_status, now, node_by_position):
        return False
    if not had_current_edge and _seconds_since(getattr(agv, "motion_updated_at", None), now) < AUTONOMY_STALLED_RECOVERY_SEC:
        return False

    target_node = node_by_key.get(target_key)
    if target_node is not None:
        target_x = int(target_node.get("x") or 0)
        target_y = int(target_node.get("y") or 0)
        if int(getattr(agv, "x", 0) or 0) == target_x and int(getattr(agv, "y", 0) or 0) == target_y:
            return _finalize_autonomy_target(agv, target_type, now)
        next_target = {
            "key": target_key,
            "x": target_x,
            "y": target_y,
        }
    else:
        next_target = _resolve_nearest_autonomy_target(
            agv,
            target_type,
            grid_cols,
            grid_rows,
            exclude_agv_id=agv.id,
        )
        if not next_target:
            return False

    if move_agv_to_autonomy_target(
        agv.id,
        int(next_target["x"]),
        int(next_target["y"]),
        target_key=str(next_target["key"]),
        target_type=target_type,
        algorithm=AUTONOMY_ALGORITHM,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
    ):
        agv.idle_since_at = None
        return True
    return False


def _sync_idle_timer(agv, now: datetime) -> None:
    if agv.task_id is not None:
        agv.idle_since_at = None
        return
    if agv.status == "idle":
        agv.idle_since_at = agv.idle_since_at or now.isoformat(timespec="seconds")
        return
    if agv.status in {"idle_returning", "waiting_for_charge", "charging"}:
        agv.idle_since_at = None


def _start_autonomy_if_needed(agv, now: datetime, grid_cols: int, grid_rows: int, policy_settings: dict) -> None:
    if agv.task_id is not None or agv.status in AUTONOMY_BLOCKING_STATUSES or agv.status == "charging":
        return

    battery_level = float(getattr(agv, "battery_level", 100.0) or 100.0)
    current_node = str(getattr(agv, "current_node", "") or "")
    idle_elapsed = _seconds_since(getattr(agv, "idle_since_at", None), now)
    idle_charge_timeout_sec = float(policy_settings.get("idle_charge_timeout_sec", DEFAULT_IDLE_CHARGE_TIMEOUT_SEC) or DEFAULT_IDLE_CHARGE_TIMEOUT_SEC)
    idle_charge_battery_threshold = float(
        policy_settings.get("idle_charge_battery_threshold", DEFAULT_IDLE_CHARGE_BATTERY_THRESHOLD)
        or DEFAULT_IDLE_CHARGE_BATTERY_THRESHOLD
    )
    low_battery_threshold = float(policy_settings.get("low_battery_threshold", LOW_BATTERY_THRESHOLD) or LOW_BATTERY_THRESHOLD)
    idle_return_timeout_sec = float(policy_settings.get("idle_return_timeout_sec", DEFAULT_IDLE_RETURN_TIMEOUT_SEC) or DEFAULT_IDLE_RETURN_TIMEOUT_SEC)

    if battery_level <= low_battery_threshold:
        target = _resolve_nearest_autonomy_target(agv, "charge", grid_cols, grid_rows)
        if target and str(target["key"]) != current_node and agv.auto_target_type != "charge":
            if move_agv_to_autonomy_target(
                agv.id,
                target["x"],
                target["y"],
                target_key=target["key"],
                target_type="charge",
                algorithm=AUTONOMY_ALGORITHM,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
            ):
                agv.idle_since_at = None
        elif target and str(target["key"]) == current_node and agv.status != "charging":
            agv.status = "charging"
            agv.charge_started_at = now.isoformat(timespec="seconds")
            agv.auto_target_node = str(target["key"])
            agv.auto_target_type = "charge"
            agv.clear_motion(motion_state="charging")
        return

    if (
        agv.status == "idle"
        and idle_elapsed >= idle_charge_timeout_sec
        and battery_level < idle_charge_battery_threshold
    ):
        target = _resolve_nearest_autonomy_target(agv, "charge", grid_cols, grid_rows)
        if target and str(target["key"]) != current_node and agv.auto_target_type != "charge":
            if move_agv_to_autonomy_target(
                agv.id,
                target["x"],
                target["y"],
                target_key=target["key"],
                target_type="charge",
                algorithm=AUTONOMY_ALGORITHM,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
            ):
                agv.idle_since_at = None
        elif target and str(target["key"]) == current_node and agv.status != "charging":
            agv.status = "charging"
            agv.charge_started_at = now.isoformat(timespec="seconds")
            agv.auto_target_node = str(target["key"])
            agv.auto_target_type = "charge"
            agv.clear_motion(motion_state="charging")
        return

    if agv.status != "idle":
        return

    if idle_elapsed < idle_return_timeout_sec:
        return

    target = _resolve_nearest_autonomy_target(agv, "parking", grid_cols, grid_rows)
    if not target or str(target["key"]) == current_node:
        return
    if move_agv_to_autonomy_target(
        agv.id,
        target["x"],
        target["y"],
        target_key=target["key"],
        target_type="parking",
        algorithm=AUTONOMY_ALGORITHM,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
    ):
        agv.idle_since_at = None


def sync_agv_autonomy() -> list:
    grid_cols, grid_rows = get_current_grid_size()
    now = datetime.now()
    policy_settings = _get_autonomy_policy_settings()
    node_by_key, node_by_position = _build_runtime_topology_node_indexes()
    agvs = list_agvs()
    for agv in agvs:
        _sync_battery_runtime(agv, now, policy_settings, node_by_key, node_by_position)
        if _release_from_charging_if_ready(agv, now):
            continue
        _sync_idle_timer(agv, now)
        if _retarget_active_autonomy_if_needed(agv, grid_cols, grid_rows):
            continue
        if _recover_stalled_autonomy_if_needed(agv, now, grid_cols, grid_rows):
            continue
        _start_autonomy_if_needed(agv, now, grid_cols, grid_rows, policy_settings)
    return agvs
