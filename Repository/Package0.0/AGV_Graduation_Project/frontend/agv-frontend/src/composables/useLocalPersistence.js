export function useLocalPersistence(options) {
  const {
    storageKeys,
    panelSections,
    panelSummaryMode,
    queueGroupsCollapsed,
    taskCardCollapsed,
    experimentRecords,
    customPoints,
    customTaskTemplates,
    dispatchMode,
    showAutoPath,
    showMarkerIcons,
    showPathArrows,
    showStatusLegend,
    statusLegendLayout,
    statusLegendOpacity,
    showMinimap,
    topologyViewMode,
    showGuideCenterOnLoad,
    compareDisplayMode,
    compareFloatingOpacity,
    clampValue,
    normalizeCustomPoints,
    templateFromStored
  } = options

  function loadPanelSections() {
    try {
      const raw = window.localStorage.getItem(storageKeys.panelSections)
      if (!raw) return

      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return

      panelSections.value = {
        ...panelSections.value,
        control: typeof parsed.control === 'boolean' ? parsed.control : panelSections.value.control,
        queue: typeof parsed.queue === 'boolean' ? parsed.queue : panelSections.value.queue,
        templates:
          typeof parsed.templates === 'boolean' ? parsed.templates : panelSections.value.templates,
        points: typeof parsed.points === 'boolean' ? parsed.points : panelSections.value.points,
        json: typeof parsed.json === 'boolean' ? parsed.json : panelSections.value.json,
        experiments:
          typeof parsed.experiments === 'boolean' ? parsed.experiments : panelSections.value.experiments,
        ai: typeof parsed.ai === 'boolean' ? parsed.ai : panelSections.value.ai,
        operations:
          typeof parsed.operations === 'boolean' ? parsed.operations : panelSections.value.operations
      }
    } catch (error) {
      console.error('Load panel sections error:', error)
    }
  }

  function savePanelSections() {
    try {
      window.localStorage.setItem(storageKeys.panelSections, JSON.stringify(panelSections.value))
    } catch (error) {
      console.error('Save panel sections error:', error)
    }
  }

  function loadPanelSummaryMode() {
    try {
      const raw = window.localStorage.getItem(storageKeys.panelSummaryMode)
      if (!raw) return
      if (['hidden', 'compact', 'full'].includes(raw)) {
        panelSummaryMode.value = raw
      }
    } catch (error) {
      console.error('Load panel summary mode error:', error)
    }
  }

  function savePanelSummaryMode() {
    try {
      window.localStorage.setItem(storageKeys.panelSummaryMode, panelSummaryMode.value)
    } catch (error) {
      console.error('Save panel summary mode error:', error)
    }
  }

  function loadTaskQueueView() {
    try {
      const raw = window.localStorage.getItem(storageKeys.taskQueueView)
      if (!raw) return

      const parsed = JSON.parse(raw)
      if (parsed?.groups && typeof parsed.groups === 'object') {
        queueGroupsCollapsed.value = {
          ...queueGroupsCollapsed.value,
          pending:
            typeof parsed.groups.pending === 'boolean'
              ? parsed.groups.pending
              : queueGroupsCollapsed.value.pending,
          blocked:
            typeof parsed.groups.blocked === 'boolean'
              ? parsed.groups.blocked
              : queueGroupsCollapsed.value.blocked,
          assigned:
            typeof parsed.groups.assigned === 'boolean'
              ? parsed.groups.assigned
              : queueGroupsCollapsed.value.assigned,
          running:
            typeof parsed.groups.running === 'boolean'
              ? parsed.groups.running
              : queueGroupsCollapsed.value.running,
          finished:
            typeof parsed.groups.finished === 'boolean'
              ? parsed.groups.finished
              : queueGroupsCollapsed.value.finished
        }
      }

      if (parsed?.cards && typeof parsed.cards === 'object') {
        taskCardCollapsed.value = Object.fromEntries(
          Object.entries(parsed.cards)
            .filter(([taskId, collapsed]) => taskId && typeof collapsed === 'boolean')
            .map(([taskId, collapsed]) => [String(taskId), collapsed])
        )
      }
    } catch (error) {
      console.error('Load task queue view error:', error)
    }
  }

  function saveTaskQueueView() {
    try {
      window.localStorage.setItem(
        storageKeys.taskQueueView,
        JSON.stringify({
          groups: queueGroupsCollapsed.value,
          cards: taskCardCollapsed.value
        })
      )
    } catch (error) {
      console.error('Save task queue view error:', error)
    }
  }

  function loadExperimentRecords() {
    try {
      const raw = window.localStorage.getItem(storageKeys.experimentRecords)
      if (!raw) return

      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return

      experimentRecords.value = parsed.filter(
        record =>
          record &&
          typeof record === 'object' &&
          record.id &&
          record.saved_at &&
          record.route_summary &&
          Array.isArray(record.algorithms)
      )
    } catch (error) {
      console.error('Load experiment records error:', error)
    }
  }

  function saveExperimentRecords() {
    try {
      window.localStorage.setItem(storageKeys.experimentRecords, JSON.stringify(experimentRecords.value))
    } catch (error) {
      console.error('Save experiment records error:', error)
    }
  }

  function loadCustomPoints() {
    try {
      const raw = window.localStorage.getItem(storageKeys.customPoints)
      if (!raw) return

      const parsed = JSON.parse(raw)
      customPoints.value = normalizeCustomPoints(parsed)
    } catch (error) {
      console.error('Load custom points error:', error)
    }
  }

  function saveCustomPoints() {
    try {
      window.localStorage.setItem(storageKeys.customPoints, JSON.stringify(customPoints.value))
    } catch (error) {
      console.error('Save custom points error:', error)
    }
  }

  function loadMapDisplaySettings() {
    try {
      const raw = window.localStorage.getItem(storageKeys.mapDisplay)
      if (!raw) return

      const parsed = JSON.parse(raw)
      if (parsed?.dispatchMode === 'auto' || parsed?.dispatchMode === 'manual') {
        dispatchMode.value = parsed.dispatchMode
      }
      if (typeof parsed?.showAutoPath === 'boolean') {
        showAutoPath.value = parsed.showAutoPath
      }
      if (typeof parsed?.showMarkerIcons === 'boolean') {
        showMarkerIcons.value = parsed.showMarkerIcons
      }
      if (typeof parsed?.showPathArrows === 'boolean') {
        showPathArrows.value = parsed.showPathArrows
      }
      if (typeof parsed?.showStatusLegend === 'boolean') {
        showStatusLegend.value = parsed.showStatusLegend
      }
      if (parsed?.statusLegendLayout === 'horizontal' || parsed?.statusLegendLayout === 'vertical') {
        statusLegendLayout.value = parsed.statusLegendLayout
      }
      if (typeof parsed?.statusLegendOpacity === 'number') {
        statusLegendOpacity.value = clampValue(parsed.statusLegendOpacity, 0.2, 0.9)
      }
      if (typeof parsed?.showMinimap === 'boolean') {
        showMinimap.value = parsed.showMinimap
      }
      if (parsed?.topologyViewMode === 'standard' || parsed?.topologyViewMode === 'pure') {
        topologyViewMode.value = parsed.topologyViewMode
      }
      if (typeof parsed?.showGuideCenterOnLoad === 'boolean') {
        showGuideCenterOnLoad.value = parsed.showGuideCenterOnLoad
      }
      if (parsed?.compareDisplayMode === 'panel' || parsed?.compareDisplayMode === 'floating') {
        compareDisplayMode.value = parsed.compareDisplayMode
      }
      if (typeof parsed?.compareFloatingOpacity === 'number') {
        compareFloatingOpacity.value = clampValue(parsed.compareFloatingOpacity, 0.45, 1)
      }
    } catch (error) {
      console.error('Load map display settings error:', error)
    }
  }

  function saveMapDisplaySettings() {
    try {
      window.localStorage.setItem(
        storageKeys.mapDisplay,
        JSON.stringify({
          showAutoPath: showAutoPath.value,
          showMarkerIcons: showMarkerIcons.value,
          showPathArrows: showPathArrows.value,
          showStatusLegend: showStatusLegend.value,
          statusLegendLayout: statusLegendLayout.value,
          statusLegendOpacity: statusLegendOpacity.value,
          showMinimap: showMinimap.value,
          topologyViewMode: topologyViewMode.value,
          showGuideCenterOnLoad: showGuideCenterOnLoad.value,
          dispatchMode: dispatchMode.value,
          compareDisplayMode: compareDisplayMode.value,
          compareFloatingOpacity: compareFloatingOpacity.value
        })
      )
    } catch (error) {
      console.error('Save map display settings error:', error)
    }
  }

  function loadTaskTemplates() {
    try {
      const raw = window.localStorage.getItem(storageKeys.taskTemplates)
      if (!raw) return

      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return

      customTaskTemplates.value = parsed.map(templateFromStored).filter(Boolean)
    } catch (error) {
      console.error('Load task templates error:', error)
    }
  }

  function saveTaskTemplates() {
    try {
      window.localStorage.setItem(storageKeys.taskTemplates, JSON.stringify(customTaskTemplates.value))
    } catch (error) {
      console.error('Save task templates error:', error)
    }
  }

  return {
    loadPanelSections,
    savePanelSections,
    loadPanelSummaryMode,
    savePanelSummaryMode,
    loadTaskQueueView,
    saveTaskQueueView,
    loadExperimentRecords,
    saveExperimentRecords,
    loadCustomPoints,
    saveCustomPoints,
    loadMapDisplaySettings,
    saveMapDisplaySettings,
    loadTaskTemplates,
    saveTaskTemplates
  }
}
