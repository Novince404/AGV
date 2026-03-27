from __future__ import annotations

from datetime import datetime

from app.models.operation_audit import OperationAudit
from app.repositories.operation_audit_repository import (
    add_operation_audit,
    delete_operation_audit,
    get_next_operation_audit_id,
    list_operation_audits,
)
from app.utils.api_error import raise_api_error


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def build_operator_label(actor: dict | None) -> str:
    if not actor:
        return "Guest"
    return str(actor.get("display_name") or actor.get("username") or "Guest")


def build_operator_payload(actor: dict | None) -> dict:
    actor = actor or {}
    return {
        "id": actor.get("id"),
        "username": str(actor.get("username") or "guest"),
        "display_name": build_operator_label(actor),
        "role": str(actor.get("role") or "guest"),
        "authenticated": bool(actor.get("authenticated", False)),
    }


def record_operation_audit(
    resource_type: str,
    resource_id: str | int,
    action: str,
    actor: dict | None,
    metadata: dict | None = None,
) -> OperationAudit:
    operator = build_operator_payload(actor)
    entry = OperationAudit(
        id=get_next_operation_audit_id(),
        resource_type=str(resource_type),
        resource_id=str(resource_id),
        action=str(action),
        operator_id=operator.get("id"),
        operator_username=operator["username"],
        operator_display_name=operator["display_name"],
        operator_role=operator["role"],
        performed_at=now_iso(),
        metadata=metadata or None,
    )
    return add_operation_audit(entry)


def _matching_audits(resource_type: str, resource_ids: set[str]) -> list[OperationAudit]:
    if not resource_ids:
        return []
    return [
        item
        for item in list_operation_audits()
        if item.resource_type == resource_type and item.resource_id in resource_ids
    ]


def build_latest_audit_map(resource_type: str, resource_ids: list[str | int]) -> dict[str, OperationAudit]:
    normalized_ids = {str(item) for item in resource_ids}
    latest: dict[str, OperationAudit] = {}
    for entry in _matching_audits(resource_type, normalized_ids):
        existing = latest.get(entry.resource_id)
        if existing is None or (entry.performed_at, entry.id) > (existing.performed_at, existing.id):
            latest[entry.resource_id] = entry
    return latest


def build_first_audit_map(
    resource_type: str,
    resource_ids: list[str | int],
    create_actions: set[str] | None = None,
) -> dict[str, OperationAudit]:
    normalized_ids = {str(item) for item in resource_ids}
    allowed_actions = create_actions or {"create", "import", "save"}
    earliest: dict[str, OperationAudit] = {}
    for entry in _matching_audits(resource_type, normalized_ids):
        if entry.action not in allowed_actions:
            continue
        existing = earliest.get(entry.resource_id)
        if existing is None or (entry.performed_at, entry.id) < (existing.performed_at, existing.id):
            earliest[entry.resource_id] = entry
    return earliest


def summarize_audit_entry(entry: OperationAudit | None) -> dict | None:
    if entry is None:
        return None
    return {
        "action": entry.action,
        "performed_at": entry.performed_at,
        "operator": entry.operator_display_name,
        "operator_username": entry.operator_username,
        "operator_role": entry.operator_role,
        "metadata": entry.metadata or None,
    }


def serialize_operation_audit(entry: OperationAudit) -> dict:
    return {
        "id": int(entry.id),
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "action": entry.action,
        "operator_id": entry.operator_id,
        "operator_username": entry.operator_username,
        "operator_display_name": entry.operator_display_name,
        "operator_role": entry.operator_role,
        "performed_at": entry.performed_at,
        "metadata": entry.metadata or None,
    }


def list_recent_operation_audits(
    limit: int = 60,
    resource_type: str | None = None,
    action: str | None = None,
) -> list[dict]:
    normalized_limit = max(1, min(int(limit or 60), 200))
    normalized_resource = str(resource_type or "").strip().lower()
    normalized_action = str(action or "").strip().lower()

    entries = list_operation_audits()
    filtered = []
    for entry in entries:
        if normalized_resource and entry.resource_type.lower() != normalized_resource:
            continue
        if normalized_action and entry.action.lower() != normalized_action:
            continue
        filtered.append(entry)

    filtered.sort(key=lambda item: (item.performed_at, int(item.id)), reverse=True)
    return [serialize_operation_audit(entry) for entry in filtered[:normalized_limit]]


def remove_operation_audit_entry(audit_id: int) -> dict:
    removed = delete_operation_audit(int(audit_id))
    if removed is None:
        raise_api_error(404, "operation_audit_not_found")
    return serialize_operation_audit(removed)
