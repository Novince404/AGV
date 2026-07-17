from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.data_scope import (
    build_scoped_storage_id,
    extract_public_id,
    get_current_scope_key,
    get_scope_storage_prefix,
    is_legacy_unscoped_storage_id,
)
from app.core.database import get_db_session
from app.models.task_template import TaskTemplate, TaskTemplateStage
from app.repositories.db_init import require_current_schema
from app.repositories.memory.template_store import DEFAULT_TASK_TEMPLATE_LIST
from app.repositories.sql_models import TaskTemplateEntity, TaskTemplateStageEntity


task_template_lists_by_scope: dict[str, list[TaskTemplate]] = {}
_loaded_scopes: set[str] = set()


def _current_scope() -> str:
    return get_current_scope_key()


def _scope_prefix(scope_key: str | None = None) -> str:
    return get_scope_storage_prefix(scope_key or _current_scope())


def _bind_template(template: TaskTemplate) -> TaskTemplate:
    template.bind_on_change(lambda template_id=template.id, scope_key=_current_scope(): _persist_cached_template(template_id, scope_key))
    return template


def _scope_query(scope_key: str):
    return (
        select(TaskTemplateEntity)
        .options(selectinload(TaskTemplateEntity.stages))
        .where(TaskTemplateEntity.id.like(f"{_scope_prefix(scope_key)}%"))
        .order_by(TaskTemplateEntity.id)
    )


def _legacy_query():
    return select(TaskTemplateEntity).options(selectinload(TaskTemplateEntity.stages)).order_by(TaskTemplateEntity.id)


def _scope_cache(scope_key: str | None = None) -> list[TaskTemplate]:
    normalized_scope = str(scope_key or _current_scope())
    return task_template_lists_by_scope.setdefault(normalized_scope, [])


def _stage_entity_to_model(entity: TaskTemplateStageEntity) -> TaskTemplateStage:
    return TaskTemplateStage(
        index=entity.stage_index,
        start_x=entity.start_x,
        start_y=entity.start_y,
        end_x=entity.end_x,
        end_y=entity.end_y,
        label=entity.label,
    )


def _template_entity_to_model(entity: TaskTemplateEntity, scope_key: str | None = None) -> TaskTemplate:
    return TaskTemplate(
        id=extract_public_id(entity.id, scope_key),
        priority=entity.priority,
        name_key=entity.name_key,
        custom_name=entity.custom_name,
        custom=entity.custom,
        stages=[_stage_entity_to_model(stage) for stage in sorted(entity.stages, key=lambda item: item.stage_index)],
    )


def _template_model_to_entity(template: TaskTemplate, entity: TaskTemplateEntity | None = None, scope_key: str | None = None) -> TaskTemplateEntity:
    storage_id = build_scoped_storage_id(template.id, scope_key)
    entity = entity or TaskTemplateEntity(id=storage_id)
    entity.id = storage_id
    entity.priority = template.priority
    entity.name_key = template.name_key
    entity.custom_name = template.custom_name
    entity.custom = template.custom
    entity.stages = [
        TaskTemplateStageEntity(
            template_id=storage_id,
            stage_index=stage.index,
            start_x=stage.start_x,
            start_y=stage.start_y,
            end_x=stage.end_x,
            end_y=stage.end_y,
            label=stage.label,
        )
        for stage in template.stages
    ]
    return entity


def _persist_cached_template(template_id: str, scope_key: str | None = None) -> None:
    cache = _scope_cache(scope_key)
    template = next((item for item in cache if item.id == template_id), None)
    if template is None:
        return
    scoped_id = build_scoped_storage_id(template.id, scope_key)
    with get_db_session() as session:
        entity = session.execute(
            select(TaskTemplateEntity)
            .options(selectinload(TaskTemplateEntity.stages))
            .where(TaskTemplateEntity.id == scoped_id)
        ).scalar_one_or_none()
        merged = session.merge(_template_model_to_entity(template, entity, scope_key))
        session.flush()
        session.refresh(merged)
        session.commit()


def _seed_defaults_for_scope(scope_key: str) -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(TaskTemplateEntity.id).where(TaskTemplateEntity.id.like(f"{_scope_prefix(scope_key)}%")).limit(1)).first() is not None
        if has_rows:
            return

        legacy_entities = [
            entity
            for entity in session.execute(_legacy_query()).scalars().all()
            if is_legacy_unscoped_storage_id(entity.id)
        ]
        if legacy_entities:
            for entity in legacy_entities:
                scoped_id = build_scoped_storage_id(entity.id, scope_key)
                if session.get(TaskTemplateEntity, scoped_id) is not None:
                    continue
                session.add(
                    _template_model_to_entity(_template_entity_to_model(entity), scope_key=scope_key)
                )
            session.commit()
            return

        for default_template in DEFAULT_TASK_TEMPLATE_LIST:
            session.add(_template_model_to_entity(TaskTemplate(**default_template.model_dump()), scope_key=scope_key))
        session.commit()


def _load_scope(scope_key: str) -> None:
    with get_db_session() as session:
        entities = session.execute(_scope_query(scope_key)).scalars().all()
    _scope_cache(scope_key)[:] = [_bind_template(_template_entity_to_model(entity, scope_key)) for entity in entities]


def _ensure_loaded() -> None:
    scope_key = _current_scope()
    if scope_key in _loaded_scopes:
        return
    require_current_schema()
    _seed_defaults_for_scope(scope_key)
    _load_scope(scope_key)
    _loaded_scopes.add(scope_key)


def list_task_templates() -> list[TaskTemplate]:
    _ensure_loaded()
    return _scope_cache()


def get_task_template_by_id(template_id: str) -> TaskTemplate | None:
    _ensure_loaded()
    return next((template for template in _scope_cache() if template.id == template_id), None)


def upsert_task_template(template: TaskTemplate) -> TaskTemplate:
    _ensure_loaded()
    existing = get_task_template_by_id(template.id)
    bound = _bind_template(template)
    cache = _scope_cache()
    if existing is None:
        cache.append(bound)
    else:
        cache[cache.index(existing)] = bound
    _persist_cached_template(bound.id)
    return bound


def remove_task_template(template_id: str) -> None:
    _ensure_loaded()
    existing = get_task_template_by_id(template_id)
    if existing is None:
        return
    _scope_cache().remove(existing)
    scoped_id = build_scoped_storage_id(template_id)
    with get_db_session() as session:
        entity = session.get(TaskTemplateEntity, scoped_id)
        if entity is not None:
            session.delete(entity)
            session.commit()
