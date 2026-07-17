export function useTaskBuilderState(options) {
  const {
    taskBuilderMode,
    taskChainStages,
    taskForm,
    taskChainMapPickStageCount,
    taskChainMapPickActive,
    taskChainMapPickPoints,
    dispatchMode,
    manualDispatchStep,
    startPoint,
    endPoint,
    manualDisplayTask,
    buildDefaultTaskChainStages,
    createTaskChainStage,
    getSelectedManualDispatchAgv,
    clearAutoMarkers
  } = options

  function addTaskChainStage() {
    setTaskChainStageCount(taskChainStages.value.length + 1)
  }

  function removeTaskChainStage(index) {
    if (taskChainStages.value.length <= 2) return
    taskChainStages.value = taskChainStages.value.filter((_, stageIndex) => stageIndex !== index)
  }

  function resetTaskChainStages() {
    taskChainStages.value = buildDefaultTaskChainStages(taskChainStages.value.length, taskForm.value)
  }

  function setTaskChainStageCount(nextCount) {
    const normalizedCount = Math.max(2, Math.floor(Number(nextCount)))
    if (!Number.isFinite(normalizedCount)) return
    if (normalizedCount === taskChainStages.value.length) return

    if (normalizedCount < taskChainStages.value.length) {
      taskChainStages.value = taskChainStages.value.slice(0, normalizedCount)
      return
    }

    const stages = [...taskChainStages.value]
    while (stages.length < normalizedCount) {
      const previousStage = stages.at(-1)
      stages.push(
        createTaskChainStage({
          start_x: previousStage?.end_x ?? 0,
          start_y: previousStage?.end_y ?? 0,
          end_x: previousStage?.end_x ?? 0,
          end_y: previousStage?.end_y ?? 0
        })
      )
    }

    taskChainStages.value = stages
  }

  function setTaskChainMapPickStageCount(nextCount) {
    const normalizedCount = Math.max(2, Math.floor(Number(nextCount)))
    if (!Number.isFinite(normalizedCount)) return
    taskChainMapPickStageCount.value = normalizedCount
  }

  function toggleTaskBuilderMode() {
    taskBuilderMode.value = taskBuilderMode.value === 'chain' ? 'single' : 'chain'
  }

  function cancelTaskChainMapPick(resetMarkers = true) {
    taskChainMapPickActive.value = false
    taskChainMapPickPoints.value = []
    if (!resetMarkers) return

    if (dispatchMode.value === 'manual') {
      if (manualDisplayTask?.value) {
        return
      }
      manualDispatchStep.value = 'idle'
      startPoint.value = null
      endPoint.value = null
      return
    }
    clearAutoMarkers()
  }

  function toggleTaskChainMapPick() {
    if (dispatchMode.value === 'manual' && !getSelectedManualDispatchAgv()) return

    if (taskChainMapPickActive.value) {
      cancelTaskChainMapPick()
      return
    }

    taskBuilderMode.value = 'chain'
    taskChainMapPickActive.value = true
    taskChainMapPickPoints.value = []
    if (dispatchMode.value === 'manual') {
      if (manualDisplayTask?.value) {
        return
      }
      manualDispatchStep.value = 'idle'
      startPoint.value = null
      endPoint.value = null
      return
    }
    clearAutoMarkers()
  }

  return {
    addTaskChainStage,
    removeTaskChainStage,
    resetTaskChainStages,
    setTaskChainStageCount,
    setTaskChainMapPickStageCount,
    toggleTaskBuilderMode,
    cancelTaskChainMapPick,
    toggleTaskChainMapPick
  }
}
