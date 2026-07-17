from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.platform_bug_feedback import PlatformBugFeedback
from app.repositories.db_init import require_current_schema
from app.repositories.sql_models import PlatformBugFeedbackEntity


def _ensure_ready() -> None:
    require_current_schema()


def _entity_to_model(entity: PlatformBugFeedbackEntity) -> PlatformBugFeedback:
    return PlatformBugFeedback(
        id=int(entity.id),
        category=entity.category,
        title=entity.title,
        content=entity.content,
        submitter_id=entity.submitter_id,
        submitter_username=entity.submitter_username,
        submitter_display_name=entity.submitter_display_name,
        submitter_role=entity.submitter_role,
        status=entity.status,
        response_note=entity.response_note,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _model_to_entity(item: PlatformBugFeedback, entity: PlatformBugFeedbackEntity | None = None) -> PlatformBugFeedbackEntity:
    entity = entity or PlatformBugFeedbackEntity(id=int(item.id))
    entity.category = item.category
    entity.title = item.title
    entity.content = item.content
    entity.submitter_id = item.submitter_id
    entity.submitter_username = item.submitter_username
    entity.submitter_display_name = item.submitter_display_name
    entity.submitter_role = item.submitter_role
    entity.status = item.status
    entity.response_note = item.response_note
    entity.created_at = item.created_at
    entity.updated_at = item.updated_at
    return entity


def list_platform_bug_feedback() -> list[PlatformBugFeedback]:
    _ensure_ready()
    with get_db_session() as session:
        entities = session.execute(
            select(PlatformBugFeedbackEntity).order_by(PlatformBugFeedbackEntity.id.desc())
        ).scalars().all()
    return [_entity_to_model(entity) for entity in entities]


def get_platform_bug_feedback_by_id(feedback_id: int) -> PlatformBugFeedback | None:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(PlatformBugFeedbackEntity, int(feedback_id or 0))
    return _entity_to_model(entity) if entity is not None else None


def get_next_platform_bug_feedback_id() -> int:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.execute(
            select(PlatformBugFeedbackEntity).order_by(PlatformBugFeedbackEntity.id.desc()).limit(1)
        ).scalar_one_or_none()
    return (int(entity.id) if entity is not None else 0) + 1


def upsert_platform_bug_feedback(item: PlatformBugFeedback) -> PlatformBugFeedback:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(PlatformBugFeedbackEntity, int(item.id))
        entity = _model_to_entity(item, entity)
        session.add(entity)
        session.commit()
        session.refresh(entity)
    return _entity_to_model(entity)
