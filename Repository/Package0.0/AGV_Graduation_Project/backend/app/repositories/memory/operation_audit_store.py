from __future__ import annotations

from app.models.operation_audit import OperationAudit


operation_audit_list: list[OperationAudit] = []


def list_operation_audits() -> list[OperationAudit]:
    return operation_audit_list


def get_next_operation_audit_id() -> int:
    return max((item.id for item in operation_audit_list), default=0) + 1


def add_operation_audit(entry: OperationAudit) -> OperationAudit:
    operation_audit_list.append(entry)
    return entry


def delete_operation_audit(audit_id: int) -> OperationAudit | None:
    normalized_id = int(audit_id)
    for index, entry in enumerate(operation_audit_list):
        if int(entry.id) != normalized_id:
            continue
        return operation_audit_list.pop(index)
    return None
