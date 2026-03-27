from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import MapBlockedCellEntity, MapLayoutEntity, MapValidCellEntity


_LAYOUT_ID = 1
_layout_cache: dict[str, object] | None = None
_loaded = False


def _query_layout():
    return (
        select(MapLayoutEntity)
        .options(selectinload(MapLayoutEntity.blocked_cells), selectinload(MapLayoutEntity.valid_cells))
        .where(MapLayoutEntity.id == _LAYOUT_ID)
    )


def _build_layout_state(entity: MapLayoutEntity) -> dict[str, object]:
    return {
        "grid_cols": int(entity.grid_cols),
        "grid_rows": int(entity.grid_rows),
        "blocked_cells": {(int(cell.x), int(cell.y)) for cell in entity.blocked_cells},
        "valid_cells": {(int(cell.x), int(cell.y)) for cell in entity.valid_cells},
    }


def _persist_layout_snapshot(layout_state: dict[str, object]) -> None:
    with get_db_session() as session:
        entity = session.execute(_query_layout()).scalar_one_or_none()
        if entity is None:
            entity = MapLayoutEntity(id=_LAYOUT_ID, scene_key="default")

        entity.grid_cols = int(layout_state["grid_cols"])
        entity.grid_rows = int(layout_state["grid_rows"])
        entity.blocked_cells = [
            MapBlockedCellEntity(x=x, y=y)
            for x, y in sorted(layout_state["blocked_cells"])
        ]
        entity.valid_cells = [
            MapValidCellEntity(x=x, y=y)
            for x, y in sorted(layout_state["valid_cells"])
        ]
        session.add(entity)
        session.commit()


def _seed_defaults_if_empty(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> None:
    with get_db_session() as session:
        entity = session.execute(_query_layout()).scalar_one_or_none()
        if entity is not None:
            return

        seeded = MapLayoutEntity(
            id=_LAYOUT_ID,
            scene_key="default",
            grid_cols=int(default_grid_cols),
            grid_rows=int(default_grid_rows),
            blocked_cells=[
                MapBlockedCellEntity(x=x, y=y)
                for x, y in sorted(default_blocked_cells)
            ],
            valid_cells=[
                MapValidCellEntity(x=x, y=y)
                for x, y in sorted(default_valid_cells)
            ],
        )
        session.add(seeded)
        session.commit()


def _load_cache() -> None:
    global _layout_cache
    with get_db_session() as session:
        entity = session.execute(_query_layout()).scalar_one()
    _layout_cache = _build_layout_state(entity)


def _ensure_loaded(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _seed_defaults_if_empty(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    _load_cache()
    _loaded = True


def get_layout_state(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> dict[str, object]:
    _ensure_loaded(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    assert _layout_cache is not None
    return {
        "grid_cols": _layout_cache["grid_cols"],
        "grid_rows": _layout_cache["grid_rows"],
        "blocked_cells": set(_layout_cache["blocked_cells"]),
        "valid_cells": set(_layout_cache["valid_cells"]),
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
    global _layout_cache
    _ensure_loaded(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    _layout_cache = {
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "blocked_cells": set(blocked_cells),
        "valid_cells": set(valid_cells),
    }
    _persist_layout_snapshot(_layout_cache)
    return get_layout_state(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
