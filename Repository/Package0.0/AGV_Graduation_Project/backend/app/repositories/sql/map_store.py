from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import selectinload

from app.core.database import get_engine
from app.core.database import get_db_session
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import (
    MapBlockedCellEntity,
    MapLayoutEntity,
    MapLayoutTopologyEdgeEntity,
    MapLayoutTopologyNodeEntity,
    MapValidCellEntity,
)


_LAYOUT_ID = 1
_layout_cache: dict[str, object] | None = None
_loaded = False


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    ddl_statements: list[str] = []
    if "map_layout_topology_node" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("map_layout_topology_node")}
        if "capacity" not in columns:
            ddl_statements.append("ALTER TABLE map_layout_topology_node ADD COLUMN capacity INTEGER NOT NULL DEFAULT 1")

    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                connection.execute(text(statement))


def _query_layout():
    return (
        select(MapLayoutEntity)
        .options(
            selectinload(MapLayoutEntity.blocked_cells),
            selectinload(MapLayoutEntity.valid_cells),
            selectinload(MapLayoutEntity.topology_nodes),
            selectinload(MapLayoutEntity.topology_edges),
        )
        .where(MapLayoutEntity.id == _LAYOUT_ID)
    )


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


def _build_topology_state(entity: MapLayoutEntity) -> dict[str, object]:
    nodes = [
        {
            "key": str(node.node_key),
            "x": int(node.x),
            "y": int(node.y),
            "label": node.label,
            "node_type": str(node.node_type or "waypoint"),
            "capacity": int(getattr(node, "capacity", 1) or 1),
        }
        for node in entity.topology_nodes
    ]
    edges = [
        {
            "key": str(edge.edge_key),
            "source": str(edge.source_key),
            "target": str(edge.target_key),
            "direction": str(edge.direction or "bidirectional"),
            "lane_type": str(edge.lane_type or "main"),
            "weight": float(edge.weight or 1.0),
            "speed_multiplier": float(edge.speed_multiplier or 1.0),
        }
        for edge in entity.topology_edges
    ]
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


def _build_layout_state(entity: MapLayoutEntity) -> dict[str, object]:
    return {
        "grid_cols": int(entity.grid_cols),
        "grid_rows": int(entity.grid_rows),
        "blocked_cells": {(int(cell.x), int(cell.y)) for cell in entity.blocked_cells},
        "valid_cells": {(int(cell.x), int(cell.y)) for cell in entity.valid_cells},
        "topology": _build_topology_state(entity),
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
        topology = _clone_topology(layout_state.get("topology"))
        entity.topology_nodes = [
            MapLayoutTopologyNodeEntity(
                node_key=str(node["key"]),
                x=int(node["x"]),
                y=int(node["y"]),
                label=node.get("label"),
                node_type=str(node.get("node_type") or "waypoint"),
                capacity=int(node.get("capacity") or 1),
            )
            for node in topology["nodes"]
        ]
        entity.topology_edges = [
            MapLayoutTopologyEdgeEntity(
                edge_key=str(edge["key"]),
                source_key=str(edge["source"]),
                target_key=str(edge["target"]),
                direction=str(edge.get("direction") or "bidirectional"),
                lane_type=str(edge.get("lane_type") or "main"),
                weight=float(edge.get("weight") or 1.0),
                speed_multiplier=float(edge.get("speed_multiplier") or 1.0),
            )
            for edge in topology["edges"]
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
    _ensure_schema()
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
        "topology": _clone_topology(_layout_cache.get("topology")),
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
    global _layout_cache
    _ensure_loaded(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    _layout_cache = {
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "blocked_cells": set(blocked_cells),
        "valid_cells": set(valid_cells),
        "topology": _clone_topology(topology),
    }
    _persist_layout_snapshot(_layout_cache)
    return get_layout_state(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
