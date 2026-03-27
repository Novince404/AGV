from __future__ import annotations

_current_layout: dict[str, object] | None = None


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
    }


def set_layout_state(
    blocked_cells: set[tuple[int, int]],
    valid_cells: set[tuple[int, int]],
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
    }
    return get_layout_state(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
