from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.enterprise_application import EnterpriseApplication
from app.repositories.db_init import require_current_schema
from app.repositories.sql_models import EnterpriseApplicationEntity


enterprise_application_list: list[EnterpriseApplication] = []
_loaded = False


def _entity_to_model(entity: EnterpriseApplicationEntity) -> EnterpriseApplication:
    return EnterpriseApplication(
        id=int(entity.id),
        company_name=entity.company_name,
        contact_name=entity.contact_name,
        contact_email=entity.contact_email,
        username=entity.username,
        user_id=entity.user_id,
        status=entity.status,
        submitted_at=entity.submitted_at,
        reviewed_at=entity.reviewed_at,
        reviewed_by=entity.reviewed_by,
        review_note=entity.review_note,
        organization_id=entity.organization_id,
    )


def _model_to_entity(application: EnterpriseApplication, entity: EnterpriseApplicationEntity | None = None) -> EnterpriseApplicationEntity:
    entity = entity or EnterpriseApplicationEntity(id=int(application.id))
    entity.company_name = application.company_name
    entity.contact_name = application.contact_name
    entity.contact_email = application.contact_email
    entity.username = application.username
    entity.user_id = application.user_id
    entity.status = application.status
    entity.submitted_at = application.submitted_at
    entity.reviewed_at = application.reviewed_at
    entity.reviewed_by = application.reviewed_by
    entity.review_note = application.review_note
    entity.organization_id = application.organization_id
    return entity


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(
            select(EnterpriseApplicationEntity).order_by(EnterpriseApplicationEntity.id.desc())
        ).scalars().all()
    enterprise_application_list[:] = [_entity_to_model(entity) for entity in entities]


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    require_current_schema()
    _load_cache()
    _loaded = True


def list_enterprise_applications() -> list[EnterpriseApplication]:
    _ensure_loaded()
    return enterprise_application_list


def get_enterprise_application_by_id(application_id: int) -> EnterpriseApplication | None:
    _ensure_loaded()
    target_id = int(application_id or 0)
    return next((item for item in enterprise_application_list if int(item.id) == target_id), None)


def get_enterprise_application_by_username(username: str) -> EnterpriseApplication | None:
    _ensure_loaded()
    normalized = str(username or "").strip().casefold()
    if not normalized:
        return None
    return next((item for item in enterprise_application_list if item.username.casefold() == normalized), None)


def get_enterprise_application_by_user_id(user_id: str) -> EnterpriseApplication | None:
    _ensure_loaded()
    normalized = str(user_id or "").strip()
    if not normalized:
        return None
    return next((item for item in enterprise_application_list if item.user_id == normalized), None)


def get_next_enterprise_application_id() -> int:
    _ensure_loaded()
    return max((int(item.id) for item in enterprise_application_list), default=0) + 1


def upsert_enterprise_application(application: EnterpriseApplication) -> EnterpriseApplication:
    _ensure_loaded()
    existing = get_enterprise_application_by_id(application.id)
    if existing is None:
        enterprise_application_list.insert(0, application)
    else:
        enterprise_application_list[enterprise_application_list.index(existing)] = application
    with get_db_session() as session:
        entity = session.get(EnterpriseApplicationEntity, int(application.id))
        entity = _model_to_entity(application, entity)
        session.add(entity)
        session.commit()
    return application
