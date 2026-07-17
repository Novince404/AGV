import { computed } from 'vue'

export function useTaskDisplayState(options) {
  const {
    tasks,
    selectedAgvId,
    trackedManualTaskId,
    dispatchMode,
    taskBuilderMode,
    taskChainMapPickActive,
    taskChainMapPickPoints,
    taskChainRequiredPointCount,
    shouldShowAutoPath,
    suppressAutoRuntimeVisuals,
    startPoint,
    endPoint,
    manualPathToStart,
    manualPathToEnd,
    autoPathToStart,
    autoPathToEnd,
    minimapCellSize,
    compareTime,
    toSvgPoints,
    taskRemainingWaypoints,
    taskChainMidPoints,
    resolveTaskDisplayStartMarker,
    resolveTaskDisplayEndMarker,
    resolveTaskEndMarker,
    resolveTaskOverallEndMarker
  } = options

  function activeTaskSort(a, b) {
    return compareTime(b.assigned_at, a.assigned_at) || b.priority - a.priority || b.id - a.id
  }

  function findLatestActiveTask(mode) {
    const activeTasks = tasks.value
      .filter(task => ['assigned', 'running'].includes(task.status) && task.dispatch_mode === mode)
      .sort(activeTaskSort)

    if (mode === 'manual' && selectedAgvId.value) {
      return activeTasks.find(task => task.agv_id === selectedAgvId.value) ?? activeTasks[0] ?? null
    }

    return activeTasks[0] ?? null
  }

  const autoDisplayTask = computed(() => findLatestActiveTask('auto'))
  const manualDisplayTask = computed(() => {
    if (trackedManualTaskId.value) {
      const trackedTask = tasks.value.find(
        task =>
          task.id === trackedManualTaskId.value &&
          task.dispatch_mode === 'manual' &&
          ['assigned', 'running'].includes(task.status)
      )
      if (trackedTask) return trackedTask
    }
    return findLatestActiveTask('manual')
  })

  const manualChainRoutePoints = computed(() => {
    const task = manualDisplayTask.value
    if (!task || Number(task.total_stages ?? 1) <= 1) return ''
    return toSvgPoints(taskRemainingWaypoints(task))
  })

  const autoChainRoutePoints = computed(() => {
    if (!shouldShowAutoPath.value || suppressAutoRuntimeVisuals.value) return ''
    const task = autoDisplayTask.value
    if (!task || Number(task.total_stages ?? 1) <= 1) return ''
    return toSvgPoints(taskRemainingWaypoints(task))
  })

  const minimapManualChainRoutePoints = computed(() => {
    const task = manualDisplayTask.value
    if (!task || Number(task.total_stages ?? 1) <= 1) return ''
    return toSvgPoints(taskRemainingWaypoints(task), minimapCellSize.value)
  })

  const minimapAutoChainRoutePoints = computed(() => {
    if (!shouldShowAutoPath.value || suppressAutoRuntimeVisuals.value) return ''
    const task = autoDisplayTask.value
    if (!task || Number(task.total_stages ?? 1) <= 1) return ''
    return toSvgPoints(taskRemainingWaypoints(task), minimapCellSize.value)
  })

  function shouldHideDraftManualMarkersInAutoMode() {
    return (
      dispatchMode.value === 'auto' &&
      autoDisplayTask.value &&
      !trackedManualTaskId.value &&
      !startPoint.value &&
      !endPoint.value &&
      !taskChainMapPickActive.value
    )
  }

  const manualDisplayStartMarker = computed(() => {
    if (manualDisplayTask.value) {
      return resolveTaskDisplayStartMarker(manualDisplayTask.value)
    }
    if (shouldHideDraftManualMarkersInAutoMode()) {
      return null
    }
    return startPoint.value ?? manualPathToStart.value.at(-1) ?? manualPathToEnd.value[0] ?? null
  })

  const manualDisplayEndMarker = computed(() => {
    if (manualDisplayTask.value) {
      return resolveTaskDisplayEndMarker(manualDisplayTask.value)
    }
    if (shouldHideDraftManualMarkersInAutoMode()) {
      return null
    }
    if (
      taskBuilderMode.value === 'chain' &&
      taskChainMapPickActive.value &&
      taskChainMapPickPoints.value.length < taskChainRequiredPointCount.value
    ) {
      return null
    }
    return endPoint.value ?? manualPathToEnd.value.at(-1) ?? null
  })

  const autoDisplayStartMarker = computed(() => {
    if (!shouldShowAutoPath.value || suppressAutoRuntimeVisuals.value) return null
    const task = autoDisplayTask.value
    if (task) {
      return resolveTaskDisplayStartMarker(task)
    }
    return autoPathToStart.value.at(-1) ?? autoPathToEnd.value[0] ?? null
  })

  const autoDisplayEndMarker = computed(() => {
    if (!shouldShowAutoPath.value || suppressAutoRuntimeVisuals.value) return null
    if (
      taskBuilderMode.value === 'chain' &&
      taskChainMapPickActive.value &&
      taskChainMapPickPoints.value.length < taskChainRequiredPointCount.value
    ) {
      return null
    }
    const task = autoDisplayTask.value
    if (task && Number(task.total_stages ?? 1) > 1) {
      return resolveTaskOverallEndMarker(task)
    }
    return resolveTaskEndMarker(task) ?? autoPathToEnd.value.at(-1) ?? null
  })

  const chainMidMarkers = computed(() => {
    if (
      taskChainMapPickActive.value &&
      manualDisplayTask.value &&
      Number(manualDisplayTask.value.total_stages ?? 1) > 1
    ) {
      return taskChainMidPoints(manualDisplayTask.value)
    }
    if (!taskChainMapPickActive.value) {
      const chainTask =
        (manualDisplayTask.value && Number(manualDisplayTask.value.total_stages ?? 1) > 1
          ? manualDisplayTask.value
          : null) ??
        (shouldShowAutoPath.value && autoDisplayTask.value && Number(autoDisplayTask.value.total_stages ?? 1) > 1
          ? autoDisplayTask.value
          : null)
      return chainTask ? taskChainMidPoints(chainTask) : []
    }
    const picked = taskChainMapPickPoints.value
    const required = taskChainRequiredPointCount.value
    const incomplete = picked.length < required
    const points = incomplete ? picked.slice(1) : picked.slice(1, -1)
    return points.map((point, index) => ({
      ...point,
      order: index + 1
    }))
  })

  return {
    activeTaskSort,
    findLatestActiveTask,
    autoDisplayTask,
    manualDisplayTask,
    manualChainRoutePoints,
    autoChainRoutePoints,
    minimapManualChainRoutePoints,
    minimapAutoChainRoutePoints,
    manualDisplayStartMarker,
    manualDisplayEndMarker,
    autoDisplayStartMarker,
    autoDisplayEndMarker,
    chainMidMarkers
  }
}
