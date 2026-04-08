from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import selectinload

from app.core.data_scope import get_current_scope_key
from app.core.database import get_engine
from app.core.database import get_db_session
from app.models.task import Task
from app.repositories.db_init import create_all_tables
from app.repositories.memory.task_store import task_list as default_task_list
from app.repositories.sql.mappers import task_entity_to_model, task_model_to_entity
from app.repositories.sql_models import TaskEntity


task_lists_by_scope: dict[str, list[Task]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    if "task" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("task")}
    ddl_statements: list[str] = []
    if "scope_key" not in columns:
        ddl_statements.append("ALTER TABLE task ADD COLUMN scope_key VARCHAR(128)")
    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                connection.execute(text(statement))


def _scope_query(scope_key: str):
    return (
        select(TaskEntity)
        .options(selectinload(TaskEntity.stages))
        .where(TaskEntity.scope_key == scope_key)
        .order_by(TaskEntity.id)
    )


def _legacy_query():
    return (
        select(TaskEntity)
        .options(selectinload(TaskEntity.stages))
        .where((TaskEntity.scope_key.is_(None)) | (TaskEntity.scope_key == ""))
        .order_by(TaskEntity.id)
    )


def _scope_cache(scope_key: str | None = None) -> list[Task]:
    normalized_scope = str(scope_key or _current_scope())
    return task_lists_by_scope.setdefault(normalized_scope, [])


def _persist_task_snapshot(task: Task) -> None:
    with get_db_session() as session:
        entity = session.execute(
            select(TaskEntity).options(selectinload(TaskEntity.stages)).where(TaskEntity.id == task.id)
        ).scalar_one_or_none()
        entity = task_model_to_entity(task, entity)
        merged = session.merge(entity)
        session.flush()
        session.refresh(merged)
        session.commit()


def _bind_task(task: Task) -> Task:
    task.bind_on_change(lambda task_id=task.id, scope_key=task.scope_key or _current_scope(): _persist_cached_task(task_id, scope_key))
    return task


def _persist_cached_task(task_id: int, scope_key: str | None = None) -> None:
    task = next((item for item in _scope_cache(scope_key) if item.id == task_id), None)
    if task is None:
        return
    _persist_task_snapshot(task)


def _seed_defaults_for_scope(scope_key: str) -> None:
    with get_db_session() as session:
        has_scoped_rows = session.execute(select(TaskEntity.id).where(TaskEntity.scope_key == scope_key).limit(1)).first() is not None
        if has_scoped_rows:
            return

        legacy_entities = session.execute(_legacy_query()).scalars().all()
        if legacy_entities:
            for entity in legacy_entities:
                entity.scope_key = scope_key
            session.commit()
            return

        next_id = session.execute(select(TaskEntity.id).order_by(TaskEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
        for default_task in default_task_list:
            next_id += 1
            session.add(task_model_to_entity(Task(**{**default_task.model_dump(), "id": next_id, "scope_key": scope_key})))
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_task(task_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    _ensure_schema()
    _seed_defaults_for_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_tasks() -> list[Task]:
    _ensure_loaded()
    return _scope_cache()


def get_task_by_id(task_id: int) -> Task | None:
    _ensure_loaded()
    return next((task for task in _scope_cache() if task.id == task_id), None)


def get_next_task_id() -> int:
    _ensure_loaded()
    with get_db_session() as session:
        next_id = session.execute(select(TaskEntity.id).order_by(TaskEntity.id.desc()).limit(1)).scalar_one_or_none() or 0
    return int(next_id) + 1


def get_existing_task_ids() -> set[int]:
    _ensure_loaded()
    return {task.id for task in _scope_cache()}


def add_task(task: Task) -> Task:
    _ensure_loaded()
    scope_key = _current_scope()
    bound = _bind_task(Task(**{**task.model_dump(), "scope_key": task.scope_key or scope_key}))
    _scope_cache(scope_key).append(bound)
    _persist_task_snapshot(bound)
    return bound


def remove_task(task: Task) -> None:
    _ensure_loaded()
    scope_key = _current_scope()
    cache = _scope_cache(scope_key)
    cache[:] = [item for item in cache if item.id != task.id]
    with get_db_session() as session:
        entity = session.execute(
            select(TaskEntity).where(TaskEntity.id == task.id, TaskEntity.scope_key == scope_key)
        ).scalar_one_or_none()
        if entity is not None:
            session.delete(entity)
            session.commit()


__all__ = [
    "add_task",
    "get_existing_task_ids",
    "get_next_task_id",
    "get_task_by_id",
    "list_tasks",
    "remove_task",
]
