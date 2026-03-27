"""Public operation-audit repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import operation_audit_store as _store
else:
    from app.repositories.memory import operation_audit_store as _store


operation_audit_list = _store.operation_audit_list


def list_operation_audits():
    return _store.list_operation_audits()


def get_next_operation_audit_id():
    return _store.get_next_operation_audit_id()


def add_operation_audit(entry):
    return _store.add_operation_audit(entry)


def delete_operation_audit(audit_id):
    return _store.delete_operation_audit(audit_id)


__all__ = [
    "add_operation_audit",
    "delete_operation_audit",
    "get_next_operation_audit_id",
    "list_operation_audits",
    "operation_audit_list",
]
