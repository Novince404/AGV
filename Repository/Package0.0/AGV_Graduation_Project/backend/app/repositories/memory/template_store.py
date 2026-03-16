from __future__ import annotations

from app.models.task_template import TaskTemplate, TaskTemplateStage


task_template_list: list[TaskTemplate] = [
    TaskTemplate(
        id="template_inbound_a_to_storage_c1",
        priority=3,
        name_key="template_name_inbound_a_to_storage_c1",
        custom=False,
        stages=[TaskTemplateStage(index=0, start_x=0, start_y=1, end_x=3, end_y=2)],
    ),
    TaskTemplate(
        id="template_inbound_b_to_storage_c2",
        priority=3,
        name_key="template_name_inbound_b_to_storage_c2",
        custom=False,
        stages=[TaskTemplateStage(index=0, start_x=0, start_y=6, end_x=3, end_y=5)],
    ),
    TaskTemplate(
        id="template_storage_c1_to_assembly_1",
        priority=4,
        name_key="template_name_storage_c1_to_assembly_1",
        custom=False,
        stages=[TaskTemplateStage(index=0, start_x=3, start_y=2, end_x=6, end_y=2)],
    ),
    TaskTemplate(
        id="template_assembly_1_to_outbound_a",
        priority=5,
        name_key="template_name_assembly_1_to_outbound_a",
        custom=False,
        stages=[TaskTemplateStage(index=0, start_x=6, start_y=2, end_x=9, end_y=1)],
    ),
]


def list_task_templates() -> list[TaskTemplate]:
    return task_template_list


def get_task_template_by_id(template_id: str) -> TaskTemplate | None:
    return next((template for template in task_template_list if template.id == template_id), None)


def upsert_task_template(template: TaskTemplate) -> TaskTemplate:
    existing = get_task_template_by_id(template.id)
    if existing is None:
        task_template_list.append(template)
        return template

    index = task_template_list.index(existing)
    task_template_list[index] = template
    return template


def remove_task_template(template_id: str) -> None:
    existing = get_task_template_by_id(template_id)
    if existing is not None:
        task_template_list.remove(existing)
