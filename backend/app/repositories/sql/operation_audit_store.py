from __future__ import annotations

from sqlalchemy import delete, select

from app.core.database import get_db_session
from app.models.operation_audit import OperationAudit
from app.repositories.db_init import require_current_schema
from app.repositories.sql_models import OperationAuditEntity


operation_audit_list: list[OperationAudit] = []
_loaded = False


def _entity_to_model(entity: OperationAuditEntity) -> OperationAudit:
    return OperationAudit(
        id=int(entity.id),
        resource_type=entity.resource_type,
        resource_id=entity.resource_id,
        action=entity.action,
        operator_id=entity.operator_id,
        operator_username=entity.operator_username,
        operator_display_name=entity.operator_display_name,
        operator_role=entity.operator_role,
        performed_at=entity.performed_at,
        metadata=entity.details or None,
    )


def _model_to_entity(entry: OperationAudit) -> OperationAuditEntity:
    return OperationAuditEntity(
        id=int(entry.id),
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        action=entry.action,
        operator_id=entry.operator_id,
        operator_username=entry.operator_username,
        operator_display_name=entry.operator_display_name,
        operator_role=entry.operator_role,
        performed_at=entry.performed_at,
        details=entry.metadata or None,
    )


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(select(OperationAuditEntity).order_by(OperationAuditEntity.id)).scalars().all()
    operation_audit_list[:] = [_entity_to_model(entity) for entity in entities]


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    require_current_schema()
    _load_cache()
    _loaded = True


def list_operation_audits() -> list[OperationAudit]:
    _ensure_loaded()
    return operation_audit_list


def get_next_operation_audit_id() -> int:
    _ensure_loaded()
    return max((item.id for item in operation_audit_list), default=0) + 1


def add_operation_audit(entry: OperationAudit) -> OperationAudit:
    _ensure_loaded()
    operation_audit_list.append(entry)
    with get_db_session() as session:
        session.add(_model_to_entity(entry))
        session.commit()
    return entry


def delete_operation_audit(audit_id: int) -> OperationAudit | None:
    _ensure_loaded()
    normalized_id = int(audit_id)
    removed = next((item for item in operation_audit_list if int(item.id) == normalized_id), None)
    if removed is None:
        return None
    operation_audit_list[:] = [item for item in operation_audit_list if int(item.id) != normalized_id]
    with get_db_session() as session:
        session.execute(delete(OperationAuditEntity).where(OperationAuditEntity.id == normalized_id))
        session.commit()
    return removed
