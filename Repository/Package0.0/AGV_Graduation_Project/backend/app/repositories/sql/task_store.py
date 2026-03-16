from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.task import Task
from app.repositories.db_init import create_all_tables
from app.repositories.memory.task_store import task_list as default_task_list
from app.repositories.sql.mappers import task_entity_to_model, task_model_to_entity
from app.repositories.sql_models import TaskEntity


task_list: list[Task] = []
_loaded = False


def _task_query():
    return select(TaskEntity).options(selectinload(TaskEntity.stages)).order_by(TaskEntity.id)


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
    task.bind_on_change(lambda task_id=task.id: _persist_cached_task(task_id))
    return task


def _persist_cached_task(task_id: int) -> None:
    task = next((item for item in task_list if item.id == task_id), None)
    if task is None:
        return
    _persist_task_snapshot(task)


def _seed_defaults_if_empty() -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(TaskEntity.id).limit(1)).first() is not None
        if has_rows:
            return

        for default_task in default_task_list:
            session.add(task_model_to_entity(Task(**default_task.model_dump())))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(_task_query()).scalars().all()

    loaded_models = [_bind_task(task_entity_to_model(entity)) for entity in entities]
    task_list[:] = loaded_models


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _seed_defaults_if_empty()
    _load_cache()
    _loaded = True


def list_tasks() -> list[Task]:
    _ensure_loaded()
    return task_list


def get_task_by_id(task_id: int) -> Task | None:
    _ensure_loaded()
    return next((task for task in task_list if task.id == task_id), None)


def get_next_task_id() -> int:
    _ensure_loaded()
    return max((task.id for task in task_list), default=0) + 1


def get_existing_task_ids() -> set[int]:
    _ensure_loaded()
    return {task.id for task in task_list}


def add_task(task: Task) -> Task:
    _ensure_loaded()
    bound = _bind_task(task)
    task_list.append(bound)
    _persist_task_snapshot(bound)
    return bound


def remove_task(task: Task) -> None:
    _ensure_loaded()
    task_list[:] = [item for item in task_list if item.id != task.id]
    with get_db_session() as session:
        entity = session.get(TaskEntity, task.id)
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
    "task_list",
]
