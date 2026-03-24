from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.comfy_template import ComfyWorkflowTemplate
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import ComfyWorkflowTemplateEntity


comfy_workflow_templates: list[ComfyWorkflowTemplate] = []
_loaded = False


def _bind_template(template: ComfyWorkflowTemplate) -> ComfyWorkflowTemplate:
    template.bind_on_change(lambda template_id=template.id: _persist_cached_template(template_id))
    return template


def _entity_to_model(entity: ComfyWorkflowTemplateEntity) -> ComfyWorkflowTemplate:
    return ComfyWorkflowTemplate(
        id=entity.id,
        name=entity.name,
        scope=entity.scope,
        organization_id=entity.organization_id,
        created_by_id=entity.created_by_id,
        created_by=entity.created_by,
        source_type=entity.source_type,
        source_ref=entity.source_ref,
        checkpoint_name=entity.checkpoint_name,
        workflow_preset=entity.workflow_preset,
        prompt_style=entity.prompt_style,
        prompt_text=entity.prompt_text or "",
        input_json_text=entity.input_json_text or "",
        workflow_json_text=entity.workflow_json_text or "",
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        tags=[str(item) for item in (entity.tags or [])],
    )


def _model_to_entity(
    template: ComfyWorkflowTemplate,
    entity: ComfyWorkflowTemplateEntity | None = None,
) -> ComfyWorkflowTemplateEntity:
    entity = entity or ComfyWorkflowTemplateEntity(id=template.id)
    entity.name = template.name
    entity.scope = template.scope
    entity.organization_id = template.organization_id
    entity.created_by_id = template.created_by_id
    entity.created_by = template.created_by
    entity.source_type = template.source_type
    entity.source_ref = template.source_ref
    entity.checkpoint_name = template.checkpoint_name
    entity.workflow_preset = template.workflow_preset
    entity.prompt_style = template.prompt_style
    entity.prompt_text = template.prompt_text
    entity.input_json_text = template.input_json_text
    entity.workflow_json_text = template.workflow_json_text
    entity.created_at = template.created_at
    entity.updated_at = template.updated_at
    entity.tags = list(template.tags or [])
    return entity


def _persist_cached_template(template_id: str) -> None:
    template = next((item for item in comfy_workflow_templates if item.id == str(template_id)), None)
    if template is None:
        return
    with get_db_session() as session:
        entity = session.get(ComfyWorkflowTemplateEntity, template.id)
        session.add(_model_to_entity(template, entity))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(
            select(ComfyWorkflowTemplateEntity).order_by(ComfyWorkflowTemplateEntity.updated_at.desc())
        ).scalars().all()
    comfy_workflow_templates[:] = [_bind_template(_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _load_cache()
    _loaded = True


def list_comfy_workflow_templates() -> list[ComfyWorkflowTemplate]:
    _ensure_loaded()
    return comfy_workflow_templates


def get_comfy_workflow_template_by_id(template_id: str) -> ComfyWorkflowTemplate | None:
    _ensure_loaded()
    normalized_id = str(template_id or "").strip()
    return next((item for item in comfy_workflow_templates if item.id == normalized_id), None)


def upsert_comfy_workflow_template(template: ComfyWorkflowTemplate) -> ComfyWorkflowTemplate:
    _ensure_loaded()
    existing = get_comfy_workflow_template_by_id(template.id)
    bound = _bind_template(template)
    if existing is None:
        comfy_workflow_templates.append(bound)
    else:
        comfy_workflow_templates[comfy_workflow_templates.index(existing)] = bound
    _persist_cached_template(bound.id)
    return bound


def delete_comfy_workflow_template(template_id: str) -> bool:
    _ensure_loaded()
    existing = get_comfy_workflow_template_by_id(template_id)
    if existing is None:
        return False

    comfy_workflow_templates.remove(existing)
    with get_db_session() as session:
        entity = session.get(ComfyWorkflowTemplateEntity, str(template_id))
        if entity is not None:
            session.delete(entity)
            session.commit()
    return True
