from __future__ import annotations

from app.models.comfy_template import ComfyWorkflowTemplate


comfy_workflow_templates: list[ComfyWorkflowTemplate] = []


def list_comfy_workflow_templates() -> list[ComfyWorkflowTemplate]:
    return comfy_workflow_templates


def get_comfy_workflow_template_by_id(template_id: str) -> ComfyWorkflowTemplate | None:
    normalized_id = str(template_id or "").strip()
    return next((item for item in comfy_workflow_templates if item.id == normalized_id), None)


def upsert_comfy_workflow_template(template: ComfyWorkflowTemplate) -> ComfyWorkflowTemplate:
    existing = get_comfy_workflow_template_by_id(template.id)
    if existing is None:
        comfy_workflow_templates.append(template)
        return template

    comfy_workflow_templates[comfy_workflow_templates.index(existing)] = template
    return template


def delete_comfy_workflow_template(template_id: str) -> bool:
    existing = get_comfy_workflow_template_by_id(template_id)
    if existing is None:
        return False
    comfy_workflow_templates.remove(existing)
    return True
