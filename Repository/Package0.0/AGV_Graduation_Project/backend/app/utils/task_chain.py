from app.models.task import Task, TaskStage


def build_stage_models(stage_items) -> list[TaskStage]:
    stages = []
    for index, item in enumerate(stage_items):
        stages.append(
            TaskStage(
                index=index,
                label=getattr(item, "label", None),
                start_x=int(item.start_x),
                start_y=int(item.start_y),
                end_x=int(item.end_x),
                end_y=int(item.end_y),
            )
        )
    return stages


def ensure_task_stages(task: Task) -> list[TaskStage]:
    if task.stages:
        task.total_stages = len(task.stages)
        task.current_stage_index = max(0, min(task.current_stage_index, len(task.stages) - 1))
        if task.overall_start_x is None:
            task.overall_start_x = task.stages[0].start_x
            task.overall_start_y = task.stages[0].start_y
        if task.overall_end_x is None:
            task.overall_end_x = task.stages[-1].end_x
            task.overall_end_y = task.stages[-1].end_y
        return task.stages

    stage = TaskStage(
        index=0,
        start_x=task.start_x,
        start_y=task.start_y,
        end_x=task.end_x,
        end_y=task.end_y,
        path_to_start=task.path_to_start,
        path_to_end=task.path_to_end,
        path_length_to_start=task.path_length_to_start,
        path_length_to_end=task.path_length_to_end,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )
    task.stages = [stage]
    task.total_stages = 1
    task.current_stage_index = 0
    task.overall_start_x = task.start_x
    task.overall_start_y = task.start_y
    task.overall_end_x = task.end_x
    task.overall_end_y = task.end_y
    return task.stages


def get_current_stage(task: Task) -> TaskStage:
    stages = ensure_task_stages(task)
    return stages[task.current_stage_index]


def sync_task_stage_fields(task: Task) -> TaskStage:
    stage = get_current_stage(task)
    task.start_x = stage.start_x
    task.start_y = stage.start_y
    task.end_x = stage.end_x
    task.end_y = stage.end_y
    task.path_to_start = stage.path_to_start
    task.path_to_end = stage.path_to_end
    task.path_length_to_start = stage.path_length_to_start
    task.path_length_to_end = stage.path_length_to_end
    return stage


def set_stage_paths(task: Task, path_to_start: list[dict], path_to_end: list[dict]) -> TaskStage:
    stage = sync_task_stage_fields(task)
    stage.path_to_start = path_to_start
    stage.path_to_end = path_to_end
    stage.path_length_to_start = max(len(path_to_start) - 1, 0) if path_to_start else 0
    stage.path_length_to_end = max(len(path_to_end) - 1, 0) if path_to_end else 0
    task.path_to_start = stage.path_to_start
    task.path_to_end = stage.path_to_end
    task.path_length_to_start = stage.path_length_to_start
    task.path_length_to_end = stage.path_length_to_end
    return stage


def clear_stage_paths(stage: TaskStage):
    stage.path_to_start = None
    stage.path_to_end = None
    stage.path_length_to_start = None
    stage.path_length_to_end = None
    return stage


def clear_task_paths(task: Task) -> TaskStage:
    stage = sync_task_stage_fields(task)
    clear_stage_paths(stage)
    task.path_to_start = None
    task.path_to_end = None
    task.path_length_to_start = None
    task.path_length_to_end = None
    return stage


def mark_task_pending(task: Task):
    task.status = "pending"
    task.agv_id = None
    task.assigned_at = None
    task.dispatch_distance = None
    task.cell_wait_retry_count = 0
    task.dispatch_reason = None
    clear_task_paths(task)
    return task


def mark_task_blocked(task: Task, reason: str, algorithm: str | None = None):
    task.status = "blocked"
    task.agv_id = None
    task.assigned_at = None
    task.dispatch_distance = None
    task.cell_wait_retry_count = 0
    if algorithm is not None:
        task.dispatch_algorithm = algorithm
    task.dispatch_reason = reason
    clear_task_paths(task)
    return task


def advance_task_stage(task: Task) -> bool:
    stages = ensure_task_stages(task)
    if task.current_stage_index + 1 >= len(stages):
        return False
    task.current_stage_index += 1
    sync_task_stage_fields(task)
    return True
