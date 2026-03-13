import { currentTaskStage } from './taskChain'
import { clampValue } from './mapGeometry'

export function isFinitePoint(point) {
  return Number.isFinite(Number(point?.x)) && Number.isFinite(Number(point?.y))
}

export function taskStageWaypoints(task) {
  const stages = Array.isArray(task?.stages) ? task.stages : []
  if (stages.length === 0) return []

  const points = []
  const firstStage = stages[0]
  if (isFinitePoint({ x: firstStage?.start_x, y: firstStage?.start_y })) {
    points.push({ x: Number(firstStage.start_x), y: Number(firstStage.start_y) })
  }
  for (const stage of stages) {
    if (isFinitePoint({ x: stage?.end_x, y: stage?.end_y })) {
      points.push({ x: Number(stage.end_x), y: Number(stage.end_y) })
    }
  }
  return points
}

export function taskCurrentStageIndex(task) {
  const stages = Array.isArray(task?.stages) ? task.stages : []
  const idx = Number(task?.current_stage_index ?? 0)
  if (!Number.isFinite(idx)) return 0
  if (stages.length === 0) return Math.max(0, Math.floor(idx))
  return clampValue(Math.floor(idx), 0, stages.length - 1)
}

export function taskStageCount(task) {
  const explicitCount = Number(task?.total_stages)
  if (Number.isFinite(explicitCount) && explicitCount > 0) {
    return explicitCount
  }
  const stages = Array.isArray(task?.stages) ? task.stages : []
  return Math.max(stages.length, 1)
}

export function taskRemainingWaypoints(task) {
  const stages = Array.isArray(task?.stages) ? task.stages : []
  if (stages.length === 0) return []

  const stageIndex = taskCurrentStageIndex(task)
  const currentStage = stages[stageIndex]
  const points = []
  const currentStageStart =
    currentStage?.path_to_start?.at(-1) ??
    (isFinitePoint({ x: currentStage?.start_x, y: currentStage?.start_y })
      ? { x: Number(currentStage.start_x), y: Number(currentStage.start_y) }
      : null)

  if (isFinitePoint(currentStageStart)) {
    points.push({ x: Number(currentStageStart.x), y: Number(currentStageStart.y) })
  }

  for (let index = stageIndex; index < stages.length; index += 1) {
    const stage = stages[index]
    if (isFinitePoint({ x: stage?.end_x, y: stage?.end_y })) {
      points.push({ x: Number(stage.end_x), y: Number(stage.end_y) })
    }
  }

  return points
}

export function taskChainMidPoints(task) {
  const waypoints = taskStageWaypoints(task)
  if (waypoints.length <= 2) return []
  const stageIndex = taskCurrentStageIndex(task)
  const firstVisibleMidpointIndex = Math.max(1, stageIndex)
  const lastMidpointIndex = waypoints.length - 2
  const points = []

  for (let waypointIndex = firstVisibleMidpointIndex; waypointIndex <= lastMidpointIndex; waypointIndex += 1) {
    const point = waypoints[waypointIndex]
    points.push({
      ...point,
      // Keep stable global midpoint numbering across stage transitions.
      order: waypointIndex
    })
  }

  return points
}

export function resolveTaskStartMarker(task) {
  if (!task) return null
  const stage = currentTaskStage(task)
  return (
    stage?.path_to_start?.at(-1) ??
    stage?.path_to_end?.[0] ?? {
      x: stage?.start_x ?? task.start_x,
      y: stage?.start_y ?? task.start_y
    }
  )
}

export function resolveTaskDisplayStartMarker(task) {
  if (!task) return null
  if (taskStageCount(task) > 1 && taskCurrentStageIndex(task) > 0) {
    return null
  }
  return resolveTaskStartMarker(task)
}

export function resolveTaskEndMarker(task) {
  if (!task) return null
  const stage = currentTaskStage(task)
  return stage?.path_to_end?.at(-1) ?? { x: stage?.end_x ?? task.end_x, y: stage?.end_y ?? task.end_y }
}

export function resolveTaskOverallEndMarker(task) {
  if (
    Number.isFinite(Number(task?.overall_end_x)) &&
    Number.isFinite(Number(task?.overall_end_y))
  ) {
    return {
      x: Number(task.overall_end_x),
      y: Number(task.overall_end_y)
    }
  }
  const waypoints = taskStageWaypoints(task)
  if (waypoints.length > 0) return waypoints.at(-1)
  return resolveTaskEndMarker(task)
}

export function resolveTaskDisplayEndMarker(task) {
  if (!task) return null
  return taskStageCount(task) > 1 ? resolveTaskOverallEndMarker(task) : resolveTaskEndMarker(task)
}

export function taskDispatchOrigin(task) {
  if (
    task?.dispatch_origin_x !== null &&
    task?.dispatch_origin_x !== undefined &&
    task?.dispatch_origin_y !== null &&
    task?.dispatch_origin_y !== undefined
  ) {
    return {
      x: Number(task.dispatch_origin_x),
      y: Number(task.dispatch_origin_y)
    }
  }
  const firstPoint = task?.path_to_start?.[0]
  if (firstPoint && Number.isFinite(Number(firstPoint.x)) && Number.isFinite(Number(firstPoint.y))) {
    return {
      x: Number(firstPoint.x),
      y: Number(firstPoint.y)
    }
  }
  return null
}
