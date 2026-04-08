import { ref, watch } from 'vue'

function isPanelSectionsObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value)
}

export function useUiSettingsBackend(options) {
  const {
    API_BASE,
    panelSections,
    showMinimap,
    showMarkerIcons,
    showPathArrows,
    showStatusLegend,
    showTopologyEdgeSpeed,
    showRuntimeSegmentType,
    showRuntimeConflictReason,
    showSelectedAgvRuntimeOverlay,
    statusLegendLayout,
    statusLegendOpacity,
    baseSpeed,
    followDistance,
    deadlockTimeoutSec,
    idleReturnTimeoutSec,
    idleChargeTimeoutSec,
    batteryActiveDrainPerSec,
    batteryWaitingDrainPerSec,
    batteryIdleDrainPerSec,
    batteryParkingIdleDrainPerSec,
    batteryChargePerSec,
    compareDisplayMode,
    clampValue,
    buildAuthHeaders
  } = options

  const backendMode = ref('memory')
  const uiSettingsLoadedFromBackend = ref(false)

  let applyingRemoteSettings = false
  let backendSyncReady = false
  let saveTimer = null

  function normalizePanelSections(value) {
    if (!isPanelSectionsObject(value)) {
      return { ...panelSections.value }
    }

    return {
      control: typeof value.control === 'boolean' ? value.control : panelSections.value.control,
      queue: typeof value.queue === 'boolean' ? value.queue : panelSections.value.queue,
      templates: typeof value.templates === 'boolean' ? value.templates : panelSections.value.templates,
      points: typeof value.points === 'boolean' ? value.points : panelSections.value.points,
      json: typeof value.json === 'boolean' ? value.json : panelSections.value.json,
      experiments:
        typeof value.experiments === 'boolean' ? value.experiments : panelSections.value.experiments,
      ai: typeof value.ai === 'boolean' ? value.ai : panelSections.value.ai,
      operations:
        typeof value.operations === 'boolean' ? value.operations : panelSections.value.operations
    }
  }

  function applyUiSettingsPayload(payload) {
    applyingRemoteSettings = true
    try {
      if (typeof payload?.show_minimap === 'boolean') {
        showMinimap.value = payload.show_minimap
      }
      if (typeof payload?.show_marker_icons === 'boolean') {
        showMarkerIcons.value = payload.show_marker_icons
      }
      if (typeof payload?.show_path_arrows === 'boolean') {
        showPathArrows.value = payload.show_path_arrows
      }
      if (typeof payload?.show_status_legend === 'boolean') {
        showStatusLegend.value = payload.show_status_legend
      }
      if (typeof payload?.show_topology_edge_speed === 'boolean') {
        showTopologyEdgeSpeed.value = payload.show_topology_edge_speed
      }
      if (typeof payload?.show_runtime_segment_type === 'boolean') {
        showRuntimeSegmentType.value = payload.show_runtime_segment_type
      }
      if (typeof payload?.show_runtime_conflict_reason === 'boolean') {
        showRuntimeConflictReason.value = payload.show_runtime_conflict_reason
      }
      if (typeof payload?.show_selected_agv_runtime_overlay === 'boolean') {
        showSelectedAgvRuntimeOverlay.value = payload.show_selected_agv_runtime_overlay
      }
      if (payload?.status_legend_layout === 'horizontal' || payload?.status_legend_layout === 'vertical') {
        statusLegendLayout.value = payload.status_legend_layout
      }
      if (typeof payload?.status_legend_opacity === 'number') {
        statusLegendOpacity.value = clampValue(payload.status_legend_opacity, 0.2, 0.9)
      }
      if (typeof payload?.base_speed === 'number') {
        baseSpeed.value = clampValue(payload.base_speed, 0.2, 6)
      }
      if (typeof payload?.follow_distance === 'number') {
        followDistance.value = clampValue(payload.follow_distance, 0.25, 3)
      }
      if (typeof payload?.deadlock_timeout_sec === 'number') {
        deadlockTimeoutSec.value = clampValue(payload.deadlock_timeout_sec, 1, 20)
      }
      if (typeof payload?.idle_return_timeout_sec === 'number') {
        idleReturnTimeoutSec.value = clampValue(payload.idle_return_timeout_sec, 5, 600)
      }
      if (typeof payload?.idle_charge_timeout_sec === 'number') {
        idleChargeTimeoutSec.value = clampValue(payload.idle_charge_timeout_sec, 5, 600)
      }
      if (typeof payload?.battery_active_drain_per_sec === 'number') {
        batteryActiveDrainPerSec.value = clampValue(payload.battery_active_drain_per_sec, 0.01, 10)
      }
      if (typeof payload?.battery_waiting_drain_per_sec === 'number') {
        batteryWaitingDrainPerSec.value = clampValue(payload.battery_waiting_drain_per_sec, 0, 5)
      }
      if (typeof payload?.battery_idle_drain_per_sec === 'number') {
        batteryIdleDrainPerSec.value = clampValue(payload.battery_idle_drain_per_sec, 0, 2)
      }
      if (typeof payload?.battery_parking_idle_drain_per_sec === 'number') {
        batteryParkingIdleDrainPerSec.value = clampValue(payload.battery_parking_idle_drain_per_sec, 0, 2)
      }
      if (typeof payload?.battery_charge_per_sec === 'number') {
        batteryChargePerSec.value = clampValue(payload.battery_charge_per_sec, 0.1, 20)
      }
      if (payload?.compare_display_mode === 'panel' || payload?.compare_display_mode === 'floating') {
        compareDisplayMode.value = payload.compare_display_mode
      }
      panelSections.value = normalizePanelSections(payload?.panel_sections)
      if (typeof payload?.data_backend === 'string' && payload.data_backend) {
        backendMode.value = payload.data_backend
      }
    } finally {
      applyingRemoteSettings = false
    }
  }

  function buildUiSettingsPayload() {
    return {
      show_minimap: showMinimap.value,
      show_marker_icons: showMarkerIcons.value,
      show_path_arrows: showPathArrows.value,
      show_status_legend: showStatusLegend.value,
      show_topology_edge_speed: showTopologyEdgeSpeed.value,
      show_runtime_segment_type: showRuntimeSegmentType.value,
      show_runtime_conflict_reason: showRuntimeConflictReason.value,
      show_selected_agv_runtime_overlay: showSelectedAgvRuntimeOverlay.value,
      status_legend_layout: statusLegendLayout.value,
      status_legend_opacity: Number(statusLegendOpacity.value),
      base_speed: Number(baseSpeed.value),
      follow_distance: Number(followDistance.value),
      deadlock_timeout_sec: Number(deadlockTimeoutSec.value),
      idle_return_timeout_sec: Number(idleReturnTimeoutSec.value),
      idle_charge_timeout_sec: Number(idleChargeTimeoutSec.value),
      battery_active_drain_per_sec: Number(batteryActiveDrainPerSec.value),
      battery_waiting_drain_per_sec: Number(batteryWaitingDrainPerSec.value),
      battery_idle_drain_per_sec: Number(batteryIdleDrainPerSec.value),
      battery_parking_idle_drain_per_sec: Number(batteryParkingIdleDrainPerSec.value),
      battery_charge_per_sec: Number(batteryChargePerSec.value),
      compare_display_mode: compareDisplayMode.value,
      panel_sections: normalizePanelSections(panelSections.value)
    }
  }

  async function readJsonResponse(response) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }

  async function fetchUiSettings() {
    try {
      const response = await fetch(`${API_BASE}/status/ui-settings`, {
        headers: buildAuthHeaders ? buildAuthHeaders() : undefined
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw new Error(data?.detail?.error_code || `UI settings request failed: ${response.status}`)
      }
      applyUiSettingsPayload(data ?? {})
      uiSettingsLoadedFromBackend.value = true
      return true
    } catch (error) {
      console.warn('Load UI settings from backend failed:', error)
      return false
    } finally {
      backendSyncReady = true
    }
  }

  async function persistUiSettings() {
    if (!backendSyncReady || applyingRemoteSettings) return
    try {
      const response = await fetch(`${API_BASE}/status/ui-settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(buildAuthHeaders ? buildAuthHeaders() : {})
        },
        body: JSON.stringify(buildUiSettingsPayload())
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw new Error(data?.detail?.error_code || `UI settings save failed: ${response.status}`)
      }
      if (typeof data?.data_backend === 'string' && data.data_backend) {
        backendMode.value = data.data_backend
      }
      uiSettingsLoadedFromBackend.value = true
    } catch (error) {
      console.warn('Save UI settings to backend failed:', error)
    }
  }

  function scheduleUiSettingsPersist() {
    if (!backendSyncReady || applyingRemoteSettings) return
    if (saveTimer) {
      window.clearTimeout(saveTimer)
    }
    saveTimer = window.setTimeout(() => {
      void persistUiSettings()
    }, 250)
  }

  watch(
    [
      showMinimap,
      showMarkerIcons,
      showPathArrows,
      showStatusLegend,
      showTopologyEdgeSpeed,
      showRuntimeSegmentType,
      showRuntimeConflictReason,
      showSelectedAgvRuntimeOverlay,
      statusLegendLayout,
      statusLegendOpacity,
      baseSpeed,
      followDistance,
      deadlockTimeoutSec,
      idleReturnTimeoutSec,
      idleChargeTimeoutSec,
      batteryActiveDrainPerSec,
      batteryWaitingDrainPerSec,
      batteryIdleDrainPerSec,
      batteryParkingIdleDrainPerSec,
      batteryChargePerSec,
      compareDisplayMode
    ],
    () => {
      scheduleUiSettingsPersist()
    }
  )

  watch(
    panelSections,
    () => {
      scheduleUiSettingsPersist()
    },
    { deep: true }
  )

  return {
    backendMode,
    uiSettingsLoadedFromBackend,
    fetchUiSettings
  }
}
