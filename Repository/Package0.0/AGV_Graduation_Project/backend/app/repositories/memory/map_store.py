from __future__ import annotations

_current_layout: dict[str, object] | None = None


def _clone_topology(topology: dict[str, object] | None) -> dict[str, object]:
    topology = topology or {}
    return {
        "topology_version": int(topology.get("topology_version", 1)),
        "nodes": [dict(node) for node in topology.get("nodes", [])],
        "edges": [dict(edge) for edge in topology.get("edges", [])],
        "stations": list(topology.get("stations", [])),
        "parking_nodes": list(topology.get("parking_nodes", [])),
        "charge_nodes": list(topology.get("charge_nodes", [])),
    }


def _ensure_layout(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> None:
    global _current_layout
    if _current_layout is not None:
        return

    _current_layout = {
        "grid_cols": int(default_grid_cols),
        "grid_rows": int(default_grid_rows),
        "blocked_cells": set(default_blocked_cells),
        "valid_cells": set(default_valid_cells),
        "topology": _clone_topology(None),
    }


def get_layout_state(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> dict[str, object]:
    _ensure_layout(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    assert _current_layout is not None
    return {
        "grid_cols": _current_layout["grid_cols"],
        "grid_rows": _current_layout["grid_rows"],
        "blocked_cells": set(_current_layout["blocked_cells"]),
        "valid_cells": set(_current_layout["valid_cells"]),
        "topology": _clone_topology(_current_layout.get("topology")),
    }


def set_layout_state(
    blocked_cells: set[tuple[int, int]],
    valid_cells: set[tuple[int, int]],
    topology: dict[str, object] | None,
    grid_cols: int,
    grid_rows: int,
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> dict[str, object]:
    global _current_layout
    _ensure_layout(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    _current_layout = {
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "blocked_cells": set(blocked_cells),
        "valid_cells": set(valid_cells),
        "topology": _clone_topology(topology),
    }
    return get_layout_state(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
