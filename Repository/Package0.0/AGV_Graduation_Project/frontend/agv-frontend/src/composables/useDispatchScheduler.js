export function useDispatchScheduler(options) {
  const {
    API_BASE,
    GRID_COLS,
    GRID_ROWS,
    algorithm,
    dispatchMode,
    obstacleEditMode,
    obstacleLayoutDirty,
    agvs,
    tasks,
    autoPathToStart,
    autoPathToEnd,
    manualPathToStart,
    manualPathToEnd,
    selectedAgvId,
    trackedManualTaskId,
    startPoint,
    endPoint,
    manualDispatchStep,
    autoScheduling,
    autoScheduleGuard,
    manualBoundScheduling,
    nextTick,
    fetchAgvs,
    fetchTasks,
    buildAuthorizedJsonHeaders,
    hasIdleAgv,
    hasPendingTask,
    resolveTaskDisplayStartMarker,
    resolveTaskDisplayEndMarker,
    resolveTaskStartMarker,
    resolveTaskEndMarker,
    resolveTaskOverallEndMarker,
    bumpManualPreviewMinVisible
  } = options

  function resolveValue(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value
  }

  function gridCols() {
    return Number(resolveValue(GRID_COLS))
  }

  function gridRows() {
    return Number(resolveValue(GRID_ROWS))
  }

  function buildScheduleHeaders() {
    if (typeof buildAuthorizedJsonHeaders === 'function') {
      return buildAuthorizedJsonHeaders()
    }
    return { 'Content-Type': 'application/json' }
  }

  async function refreshAfterScheduleStarts() {
    await new Promise(resolve => setTimeout(resolve, 90))
    await Promise.all([fetchAgvs(), fetchTasks()])
  }

  function resolveTaskDisplayEndMarkerLocal(task) {
    if (Number(task?.total_stages ?? 1) > 1 && typeof resolveTaskOverallEndMarker === 'function') {
      return resolveTaskOverallEndMarker(task)
    }
    return resolveTaskEndMarker(task)
  }

  function resolveTaskDisplayStartMarkerLocal(task) {
    if (typeof resolveTaskDisplayStartMarker === 'function') {
      return resolveTaskDisplayStartMarker(task)
    }
    return resolveTaskStartMarker(task)
  }

  function mergeTaskDisplayPayload(taskPayload, fallbackTask) {
    if (!taskPayload) return fallbackTask
    if (!fallbackTask) return taskPayload
    return {
      ...fallbackTask,
      ...taskPayload,
      stages:
        Array.isArray(taskPayload.stages) && taskPayload.stages.length > 0
          ? taskPayload.stages
          : fallbackTask.stages,
      overall_start_x:
        taskPayload.overall_start_x ?? fallbackTask.overall_start_x ?? fallbackTask.start_x ?? taskPayload.start_x,
      overall_start_y:
        taskPayload.overall_start_y ?? fallbackTask.overall_start_y ?? fallbackTask.start_y ?? taskPayload.start_y,
      overall_end_x: taskPayload.overall_end_x ?? fallbackTask.overall_end_x ?? fallbackTask.end_x ?? taskPayload.end_x,
      overall_end_y: taskPayload.overall_end_y ?? fallbackTask.overall_end_y ?? fallbackTask.end_y ?? taskPayload.end_y
    }
  }

  async function tryAutoSchedule() {
    if (autoScheduling.value) return
    if (autoScheduleGuard.value) return
    if (obstacleEditMode.value || obstacleLayoutDirty.value) return
    if (!hasIdleAgv() || !hasPendingTask()) return

    autoScheduling.value = true
    try {
      const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
        method: 'POST',
        headers: buildScheduleHeaders(),
        body: JSON.stringify({
          task_id: null,
          agv_id: null,
          schedule_mode: 'auto',
          algorithm: algorithm.value,
          grid_cols: gridCols(),
          grid_rows: gridRows()
        })
      })
      const scheduleData = await scheduleRes.json()
      if (!scheduleRes.ok) {
        await fetchTasks()
        return
      }

      autoPathToStart.value = scheduleData.path_to_start ?? []
      autoPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
      await refreshAfterScheduleStarts()
    } catch (error) {
      console.error('Auto schedule error:', error)
    } finally {
      autoScheduling.value = false
    }
  }

  async function tryManualBoundSchedule() {
    if (manualBoundScheduling.value) return
    if (obstacleEditMode.value || obstacleLayoutDirty.value) return

    const idleAgvIds = new Set(
      agvs.value
        .filter(agv => ['idle', 'idle_returning'].includes(String(agv?.status || '')))
        .map(agv => agv.id)
    )
    const candidate = tasks.value
      .filter(
        task =>
          task.status === 'pending' &&
          task.dispatch_mode === 'manual' &&
          Number.isInteger(task.preferred_agv_id) &&
          idleAgvIds.has(task.preferred_agv_id)
      )
      .sort((a, b) => {
        const priorityDiff = Number(b.priority ?? 0) - Number(a.priority ?? 0)
        if (priorityDiff !== 0) return priorityDiff
        return Number(a.id ?? 0) - Number(b.id ?? 0)
      })[0]

    if (!candidate) return

    manualBoundScheduling.value = true
    try {
      const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
        method: 'POST',
        headers: buildScheduleHeaders(),
        body: JSON.stringify({
          task_id: candidate.id,
          agv_id: candidate.preferred_agv_id,
          schedule_mode: 'manual',
          algorithm: (candidate.dispatch_algorithm || algorithm.value || 'simple').toLowerCase(),
          grid_cols: gridCols(),
          grid_rows: gridRows()
        })
      })
      const scheduleData = await scheduleRes.json()
      if (!scheduleRes.ok) {
        await fetchTasks()
        return
      }

      if (
        dispatchMode.value === 'manual' ||
        selectedAgvId.value === scheduleData?.agv?.id ||
        trackedManualTaskId.value === candidate.id
      ) {
        const displayTask = mergeTaskDisplayPayload(scheduleData?.task, candidate)
        trackedManualTaskId.value = scheduleData?.task?.id ?? candidate.id
        startPoint.value = resolveTaskDisplayStartMarkerLocal(displayTask)
        endPoint.value =
          typeof resolveTaskDisplayEndMarker === 'function'
            ? resolveTaskDisplayEndMarker(displayTask)
            : resolveTaskDisplayEndMarkerLocal(displayTask)
        manualDispatchStep.value = 'running'
        bumpManualPreviewMinVisible()
        manualPathToStart.value = scheduleData.path_to_start ?? []
        manualPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
        await refreshAfterScheduleStarts()
      } else {
        await refreshAfterScheduleStarts()
      }
    } catch (error) {
      console.error('Manual bound schedule error:', error)
    } finally {
      manualBoundScheduling.value = false
    }
  }

  async function scheduleAutoIfReady() {
    await nextTick()
    await tryAutoSchedule()
  }

  return {
    tryAutoSchedule,
    tryManualBoundSchedule,
    scheduleAutoIfReady
  }
}
