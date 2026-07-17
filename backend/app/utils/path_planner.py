from __future__ import annotations

import heapq
from collections import defaultdict

from app.repositories.agv_repository import list_agvs
from app.repositories.task_repository import list_tasks
from app.utils.warehouse_map import (
    get_map_layout_state,
    get_navigation_blocked_cells,
    normalize_topology_node_capacity,
)


TOPOLOGY_LANE_COST_FACTORS = {
    "main": 1.0,
    "branch": 1.08,
    "service": 1.16,
}
TOPOLOGY_OCCUPIED_EDGE_PENALTY = 72.0
TOPOLOGY_OCCUPIED_NODE_PENALTY = 22.0
TOPOLOGY_PARTIAL_NODE_USAGE_PENALTY = 3.0
TOPOLOGY_ENTRY_EXIT_PENALTY = 0.4
TOPOLOGY_SAME_NODE_TRANSFER_PENALTY = 1.25
TOPOLOGY_ENTRY_RETREAT_PENALTY = 0.9
TOPOLOGY_ENTRY_TURNBACK_PENALTY = 1.6
TOPOLOGY_EXIT_TURNBACK_PENALTY = 0.8
TOPOLOGY_MAX_ENTRY_CANDIDATES = 8
TOPOLOGY_GRID_FALLBACK_MARGIN = 1.25
TOPOLOGY_RUNTIME_LANE_FACTORS = {
    "main": 1.0,
    "branch": 1.03,
    "service": 1.08,
}
TOPOLOGY_RUNTIME_EQUAL_MARGIN = 0.05


def _is_topology_edge_hard_blocked_for_request(edge: dict, edge_blockers: dict[str, dict], request_priority: int) -> bool:
    blocker = edge_blockers.get(str(edge.get("key") or ""))
    if blocker is None:
        return False
    blocker_priority = max(int(blocker.get("priority") or 0), 0)
    return blocker_priority > max(int(request_priority or 0), 0)


def _build_point(x: int, y: int, **meta):
    point = {"x": int(x), "y": int(y)}
    for key, value in meta.items():
        if value is not None:
            point[key] = value
    return point


def _same_point(a: dict | None, b: dict | None) -> bool:
    if not a or not b:
        return False
    return int(a.get("x", -1)) == int(b.get("x", -2)) and int(a.get("y", -1)) == int(b.get("y", -2))


def _manhattan_distance(ax: int, ay: int, bx: int, by: int) -> int:
    return abs(int(ax) - int(bx)) + abs(int(ay) - int(by))


def _vector_dot(ax: int, ay: int, bx: int, by: int) -> int:
    return int(ax) * int(bx) + int(ay) * int(by)


def _merge_path_segments(*segments: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for segment in segments:
        for point in segment or []:
            normalized = dict(point)
            if merged and _same_point(merged[-1], normalized):
                for key, value in normalized.items():
                    if key in {"x", "y"}:
                        continue
                    if value is not None:
                        merged[-1][key] = value
                continue
            merged.append(normalized)
    return merged


def _reverse_path(path: list[dict]) -> list[dict]:
    return [_build_point(int(point["x"]), int(point["y"])) for point in reversed(path or [])]


def _path_step_cost(path: list[dict]) -> int:
    if not path:
        return 0
    return max(len(path) - 1, 0)


def _trace_simple_candidate(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    axis_order: tuple[str, str],
    blocked: set[tuple[int, int]],
):
    path = [_build_point(sx, sy)]
    x, y = sx, sy

    for axis in axis_order:
        if axis == "x":
            while x != ex:
                x += 1 if ex > x else -1
                if (x, y) in blocked:
                    return []
                path.append(_build_point(x, y))
        else:
            while y != ey:
                y += 1 if ey > y else -1
                if (x, y) in blocked:
                    return []
                path.append(_build_point(x, y))

    return path


def generate_simple_path(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]] | None = None,
):
    if blocked is None:
        blocked = set()

    def in_bounds(x: int, y: int):
        return 0 <= x < grid_cols and 0 <= y < grid_rows

    if not in_bounds(sx, sy) or not in_bounds(ex, ey):
        return []

    if (sx, sy) in blocked or (ex, ey) in blocked:
        return []

    if sx == ex and sy == ey:
        return [_build_point(sx, sy)]

    for axis_order in (("x", "y"), ("y", "x")):
        path = _trace_simple_candidate(sx, sy, ex, ey, axis_order, blocked)
        if path:
            return path

    return []


def generate_astar_path(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]] | None = None,
):
    start = (sx, sy)
    goal = (ex, ey)

    if start == goal:
        return [_build_point(sx, sy)]

    if blocked is None:
        blocked = set()

    def in_bounds(x: int, y: int):
        return 0 <= x < grid_cols and 0 <= y < grid_rows

    def neighbors(node: tuple[int, int]):
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if in_bounds(nx, ny) and (nx, ny) not in blocked:
                yield (nx, ny)

    def heuristic(a: tuple[int, int], b: tuple[int, int]):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    if not in_bounds(*start) or not in_bounds(*goal):
        return []

    if start in blocked or goal in blocked:
        return []

    open_heap = []
    heapq.heappush(open_heap, (0, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score = {start: 0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return [_build_point(x, y) for x, y in path]

        for neighbor in neighbors(current):
            tentative = g_score[current] + 1
            if neighbor not in g_score or tentative < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f_score = tentative + heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f_score, neighbor))

    return []


def _plan_grid_path(
    algorithm: str,
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]],
):
    if algorithm == "astar":
        return generate_astar_path(sx, sy, ex, ey, grid_cols, grid_rows, blocked)
    return generate_simple_path(sx, sy, ex, ey, grid_cols, grid_rows, blocked)


def _get_runtime_topology_state():
    state = get_map_layout_state()
    return state.get("topology") or {}, state.get("valid_cells") or []


def _build_task_priority_map() -> dict[int, int]:
    priorities: dict[int, int] = {}
    for task in list_tasks():
        try:
            priorities[int(task.id)] = max(int(getattr(task, "priority", 0) or 0), 0)
        except Exception:
            continue
    return priorities


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


def _build_live_topology_reservations(exclude_agv_id: int | None = None):
    task_priorities = _build_task_priority_map()
    occupied_positions: set[tuple[int, int]] = set()
    occupied_node_counts: dict[str, int] = defaultdict(int)
    edge_blockers: dict[str, dict[str, int | str | None]] = {}
    topology_payload, _ = _get_runtime_topology_state()
    node_by_key, node_by_position, _ = _build_topology_indexes(topology_payload)

    for agv in list_agvs():
        try:
            current_agv_id = int(agv.id)
        except Exception:
            continue
        if exclude_agv_id is not None and current_agv_id == int(exclude_agv_id):
            continue
        if getattr(agv, "status", None) == "maintenance":
            continue

        occupied_positions.add((int(agv.x), int(agv.y)))
        node_key = _resolve_runtime_topology_node_key_for_agv(agv, node_by_key, node_by_position)
        if node_key:
            occupied_node_counts[node_key] += 1
        reserved_node_key = str(getattr(agv, "auto_target_node", "") or "").strip()
        reserved_target_type = str(getattr(agv, "auto_target_type", "") or "").strip().lower()
        reserved_motion_state = str(getattr(agv, "status", "") or "").strip().lower()
        if (
            reserved_node_key
            and reserved_node_key != node_key
            and reserved_target_type in {"parking", "charge"}
            and reserved_motion_state in {"idle_returning", "waiting_for_charge", "charging"}
        ):
            occupied_node_counts[reserved_node_key] += 1

        edge_key = str(getattr(agv, "current_edge", "") or "").strip()
        if not edge_key:
            continue

        blocker = {
            "agv_id": current_agv_id,
            "task_id": int(agv.task_id) if getattr(agv, "task_id", None) is not None else None,
            "priority": task_priorities.get(int(agv.task_id), 0) if getattr(agv, "task_id", None) is not None else 0,
            "motion_state": str(getattr(agv, "motion_state", "") or getattr(agv, "status", "") or "idle"),
        }
        existing = edge_blockers.get(edge_key)
        if existing is None or int(blocker["priority"] or 0) >= int(existing["priority"] or 0):
            edge_blockers[edge_key] = blocker

    return {
        "occupied_positions": occupied_positions,
        "occupied_node_counts": dict(occupied_node_counts),
        "edge_blockers": edge_blockers,
    }


def build_runtime_special_node_constraints(
    *,
    exclude_agv_id: int | None = None,
    goal_node_key: str | None = None,
    allowed_node_keys: set[str] | None = None,
    include_types: set[str] | None = None,
) -> dict[str, set]:
    topology_payload, _ = _get_runtime_topology_state()
    node_by_key, _, _ = _build_topology_indexes(topology_payload)
    reservations = _build_live_topology_reservations(exclude_agv_id)
    occupied_node_counts = reservations["occupied_node_counts"]
    normalized_goal = str(goal_node_key or "").strip()
    normalized_allowed = {
        str(item).strip()
        for item in (allowed_node_keys or set())
        if str(item).strip()
    }
    normalized_types = {
        str(item).strip().lower()
        for item in (include_types or {"station", "parking", "charge"})
        if str(item).strip()
    }
    blocked_positions: set[tuple[int, int]] = set()
    avoid_node_keys: set[str] = set()

    for node_key, node in node_by_key.items():
        normalized_key = str(node_key or "").strip()
        if not normalized_key or normalized_key == normalized_goal or normalized_key in normalized_allowed:
            continue
        node_type = str(node.get("node_type") or "").strip().lower()
        if normalized_types and node_type not in normalized_types:
            continue
        capacity = normalize_topology_node_capacity(node_type or "waypoint", node.get("capacity"))
        occupancy = max(int(occupied_node_counts.get(normalized_key, 0) or 0), 0)
        if occupancy < capacity:
            continue
        blocked_positions.add((int(node.get("x") or 0), int(node.get("y") or 0)))
        avoid_node_keys.add(normalized_key)

    return {
        "blocked_positions": blocked_positions,
        "avoid_node_keys": avoid_node_keys,
    }


def _build_topology_indexes(topology: dict | None):
    source = topology if isinstance(topology, dict) else {}
    nodes = source.get("nodes") if isinstance(source.get("nodes"), list) else []
    edges = source.get("edges") if isinstance(source.get("edges"), list) else []

    node_by_key: dict[str, dict] = {}
    node_by_position: dict[tuple[int, int], dict] = {}
    outgoing: dict[str, list[dict]] = defaultdict(list)

    for node in nodes:
        if not isinstance(node, dict):
            continue
        key = str(node.get("key") or "").strip()
        if not key:
            continue
        payload = {
            "key": key,
            "x": int(node.get("x", 0)),
            "y": int(node.get("y", 0)),
            "label": node.get("label"),
            "node_type": str(node.get("node_type") or "waypoint"),
            "capacity": normalize_topology_node_capacity(node.get("node_type") or "waypoint", node.get("capacity")),
        }
        node_by_key[key] = payload
        node_by_position[(payload["x"], payload["y"])] = payload

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        key = str(edge.get("key") or "").strip()
        source_key = str(edge.get("source") or "").strip()
        target_key = str(edge.get("target") or "").strip()
        if not key or source_key not in node_by_key or target_key not in node_by_key or source_key == target_key:
            continue
        direction = str(edge.get("direction") or "bidirectional").strip().lower()
        lane_type = str(edge.get("lane_type") or "main").strip().lower()
        source_node = node_by_key[source_key]
        target_node = node_by_key[target_key]
        geometry_weight = max(
            abs(int(target_node["x"]) - int(source_node["x"])) + abs(int(target_node["y"]) - int(source_node["y"])),
            1,
        )
        try:
            parsed_weight = float(edge.get("weight", geometry_weight))
        except (TypeError, ValueError):
            parsed_weight = float(geometry_weight)
        weight = max(parsed_weight, float(geometry_weight), 0.1)
        speed_multiplier = max(float(edge.get("speed_multiplier") or 1.0), 0.1)
        base_edge = {
            "key": key,
            "source": source_key,
            "target": target_key,
            "direction": direction if direction in {"bidirectional", "forward", "reverse"} else "bidirectional",
            "lane_type": lane_type if lane_type in TOPOLOGY_LANE_COST_FACTORS else "main",
            "weight": weight,
            "speed_multiplier": speed_multiplier,
        }
        if base_edge["direction"] in {"bidirectional", "forward"}:
            outgoing[source_key].append({**base_edge, "from": source_key, "to": target_key})
        if base_edge["direction"] in {"bidirectional", "reverse"}:
            outgoing[target_key].append({**base_edge, "from": target_key, "to": source_key})

    return node_by_key, node_by_position, outgoing


def resolve_topology_segment_metadata(
    source_x: int,
    source_y: int,
    target_x: int,
    target_y: int,
    *,
    edge_key: str | None = None,
    topology: dict | None = None,
):
    fallback_source = f"grid:{int(source_x)}:{int(source_y)}"
    fallback_target = f"grid:{int(target_x)}:{int(target_y)}"
    fallback_edge = str(edge_key or f"{fallback_source}->{fallback_target}")

    topology_payload = topology
    if topology_payload is None:
        topology_payload, _ = _get_runtime_topology_state()
    node_by_key, node_by_position, outgoing = _build_topology_indexes(topology_payload)

    source_node = node_by_position.get((int(source_x), int(source_y)))
    target_node = node_by_position.get((int(target_x), int(target_y)))
    resolved_source_key = str(source_node["key"]) if source_node is not None else fallback_source
    resolved_target_key = str(target_node["key"]) if target_node is not None else fallback_target
    if not source_node or not target_node:
        source_segment_x = int(source_x)
        source_segment_y = int(source_y)
        target_segment_x = int(target_x)
        target_segment_y = int(target_y)
        for raw_edge in topology_payload.get("edges", []) or []:
            if not isinstance(raw_edge, dict):
                continue
            raw_source_key = str(raw_edge.get("source") or "").strip()
            raw_target_key = str(raw_edge.get("target") or "").strip()
            raw_source_node = node_by_key.get(raw_source_key)
            raw_target_node = node_by_key.get(raw_target_key)
            if raw_source_node is None or raw_target_node is None:
                continue

            sx_node = int(raw_source_node["x"])
            sy_node = int(raw_source_node["y"])
            tx_node = int(raw_target_node["x"])
            ty_node = int(raw_target_node["y"])

            horizontal = sy_node == ty_node and source_segment_y == target_segment_y == sy_node
            vertical = sx_node == tx_node and source_segment_x == target_segment_x == sx_node
            if not horizontal and not vertical:
                continue

            min_x, max_x = sorted((sx_node, tx_node))
            min_y, max_y = sorted((sy_node, ty_node))
            if not (min_x <= source_segment_x <= max_x and min_x <= target_segment_x <= max_x):
                continue
            if not (min_y <= source_segment_y <= max_y and min_y <= target_segment_y <= max_y):
                continue

            step_dx = int(target_segment_x) - int(source_segment_x)
            step_dy = int(target_segment_y) - int(source_segment_y)
            if step_dx == 0 and step_dy == 0:
                continue

            corridor_dx = 0 if sx_node == tx_node else (1 if tx_node > sx_node else -1)
            corridor_dy = 0 if sy_node == ty_node else (1 if ty_node > sy_node else -1)
            if corridor_dx != 0 and step_dy != 0:
                continue
            if corridor_dy != 0 and step_dx != 0:
                continue
            normalized_step_dx = 0 if step_dx == 0 else (1 if step_dx > 0 else -1)
            normalized_step_dy = 0 if step_dy == 0 else (1 if step_dy > 0 else -1)
            direction = str(raw_edge.get("direction") or "bidirectional")
            if direction == "forward" and (normalized_step_dx, normalized_step_dy) != (corridor_dx, corridor_dy):
                continue
            if direction == "reverse" and (normalized_step_dx, normalized_step_dy) != (-corridor_dx, -corridor_dy):
                continue

            if edge_key and str(raw_edge.get("key") or "") != str(edge_key):
                continue

            return {
                "source_node": resolved_source_key,
                "target_node": resolved_target_key,
                "edge_key": str(raw_edge.get("key") or fallback_edge),
                "lane_type": str(raw_edge.get("lane_type") or "main"),
                "speed_multiplier": float(raw_edge.get("speed_multiplier") or 1.0),
            }

        return {
            "source_node": resolved_source_key,
            "target_node": resolved_target_key,
            "edge_key": fallback_edge,
            "lane_type": "grid",
            "speed_multiplier": 1.0,
        }

    selected_edge = None
    for candidate in outgoing.get(source_node["key"], []):
        if candidate["to"] != target_node["key"]:
            continue
        if edge_key and str(candidate["key"]) != str(edge_key):
            continue
        selected_edge = candidate
        break

    return {
        "source_node": source_node["key"],
        "target_node": target_node["key"],
        "edge_key": str(selected_edge["key"]) if selected_edge else fallback_edge,
        "lane_type": str(selected_edge["lane_type"]) if selected_edge else "grid",
        "speed_multiplier": float(selected_edge["speed_multiplier"]) if selected_edge else 1.0,
    }


def _estimate_runtime_cost_for_path(path: list[dict], *, topology: dict | None = None) -> float:
    if not path or len(path) <= 1:
        return 0.0
    total = 0.0
    for source_point, target_point in zip(path, path[1:]):
        segment = resolve_topology_segment_metadata(
            int(source_point["x"]),
            int(source_point["y"]),
            int(target_point["x"]),
            int(target_point["y"]),
            edge_key=target_point.get("topology_edge_key"),
            topology=topology,
        )
        lane_type = str(segment.get("lane_type") or "grid")
        speed_multiplier = max(float(segment.get("speed_multiplier") or 1.0), 0.1)
        if lane_type == "grid" or str(segment.get("edge_key") or "").startswith("grid:"):
            total += 1.0
        else:
            total += TOPOLOGY_RUNTIME_LANE_FACTORS.get(lane_type, 1.0) / speed_multiplier
    return float(total)


def _find_topology_edge_position_candidates(
    x: int,
    y: int,
    *,
    topology_payload: dict,
    node_by_key: dict[str, dict],
) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, int, int]] = set()
    point_x = int(x)
    point_y = int(y)

    for edge in topology_payload.get("edges", []) or []:
        if not isinstance(edge, dict):
            continue
        source_key = str(edge.get("source") or "").strip()
        target_key = str(edge.get("target") or "").strip()
        source_node = node_by_key.get(source_key)
        target_node = node_by_key.get(target_key)
        if source_node is None or target_node is None:
            continue

        sx = int(source_node["x"])
        sy = int(source_node["y"])
        tx = int(target_node["x"])
        ty = int(target_node["y"])
        on_horizontal = sy == ty == point_y and min(sx, tx) <= point_x <= max(sx, tx)
        on_vertical = sx == tx == point_x and min(sy, ty) <= point_y <= max(sy, ty)
        if not on_horizontal and not on_vertical:
            continue
        if (point_x, point_y) in {(sx, sy), (tx, ty)}:
            continue

        edge_key = str(edge.get("key") or f"{source_key}->{target_key}")
        dedupe_key = (edge_key, point_x, point_y)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        source_distance = _manhattan_distance(point_x, point_y, sx, sy)
        target_distance = _manhattan_distance(point_x, point_y, tx, ty)
        total_length = max(source_distance + target_distance, 1)
        candidates.append(
            {
                "kind": "edge",
                "node": {
                    "x": point_x,
                    "y": point_y,
                    "label": edge_key,
                },
                "path": [_build_point(point_x, point_y)],
                "distance": 0,
                "exact": True,
                "edge_key": edge_key,
                "direction": str(edge.get("direction") or "bidirectional"),
                "lane_type": str(edge.get("lane_type") or "main"),
                "speed_multiplier": float(edge.get("speed_multiplier") or 1.0),
                "source_key": source_key,
                "target_key": target_key,
                "source_distance": float(source_distance),
                "target_distance": float(target_distance),
                "offset_from_source": float(source_distance),
                "total_length": float(total_length),
            }
        )

    return candidates


def _find_reachable_topology_edge_candidates(
    x: int,
    y: int,
    *,
    topology_payload: dict,
    node_by_key: dict[str, dict],
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]],
) -> list[dict]:
    point_x = int(x)
    point_y = int(y)
    candidates: list[dict] = []

    for edge in topology_payload.get("edges", []) or []:
        if not isinstance(edge, dict):
            continue

        source_key = str(edge.get("source") or "").strip()
        target_key = str(edge.get("target") or "").strip()
        source_node = node_by_key.get(source_key)
        target_node = node_by_key.get(target_key)
        if source_node is None or target_node is None:
            continue

        sx = int(source_node["x"])
        sy = int(source_node["y"])
        tx = int(target_node["x"])
        ty = int(target_node["y"])
        edge_key = str(edge.get("key") or f"{source_key}->{target_key}")

        best_path: list[dict] = []
        best_point: tuple[int, int] | None = None
        best_distance: int | None = None

        if sy == ty:
            interior_points = ((candidate_x, sy) for candidate_x in range(min(sx, tx) + 1, max(sx, tx)))
        elif sx == tx:
            interior_points = ((sx, candidate_y) for candidate_y in range(min(sy, ty) + 1, max(sy, ty)))
        else:
            interior_points = ()

        for candidate_x, candidate_y in interior_points:
            if (candidate_x, candidate_y) == (point_x, point_y):
                continue
            path = _plan_grid_path(
                algorithm,
                point_x,
                point_y,
                candidate_x,
                candidate_y,
                grid_cols,
                grid_rows,
                blocked,
            )
            if not path:
                continue
            distance = _path_step_cost(path)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_path = path
                best_point = (candidate_x, candidate_y)

        if best_point is None or best_distance is None or best_distance <= 0:
            continue

        source_distance = _manhattan_distance(best_point[0], best_point[1], sx, sy)
        target_distance = _manhattan_distance(best_point[0], best_point[1], tx, ty)
        total_length = max(source_distance + target_distance, 1)
        candidates.append(
            {
                "kind": "edge",
                "node": {
                    "x": int(best_point[0]),
                    "y": int(best_point[1]),
                    "label": edge_key,
                },
                "path": best_path,
                "distance": best_distance,
                "exact": False,
                "edge_key": edge_key,
                "direction": str(edge.get("direction") or "bidirectional"),
                "lane_type": str(edge.get("lane_type") or "main"),
                "speed_multiplier": float(edge.get("speed_multiplier") or 1.0),
                "source_key": source_key,
                "target_key": target_key,
                "source_distance": float(source_distance),
                "target_distance": float(target_distance),
                "offset_from_source": float(source_distance),
                "total_length": float(total_length),
            }
        )

    return candidates


def _build_augmented_topology_graph(
    node_by_key: dict[str, dict],
    outgoing: dict[str, list[dict]],
    *,
    start_candidate: dict,
    end_candidate: dict,
) -> tuple[dict[str, dict], dict[str, list[dict]], str, str]:
    augmented_node_by_key = {str(key): dict(value) for key, value in node_by_key.items()}
    augmented_outgoing: dict[str, list[dict]] = {
        str(key): [{**edge} for edge in edges]
        for key, edges in outgoing.items()
    }

    def ensure_node(key: str, candidate: dict):
        augmented_node_by_key[key] = {
            "key": key,
            "x": int(candidate["node"]["x"]),
            "y": int(candidate["node"]["y"]),
            "label": str(candidate["node"].get("label") or key),
            "node_type": "waypoint",
            "capacity": 1,
        }
        augmented_outgoing.setdefault(key, [])

    def edge_payload(from_key: str, to_key: str, candidate: dict, distance: float) -> dict:
        return {
            "key": str(candidate["edge_key"]),
            "from": str(from_key),
            "to": str(to_key),
            "direction": "bidirectional",
            "lane_type": str(candidate["lane_type"]),
            "weight": max(float(distance), 0.1),
            "speed_multiplier": max(float(candidate["speed_multiplier"]), 0.1),
        }

    if start_candidate.get("kind") == "edge":
        start_key = f"virtual:start:{start_candidate['edge_key']}:{int(start_candidate['node']['x'])}:{int(start_candidate['node']['y'])}"
        ensure_node(start_key, start_candidate)
        direction = str(start_candidate["direction"])
        if direction in {"bidirectional", "reverse"} and float(start_candidate["source_distance"]) > 0:
            augmented_outgoing[start_key].append(
                edge_payload(start_key, str(start_candidate["source_key"]), start_candidate, float(start_candidate["source_distance"]))
            )
        if direction in {"bidirectional", "forward"} and float(start_candidate["target_distance"]) > 0:
            augmented_outgoing[start_key].append(
                edge_payload(start_key, str(start_candidate["target_key"]), start_candidate, float(start_candidate["target_distance"]))
            )
    else:
        start_key = str(start_candidate["node"]["key"])

    if end_candidate.get("kind") == "edge":
        end_key = f"virtual:end:{end_candidate['edge_key']}:{int(end_candidate['node']['x'])}:{int(end_candidate['node']['y'])}"
        ensure_node(end_key, end_candidate)
        direction = str(end_candidate["direction"])
        if direction in {"bidirectional", "forward"} and float(end_candidate["source_distance"]) > 0:
            augmented_outgoing.setdefault(str(end_candidate["source_key"]), []).append(
                edge_payload(str(end_candidate["source_key"]), end_key, end_candidate, float(end_candidate["source_distance"]))
            )
        if direction in {"bidirectional", "reverse"} and float(end_candidate["target_distance"]) > 0:
            augmented_outgoing.setdefault(str(end_candidate["target_key"]), []).append(
                edge_payload(str(end_candidate["target_key"]), end_key, end_candidate, float(end_candidate["target_distance"]))
            )
    else:
        end_key = str(end_candidate["node"]["key"])

    if start_candidate.get("kind") == "edge" and end_candidate.get("kind") == "edge":
        if str(start_candidate["edge_key"]) == str(end_candidate["edge_key"]):
            start_offset = float(start_candidate["offset_from_source"])
            end_offset = float(end_candidate["offset_from_source"])
            direction = str(start_candidate["direction"])
            direct_distance = abs(end_offset - start_offset)
            if direct_distance <= 0:
                augmented_outgoing.setdefault(start_key, [])
            else:
                if end_offset > start_offset and direction in {"bidirectional", "forward"}:
                    augmented_outgoing.setdefault(start_key, []).append(
                        edge_payload(start_key, end_key, start_candidate, direct_distance)
                    )
                if end_offset < start_offset and direction in {"bidirectional", "reverse"}:
                    augmented_outgoing.setdefault(start_key, []).append(
                        edge_payload(start_key, end_key, start_candidate, direct_distance)
                    )

    return augmented_node_by_key, augmented_outgoing, start_key, end_key


def _find_topology_node_candidates(
    x: int,
    y: int,
    *,
    node_by_position: dict[tuple[int, int], dict],
    node_by_key: dict[str, dict],
    algorithm: str,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]],
    topology_payload: dict | None = None,
    limit: int = TOPOLOGY_MAX_ENTRY_CANDIDATES,
):
    exact = node_by_position.get((int(x), int(y)))
    if exact:
        return [
            {
                "node": exact,
                "path": [_build_point(x, y)],
                "distance": 0,
                "exact": True,
            }
        ]

    topology_payload = topology_payload or {}
    exact_edge_candidates = _find_topology_edge_position_candidates(
        int(x),
        int(y),
        topology_payload=topology_payload,
        node_by_key=node_by_key,
    )
    reachable_edge_candidates = _find_reachable_topology_edge_candidates(
        int(x),
        int(y),
        topology_payload=topology_payload,
        node_by_key=node_by_key,
        algorithm=algorithm,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        blocked=blocked,
    )

    candidates: list[tuple[int, int, int, str, dict]] = []
    for candidate in exact_edge_candidates:
        candidates.append((0, 0, 0, str(candidate["edge_key"]), candidate))
    for candidate in reachable_edge_candidates:
        candidates.append(
            (
                int(candidate["distance"]),
                _manhattan_distance(int(x), int(y), int(candidate["node"]["x"]), int(candidate["node"]["y"])),
                1,
                f"{candidate['edge_key']}:{int(candidate['node']['x'])}:{int(candidate['node']['y'])}",
                candidate,
            )
        )

    for node in node_by_key.values():
        path = _plan_grid_path(
            algorithm,
            int(x),
            int(y),
            int(node["x"]),
            int(node["y"]),
            grid_cols,
            grid_rows,
            blocked,
        )
        if not path:
            continue
        distance = max(len(path) - 1, 0)
        manhattan = abs(int(node["x"]) - int(x)) + abs(int(node["y"]) - int(y))
        candidates.append(
            (
                distance,
                manhattan,
                2,
                str(node["key"]),
                {
                    "kind": "node",
                    "node": node,
                    "path": path,
                    "distance": distance,
                    "exact": distance == 0,
                },
            )
        )

    if not candidates:
        return []

    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return [candidate for _, _, _, _, candidate in candidates[: max(int(limit), 1)]]


def _build_topology_path_points(node_path: list[str], edge_path: list[dict], node_by_key: dict[str, dict]) -> list[dict]:
    if not node_path:
        return []
    points = [_build_point(node_by_key[node_path[0]]["x"], node_by_key[node_path[0]]["y"])]
    for node_key, edge in zip(node_path[1:], edge_path):
        node = node_by_key[node_key]
        points.append(
            _build_point(
                node["x"],
                node["y"],
                topology_source_node=str(edge["from"]),
                topology_target_node=str(edge["to"]),
                topology_edge_key=str(edge["key"]),
                topology_lane_type=str(edge["lane_type"]),
                topology_speed_multiplier=float(edge["speed_multiplier"]),
            )
        )
    return points


def _compute_topology_candidate_progress_penalty(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    *,
    start_candidate: dict,
    end_candidate: dict,
    node_path: list[str],
    node_by_key: dict[str, dict],
) -> float:
    penalty = 0.0
    start_goal_distance = _manhattan_distance(sx, sy, ex, ey)

    start_node = start_candidate["node"]
    if not start_candidate["exact"]:
        entry_goal_distance = _manhattan_distance(start_node["x"], start_node["y"], ex, ey)
        if entry_goal_distance > start_goal_distance:
            penalty += min((entry_goal_distance - start_goal_distance) * 0.35, TOPOLOGY_ENTRY_RETREAT_PENALTY)

    if not start_candidate["exact"] and len(node_path) > 1:
        next_node = node_by_key.get(node_path[1])
        if next_node is not None:
            entry_dx = int(start_node["x"]) - int(sx)
            entry_dy = int(start_node["y"]) - int(sy)
            topology_dx = int(next_node["x"]) - int(start_node["x"])
            topology_dy = int(next_node["y"]) - int(start_node["y"])
            if _vector_dot(entry_dx, entry_dy, topology_dx, topology_dy) < 0:
                penalty += TOPOLOGY_ENTRY_TURNBACK_PENALTY

    if not end_candidate["exact"] and len(node_path) > 1:
        end_node = end_candidate["node"]
        previous_node = node_by_key.get(node_path[-2])
        if previous_node is not None:
            topology_dx = int(end_node["x"]) - int(previous_node["x"])
            topology_dy = int(end_node["y"]) - int(previous_node["y"])
            exit_dx = int(ex) - int(end_node["x"])
            exit_dy = int(ey) - int(end_node["y"])
            if _vector_dot(topology_dx, topology_dy, exit_dx, exit_dy) < 0:
                penalty += TOPOLOGY_EXIT_TURNBACK_PENALTY

    return penalty


def _topology_edge_runtime_cost(edge: dict, node_by_key: dict[str, dict]) -> float:
    source_node = node_by_key.get(str(edge.get("from") or ""))
    target_node = node_by_key.get(str(edge.get("to") or ""))
    if source_node is None or target_node is None:
        return max(float(edge.get("weight") or 1.0), 0.1)

    distance = max(
        abs(int(target_node["x"]) - int(source_node["x"])),
        abs(int(target_node["y"]) - int(source_node["y"])),
        1,
    )
    speed_multiplier = max(float(edge.get("speed_multiplier") or 1.0), 0.1)
    lane_factor = TOPOLOGY_RUNTIME_LANE_FACTORS.get(str(edge.get("lane_type") or "main"), 1.0)
    return (float(distance) * lane_factor) / speed_multiplier


def _estimate_topology_candidate_runtime_cost(
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    *,
    start_candidate: dict,
    end_candidate: dict,
    node_path: list[str],
    edge_path: list[dict],
    node_by_key: dict[str, dict],
) -> float:
    runtime_cost = float(start_candidate["distance"]) + float(end_candidate["distance"])
    if not start_candidate["exact"]:
        runtime_cost += TOPOLOGY_ENTRY_EXIT_PENALTY * 0.15
    if not end_candidate["exact"]:
        runtime_cost += TOPOLOGY_ENTRY_EXIT_PENALTY * 0.15
    if not edge_path:
        runtime_cost += TOPOLOGY_SAME_NODE_TRANSFER_PENALTY + 1.0
    else:
        runtime_cost += sum(_topology_edge_runtime_cost(edge, node_by_key) for edge in edge_path)
    runtime_cost += _compute_topology_candidate_progress_penalty(
        sx,
        sy,
        ex,
        ey,
        start_candidate=start_candidate,
        end_candidate=end_candidate,
        node_path=node_path,
        node_by_key=node_by_key,
    ) * 0.25
    return runtime_cost


def _plan_topology_node_path(
    start_key: str,
    goal_key: str,
    *,
    outgoing: dict[str, list[dict]],
    edge_blockers: dict[str, dict],
    occupied_node_counts: dict[str, int],
    node_by_key: dict[str, dict],
    request_priority: int,
    avoid_edge_keys: set[str],
    avoid_node_keys: set[str],
):
    distances = {start_key: 0.0}
    came_from: dict[str, tuple[str, dict]] = {}
    heap: list[tuple[float, str]] = [(0.0, start_key)]
    visited: set[str] = set()

    while heap:
        current_cost, current_key = heapq.heappop(heap)
        if current_key in visited:
            continue
        visited.add(current_key)
        if current_key == goal_key:
            break

        for edge in outgoing.get(current_key, []):
            edge_key = str(edge["key"])
            next_key = str(edge["to"])
            if edge_key in avoid_edge_keys:
                continue
            if next_key in avoid_node_keys and next_key != goal_key:
                continue
            if _is_topology_edge_hard_blocked_for_request(edge, edge_blockers, request_priority):
                continue

            edge_cost = _topology_edge_cost(edge, edge_blockers, occupied_node_counts, node_by_key, request_priority, goal_key)
            next_cost = current_cost + edge_cost
            if next_cost < distances.get(next_key, float("inf")):
                distances[next_key] = next_cost
                came_from[next_key] = (current_key, edge)
                heapq.heappush(heap, (next_cost, next_key))

    if goal_key not in distances:
        return [], [], float("inf")

    node_path = [goal_key]
    edge_path: list[dict] = []
    current_key = goal_key
    while current_key != start_key:
        previous_key, edge = came_from[current_key]
        edge_path.append(edge)
        node_path.append(previous_key)
        current_key = previous_key
    node_path.reverse()
    edge_path.reverse()
    return node_path, edge_path, float(distances[goal_key])


def _topology_edge_cost(
    edge: dict,
    edge_blockers: dict[str, dict],
    occupied_node_counts: dict[str, int],
    node_by_key: dict[str, dict],
    request_priority: int,
    goal_key: str,
):
    base_cost = max(float(edge.get("weight") or 1.0), 0.1)
    speed_multiplier = max(float(edge.get("speed_multiplier") or 1.0), 0.1)
    lane_factor = TOPOLOGY_LANE_COST_FACTORS.get(str(edge.get("lane_type") or "main"), 1.0)
    total_cost = (base_cost * lane_factor) / speed_multiplier

    blocker = edge_blockers.get(str(edge["key"]))
    if blocker is not None:
        blocker_priority = max(int(blocker.get("priority") or 0), 0)
        total_cost += TOPOLOGY_OCCUPIED_EDGE_PENALTY + max(blocker_priority - max(int(request_priority or 0), 0), 0) * 6

    target_key = str(edge["to"])
    if target_key != str(goal_key):
        occupied_count = max(int(occupied_node_counts.get(target_key, 0) or 0), 0)
        target_capacity = normalize_topology_node_capacity(
            (node_by_key.get(target_key) or {}).get("node_type") or "waypoint",
            (node_by_key.get(target_key) or {}).get("capacity"),
        )
        if occupied_count >= target_capacity:
            total_cost += TOPOLOGY_OCCUPIED_NODE_PENALTY
        elif occupied_count > 0:
            total_cost += TOPOLOGY_PARTIAL_NODE_USAGE_PENALTY * occupied_count

    return total_cost


def _plan_topology_path(
    algorithm: str,
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]],
    *,
    topology: dict | None,
    request_priority: int,
    agv_id: int | None,
    avoid_edge_keys: set[str] | None = None,
    avoid_node_keys: set[str] | None = None,
):
    topology_payload = topology
    if topology_payload is None:
        topology_payload, _ = _get_runtime_topology_state()

    node_by_key, node_by_position, outgoing = _build_topology_indexes(topology_payload)
    if len(node_by_key) < 2 or not any(outgoing.values()):
        return []

    start_candidates = _find_topology_node_candidates(
        sx,
        sy,
        node_by_position=node_by_position,
        node_by_key=node_by_key,
        algorithm=algorithm,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        blocked=blocked,
        topology_payload=topology_payload,
    )
    end_candidates = _find_topology_node_candidates(
        ex,
        ey,
        node_by_position=node_by_position,
        node_by_key=node_by_key,
        algorithm=algorithm,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        blocked=blocked,
        topology_payload=topology_payload,
    )
    if not start_candidates or not end_candidates:
        return []

    reservations = _build_live_topology_reservations(agv_id)
    edge_blockers = reservations["edge_blockers"]
    occupied_node_counts = reservations["occupied_node_counts"]
    direct_grid_path = _plan_grid_path(algorithm, sx, sy, ex, ey, grid_cols, grid_rows, blocked)
    direct_grid_cost = float("inf") if not direct_grid_path else float(_path_step_cost(direct_grid_path))
    direct_grid_runtime_cost = (
        float("inf")
        if not direct_grid_path
        else _estimate_runtime_cost_for_path(direct_grid_path, topology=topology_payload)
    )

    normalized_avoid_edges = {str(item).strip() for item in (avoid_edge_keys or set()) if str(item).strip()}
    normalized_avoid_nodes = {str(item).strip() for item in (avoid_node_keys or set()) if str(item).strip()}

    best_payload = None
    for start_candidate in start_candidates:
        prefix_path = start_candidate["path"]

        for end_candidate in end_candidates:
            end_node = end_candidate["node"]
            augmented_node_by_key, augmented_outgoing, start_key, goal_key = _build_augmented_topology_graph(
                node_by_key,
                outgoing,
                start_candidate=start_candidate,
                end_candidate=end_candidate,
            )
            node_path, edge_path, topology_cost = _plan_topology_node_path(
                start_key,
                goal_key,
                outgoing=augmented_outgoing,
                edge_blockers=edge_blockers,
                occupied_node_counts=occupied_node_counts,
                node_by_key=augmented_node_by_key,
                request_priority=request_priority,
                avoid_edge_keys=normalized_avoid_edges,
                avoid_node_keys=normalized_avoid_nodes,
            )
            if not node_path:
                continue
            if not edge_path and (not start_candidate["exact"] or not end_candidate["exact"]):
                continue

            suffix_path = _reverse_path(end_candidate["path"])
            candidate_total_cost = float(start_candidate["distance"]) + topology_cost + float(end_candidate["distance"])
            if not start_candidate["exact"]:
                candidate_total_cost += TOPOLOGY_ENTRY_EXIT_PENALTY
            if not end_candidate["exact"]:
                candidate_total_cost += TOPOLOGY_ENTRY_EXIT_PENALTY
            if len(node_path) == 1 and (not start_candidate["exact"] or not end_candidate["exact"]):
                candidate_total_cost += TOPOLOGY_SAME_NODE_TRANSFER_PENALTY
            candidate_progress_penalty = _compute_topology_candidate_progress_penalty(
                sx,
                sy,
                ex,
                ey,
                start_candidate=start_candidate,
                end_candidate=end_candidate,
                node_path=node_path,
                node_by_key=augmented_node_by_key,
            )
            candidate_total_cost += candidate_progress_penalty
            candidate_runtime_cost = _estimate_topology_candidate_runtime_cost(
                sx,
                sy,
                ex,
                ey,
                start_candidate=start_candidate,
                end_candidate=end_candidate,
                node_path=node_path,
                edge_path=edge_path,
                node_by_key=augmented_node_by_key,
            )

            topology_points = _build_topology_path_points(node_path, edge_path, augmented_node_by_key)
            candidate_path = _merge_path_segments(
                prefix_path or [_build_point(sx, sy)],
                topology_points,
                suffix_path or [_build_point(int(end_node["x"]), int(end_node["y"]))],
            )

            candidate_length = _path_step_cost(candidate_path)
            candidate_key = (
                round(candidate_runtime_cost, 4),
                round(candidate_total_cost, 4),
                candidate_length,
                len(edge_path),
                str(start_key),
                str(goal_key),
            )
            if best_payload is None or candidate_key < best_payload["key"]:
                best_payload = {
                    "key": candidate_key,
                    "total_cost": candidate_total_cost,
                    "runtime_cost": candidate_runtime_cost,
                    "edge_count": len(edge_path),
                    "path": candidate_path,
                }

    if best_payload is None:
        return []

    if direct_grid_cost != float("inf"):
        if best_payload.get("edge_count", 0) <= 0:
            return []
        if (
            best_payload["total_cost"] > direct_grid_cost + TOPOLOGY_GRID_FALLBACK_MARGIN
            and _path_step_cost(best_payload["path"]) > direct_grid_cost + 1
        ):
            return []
        if (
            best_payload.get("runtime_cost", float("inf")) >= direct_grid_runtime_cost - TOPOLOGY_RUNTIME_EQUAL_MARGIN
            and _path_step_cost(best_payload["path"]) > direct_grid_cost + 1
        ):
            return []

    return best_payload["path"]


def plan_path(
    algorithm: str,
    sx: int,
    sy: int,
    ex: int,
    ey: int,
    grid_cols: int,
    grid_rows: int,
    blocked: set[tuple[int, int]] | None = None,
    *,
    topology: dict | None = None,
    request_priority: int = 0,
    agv_id: int | None = None,
    avoid_edge_keys: set[str] | None = None,
    avoid_node_keys: set[str] | None = None,
):
    if blocked is None:
        blocked = get_navigation_blocked_cells(grid_cols, grid_rows)

    topology_path = _plan_topology_path(
        algorithm,
        sx,
        sy,
        ex,
        ey,
        grid_cols,
        grid_rows,
        blocked,
        topology=topology,
        request_priority=request_priority,
        agv_id=agv_id,
        avoid_edge_keys=avoid_edge_keys,
        avoid_node_keys=avoid_node_keys,
    )
    if topology_path:
        return topology_path

    return _plan_grid_path(algorithm, sx, sy, ex, ey, grid_cols, grid_rows, blocked)
