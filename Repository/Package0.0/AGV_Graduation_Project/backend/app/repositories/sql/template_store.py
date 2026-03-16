from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.task_template import TaskTemplate, TaskTemplateStage
from app.repositories.db_init import create_all_tables
from app.repositories.memory.template_store import task_template_list as default_task_template_list
from app.repositories.sql_models import TaskTemplateEntity, TaskTemplateStageEntity


task_template_list: list[TaskTemplate] = []
_loaded = False


def _bind_template(template: TaskTemplate) -> TaskTemplate:
    template.bind_on_change(lambda template_id=template.id: _persist_cached_template(template_id))
    return template


def _stage_entity_to_model(entity: TaskTemplateStageEntity) -> TaskTemplateStage:
    return TaskTemplateStage(
        index=entity.stage_index,
        start_x=entity.start_x,
        start_y=entity.start_y,
        end_x=entity.end_x,
        end_y=entity.end_y,
        label=entity.label,
    )


def _template_entity_to_model(entity: TaskTemplateEntity) -> TaskTemplate:
    return TaskTemplate(
        id=entity.id,
        priority=entity.priority,
        name_key=entity.name_key,
        custom_name=entity.custom_name,
        custom=entity.custom,
        stages=[_stage_entity_to_model(stage) for stage in sorted(entity.stages, key=lambda item: item.stage_index)],
    )


def _template_model_to_entity(template: TaskTemplate, entity: TaskTemplateEntity | None = None) -> TaskTemplateEntity:
    entity = entity or TaskTemplateEntity(id=template.id)
    entity.priority = template.priority
    entity.name_key = template.name_key
    entity.custom_name = template.custom_name
    entity.custom = template.custom
    entity.stages = [
        TaskTemplateStageEntity(
            template_id=template.id,
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


def _persist_cached_template(template_id: str) -> None:
    template = next((item for item in task_template_list if item.id == template_id), None)
    if template is None:
        return
    with get_db_session() as session:
        entity = session.execute(
            select(TaskTemplateEntity)
            .options(selectinload(TaskTemplateEntity.stages))
            .where(TaskTemplateEntity.id == template.id)
        ).scalar_one_or_none()
        merged = session.merge(_template_model_to_entity(template, entity))
        session.flush()
        session.refresh(merged)
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(
            select(TaskTemplateEntity)
            .options(selectinload(TaskTemplateEntity.stages))
            .order_by(TaskTemplateEntity.id)
        ).scalars().all()
    task_template_list[:] = [_bind_template(_template_entity_to_model(entity)) for entity in entities]


def _seed_defaults_if_empty() -> None:
    with get_db_session() as session:
        has_rows = session.execute(select(TaskTemplateEntity.id).limit(1)).first() is not None
        if has_rows:
            return
        for default_template in default_task_template_list:
            session.add(_template_model_to_entity(TaskTemplate(**default_template.model_dump())))
        session.commit()


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _seed_defaults_if_empty()
    _load_cache()
    _loaded = True


def list_task_templates() -> list[TaskTemplate]:
    _ensure_loaded()
    return task_template_list


def get_task_template_by_id(template_id: str) -> TaskTemplate | None:
    _ensure_loaded()
    return next((template for template in task_template_list if template.id == template_id), None)


def upsert_task_template(template: TaskTemplate) -> TaskTemplate:
    _ensure_loaded()
    existing = get_task_template_by_id(template.id)
    bound = _bind_template(template)
    if existing is None:
        task_template_list.append(bound)
    else:
        task_template_list[task_template_list.index(existing)] = bound
    _persist_cached_template(bound.id)
    return bound


def remove_task_template(template_id: str) -> None:
    _ensure_loaded()
    existing = get_task_template_by_id(template_id)
    if existing is None:
        return
    task_template_list.remove(existing)
    with get_db_session() as session:
        entity = session.get(TaskTemplateEntity, template_id)
        if entity is not None:
            session.delete(entity)
            session.commit()
