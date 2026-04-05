from __future__ import annotations

from datetime import datetime

from app.repositories.agv_repository import list_agvs
from app.repositories.ui_settings_repository import get_ui_settings as get_ui_settings_store
from app.utils.agv_movement import move_agv_to_autonomy_target, now_iso
from app.utils.path_planner import plan_path
from app.utils.warehouse_map import (
    get_current_grid_size,
    get_map_layout_state,
    get_topology_node_default_capacity,
    normalize_topology_node_capacity,
)


DEFAULT_IDLE_RETURN_TIMEOUT_SEC = 12.0
DEFAULT_IDLE_CHARGE_TIMEOUT_SEC = 45.0
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


AUTONOMY_UI_SETTINGS_DEFAULTS = {
    "idle_return_timeout_sec": DEFAULT_IDLE_RETURN_TIMEOUT_SEC,
    "idle_charge_timeout_sec": DEFAULT_IDLE_CHARGE_TIMEOUT_SEC,
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


def _build_runtime_topology_occupancy_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for agv in list_agvs():
        if getattr(agv, "status", None) == "maintenance":
            continue
        node_key = str(getattr(agv, "current_node", "") or "").strip()
        if not node_key:
            continue
        counts[node_key] = counts.get(node_key, 0) + 1
    return counts


def _resolve_nearest_autonomy_target(agv, target_type: str, grid_cols: int, grid_rows: int) -> dict | None:
    candidate_types = ("charge",) if target_type == "charge" else ("parking",)
    occupancy_counts = _build_runtime_topology_occupancy_counts()
    best: tuple[int, dict] | None = None
    fallback: tuple[int, dict] | None = None
    for node in _resolve_runtime_topology_nodes(*candidate_types):
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
        if payload["key"] != str(getattr(agv, "current_node", "") or "") and current_occupancy >= payload["capacity"]:
            continue
        path = plan_path(
            AUTONOMY_ALGORITHM,
            int(agv.x),
            int(agv.y),
            node_x,
            node_y,
            grid_cols,
            grid_rows,
            request_priority=0,
            agv_id=agv.id,
        )
        if not path:
            continue
        distance = max(len(path) - 1, 0)
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
    idle_return_timeout_sec = float(policy_settings.get("idle_return_timeout_sec", DEFAULT_IDLE_RETURN_TIMEOUT_SEC) or DEFAULT_IDLE_RETURN_TIMEOUT_SEC)

    if battery_level <= LOW_BATTERY_THRESHOLD:
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
        and battery_level < CHARGE_RELEASE_THRESHOLD
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
        _start_autonomy_if_needed(agv, now, grid_cols, grid_rows, policy_settings)
    return agvs
