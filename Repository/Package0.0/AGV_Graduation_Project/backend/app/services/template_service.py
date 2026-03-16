from __future__ import annotations

from app.models.task_template import TaskTemplate, TaskTemplateStage
from app.repositories.template_repository import (
    get_task_template_by_id,
    list_task_templates,
    remove_task_template,
    upsert_task_template,
)
from app.utils.api_error import raise_api_error


def get_template_list():
    return list_task_templates()


def create_or_update_template(payload):
    if not payload.stages:
        raise_api_error(400, "template_stages_required")

    stages = [
        TaskTemplateStage(
            index=stage.index,
            start_x=stage.start_x,
            start_y=stage.start_y,
            end_x=stage.end_x,
            end_y=stage.end_y,
            label=stage.label,
        )
        for stage in payload.stages
    ]
    template = TaskTemplate(
        id=payload.id,
        priority=payload.priority,
        name_key=payload.name_key,
        custom_name=payload.custom_name,
        custom=payload.custom,
        stages=stages,
    )
    upsert_task_template(template)
    return {"message": "Template saved", "template": template}


def delete_template(template_id: str):
    template = get_task_template_by_id(template_id)
    if template is None:
        raise_api_error(404, "template_not_found")
    remove_task_template(template_id)
    return {"message": "Template deleted", "template_id": template_id}
