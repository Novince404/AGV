from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.map_profile import MapProfile, MapProfileCell
from app.models.map_topology import MapTopology, MapTopologyEdge, MapTopologyNode
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import (
    MapProfileCellEntity,
    MapProfileEntity,
    MapProfileTopologyEdgeEntity,
    MapProfileTopologyNodeEntity,
    MapProfileValidCellEntity,
)


map_profiles: list[MapProfile] = []
_loaded = False


def _bind_profile(profile: MapProfile) -> MapProfile:
    profile.bind_on_change(lambda profile_key=profile.key: _persist_cached_profile(profile_key))
    return profile


def _query_profiles():
    return select(MapProfileEntity).options(
        selectinload(MapProfileEntity.blocked_cells),
        selectinload(MapProfileEntity.valid_cells),
        selectinload(MapProfileEntity.topology_nodes),
        selectinload(MapProfileEntity.topology_edges),
    ).order_by(MapProfileEntity.id)


def _entity_to_topology(entity: MapProfileEntity) -> MapTopology | None:
    nodes = [
        MapTopologyNode(
            key=str(node.node_key),
            x=int(node.x),
            y=int(node.y),
            label=node.label,
            node_type=str(node.node_type or "waypoint"),
        )
        for node in entity.topology_nodes
    ]
    edges = [
        MapTopologyEdge(
            key=str(edge.edge_key),
            source=str(edge.source_key),
            target=str(edge.target_key),
            direction=str(edge.direction or "bidirectional"),
            lane_type=str(edge.lane_type or "main"),
            weight=float(edge.weight or 1.0),
            speed_multiplier=float(edge.speed_multiplier or 1.0),
        )
        for edge in entity.topology_edges
    ]
    if not nodes and not edges:
        return None
    return MapTopology(
        topology_version=1,
        nodes=nodes,
        edges=edges,
        stations=[node.key for node in nodes if node.node_type == "station"],
        parking_nodes=[node.key for node in nodes if node.node_type == "parking"],
        charge_nodes=[node.key for node in nodes if node.node_type == "charge"],
    )


def _entity_to_model(entity: MapProfileEntity) -> MapProfile:
    cells = [MapProfileCell(x=int(cell.x), y=int(cell.y)) for cell in entity.blocked_cells]
    valid_cells = [MapProfileCell(x=int(cell.x), y=int(cell.y)) for cell in entity.valid_cells]
    return MapProfile(
        key=entity.id,
        custom_name=entity.custom_name,
        description=entity.description,
        grid_cols=int(entity.grid_cols),
        grid_rows=int(entity.grid_rows),
        valid_cells=valid_cells,
        blocked_cells=cells,
        topology=_entity_to_topology(entity),
        custom=entity.custom,
    )


def _model_to_entity(profile: MapProfile, entity: MapProfileEntity | None = None) -> MapProfileEntity:
    entity = entity or MapProfileEntity(id=profile.key)
    entity.custom_name = profile.custom_name
    entity.description = profile.description
    entity.grid_cols = int(profile.grid_cols)
    entity.grid_rows = int(profile.grid_rows)
    entity.custom = profile.custom
    entity.valid_cells = [
        MapProfileValidCellEntity(x=int(cell.x), y=int(cell.y))
        for cell in profile.valid_cells
    ]
    entity.blocked_cells = [
        MapProfileCellEntity(x=int(cell.x), y=int(cell.y))
        for cell in profile.blocked_cells
    ]
    topology = profile.topology
    entity.topology_nodes = [
        MapProfileTopologyNodeEntity(
            node_key=str(node.key),
            x=int(node.x),
            y=int(node.y),
            label=node.label,
            node_type=str(node.node_type or "waypoint"),
        )
        for node in (topology.nodes if topology is not None else [])
    ]
    entity.topology_edges = [
        MapProfileTopologyEdgeEntity(
            edge_key=str(edge.key),
            source_key=str(edge.source),
            target_key=str(edge.target),
            direction=str(edge.direction or "bidirectional"),
            lane_type=str(edge.lane_type or "main"),
            weight=float(edge.weight or 1.0),
            speed_multiplier=float(edge.speed_multiplier or 1.0),
        )
        for edge in (topology.edges if topology is not None else [])
    ]
    return entity


def _persist_cached_profile(profile_key: str) -> None:
    profile = next((item for item in map_profiles if item.key == profile_key), None)
    if profile is None:
        return
    with get_db_session() as session:
        entity = session.get(MapProfileEntity, profile.key)
        session.add(_model_to_entity(profile, entity))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(_query_profiles()).scalars().all()
    map_profiles[:] = [_bind_profile(_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _load_cache()
    _loaded = True


def list_map_profiles() -> list[MapProfile]:
    _ensure_loaded()
    return map_profiles


def get_map_profile_by_key(profile_key: str) -> MapProfile | None:
    _ensure_loaded()
    return next((profile for profile in map_profiles if profile.key == profile_key), None)


def upsert_map_profile(profile: MapProfile) -> MapProfile:
    _ensure_loaded()
    existing = get_map_profile_by_key(profile.key)
    bound = _bind_profile(profile)
    if existing is None:
        map_profiles.append(bound)
    else:
        map_profiles[map_profiles.index(existing)] = bound
    _persist_cached_profile(bound.key)
    return bound


def remove_map_profile(profile_key: str) -> None:
    _ensure_loaded()
    existing = get_map_profile_by_key(profile_key)
    if existing is None:
        return
    map_profiles.remove(existing)
    with get_db_session() as session:
        entity = session.get(MapProfileEntity, profile_key)
        if entity is not None:
            session.delete(entity)
            session.commit()
