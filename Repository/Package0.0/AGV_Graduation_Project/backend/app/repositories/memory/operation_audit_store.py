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
