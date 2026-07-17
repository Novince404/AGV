from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.enterprise_request import EnterpriseRequest
from app.repositories.db_init import require_current_schema
from app.repositories.sql_models import EnterpriseRequestEntity


def _ensure_ready() -> None:
    require_current_schema()


def _entity_to_model(entity: EnterpriseRequestEntity) -> EnterpriseRequest:
    return EnterpriseRequest(
        id=int(entity.id),
        organization_id=entity.organization_id,
        organization_name=entity.organization_name,
        category=entity.category,
        title=entity.title,
        content=entity.content,
        submitter_id=entity.submitter_id,
        submitter_username=entity.submitter_username,
        submitter_display_name=entity.submitter_display_name,
        submitter_role=entity.submitter_role,
        target_user_id=entity.target_user_id,
        target_username=entity.target_username,
        target_display_name=entity.target_display_name,
        target_role=entity.target_role,
        status=entity.status,
        response_note=entity.response_note,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _model_to_entity(item: EnterpriseRequest, entity: EnterpriseRequestEntity | None = None) -> EnterpriseRequestEntity:
    entity = entity or EnterpriseRequestEntity(id=int(item.id))
    entity.organization_id = item.organization_id
    entity.organization_name = item.organization_name
    entity.category = item.category
    entity.title = item.title
    entity.content = item.content
    entity.submitter_id = item.submitter_id
    entity.submitter_username = item.submitter_username
    entity.submitter_display_name = item.submitter_display_name
    entity.submitter_role = item.submitter_role
    entity.target_user_id = item.target_user_id
    entity.target_username = item.target_username
    entity.target_display_name = item.target_display_name
    entity.target_role = item.target_role
    entity.status = item.status
    entity.response_note = item.response_note
    entity.created_at = item.created_at
    entity.updated_at = item.updated_at
    return entity


def list_enterprise_requests() -> list[EnterpriseRequest]:
    _ensure_ready()
    with get_db_session() as session:
        entities = session.execute(select(EnterpriseRequestEntity).order_by(EnterpriseRequestEntity.id.desc())).scalars().all()
    return [_entity_to_model(entity) for entity in entities]


def get_enterprise_request_by_id(request_id: int) -> EnterpriseRequest | None:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(EnterpriseRequestEntity, int(request_id or 0))
    return _entity_to_model(entity) if entity is not None else None


def get_next_enterprise_request_id() -> int:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.execute(
            select(EnterpriseRequestEntity).order_by(EnterpriseRequestEntity.id.desc()).limit(1)
        ).scalar_one_or_none()
    return (int(entity.id) if entity is not None else 0) + 1


def upsert_enterprise_request(item: EnterpriseRequest) -> EnterpriseRequest:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(EnterpriseRequestEntity, int(item.id))
        entity = _model_to_entity(item, entity)
        session.add(entity)
        session.commit()
        session.refresh(entity)
    return _entity_to_model(entity)
