from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

from app.core.data_scope import get_current_scope_key
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


_layout_cache_by_scope: dict[str, dict[str, object]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _is_duplicate_column_error(error: Exception) -> bool:
    original = getattr(error, "orig", None)
    args = getattr(original, "args", ()) if original is not None else ()
    if args and args[0] == 1060:
        return True
    message = str(original or error or "")
    return "Duplicate column name" in message


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    ddl_statements: list[str] = []
    if "map_layout" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("map_layout")}
        if "scope_key" not in columns:
            ddl_statements.append("ALTER TABLE map_layout ADD COLUMN scope_key VARCHAR(128)")
    if "map_layout_topology_node" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("map_layout_topology_node")}
        if "capacity" not in columns:
            ddl_statements.append("ALTER TABLE map_layout_topology_node ADD COLUMN capacity INTEGER NOT NULL DEFAULT 1")

    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                try:
                    connection.execute(text(statement))
                except OperationalError as exc:
                    if _is_duplicate_column_error(exc):
                        continue
                    raise


def _query_layout(scope_key: str):
    return (
        select(MapLayoutEntity)
        .options(
            selectinload(MapLayoutEntity.blocked_cells),
            selectinload(MapLayoutEntity.valid_cells),
            selectinload(MapLayoutEntity.topology_nodes),
            selectinload(MapLayoutEntity.topology_edges),
        )
        .where(MapLayoutEntity.scope_key == scope_key)
        .order_by(MapLayoutEntity.id.desc())
    )


def _legacy_layout_query():
    return (
        select(MapLayoutEntity)
        .options(
            selectinload(MapLayoutEntity.blocked_cells),
            selectinload(MapLayoutEntity.valid_cells),
            selectinload(MapLayoutEntity.topology_nodes),
            selectinload(MapLayoutEntity.topology_edges),
        )
        .where((MapLayoutEntity.scope_key.is_(None)) | (MapLayoutEntity.scope_key == ""))
        .order_by(MapLayoutEntity.id.desc())
    )


def _first_layout(session, scope_key: str) -> MapLayoutEntity | None:
    return session.execute(_query_layout(scope_key)).scalars().first()


def _first_legacy_layout(session) -> MapLayoutEntity | None:
    return session.execute(_legacy_layout_query()).scalars().first()


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


def _migrate_legacy_layout(scope_key: str) -> None:
    with get_db_session() as session:
        scoped = _first_layout(session, scope_key)
        if scoped is not None:
            return
        legacy = _first_legacy_layout(session)
        if legacy is None:
            return
        legacy.scope_key = scope_key
        session.commit()


def _persist_layout_snapshot(layout_state: dict[str, object]) -> None:
    scope_key = _current_scope()
    with get_db_session() as session:
        entity = _first_layout(session, scope_key)
        if entity is None:
            entity = MapLayoutEntity(scene_key="default", scope_key=scope_key)

        entity.scope_key = scope_key
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
    scope_key: str,
) -> None:
    with get_db_session() as session:
        entity = _first_layout(session, scope_key)
        if entity is not None:
            return

        seeded = MapLayoutEntity(
            scene_key="default",
            scope_key=scope_key,
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


def _load_cache(scope_key: str) -> None:
    with get_db_session() as session:
        entity = _first_layout(session, scope_key)
        if entity is None:
            raise RuntimeError(f"map layout not found for scope {scope_key!r}")
    _layout_cache_by_scope[scope_key] = _build_layout_state(entity)


def _ensure_loaded(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    _ensure_schema()
    _migrate_legacy_layout(scope_key)
    _seed_defaults_if_empty(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells, scope_key)
    _load_cache(scope_key)
    _loaded_scopes.add(scope_key)


def get_layout_state(
    default_grid_cols: int,
    default_grid_rows: int,
    default_blocked_cells: set[tuple[int, int]],
    default_valid_cells: set[tuple[int, int]],
) -> dict[str, object]:
    _ensure_loaded(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    cache = _layout_cache_by_scope[_current_scope()]
    return {
        "grid_cols": cache["grid_cols"],
        "grid_rows": cache["grid_rows"],
        "blocked_cells": set(cache["blocked_cells"]),
        "valid_cells": set(cache["valid_cells"]),
        "topology": _clone_topology(cache.get("topology")),
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
    scope_key = _current_scope()
    _ensure_loaded(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
    _layout_cache_by_scope[scope_key] = {
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "blocked_cells": set(blocked_cells),
        "valid_cells": set(valid_cells),
        "topology": _clone_topology(topology),
    }
    _persist_layout_snapshot(_layout_cache_by_scope[scope_key])
    return get_layout_state(default_grid_cols, default_grid_rows, default_blocked_cells, default_valid_cells)
