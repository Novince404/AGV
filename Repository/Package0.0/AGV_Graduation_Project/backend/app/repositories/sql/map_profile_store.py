from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import selectinload

from app.core.data_scope import (
    build_scoped_storage_id,
    extract_public_id,
    get_current_scope_key,
    get_scope_storage_prefix,
    is_legacy_unscoped_storage_id,
)
from app.core.database import get_db_session, get_engine
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


map_profiles_by_scope: dict[str, list[MapProfile]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _scope_prefix(scope_key: str | None = None) -> str:
    return get_scope_storage_prefix(scope_key or _current_scope())


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    ddl_statements: list[str] = []
    if "map_profile_topology_node" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("map_profile_topology_node")}
        if "capacity" not in columns:
            ddl_statements.append("ALTER TABLE map_profile_topology_node ADD COLUMN capacity INTEGER NOT NULL DEFAULT 1")

    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                connection.execute(text(statement))


def _bind_profile(profile: MapProfile) -> MapProfile:
    profile.bind_on_change(lambda profile_key=profile.key, scope_key=_current_scope(): _persist_cached_profile(profile_key, scope_key))
    return profile


def _scope_query(scope_key: str):
    return (
        select(MapProfileEntity)
        .options(
            selectinload(MapProfileEntity.blocked_cells),
            selectinload(MapProfileEntity.valid_cells),
            selectinload(MapProfileEntity.topology_nodes),
            selectinload(MapProfileEntity.topology_edges),
        )
        .where(MapProfileEntity.id.like(f"{_scope_prefix(scope_key)}%"))
        .order_by(MapProfileEntity.id)
    )


def _legacy_query():
    return (
        select(MapProfileEntity)
        .options(
            selectinload(MapProfileEntity.blocked_cells),
            selectinload(MapProfileEntity.valid_cells),
            selectinload(MapProfileEntity.topology_nodes),
            selectinload(MapProfileEntity.topology_edges),
        )
        .order_by(MapProfileEntity.id)
    )


def _scope_cache(scope_key: str | None = None) -> list[MapProfile]:
    normalized_scope = str(scope_key or _current_scope())
    return map_profiles_by_scope.setdefault(normalized_scope, [])


def _entity_to_topology(entity: MapProfileEntity) -> MapTopology | None:
    nodes = [
        MapTopologyNode(
            key=str(node.node_key),
            x=int(node.x),
            y=int(node.y),
            label=node.label,
            node_type=str(node.node_type or "waypoint"),
            capacity=int(getattr(node, "capacity", 1) or 1),
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


def _entity_to_model(entity: MapProfileEntity, scope_key: str | None = None) -> MapProfile:
    cells = [MapProfileCell(x=int(cell.x), y=int(cell.y)) for cell in entity.blocked_cells]
    valid_cells = [MapProfileCell(x=int(cell.x), y=int(cell.y)) for cell in entity.valid_cells]
    return MapProfile(
        key=extract_public_id(entity.id, scope_key),
        custom_name=entity.custom_name,
        description=entity.description,
        grid_cols=int(entity.grid_cols),
        grid_rows=int(entity.grid_rows),
        valid_cells=valid_cells,
        blocked_cells=cells,
        topology=_entity_to_topology(entity),
        custom=entity.custom,
    )


def _model_to_entity(profile: MapProfile, entity: MapProfileEntity | None = None, scope_key: str | None = None) -> MapProfileEntity:
    storage_id = build_scoped_storage_id(profile.key, scope_key)
    entity = entity or MapProfileEntity(id=storage_id)
    entity.id = storage_id
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
            profile_id=storage_id,
            node_key=str(node.key),
            x=int(node.x),
            y=int(node.y),
            label=node.label,
            node_type=str(node.node_type or "waypoint"),
            capacity=int(getattr(node, "capacity", 1) or 1),
        )
        for node in (topology.nodes if topology is not None else [])
    ]
    entity.topology_edges = [
        MapProfileTopologyEdgeEntity(
            profile_id=storage_id,
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


def _persist_cached_profile(profile_key: str, scope_key: str | None = None) -> None:
    profile = next((item for item in _scope_cache(scope_key) if item.key == profile_key), None)
    if profile is None:
        return
    scoped_id = build_scoped_storage_id(profile.key, scope_key)
    with get_db_session() as session:
        entity = session.get(MapProfileEntity, scoped_id)
        session.add(_model_to_entity(profile, entity, scope_key))
        session.commit()


def _seed_scope(scope_key: str) -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(MapProfileEntity.id).where(MapProfileEntity.id.like(f"{_scope_prefix(scope_key)}%")).limit(1)).first() is not None
        if has_rows:
            return

        legacy_entities = [
            entity
            for entity in session.execute(_legacy_query()).scalars().all()
            if is_legacy_unscoped_storage_id(entity.id)
        ]
        if not legacy_entities:
            return
        for entity in legacy_entities:
            scoped_id = build_scoped_storage_id(entity.id, scope_key)
            if session.get(MapProfileEntity, scoped_id) is not None:
                continue
            session.add(_model_to_entity(_entity_to_model(entity), scope_key=scope_key))
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_profile(_entity_to_model(entity, scope_key)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    _ensure_schema()
    _seed_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_map_profiles() -> list[MapProfile]:
    _ensure_loaded()
    return _scope_cache()


def get_map_profile_by_key(profile_key: str) -> MapProfile | None:
    _ensure_loaded()
    return next((profile for profile in _scope_cache() if profile.key == profile_key), None)


def upsert_map_profile(profile: MapProfile) -> MapProfile:
    _ensure_loaded()
    existing = get_map_profile_by_key(profile.key)
    bound = _bind_profile(profile)
    cache = _scope_cache()
    if existing is None:
        cache.append(bound)
    else:
        cache[cache.index(existing)] = bound
    _persist_cached_profile(bound.key)
    return bound


def remove_map_profile(profile_key: str) -> None:
    _ensure_loaded()
    existing = get_map_profile_by_key(profile_key)
    if existing is None:
        return
    _scope_cache().remove(existing)
    scoped_id = build_scoped_storage_id(profile_key)
    with get_db_session() as session:
        entity = session.get(MapProfileEntity, scoped_id)
        if entity is not None:
            session.delete(entity)
            session.commit()
