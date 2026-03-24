"""Public Comfy workflow template repository facade."""

from __future__ import annotations

from app.core.settings import get_settings

if get_settings().data_backend in {"sqlite", "mysql"}:
    from app.repositories.sql import comfy_template_store as _store
else:
    from app.repositories.memory import comfy_template_store as _store


def list_comfy_workflow_templates():
    return _store.list_comfy_workflow_templates()


def get_comfy_workflow_template_by_id(template_id: str):
    return _store.get_comfy_workflow_template_by_id(template_id)


def upsert_comfy_workflow_template(template):
    return _store.upsert_comfy_workflow_template(template)


def delete_comfy_workflow_template(template_id: str):
    return _store.delete_comfy_workflow_template(template_id)


__all__ = [
    "list_comfy_workflow_templates",
    "get_comfy_workflow_template_by_id",
    "upsert_comfy_workflow_template",
    "delete_comfy_workflow_template",
]
