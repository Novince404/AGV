from __future__ import annotations

from app.core.data_scope import get_current_scope_key
from app.models.task_template import TaskTemplate, TaskTemplateStage


DEFAULT_TASK_TEMPLATE_LIST: list[TaskTemplate] = [
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


task_template_lists_by_scope: dict[str, list[TaskTemplate]] = {}


def _current_scope() -> str:
    return get_current_scope_key()


def _clone_template(template: TaskTemplate) -> TaskTemplate:
    return TaskTemplate(**template.model_dump())


def _scope_cache() -> list[TaskTemplate]:
    scope_key = _current_scope()
    if scope_key not in task_template_lists_by_scope:
        task_template_lists_by_scope[scope_key] = [_clone_template(template) for template in DEFAULT_TASK_TEMPLATE_LIST]
    return task_template_lists_by_scope[scope_key]


def list_task_templates() -> list[TaskTemplate]:
    return _scope_cache()


def get_task_template_by_id(template_id: str) -> TaskTemplate | None:
    return next((template for template in _scope_cache() if template.id == template_id), None)


def upsert_task_template(template: TaskTemplate) -> TaskTemplate:
    existing = get_task_template_by_id(template.id)
    bound = _clone_template(template)
    cache = _scope_cache()
    if existing is None:
        cache.append(bound)
        return bound

    index = cache.index(existing)
    cache[index] = bound
    return bound


def remove_task_template(template_id: str) -> None:
    existing = get_task_template_by_id(template_id)
    if existing is not None:
        _scope_cache().remove(existing)
