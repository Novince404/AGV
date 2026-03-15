from __future__ import annotations

from app.models.agv import AGV
from app.models.fault_event import FaultEvent
from app.models.task import Task, TaskStage
from app.repositories.sql_models import AgvEntity, FaultEventEntity, TaskEntity, TaskStageEntity


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def agv_entity_to_model(entity: AgvEntity) -> AGV:
    return AGV(
        id=entity.id,
        x=entity.x,
        y=entity.y,
        status=entity.status,
        task_id=entity.task_id,
        active_fault_event_id=entity.active_fault_event_id,
    )


def agv_model_to_entity(model: AGV, entity: AgvEntity | None = None) -> AgvEntity:
    payload = _model_dump(model)
    entity = entity or AgvEntity(id=payload["id"])
    entity.x = payload["x"]
    entity.y = payload["y"]
    entity.status = payload["status"]
    entity.task_id = payload.get("task_id")
    entity.active_fault_event_id = payload.get("active_fault_event_id")
    return entity


def task_stage_entity_to_model(entity: TaskStageEntity) -> TaskStage:
    return TaskStage(
        index=entity.stage_index,
        start_x=entity.start_x,
        start_y=entity.start_y,
        end_x=entity.end_x,
        end_y=entity.end_y,
        label=entity.label,
        path_to_start=entity.path_to_start,
        path_to_end=entity.path_to_end,
        path_length_to_start=entity.path_length_to_start,
        path_length_to_end=entity.path_length_to_end,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
    )


def task_stage_model_to_entity(model: TaskStage, task_id: int, entity: TaskStageEntity | None = None) -> TaskStageEntity:
    payload = _model_dump(model)
    entity = entity or TaskStageEntity(task_id=task_id, stage_index=payload["index"])
    entity.task_id = task_id
    entity.stage_index = payload["index"]
    entity.label = payload.get("label")
    entity.start_x = payload["start_x"]
    entity.start_y = payload["start_y"]
    entity.end_x = payload["end_x"]
    entity.end_y = payload["end_y"]
    entity.path_to_start = payload.get("path_to_start")
    entity.path_to_end = payload.get("path_to_end")
    entity.path_length_to_start = payload.get("path_length_to_start")
    entity.path_length_to_end = payload.get("path_length_to_end")
    entity.started_at = payload.get("started_at")
    entity.finished_at = payload.get("finished_at")
    return entity


def task_entity_to_model(entity: TaskEntity) -> Task:
    stages = [task_stage_entity_to_model(stage) for stage in sorted(entity.stages, key=lambda item: item.stage_index)]
    return Task(
        id=entity.id,
        start_x=entity.start_x,
        start_y=entity.start_y,
        end_x=entity.end_x,
        end_y=entity.end_y,
        priority=entity.priority,
        status=entity.status,
        agv_id=entity.agv_id,
        preferred_agv_id=entity.preferred_agv_id,
        dispatch_origin_x=entity.dispatch_origin_x,
        dispatch_origin_y=entity.dispatch_origin_y,
        created_at=entity.created_at,
        assigned_at=entity.assigned_at,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
        path_to_start=entity.path_to_start,
        path_to_end=entity.path_to_end,
        path_length_to_start=entity.path_length_to_start,
        path_length_to_end=entity.path_length_to_end,
        dispatch_mode=entity.dispatch_mode,
        dispatch_distance=entity.dispatch_distance,
        dispatch_algorithm=entity.dispatch_algorithm,
        dispatch_reason=entity.dispatch_reason,
        cell_wait_retry_count=entity.cell_wait_retry_count,
        cell_wait_retry_budget=entity.cell_wait_retry_budget,
        current_stage_index=entity.current_stage_index,
        total_stages=entity.total_stages,
        overall_start_x=entity.overall_start_x,
        overall_start_y=entity.overall_start_y,
        overall_end_x=entity.overall_end_x,
        overall_end_y=entity.overall_end_y,
        stages=stages,
    )


def task_model_to_entity(model: Task, entity: TaskEntity | None = None) -> TaskEntity:
    payload = _model_dump(model)
    entity = entity or TaskEntity(id=payload["id"])
    entity.start_x = payload["start_x"]
    entity.start_y = payload["start_y"]
    entity.end_x = payload["end_x"]
    entity.end_y = payload["end_y"]
    entity.priority = payload.get("priority", 1)
    entity.status = payload["status"]
    entity.agv_id = payload.get("agv_id")
    entity.preferred_agv_id = payload.get("preferred_agv_id")
    entity.dispatch_origin_x = payload.get("dispatch_origin_x")
    entity.dispatch_origin_y = payload.get("dispatch_origin_y")
    entity.created_at = payload.get("created_at")
    entity.assigned_at = payload.get("assigned_at")
    entity.started_at = payload.get("started_at")
    entity.finished_at = payload.get("finished_at")
    entity.path_to_start = payload.get("path_to_start")
    entity.path_to_end = payload.get("path_to_end")
    entity.path_length_to_start = payload.get("path_length_to_start")
    entity.path_length_to_end = payload.get("path_length_to_end")
    entity.dispatch_mode = payload.get("dispatch_mode")
    entity.dispatch_distance = payload.get("dispatch_distance")
    entity.dispatch_algorithm = payload.get("dispatch_algorithm")
    entity.dispatch_reason = payload.get("dispatch_reason")
    entity.cell_wait_retry_count = payload.get("cell_wait_retry_count", 0)
    entity.cell_wait_retry_budget = payload.get("cell_wait_retry_budget", 1)
    entity.current_stage_index = payload.get("current_stage_index", 0)
    entity.total_stages = payload.get("total_stages", 1)
    entity.overall_start_x = payload.get("overall_start_x")
    entity.overall_start_y = payload.get("overall_start_y")
    entity.overall_end_x = payload.get("overall_end_x")
    entity.overall_end_y = payload.get("overall_end_y")

    incoming_stages = payload.get("stages") or []
    entity.stages = [
        task_stage_model_to_entity(TaskStage(**stage) if isinstance(stage, dict) else stage, payload["id"])
        for stage in incoming_stages
    ]
    return entity


def fault_event_entity_to_model(entity: FaultEventEntity) -> FaultEvent:
    return FaultEvent(
        id=entity.id,
        agv_id=entity.agv_id,
        fault_type=entity.fault_type,
        severity=entity.severity,
        message=entity.message,
        event_type=entity.event_type,
        status=entity.status,
        reported_at=entity.reported_at,
        resolved_at=entity.resolved_at,
        reported_by=entity.reported_by,
        task_id=entity.task_id,
    )


def fault_event_model_to_entity(model: FaultEvent, entity: FaultEventEntity | None = None) -> FaultEventEntity:
    payload = _model_dump(model)
    entity = entity or FaultEventEntity(id=payload["id"])
    entity.agv_id = payload["agv_id"]
    entity.task_id = payload.get("task_id")
    entity.fault_type = payload["fault_type"]
    entity.severity = payload["severity"]
    entity.message = payload.get("message")
    entity.event_type = payload.get("event_type", "fault")
    entity.status = payload.get("status", "open")
    entity.reported_at = payload["reported_at"]
    entity.resolved_at = payload.get("resolved_at")
    entity.reported_by = payload.get("reported_by", "system")
    return entity
