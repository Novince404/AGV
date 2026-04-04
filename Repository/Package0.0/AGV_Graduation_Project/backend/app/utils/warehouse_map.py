from __future__ import annotations

from app.repositories.map_repository import get_layout_state as get_runtime_layout_state
from app.repositories.map_repository import set_layout_state as persist_runtime_layout_state


DEFAULT_GRID_COLS = 10
DEFAULT_GRID_ROWS = 8
DEFAULT_MAP_PROFILE_KEY = "warehouse_demo_10x8"
TOPOLOGY_NODE_DEFAULT_CAPACITY = {
    "waypoint": 1,
    "station": 2,
    "parking": 4,
    "charge": 4,
}

# Fixed shelf layout for the current warehouse demo map.
DEFAULT_BLOCKED_CELLS = {
    (3, 0),
    (3, 1),
    (3, 2),
    (3, 4),
    (3, 5),
    (3, 6),
    (3, 7),
    (6, 0),
    (6, 1),
    (6, 3),
    (6, 4),
    (6, 5),
    (6, 6),
    (6, 7),
}

DEFAULT_MAP_PRESETS = {
    "default_shelves": {
        "name": {
            "zh": "默认货架",
            "ja": "標準棚配置",
            "en": "Default Shelves",
        },
        "description": {
            "zh": "两列货架，中间保留关键通道，适合基础算法对比。",
            "ja": "2 列の棚と通路を確保した標準配置で、基本アルゴリズム比較に適しています。",
            "en": "Two shelf columns with corridor gaps for baseline algorithm comparison.",
        },
        "cells": DEFAULT_BLOCKED_CELLS,
    },
    "central_block": {
        "name": {
            "zh": "中心库区",
            "ja": "中央ブロック",
            "en": "Central Block",
        },
        "description": {
            "zh": "中部形成连续障碍，适合验证绕行能力。",
            "ja": "中央に連続障害を配置し、迂回性能の検証に適しています。",
            "en": "A central obstacle cluster for testing detour capability.",
        },
        "cells": {
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (5, 1),
            (5, 2),
            (5, 3),
            (5, 4),
            (5, 5),
        },
    },
    "zigzag_aisles": {
        "name": {
            "zh": "曲折通道",
            "ja": "ジグザグ通路",
            "en": "Zigzag Aisles",
        },
        "description": {
            "zh": "形成交错通道，适合测试多拐点路径规划。",
            "ja": "交差する通路を形成し、多折れ経路の計画検証に適しています。",
            "en": "Interleaved aisles suited for multi-turn path planning tests.",
        },
        "cells": {
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 4),
            (2, 5),
            (2, 6),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 5),
            (4, 6),
            (4, 7),
            (7, 0),
            (7, 1),
            (7, 3),
            (7, 4),
            (7, 5),
            (7, 7),
        },
    },
}

DEFAULT_MAP_PROFILES = {
    DEFAULT_MAP_PROFILE_KEY: {
        "name": {
            "zh": "标准演示仓库",
            "ja": "標準デモ倉庫",
            "en": "Standard Demo Warehouse",
        },
        "description": {
            "zh": "当前毕业设计默认使用的 10 x 8 演示地图方案，后续模块 4 将在此基础上扩展动态地图尺寸。",
            "ja": "現行の卒業設計で既定利用している 10 x 8 のデモ用マップ構成です。後続のモジュール 4 で動的サイズ拡張を行います。",
            "en": "The default 10 x 8 demo warehouse profile used by the current project. Dynamic map sizing will build on top of this in module 4.",
        },
        "grid_cols": DEFAULT_GRID_COLS,
        "grid_rows": DEFAULT_GRID_ROWS,
        "cells": DEFAULT_BLOCKED_CELLS,
        "custom": False,
    },
    "warehouse_expanded_12x9": {
        "name": {
            "zh": "扩展示范仓库",
            "ja": "拡張デモ倉庫",
            "en": "Expanded Demo Warehouse",
        },
        "description": {
            "zh": "在默认演示仓库基础上扩展到 12 x 9，并增加一组货架列，便于验证尺寸升级后的路线规划。",
            "ja": "標準デモ倉庫を 12 x 9 に拡張し、棚列を追加した構成で、拡張サイズ後の経路計画を検証しやすくしています。",
            "en": "Expands the demo warehouse to 12 x 9 with an extra shelf lane for larger-map path planning checks.",
        },
        "grid_cols": 12,
        "grid_rows": 9,
        "cells": {
            (3, 0), (3, 1), (3, 2), (3, 4), (3, 5), (3, 6), (3, 7), (3, 8),
            (7, 0), (7, 1), (7, 2), (7, 4), (7, 5), (7, 6), (7, 7), (7, 8),
        },
        "custom": False,
    },
    "warehouse_large_14x10": {
        "name": {
            "zh": "大尺寸演示仓库",
            "ja": "大型デモ倉庫",
            "en": "Large Demo Warehouse",
        },
        "description": {
            "zh": "扩展到 14 x 10 的大尺寸地图方案，用于演示地图 profile 切换与更大范围调度。",
            "ja": "14 x 10 の大型マップ構成で、マップ profile 切替と広い範囲の調度を演示します。",
            "en": "A 14 x 10 large-map profile for demonstrating profile switching and wider dispatch coverage.",
        },
        "grid_cols": 14,
        "grid_rows": 10,
        "cells": {
            (4, 0), (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9),
            (9, 0), (9, 1), (9, 2), (9, 4), (9, 5), (9, 6), (9, 7), (9, 8), (9, 9),
        },
        "custom": False,
    },
}

_TOPOLOGY_KEEP = object()


def _build_full_grid_cells(grid_cols: int, grid_rows: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(int(grid_cols))
        for y in range(int(grid_rows))
    }


def _normalize_cells(cells, grid_cols: int, grid_rows: int) -> set[tuple[int, int]]:
    normalized = set()
    for cell in cells:
        x, y = cell
        if 0 <= x < grid_cols and 0 <= y < grid_rows:
            normalized.add((int(x), int(y)))
    return normalized


def _normalize_valid_cells(
    cells,
    grid_cols: int,
    grid_rows: int,
) -> set[tuple[int, int]]:
    if cells is None:
        return _build_full_grid_cells(grid_cols, grid_rows)
    normalized = _normalize_cells(cells, grid_cols, grid_rows)
    return normalized or _build_full_grid_cells(grid_cols, grid_rows)


def create_empty_map_topology() -> dict[str, object]:
    return {
        "topology_version": 1,
        "nodes": [],
        "edges": [],
        "stations": [],
        "parking_nodes": [],
        "charge_nodes": [],
    }


def get_topology_node_default_capacity(node_type: str) -> int:
    normalized = str(node_type or "waypoint").strip().lower()
    return max(int(TOPOLOGY_NODE_DEFAULT_CAPACITY.get(normalized, 1)), 1)


def normalize_topology_node_capacity(node_type: str, capacity) -> int:
    default_capacity = get_topology_node_default_capacity(node_type)
    try:
        normalized = int(capacity)
    except (TypeError, ValueError):
        return default_capacity
    return max(normalized, 1)


def _coerce_topology_mapping(item) -> dict:
    if item is None:
        return {}
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if isinstance(item, dict):
        return item
    return {}


def _normalize_topology_key(raw_value, fallback: str) -> str:
    value = str(raw_value or "").strip()
    return value or fallback


def normalize_map_topology_payload(
    topology,
    grid_cols: int,
    grid_rows: int,
    valid_cells: set[tuple[int, int]] | list[tuple[int, int]] | None = None,
) -> dict[str, object]:
    normalized_valid_cells = _normalize_valid_cells(valid_cells, grid_cols, grid_rows)
    payload = _coerce_topology_mapping(topology)
    special_station_keys = {str(item).strip() for item in payload.get("stations", []) if str(item).strip()}
    special_parking_keys = {str(item).strip() for item in payload.get("parking_nodes", []) if str(item).strip()}
    special_charge_keys = {str(item).strip() for item in payload.get("charge_nodes", []) if str(item).strip()}

    nodes = []
    seen_node_keys: set[str] = set()
    seen_positions: set[tuple[int, int]] = set()
    for index, raw_node in enumerate(payload.get("nodes", []) or []):
        item = _coerce_topology_mapping(raw_node)
        try:
            x = int(item.get("x"))
            y = int(item.get("y"))
        except (TypeError, ValueError):
            continue
        if not (0 <= x < int(grid_cols) and 0 <= y < int(grid_rows)):
            continue
        if (x, y) not in normalized_valid_cells:
            continue
        node_key = _normalize_topology_key(item.get("key"), f"node_{x}_{y}_{index + 1}")
        if node_key in seen_node_keys or (x, y) in seen_positions:
            continue
        node_type = str(item.get("node_type") or "waypoint").strip().lower()
        if node_key in special_charge_keys:
            node_type = "charge"
        elif node_key in special_parking_keys:
            node_type = "parking"
        elif node_key in special_station_keys:
            node_type = "station"
        if node_type not in {"waypoint", "station", "parking", "charge"}:
            node_type = "waypoint"
        label = str(item.get("label") or "").strip() or None
        nodes.append(
            {
                "key": node_key,
                "x": x,
                "y": y,
                "label": label,
                "node_type": node_type,
                "capacity": normalize_topology_node_capacity(node_type, item.get("capacity")),
            }
        )
        seen_node_keys.add(node_key)
        seen_positions.add((x, y))

    node_keys = {node["key"] for node in nodes}
    edges = []
    seen_edge_keys: set[str] = set()
    for index, raw_edge in enumerate(payload.get("edges", []) or []):
        item = _coerce_topology_mapping(raw_edge)
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if not source or not target or source == target:
            continue
        if source not in node_keys or target not in node_keys:
            continue
        edge_key = _normalize_topology_key(item.get("key"), f"edge_{source}_{target}_{index + 1}")
        if edge_key in seen_edge_keys:
            continue
        direction = str(item.get("direction") or "bidirectional").strip().lower()
        if direction not in {"bidirectional", "forward", "reverse"}:
            direction = "bidirectional"
        lane_type = str(item.get("lane_type") or "main").strip().lower()
        if lane_type not in {"main", "branch", "service"}:
            lane_type = "main"
        try:
            weight = float(item.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        try:
            speed_multiplier = float(item.get("speed_multiplier", 1.0))
        except (TypeError, ValueError):
            speed_multiplier = 1.0
        edges.append(
            {
                "key": edge_key,
                "source": source,
                "target": target,
                "direction": direction,
                "lane_type": lane_type,
                "weight": weight if weight > 0 else 1.0,
                "speed_multiplier": speed_multiplier if speed_multiplier > 0 else 1.0,
            }
        )
        seen_edge_keys.add(edge_key)

    stations = [node["key"] for node in nodes if node["node_type"] == "station"]
    parking_nodes = [node["key"] for node in nodes if node["node_type"] == "parking"]
    charge_nodes = [node["key"] for node in nodes if node["node_type"] == "charge"]
    return {
        "topology_version": 1,
        "nodes": nodes,
        "edges": edges,
        "stations": stations,
        "parking_nodes": parking_nodes,
        "charge_nodes": charge_nodes,
    }


def build_map_topology_summary(
    topology,
    grid_cols: int | None = None,
    grid_rows: int | None = None,
    valid_cells: set[tuple[int, int]] | list[tuple[int, int]] | None = None,
) -> dict[str, object]:
    normalized = (
        normalize_map_topology_payload(topology, int(grid_cols), int(grid_rows), valid_cells)
        if grid_cols is not None and grid_rows is not None
        else _coerce_topology_mapping(topology) or create_empty_map_topology()
    )
    node_count = len(normalized.get("nodes", []))
    edge_count = len(normalized.get("edges", []))
    station_count = len(normalized.get("stations", []))
    parking_count = len(normalized.get("parking_nodes", []))
    charge_count = len(normalized.get("charge_nodes", []))
    return {
        "enabled": bool(node_count or edge_count),
        "node_count": node_count,
        "edge_count": edge_count,
        "station_count": station_count,
        "parking_count": parking_count,
        "charge_count": charge_count,
    }


def build_map_topology_signature(
    topology,
    grid_cols: int,
    grid_rows: int,
    valid_cells: set[tuple[int, int]] | list[tuple[int, int]] | None = None,
) -> tuple:
    normalized = normalize_map_topology_payload(topology, grid_cols, grid_rows, valid_cells)
    return (
        tuple(
            sorted(
                (
                    str(node["key"]),
                    int(node["x"]),
                    int(node["y"]),
                    str(node.get("label") or ""),
                    str(node.get("node_type") or "waypoint"),
                    int(node.get("capacity") or get_topology_node_default_capacity(node.get("node_type") or "waypoint")),
                )
                for node in normalized["nodes"]
            )
        ),
        tuple(
            sorted(
                (
                    str(edge["key"]),
                    str(edge["source"]),
                    str(edge["target"]),
                    str(edge.get("direction") or "bidirectional"),
                    str(edge.get("lane_type") or "main"),
                    float(edge.get("weight") or 1.0),
                    float(edge.get("speed_multiplier") or 1.0),
                )
                for edge in normalized["edges"]
            )
        ),
    )


def get_default_blocked_cells(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> set[tuple[int, int]]:
    return _normalize_cells(DEFAULT_BLOCKED_CELLS, grid_cols, grid_rows)


def get_default_valid_cells(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> set[tuple[int, int]]:
    return _build_full_grid_cells(grid_cols, grid_rows)


def get_map_layout_state() -> dict[str, object]:
    state = get_runtime_layout_state(
        DEFAULT_GRID_COLS,
        DEFAULT_GRID_ROWS,
        get_default_blocked_cells(),
        get_default_valid_cells(),
    )
    grid_cols = int(state["grid_cols"])
    grid_rows = int(state["grid_rows"])
    valid_cells = _normalize_valid_cells(state.get("valid_cells"), grid_cols, grid_rows)
    return {
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "blocked_cells": _normalize_cells(state["blocked_cells"], grid_cols, grid_rows),
        "valid_cells": valid_cells,
        "topology": normalize_map_topology_payload(state.get("topology"), grid_cols, grid_rows, valid_cells),
    }


def get_current_grid_size() -> tuple[int, int]:
    state = get_map_layout_state()
    return int(state["grid_cols"]), int(state["grid_rows"])


def get_valid_cells(grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS) -> set[tuple[int, int]]:
    state = get_map_layout_state()
    return _normalize_valid_cells(state.get("valid_cells"), grid_cols, grid_rows)


def get_blocked_cells(grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS) -> set[tuple[int, int]]:
    state = get_map_layout_state()
    valid_cells = _normalize_valid_cells(state.get("valid_cells"), grid_cols, grid_rows)
    blocked_cells = _normalize_cells(state["blocked_cells"], grid_cols, grid_rows)
    return blocked_cells & valid_cells


def get_navigation_blocked_cells(
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    valid_cells = get_valid_cells(grid_cols, grid_rows)
    blocked_cells = get_blocked_cells(grid_cols, grid_rows)
    return blocked_cells | (_build_full_grid_cells(grid_cols, grid_rows) - valid_cells)


def set_layout_cells(
    blocked_cells: set[tuple[int, int]] | list[tuple[int, int]],
    valid_cells: set[tuple[int, int]] | list[tuple[int, int]] | None,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
    topology=_TOPOLOGY_KEEP,
) -> dict[str, object]:
    normalized_valid = _normalize_valid_cells(valid_cells, grid_cols, grid_rows)
    normalized_blocked = _normalize_cells(blocked_cells, grid_cols, grid_rows) & normalized_valid
    current_state = get_map_layout_state()
    topology_source = current_state.get("topology") if topology is _TOPOLOGY_KEEP else topology
    normalized_topology = normalize_map_topology_payload(topology_source, grid_cols, grid_rows, normalized_valid)
    updated = persist_runtime_layout_state(
        normalized_blocked,
        normalized_valid,
        normalized_topology,
        grid_cols,
        grid_rows,
        DEFAULT_GRID_COLS,
        DEFAULT_GRID_ROWS,
        get_default_blocked_cells(),
        get_default_valid_cells(),
    )
    return {
        "grid_cols": int(updated["grid_cols"]),
        "grid_rows": int(updated["grid_rows"]),
        "blocked_cells": _normalize_cells(updated["blocked_cells"], grid_cols, grid_rows),
        "valid_cells": _normalize_valid_cells(updated.get("valid_cells"), grid_cols, grid_rows),
        "topology": normalize_map_topology_payload(updated.get("topology"), grid_cols, grid_rows, normalized_valid),
    }


def set_blocked_cells(
    cells: set[tuple[int, int]] | list[tuple[int, int]],
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    return set_layout_cells(cells, get_valid_cells(grid_cols, grid_rows), grid_cols, grid_rows)["blocked_cells"]


def reset_blocked_cells(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> set[tuple[int, int]]:
    return set_blocked_cells(get_default_blocked_cells(grid_cols, grid_rows), grid_cols, grid_rows)


def get_map_preset_cells(
    preset_key: str,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    preset = DEFAULT_MAP_PRESETS.get(preset_key)
    if not preset:
        raise KeyError(preset_key)
    return _normalize_cells(preset["cells"], grid_cols, grid_rows)


def get_map_preset_valid_cells(
    preset_key: str,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    preset = DEFAULT_MAP_PRESETS.get(preset_key)
    if not preset:
        raise KeyError(preset_key)
    return _normalize_valid_cells(preset.get("valid_cells"), grid_cols, grid_rows)


def apply_map_preset(
    preset_key: str,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> set[tuple[int, int]]:
    return set_blocked_cells(get_map_preset_cells(preset_key, grid_cols, grid_rows), grid_cols, grid_rows)


def get_blocked_cell_payload(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> list[dict[str, int]]:
    return [{"x": x, "y": y} for x, y in sorted(get_blocked_cells(grid_cols, grid_rows))]


def get_valid_cell_payload(
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
) -> list[dict[str, int]]:
    return [{"x": x, "y": y} for x, y in sorted(get_valid_cells(grid_cols, grid_rows))]


def build_map_preset_payload(
    key: str,
    name,
    description,
    cells: set[tuple[int, int]],
    custom: bool,
    deletable: bool,
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
    profile_key: str | None = DEFAULT_MAP_PROFILE_KEY,
    valid_cells: set[tuple[int, int]] | None = None,
) -> dict:
    normalized_valid_cells = _normalize_valid_cells(valid_cells, grid_cols, grid_rows)
    normalized_cells = _normalize_cells(cells, grid_cols, grid_rows) & normalized_valid_cells
    return {
        "key": key,
        "name": name,
        "description": description,
        "blocked_count": len(normalized_cells),
        "valid_count": len(normalized_valid_cells),
        "blocked_cells": [{"x": x, "y": y} for x, y in sorted(normalized_cells)],
        "valid_cells": [{"x": x, "y": y} for x, y in sorted(normalized_valid_cells)],
        "is_irregular": len(normalized_valid_cells) != int(grid_cols) * int(grid_rows),
        "custom": custom,
        "deletable": deletable,
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "profile_key": profile_key,
    }


def build_map_profile_payload(
    key: str,
    name,
    description,
    grid_cols: int,
    grid_rows: int,
    *,
    custom: bool,
    editable: bool,
    deletable: bool = False,
    valid_cells: set[tuple[int, int]] | None = None,
    topology=None,
) -> dict:
    normalized_valid_cells = _normalize_valid_cells(valid_cells, grid_cols, grid_rows)
    normalized_topology = normalize_map_topology_payload(topology, grid_cols, grid_rows, normalized_valid_cells)
    topology_summary = build_map_topology_summary(normalized_topology)
    return {
        "key": key,
        "name": name,
        "description": description,
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "valid_count": len(normalized_valid_cells),
        "valid_cells": [{"x": x, "y": y} for x, y in sorted(normalized_valid_cells)],
        "is_irregular": len(normalized_valid_cells) != int(grid_cols) * int(grid_rows),
        "custom": custom,
        "editable": editable,
        "deletable": deletable,
        "topology": normalized_topology,
        "topology_summary": topology_summary,
        "has_topology": bool(topology_summary["enabled"]),
    }


def get_map_profile_definition(profile_key: str) -> dict | None:
    profile = DEFAULT_MAP_PROFILES.get(profile_key)
    if profile is None:
        return None
    grid_cols = int(profile["grid_cols"])
    grid_rows = int(profile["grid_rows"])
    return {
        "key": profile_key,
        "name": profile["name"],
        "description": profile["description"],
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "cells": _normalize_cells(profile.get("cells", set()), grid_cols, grid_rows),
        "valid_cells": _normalize_valid_cells(profile.get("valid_cells"), grid_cols, grid_rows),
        "topology": normalize_map_topology_payload(
            profile.get("topology"),
            grid_cols,
            grid_rows,
            _normalize_valid_cells(profile.get("valid_cells"), grid_cols, grid_rows),
        ),
        "custom": bool(profile.get("custom", False)),
    }


def get_map_profile_cells(profile_key: str) -> set[tuple[int, int]]:
    profile = get_map_profile_definition(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    return set(profile["cells"])


def get_map_profile_valid_cells(profile_key: str) -> set[tuple[int, int]]:
    profile = get_map_profile_definition(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    return set(profile["valid_cells"])


def get_map_presets_payload(
    grid_cols: int = DEFAULT_GRID_COLS, grid_rows: int = DEFAULT_GRID_ROWS
) -> list[dict]:
    current_profile_key = get_current_map_profile_payload(grid_cols, grid_rows)["key"]
    payload = []
    for key, preset in DEFAULT_MAP_PRESETS.items():
        cells = _normalize_cells(preset["cells"], grid_cols, grid_rows)
        valid_cells = _normalize_valid_cells(preset.get("valid_cells"), grid_cols, grid_rows)
        payload.append(
            build_map_preset_payload(
                key=key,
                name=preset["name"],
                description=preset["description"],
                cells=cells,
                valid_cells=valid_cells,
                custom=False,
                deletable=False,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
                profile_key=current_profile_key,
            )
        )
    return payload


def get_map_profiles_payload() -> list[dict]:
    payload = []
    for key, profile in DEFAULT_MAP_PROFILES.items():
        payload.append(
            build_map_profile_payload(
                key=key,
                name=profile["name"],
                description=profile["description"],
                grid_cols=int(profile["grid_cols"]),
                grid_rows=int(profile["grid_rows"]),
                valid_cells=_normalize_valid_cells(profile.get("valid_cells"), int(profile["grid_cols"]), int(profile["grid_rows"])),
                topology=profile.get("topology"),
                custom=bool(profile.get("custom", False)),
                editable=False,
                deletable=False,
            )
        )
    return payload


def get_current_map_profile_payload(
    grid_cols: int = DEFAULT_GRID_COLS,
    grid_rows: int = DEFAULT_GRID_ROWS,
    topology=None,
) -> dict:
    for key, profile in DEFAULT_MAP_PROFILES.items():
        if int(profile["grid_cols"]) == int(grid_cols) and int(profile["grid_rows"]) == int(grid_rows):
            return build_map_profile_payload(
                key=key,
                name=profile["name"],
                description=profile["description"],
                grid_cols=grid_cols,
                grid_rows=grid_rows,
                valid_cells=_normalize_valid_cells(profile.get("valid_cells"), grid_cols, grid_rows),
                topology=profile.get("topology"),
                custom=bool(profile.get("custom", False)),
                editable=False,
                deletable=False,
            )

    return build_map_profile_payload(
        key=f"runtime_{int(grid_cols)}x{int(grid_rows)}",
        name={
            "zh": "运行时地图方案",
            "ja": "実行時マップ構成",
            "en": "Runtime Map Profile",
        },
        description={
            "zh": "当前运行中的地图尺寸尚未匹配到内置方案，后续可作为自定义地图方案的入口。",
            "ja": "現在の実行時マップサイズは組み込み profile に一致しておらず、将来のカスタムマップ構成の入口になります。",
            "en": "The current runtime map size does not match a built-in profile and can later become the entry point for custom map schemes.",
        },
        grid_cols=grid_cols,
        grid_rows=grid_rows,
        valid_cells=get_valid_cells(grid_cols, grid_rows),
        topology=topology,
        custom=True,
        editable=False,
        deletable=False,
    )
