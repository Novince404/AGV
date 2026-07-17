"""Public map-layout repository facade.

This facade keeps the current warehouse layout access stable while allowing the
actual persistence backend to switch between memory and SQL implementations.
"""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import map_store as _store
else:
    from app.repositories.memory import map_store as _store


def get_layout_state(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
):
    return _store.get_layout_state(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)


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
):
    return _store.set_layout_state(
        blocked_cells,
        valid_cells,
        topology,
        grid_cols,
        grid_rows,
        default_grid_cols,
        default_grid_rows,
        default_blocked_cells,
        default_valid_cells,
    )


__all__ = [
    "get_layout_state",
    "set_layout_state",
]
