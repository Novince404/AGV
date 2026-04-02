<script setup>
import './assets/agv-map.css'
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LOCALE_TEXTS } from './locales'
import { DEFAULT_POINT_LIBRARY, DEFAULT_TASK_TEMPLATES } from './config/defaultData'
import { useDispatchScheduler } from './composables/useDispatchScheduler'
import { useLocalPersistence } from './composables/useLocalPersistence'
import { usePointTemplateBackend } from './composables/usePointTemplateBackend'
import { useUiSettingsBackend } from './composables/useUiSettingsBackend'
import { useAuthSession } from './composables/useAuthSession'
import { useTemplatePointActions } from './composables/useTemplatePointActions'
import { usePanelCompareUi } from './composables/usePanelCompareUi'
import { useDataExportActions } from './composables/useDataExportActions'
import { useMapViewport } from './composables/useMapViewport'
import { useTaskBuilderState } from './composables/useTaskBuilderState'
import { useTaskDisplayState } from './composables/useTaskDisplayState'
import { useLocaleText } from './composables/useLocaleText'
import { useTaskPreview } from './composables/useTaskPreview'
import { useUiLocales } from './composables/useUiLocales'
import { useTaskTextFormatters } from './composables/useTaskTextFormatters'
import {
  buildDefaultTaskChainStages,
  buildTaskJsonExamplePayload,
  createTaskChainStage,
  currentTaskStage,
  isTaskChain,
  normalizeTaskStages,
  overallTaskEnd,
  overallTaskStart
} from './utils/taskChain'
import { buildDefaultQueueGroupState, compareTime, sortTasks } from './utils/taskQueue'
import { rowsToCsv } from './utils/csv'
import { downloadCsvFile, downloadJsonFile } from './utils/fileDownload'
import {
  buildDefaultComfyPromptText,
  buildDefaultComfyWorkflowTemplate,
  COMFY_PROMPT_STYLE_DEFAULT,
  COMFY_WORKFLOW_PRESET_DEFAULT,
  getComfyPromptStyleConfig,
  getComfyWorkflowPresetConfig
} from './utils/comfyWorkflowTemplates'
import { blockedCellKey, clampValue, pointStyle, toArrowSegments, toSvgPoints } from './utils/mapGeometry'
import {
  resolveTaskDisplayEndMarker,
  resolveTaskDisplayStartMarker,
  resolveTaskEndMarker,
  resolveTaskOverallEndMarker,
  resolveTaskStartMarker,
  taskChainMidPoints,
  taskDispatchOrigin,
  taskRemainingWaypoints
} from './utils/taskMarkers'
import {
  buildTaskTemplateSignature as buildTaskTemplateSignatureRaw,
  buildTemplateExportPayload as buildTemplateExportPayloadRaw,
  buildTemplateFromStages as buildTemplateFromStagesRaw,
  formatTemplateJsonSummary as formatTemplateJsonSummaryRaw,
  isValidGridCoordinate,
  normalizeImportedTaskTemplate as normalizeImportedTaskTemplateRaw,
  normalizeTemplateStages as normalizeTemplateStagesRaw
} from './utils/templateHelpers'
import { buildCustomPoint, normalizeStoredCustomPoints } from './utils/pointHelpers'

const ComfyAiWorkspace = defineAsyncComponent(() => import('./components/ComfyAiWorkspace.vue'))
const EnterpriseSettingsDialog = defineAsyncComponent(() => import('./components/EnterpriseSettingsDialog.vue'))
const EnterpriseApprovalDialog = defineAsyncComponent(() => import('./components/EnterpriseApprovalDialog.vue'))
const PlatformAccountGovernanceDialog = defineAsyncComponent(() => import('./components/PlatformAccountGovernanceDialog.vue'))
const PlatformAdminGovernanceHub = defineAsyncComponent(() => import('./components/PlatformAdminGovernanceHub.vue'))
const EnterpriseRequestDialog = defineAsyncComponent(() => import('./components/EnterpriseRequestDialog.vue'))
const PlatformBugFeedbackDialog = defineAsyncComponent(() => import('./components/PlatformBugFeedbackDialog.vue'))
const AuthDialog = defineAsyncComponent(() => import('./components/AuthDialog.vue'))
const OperationsAuditPanel = defineAsyncComponent(() => import('./components/OperationsAuditPanel.vue'))
const ExperimentRecordsPanel = defineAsyncComponent(() => import('./components/ExperimentRecordsPanel.vue'))
const TaskTemplatesPanel = defineAsyncComponent(() => import('./components/TaskTemplatesPanel.vue'))
const PointLibraryPanel = defineAsyncComponent(() => import('./components/PointLibraryPanel.vue'))
const JsonToolsPanel = defineAsyncComponent(() => import('./components/JsonToolsPanel.vue'))
const TaskQueuePanel = defineAsyncComponent(() => import('./components/TaskQueuePanel.vue'))
const FaultOperationsPanel = defineAsyncComponent(() => import('./components/FaultOperationsPanel.vue'))
const TaskBuilderPanel = defineAsyncComponent(() => import('./components/TaskBuilderPanel.vue'))
const DispatchControlSummaryPanel = defineAsyncComponent(() => import('./components/DispatchControlSummaryPanel.vue'))
const FloatingComparePanel = defineAsyncComponent(() => import('./components/FloatingComparePanel.vue'))
const MapSettingsPanel = defineAsyncComponent(() => import('./components/MapSettingsPanel.vue'))
const GuideCenterDialog = defineAsyncComponent(() => import('./components/GuideCenterDialog.vue'))

const GRID_COLS = 10
const GRID_ROWS = 8
const CELL_SIZE = 50
const AGV_SIZE = 30
const API_BASE = (() => {
  const configured = import.meta.env.VITE_API_BASE?.trim()
  if (configured) {
    return configured.replace(/\/$/, '')
  }
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location
    if (port === '8000') {
      return `${protocol}//${hostname}${port ? `:${port}` : ''}`
    }
  }
  return 'http://127.0.0.1:8000'
})()
const CUSTOM_POINTS_STORAGE_KEY = 'agv_custom_points'
const MAP_DISPLAY_STORAGE_KEY = 'agv_map_display_settings'
const TASK_TEMPLATE_STORAGE_KEY = 'agv_task_templates'
const PANEL_SECTION_STORAGE_KEY = 'agv_panel_sections'
const PANEL_SUMMARY_MODE_STORAGE_KEY = 'agv_panel_summary_mode'
const TASK_QUEUE_VIEW_STORAGE_KEY = 'agv_task_queue_view'
const EXPERIMENT_RECORDS_STORAGE_KEY = 'agv_experiment_records'
const COMFY_WORKFLOW_TEMPLATE_STORAGE_KEY = 'agv_comfy_workflow_templates'
const SHORTCUT_PREFERENCES_STORAGE_KEY = 'agv_shortcut_preferences'
const ENTERPRISE_SETTINGS_TAB_STORAGE_KEY = 'agv_enterprise_settings_tabs'
const ENTERPRISE_SETTINGS_SIDEBAR_STORAGE_KEY = 'agv_enterprise_settings_sidebar_collapsed'
const PANEL_SECTION_KEYS = ['control', 'queue', 'templates', 'points', 'json', 'experiments', 'ai', 'operations']
const ENTERPRISE_REGISTER_DRAFT_STORAGE_KEY = 'agv_enterprise_register_draft'
const ENTERPRISE_REGISTER_FOLLOWUP_STORAGE_KEY = 'agv_enterprise_register_followup'
const ENTERPRISE_APPROVAL_UI_STORAGE_KEY = 'agv_enterprise_approval_ui'
const ENTERPRISE_STATUS_FOLLOWUP_STORAGE_KEY = 'agv_enterprise_status_followup'
const ENTERPRISE_APPROVAL_REVIEW_FOLLOWUP_STORAGE_KEY = 'agv_enterprise_approval_review_followup'
const MINIMAP_WIDTH = 168
const ENTERPRISE_AGV_MOTION_POLL_INTERVAL_MS = 250
const ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT = 0.85
const ENTERPRISE_MAP_EDITOR_ZOOM_MIN = 0.5
const ENTERPRISE_MAP_EDITOR_ZOOM_MAX = 1.6
const ENTERPRISE_MAP_EDITOR_ZOOM_STEP = 0.05
const TOPOLOGY_NODE_TYPE_KEYS = ['waypoint', 'station', 'parking', 'charge']
const TOPOLOGY_EDGE_DIRECTION_KEYS = ['bidirectional', 'forward', 'reverse']
const TOPOLOGY_EDGE_LANE_TYPE_KEYS = ['main', 'branch', 'service']
const MIN_ZOOM = 0.75
const MAX_ZOOM = 3
const DEFAULT_BLOCKED_CELLS = [
  { x: 3, y: 0 },
  { x: 3, y: 1 },
  { x: 3, y: 2 },
  { x: 3, y: 4 },
  { x: 3, y: 5 },
  { x: 3, y: 6 },
  { x: 3, y: 7 },
  { x: 6, y: 0 },
  { x: 6, y: 1 },
  { x: 6, y: 3 },
  { x: 6, y: 4 },
  { x: 6, y: 5 },
  { x: 6, y: 6 },
  { x: 6, y: 7 }
]

function buildFullValidCellList(gridCols = GRID_COLS, gridRows = GRID_ROWS) {
  const cells = []
  for (let y = 0; y < Number(gridRows || GRID_ROWS); y += 1) {
    for (let x = 0; x < Number(gridCols || GRID_COLS); x += 1) {
      cells.push({ x, y })
    }
  }
  return cells
}

const agvs = ref([])
const agvAnimationNow = ref(Date.now())
const localAgvs = ref([])
const tasks = ref([])
const blockedCells = ref([...DEFAULT_BLOCKED_CELLS])
const validCells = ref(buildFullValidCellList(GRID_COLS, GRID_ROWS))
const currentMapTopology = ref(createEmptyMapTopology())
const currentGridCols = ref(GRID_COLS)
const currentGridRows = ref(GRID_ROWS)
const mapWidth = computed(() => currentGridCols.value * CELL_SIZE)
const mapHeight = computed(() => currentGridRows.value * CELL_SIZE)

function gridColsValue() {
  return Number(currentGridCols.value || GRID_COLS)
}

function gridRowsValue() {
  return Number(currentGridRows.value || GRID_ROWS)
}

function clampXToCurrentGrid(value) {
  return clampValue(Math.round(Number(value) || 0), 0, Math.max(0, gridColsValue() - 1))
}

function clampYToCurrentGrid(value) {
  return clampValue(Math.round(Number(value) || 0), 0, Math.max(0, gridRowsValue() - 1))
}

function isWithinCurrentGrid(point) {
  if (!point) return false
  return (
    Number.isInteger(Number(point.x)) &&
    Number.isInteger(Number(point.y)) &&
    Number(point.x) >= 0 &&
    Number(point.x) < gridColsValue() &&
    Number(point.y) >= 0 &&
    Number(point.y) < gridRowsValue()
  )
}

function normalizeValidCellList(cells, gridCols = gridColsValue(), gridRows = gridRowsValue()) {
  const fallback = buildFullValidCellList(gridCols, gridRows)
  if (!Array.isArray(cells)) return fallback

  const normalized = Array.from(new Set(
    cells
      .filter(cell => Number.isFinite(Number(cell?.x)) && Number.isFinite(Number(cell?.y)))
      .map(cell => `${Math.round(Number(cell.x))},${Math.round(Number(cell.y))}`)
  ))
    .map(key => {
      const [x, y] = key.split(',').map(Number)
      return { x, y }
    })
    .filter(cell => cell.x >= 0 && cell.x < gridCols && cell.y >= 0 && cell.y < gridRows)
    .sort((a, b) => a.y - b.y || a.x - b.x)

  return normalized.length ? normalized : fallback
}

function createEmptyMapTopology() {
  return {
    topology_version: 1,
    nodes: [],
    edges: [],
    stations: [],
    parking_nodes: [],
    charge_nodes: []
  }
}

function normalizeMapTopology(topology, gridCols = gridColsValue(), gridRows = gridRowsValue(), nextValidCells = validCells.value) {
  const normalizedValidCells = normalizeValidCellList(nextValidCells, gridCols, gridRows)
  const validCellKeySet = new Set(normalizedValidCells.map(cell => blockedCellKey(cell.x, cell.y)))
  const source = topology && typeof topology === 'object' ? topology : {}
  const stationKeys = new Set((Array.isArray(source?.stations) ? source.stations : []).map(item => String(item || '').trim()).filter(Boolean))
  const parkingKeys = new Set((Array.isArray(source?.parking_nodes) ? source.parking_nodes : []).map(item => String(item || '').trim()).filter(Boolean))
  const chargeKeys = new Set((Array.isArray(source?.charge_nodes) ? source.charge_nodes : []).map(item => String(item || '').trim()).filter(Boolean))

  const nodes = []
  const seenNodeKeys = new Set()
  const seenNodeCells = new Set()
  ;(Array.isArray(source?.nodes) ? source.nodes : []).forEach((node, index) => {
    const x = Math.round(Number(node?.x))
    const y = Math.round(Number(node?.y))
    if (!Number.isFinite(x) || !Number.isFinite(y)) return
    const cellKey = blockedCellKey(x, y)
    if (!validCellKeySet.has(cellKey)) return
    const fallbackKey = `node_${x}_${y}_${index + 1}`
    const key = String(node?.key || fallbackKey).trim() || fallbackKey
    if (seenNodeKeys.has(key) || seenNodeCells.has(cellKey)) return
    let nodeType = String(node?.node_type || 'waypoint').trim().toLowerCase()
    if (chargeKeys.has(key)) nodeType = 'charge'
    else if (parkingKeys.has(key)) nodeType = 'parking'
    else if (stationKeys.has(key)) nodeType = 'station'
    if (!TOPOLOGY_NODE_TYPE_KEYS.includes(nodeType)) nodeType = 'waypoint'
    nodes.push({
      key,
      x,
      y,
      label: String(node?.label || '').trim() || null,
      node_type: nodeType
    })
    seenNodeKeys.add(key)
    seenNodeCells.add(cellKey)
  })

  const nodeKeySet = new Set(nodes.map(node => node.key))
  const edges = []
  const seenEdgeKeys = new Set()
  ;(Array.isArray(source?.edges) ? source.edges : []).forEach((edge, index) => {
    const sourceKey = String(edge?.source || '').trim()
    const targetKey = String(edge?.target || '').trim()
    if (!sourceKey || !targetKey || sourceKey === targetKey) return
    if (!nodeKeySet.has(sourceKey) || !nodeKeySet.has(targetKey)) return
    const fallbackKey = `edge_${sourceKey}_${targetKey}_${index + 1}`
    const key = String(edge?.key || fallbackKey).trim() || fallbackKey
    if (seenEdgeKeys.has(key)) return
    const direction = TOPOLOGY_EDGE_DIRECTION_KEYS.includes(String(edge?.direction || '').trim())
      ? String(edge.direction).trim()
      : 'bidirectional'
    const laneType = TOPOLOGY_EDGE_LANE_TYPE_KEYS.includes(String(edge?.lane_type || '').trim())
      ? String(edge.lane_type).trim()
      : 'main'
    const weight = Math.max(0.1, Number(edge?.weight) || 1)
    const speedMultiplier = Math.max(0.1, Number(edge?.speed_multiplier) || 1)
    edges.push({
      key,
      source: sourceKey,
      target: targetKey,
      direction,
      lane_type: laneType,
      weight,
      speed_multiplier: speedMultiplier
    })
    seenEdgeKeys.add(key)
  })

  return {
    topology_version: 1,
    nodes,
    edges,
    stations: nodes.filter(node => node.node_type === 'station').map(node => node.key),
    parking_nodes: nodes.filter(node => node.node_type === 'parking').map(node => node.key),
    charge_nodes: nodes.filter(node => node.node_type === 'charge').map(node => node.key)
  }
}

function cloneMapTopology(topology, gridCols = gridColsValue(), gridRows = gridRowsValue(), nextValidCells = validCells.value) {
  return normalizeMapTopology(topology, gridCols, gridRows, nextValidCells)
}

function buildMapTopologySummary(topology, gridCols = gridColsValue(), gridRows = gridRowsValue(), nextValidCells = validCells.value) {
  const normalized = normalizeMapTopology(topology, gridCols, gridRows, nextValidCells)
  return {
    enabled: normalized.nodes.length > 0 || normalized.edges.length > 0,
    node_count: normalized.nodes.length,
    edge_count: normalized.edges.length,
    station_count: normalized.stations.length,
    parking_count: normalized.parking_nodes.length,
    charge_count: normalized.charge_nodes.length
  }
}

function findMapTopologyNodeAtCell(topology, x, y) {
  const normalized = topology && typeof topology === 'object' ? topology : createEmptyMapTopology()
  return (normalized.nodes || []).find(node => Number(node.x) === Number(x) && Number(node.y) === Number(y)) || null
}

function buildMapTopologyNodeKey(topology, x, y) {
  const existing = new Set((topology?.nodes || []).map(node => String(node.key)))
  let counter = (topology?.nodes || []).length + 1
  let key = `node_${x}_${y}_${counter}`
  while (existing.has(key)) {
    counter += 1
    key = `node_${x}_${y}_${counter}`
  }
  return key
}

function buildMapTopologyEdgeKey(topology, sourceKey, targetKey) {
  const existing = new Set((topology?.edges || []).map(edge => String(edge.key)))
  let counter = (topology?.edges || []).length + 1
  let key = `edge_${sourceKey}_${targetKey}_${counter}`
  while (existing.has(key)) {
    counter += 1
    key = `edge_${sourceKey}_${targetKey}_${counter}`
  }
  return key
}

function formatEnterpriseTopologyNodeBadge(node) {
  if (!node) return ''
  if (node.node_type === 'station') return 'S'
  if (node.node_type === 'parking') return 'P'
  if (node.node_type === 'charge') return 'C'
  const label = String(node.label || '').trim()
  return label ? label.slice(0, 2).toUpperCase() : 'N'
}

function formatMapProfileTopologySummary(profile) {
  const summary = profile?.topology_summary || {}
  const nodeCount = Number(summary.node_count || 0)
  const edgeCount = Number(summary.edge_count || 0)
  if (!nodeCount && !edgeCount) return ''
  return t('enterprise_settings_route_topology_profile_meta')
    .replace('{nodes}', String(nodeCount))
    .replace('{edges}', String(edgeCount))
}

function isValidMapCell(x, y) {
  return validCellSet.value.has(blockedCellKey(x, y))
}

function sanitizeGridDimensionInput(value, fallback) {
  const normalizedFallback = Math.max(1, Math.round(Number(fallback) || 1))
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return normalizedFallback
  return Math.max(1, Math.round(numeric))
}

function isPrimitiveGridOverride(value) {
  return ['string', 'number'].includes(typeof value)
}

function setMapResizePreviewDraft(cols, rows) {
  const normalizedCols = sanitizeGridDimensionInput(cols, gridColsValue())
  const normalizedRows = sanitizeGridDimensionInput(rows, gridRowsValue())
  mapResizePreviewCols.value = normalizedCols
  mapResizePreviewRows.value = normalizedRows
  mapResizePreviewColsInput.value = String(normalizedCols)
  mapResizePreviewRowsInput.value = String(normalizedRows)
  return {
    requestedCols: normalizedCols,
    requestedRows: normalizedRows
  }
}

const dispatchMode = ref('auto')
const locale = ref('zh')
const algorithm = ref('simple')
const taskPriority = ref(3)
const showAutoPath = ref(false)

const taskForm = ref({
  start_x: 0,
  start_y: 0,
  end_x: 0,
  end_y: 0,
  priority: 3
})
const taskChainStages = ref(buildDefaultTaskChainStages(2, taskForm.value))
const taskBuilderMode = ref('single')
const taskChainMapPickActive = ref(false)
const taskChainMapPickStageCount = ref(2)
const taskChainMapPickPoints = ref([])

const taskTemplateForm = ref({
  name: ''
})

const customPointForm = ref({
  name: '',
  zone: '',
  x: 0,
  y: 0
})

const pointSearch = ref('')
const builtinPoints = ref([...DEFAULT_POINT_LIBRARY])
const builtinTemplates = ref([...DEFAULT_TASK_TEMPLATES])
const customPoints = ref([])
const customTaskTemplates = ref([])
const pointsLoadedFromApi = ref(false)
const templatesLoadedFromApi = ref(false)
const pointFormStatus = ref('')
const pointFormStatusType = ref('info')
const taskTemplateStatus = ref('')
const taskTemplateStatusType = ref('info')
const templateJsonText = ref('')
const templateJsonStatus = ref('')
const templateJsonStatusType = ref('info')
const taskTemplateJumpReady = ref(false)
const jsonText = ref('')
const jsonStatus = ref('')
const experimentRecords = ref([])
const experimentStatus = ref('')
const experimentStatusType = ref('info')
const pathCompareResult = ref(null)
const pathCompareLoading = ref(false)
const pathCompareError = ref('')
const faultEvents = ref([])
const faultEventFilter = ref('open')
const faultPanelStatus = ref('')
const faultPanelStatusType = ref('info')
const faultReportForm = ref({
  fault_type: 'path_blocked',
  severity: 'medium',
  message: ''
})
const showFaultReportForm = ref(false)
const agvActionLoadingId = ref(null)
const resolvingFaultId = ref(null)
const taskRecoveryActionKey = ref('')
const agvRecoveryJumpReady = ref(false)
const agvRecoveryJumpTargetAgvId = ref(null)
const faultSelectedAgvPulse = ref(false)
const floatingToastVisible = ref(false)
const floatingToastMessage = ref('')
const floatingToastType = ref('info')
const panelSearch = ref('')
const focusedPanelSection = ref('')
const panelSummaryMode = ref('compact')
const panelSections = ref({
  control: true,
  queue: true,
  templates: false,
  points: false,
  json: false,
  experiments: false,
  ai: false,
  operations: false
})
const queueGroupsCollapsed = ref(buildDefaultQueueGroupState())
const taskQueueViewFilter = ref('all')
const taskCardCollapsed = ref({})
const summaryZoomArmed = ref(false)

const selectedAgvId = ref(null)
const trackedManualTaskId = ref(null)
const manualDispatchStep = ref('idle')
const manualPreviewMinVisibleUntil = ref(0)
const autoDraftPicking = ref(false)
const manualDraftPicking = ref(false)
const preferredRuntimeDisplayMode = ref('auto')
const mapDraftPrimedMode = ref(null)
const startPoint = ref(null)
const endPoint = ref(null)
const showGuideCenter = ref(false)
const showGuideCenterOnLoad = ref(true)
const feedbackBellMenuOpen = ref(false)

const manualPathToStart = ref([])
const manualPathToEnd = ref([])
const autoPathToStart = ref([])
const autoPathToEnd = ref([])
const layoutRef = ref(null)
const mapSettingsPanelRef = ref(null)
const mapViewportRef = ref(null)
const mapPaneRef = ref(null)
const minimapRef = ref(null)
const panelRef = ref(null)
const compareEntryButtonRef = ref(null)
const enterpriseWorkspacePopupRef = ref(null)
const controlSectionRef = ref(null)
const taskBuilderRef = ref(null)
const comparePanelRef = ref(null)
const faultSelectedAgvCardRef = ref(null)
const queueSectionRef = ref(null)
const templatesSectionRef = ref(null)
const pointsSectionRef = ref(null)
const jsonSectionRef = ref(null)
const experimentsSectionRef = ref(null)
const aiSectionRef = ref(null)
const operationsSectionRef = ref(null)
const panelWidth = ref(380)
const showPanelBackToTop = ref(false)
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
const mapZoom = ref(1)
const mapOffsetX = ref(0)
const mapOffsetY = ref(0)
const mapViewportWidth = ref(mapWidth.value)
const mapViewportHeight = ref(mapHeight.value)
const isMapPanning = ref(false)
const showMapSettings = ref(false)
const showStatusLegend = ref(true)
const statusLegendLayout = ref('horizontal')
const statusLegendOpacity = ref(0.55)
const showMarkerIcons = ref(true)
const showPathArrows = ref(false)
const showMinimap = ref(true)
const obstacleEditMode = ref(false)
const obstacleMapSaving = ref(false)
const syncedBlockedCells = ref([...DEFAULT_BLOCKED_CELLS])
const syncedValidCells = ref(buildFullValidCellList(GRID_COLS, GRID_ROWS))
const obstaclePresets = ref([])
const mapProfiles = ref([])
const mapProfileApplyingKey = ref('')
const mapProfileDeletingKey = ref('')
const mapProfileExportingKey = ref('')
const mapProfileImporting = ref(false)
const mapProfileSaving = ref(false)
const mapProfilePreviewingKey = ref('')
const mapProfileActionSummary = ref(null)
const selectedObstaclePreset = ref('default_shelves')
const appliedObstacleSceneKey = ref('default_shelves')
const currentMapProfile = ref(null)
const mapSizeResizeReady = ref(false)
const mapSizeResizeLockReason = ref('ready')
const mapResizePreviewCols = ref(GRID_COLS)
const mapResizePreviewRows = ref(GRID_ROWS)
const mapResizePreviewColsInput = ref(String(GRID_COLS))
const mapResizePreviewRowsInput = ref(String(GRID_ROWS))
const mapResizePreview = ref(null)
const mapResizePreviewLoading = ref(false)
const mapPreviewFocusCells = ref([])
const mapResizePreviewDirty = ref(false)
const mapResizeHighlightedSection = ref('')
const mapResizeHighlightedItemKeys = ref([])
const obstacleLayoutStatus = ref('')
const obstacleLayoutStatusType = ref('info')
const obstacleLayoutFileInputRef = ref(null)
const mapProfileFileInputRef = ref(null)
const importedObstacleLayoutPendingPreset = ref(false)
const importedObstaclePresetSuggestedName = ref('')
const compareDisplayMode = ref('panel')
const comparePanelExpanded = ref(false)
const showFloatingCompare = ref(false)
const compareFloatingOpacity = ref(0.92)
const compareFloatingX = ref(0)
const compareFloatingY = ref(140)
const operationAudits = ref([])
const operationAuditLoading = ref(false)
const deletingOperationAuditId = ref(null)
const operationAuditBulkDeleting = ref(false)
const selectedOperationAuditIds = ref([])
const operationAuditResourceFilter = ref('all')
const operationAuditActionFilter = ref('all')
const operationAuditLastFetchedAt = ref('')
const comfyRenderSourceType = ref('map_profile')
const comfyRenderSourceRef = ref('')
const comfyRenderCheckpointName = ref('')
const comfyRenderWorkflowPreset = ref(COMFY_WORKFLOW_PRESET_DEFAULT)
const comfyRenderPromptStyle = ref(COMFY_PROMPT_STYLE_DEFAULT)
const comfyRenderBuiltinTemplateKey = ref('')
const comfyRenderBuiltinTemplatesOverviewVisible = ref(false)
const comfyRenderAvailableCheckpoints = ref([])
const comfyRenderCheckpointsLoading = ref(false)
const comfyRenderPromptText = ref('')
const comfyRenderInputJsonText = ref('')
const comfyRenderWorkflowJsonText = ref('')
const comfyRenderStatus = ref('')
const comfyRenderStatusType = ref('info')
const comfyRenderJobs = ref([])
const comfyRenderLoading = ref(false)
const comfyRenderSubmitting = ref(false)
const comfyRenderLastFetchedAt = ref('')
const comfyRenderPreviewVisible = ref(false)
const comfyRenderPreviewUrl = ref('')
const comfyRenderPreviewTitle = ref('')
const comfyRenderPreviewJobId = ref(null)
const comfyRenderTemplateName = ref('')
const comfyRenderSelectedTemplateId = ref('')
const comfyRenderSavedTemplates = ref([])
const comfyRenderSharedTemplates = ref([])
const comfyRenderSelectedSharedTemplateId = ref('')
const comfyRenderSharedTemplatesLoading = ref(false)
const comfyRenderSharedTemplateSaving = ref(false)
const deletingComfyJobId = ref(null)

let timer = null
let enterpriseAgvMotionPollTimer = null
let agvAnimationFrameHandle = null
let clickTimer = null
let taskBuilderJumpTimer = null
let agvRecoveryJumpTimer = null
let faultSelectedAgvPulseTimer = null
let floatingToastTimer = null
let localNextId = 1000
const autoScheduling = ref(false)
const autoScheduleGuard = ref(false)
const manualBoundScheduling = ref(false)
let polling = false
let mapResizeObserver = null
let mapPanCandidate = false
let mapPanMoved = false
let mapPanStartX = 0
let mapPanStartY = 0
let mapPanOriginX = 0
let mapPanOriginY = 0
let ignoreNextMapClick = false
let obstaclePaintActive = false
let obstaclePaintMode = 'add'
let obstaclePaintLastKey = ''
let compareFloatingDragging = false
let compareFloatingDragOffsetX = 0
let compareFloatingDragOffsetY = 0
let manualPreviewHoldTimer = null
let mapPreviewFocusTimer = null
let mapResizeSectionHighlightTimer = null
let mapResizeItemHighlightTimer = null
let accountGovernanceSearchTimer = null
let authGovernanceSyncTimer = null
let mapPreviewFocusSequence = 0
let operationAuditRefreshPending = false

const { t, localeTexts, localizeDispatchReason, localizeApiErrorDetail, createApiError } = useLocaleText(locale)
const {
  templateJsonLocale,
  panelLocale,
  panelSearchLocale,
  guideCenterLocale,
  toolbarGuideHintText,
  taskChainLocale,
  taskBuilderLocale,
  taskJsonLocale,
  taskJsonExampleFileLocale,
  taskChainMapPickUiLocale,
  queueViewLocale,
  experimentLocale,
  algorithmCompareLocale
} = useUiLocales({ locale, t })

function formatInlineMessage(template, replacements = {}) {
  return Object.entries(replacements).reduce(
    (message, [key, value]) => message.replaceAll(`{${key}}`, String(value ?? '')),
    String(template ?? '')
  )
}

function readEnterpriseRegisterDraftPayload() {
  if (typeof window === 'undefined' || !window.localStorage) return null
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_REGISTER_DRAFT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? parsed : null
  } catch {
    return null
  }
}

function loadEnterpriseRegisterDraft() {
  const parsed = readEnterpriseRegisterDraftPayload()
  if (!parsed) {
    return {
      company_name: '',
      contact_name: '',
      contact_email: '',
      username: '',
      password: ''
    }
  }
  return {
    company_name: String(parsed?.company_name || ''),
    contact_name: String(parsed?.contact_name || ''),
    contact_email: String(parsed?.contact_email || ''),
    username: String(parsed?.username || ''),
    password: ''
  }
}

function readEnterpriseRegisterFollowupPayload() {
  if (typeof window === 'undefined' || !window.localStorage) return null
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_REGISTER_FOLLOWUP_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? parsed : null
  } catch {
    return null
  }
}

function loadEnterpriseRegisterFollowup() {
  const parsed = readEnterpriseRegisterFollowupPayload()
  if (!parsed) return null
  return {
    company_name: String(parsed?.company_name || '').trim(),
    username: String(parsed?.username || '').trim(),
    contact_name: String(parsed?.contact_name || '').trim(),
    contact_email: String(parsed?.contact_email || '').trim(),
    submitted_at: parsed?.submitted_at ? String(parsed.submitted_at) : null,
    status: String(parsed?.status || 'pending').trim() || 'pending',
    updated_at: parsed?.updated_at ? String(parsed.updated_at) : null
  }
}

function normalizeEnterpriseApplicationSnapshot(application, statusFallback = 'pending') {
  if (!application || typeof application !== 'object') return null
  const normalizedId = Number(application?.id)
  return {
    id: Number.isFinite(normalizedId) && normalizedId > 0 ? normalizedId : null,
    company_name: String(application?.company_name || '').trim(),
    username: String(application?.username || '').trim(),
    contact_name: String(application?.contact_name || '').trim(),
    contact_email: String(application?.contact_email || '').trim(),
    submitted_at: application?.submitted_at ? String(application.submitted_at) : null,
    reviewed_at: application?.reviewed_at ? String(application.reviewed_at) : null,
    reviewed_by: application?.reviewed_by ? String(application.reviewed_by) : null,
    review_note: String(application?.review_note || '').trim(),
    status: String(application?.status || statusFallback || 'pending').trim() || 'pending',
    updated_at: application?.updated_at ? String(application.updated_at) : null
  }
}

const EDITABLE_SHORTCUT_ACTION_KEYS = ['selection_cancel', 'algorithm_toggle', 'context_cancel']
const DEFAULT_EDITABLE_SHORTCUTS = Object.freeze({
  selection_cancel: 'F',
  algorithm_toggle: 'R',
  context_cancel: 'Escape'
})

function normalizeShortcutKeyValue(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  if (raw === ' ') return 'Space'
  const normalizedNamed = {
    esc: 'Escape',
    escape: 'Escape',
    space: 'Space',
    ' ': 'Space',
    del: 'Delete',
    delete: 'Delete',
    enter: 'Enter',
    return: 'Enter',
    tab: 'Tab',
    backspace: 'Backspace'
  }
  const lowered = raw.toLowerCase()
  if (normalizedNamed[lowered]) return normalizedNamed[lowered]
  if (/^arrow(up|down|left|right)$/i.test(raw)) {
    const suffix = lowered.replace('arrow', '')
    return `Arrow${suffix.charAt(0).toUpperCase()}${suffix.slice(1)}`
  }
  if (raw.length === 1) return raw.toUpperCase()
  return `${raw.charAt(0).toUpperCase()}${raw.slice(1)}`
}

function formatShortcutKeyLabel(value) {
  const normalized = normalizeShortcutKeyValue(value)
  if (!normalized) return '—'
  const labels = {
    Escape: 'Esc',
    Space: 'Space',
    Delete: 'Del',
    Backspace: 'Backspace',
    ArrowUp: '↑',
    ArrowDown: '↓',
    ArrowLeft: '←',
    ArrowRight: '→'
  }
  return labels[normalized] || normalized
}

function normalizeEditableShortcutConfig(raw, { allowEmpty = false } = {}) {
  const source = raw && typeof raw === 'object' ? raw : {}
  return Object.fromEntries(
    EDITABLE_SHORTCUT_ACTION_KEYS.map(actionKey => {
      const hasOwnValue = Object.prototype.hasOwnProperty.call(source, actionKey)
      if (!hasOwnValue) {
        return [actionKey, DEFAULT_EDITABLE_SHORTCUTS[actionKey]]
      }
      const normalized = normalizeShortcutKeyValue(source[actionKey])
      const safeValue = normalized === 'P' ? '' : normalized
      if (safeValue) {
        return [actionKey, safeValue]
      }
      return [actionKey, allowEmpty ? '' : DEFAULT_EDITABLE_SHORTCUTS[actionKey]]
    })
  )
}

function areEditableShortcutConfigsEqual(left, right) {
  const normalizedLeft = normalizeEditableShortcutConfig(left, { allowEmpty: true })
  const normalizedRight = normalizeEditableShortcutConfig(right, { allowEmpty: true })
  return EDITABLE_SHORTCUT_ACTION_KEYS.every(actionKey => normalizedLeft[actionKey] === normalizedRight[actionKey])
}

function readShortcutPreferencePayload() {
  if (typeof window === 'undefined' || !window.localStorage) return {}
  try {
    const raw = window.localStorage.getItem(SHORTCUT_PREFERENCES_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? parsed : {}
  } catch {
    return {}
  }
}

function readEnterpriseStatusFollowupPayload() {
  if (typeof window === 'undefined' || !window.localStorage) return null
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_STATUS_FOLLOWUP_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? parsed : null
  } catch {
    return null
  }
}

function loadEnterpriseStatusFollowup() {
  return normalizeEnterpriseApplicationSnapshot(readEnterpriseStatusFollowupPayload())
}

function readEnterpriseApprovalReviewFollowupPayload() {
  if (typeof window === 'undefined' || !window.localStorage) return null
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_APPROVAL_REVIEW_FOLLOWUP_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? parsed : null
  } catch {
    return null
  }
}

function loadEnterpriseApprovalReviewFollowup() {
  return normalizeEnterpriseApplicationSnapshot(readEnterpriseApprovalReviewFollowupPayload())
}

function readEnterpriseApprovalUiPayload() {
  if (typeof window === 'undefined' || !window.localStorage) return null
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_APPROVAL_UI_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed ? parsed : null
  } catch {
    return null
  }
}

function loadEnterpriseApprovalUiState() {
  const parsed = readEnterpriseApprovalUiPayload()
  if (!parsed) {
    return {
      status: 'pending',
      search: '',
      draftOnly: false,
      selectedId: null,
      noteDrafts: {}
    }
  }
  const normalizedStatus = ['all', 'pending', 'approved', 'rejected'].includes(String(parsed?.status || ''))
    ? String(parsed.status)
    : 'pending'
  const selectedId = Number(parsed?.selectedId)
  const rawDrafts = parsed?.noteDrafts && typeof parsed.noteDrafts === 'object' ? parsed.noteDrafts : {}
  const noteDrafts = Object.fromEntries(
    Object.entries(rawDrafts).map(([key, value]) => {
      const normalized = value && typeof value === 'object' ? value : {}
      return [
        String(key),
        {
          text: String(normalized.text || ''),
          updated_at: String(normalized.updated_at || '')
        }
      ]
    })
  )
  return {
    status: normalizedStatus,
    search: String(parsed?.search || ''),
    draftOnly: Boolean(parsed?.draftOnly),
    selectedId: Number.isFinite(selectedId) && selectedId > 0 ? selectedId : null,
    noteDrafts
  }
}

const {
  authPanelOpen,
  authLoading,
  authInitialized,
  authUsername,
  authPassword,
  authLastFetchedAt,
  demoAccounts: authDemoAccounts,
  isAuthenticated: authAuthenticated,
  currentUser: authCurrentUser,
  currentRole: authCurrentRole,
  currentDisplayName: authCurrentDisplayName,
  currentAccountStatus: authCurrentAccountStatus,
  currentOrganizationName: authCurrentOrganizationName,
  currentEnterpriseApplication: authCurrentEnterpriseApplication,
  currentCapabilities: authCurrentCapabilities,
  currentCapabilityGroups: authCurrentCapabilityGroups,
  buildAuthHeaders,
  fetchAuthMe,
  login: loginWithAuthSession,
  registerPersonal: registerPersonalWithAuthSession,
  logout: logoutFromAuthSession,
  fillDemoAccount,
  resetAuthState: resetAuthStateWithAuthSession
} = useAuthSession({
  API_BASE,
  createApiError
})

const authGuestAccepted = ref(false)
const authDialogView = ref('login')
const authPersonalRegisterForm = ref({
  display_name: '',
  username: '',
  password: ''
})
const authEnterpriseRegisterLoading = ref(false)
const authEnterpriseRegisterFollowup = ref(loadEnterpriseRegisterFollowup())
const authEnterpriseStatusFollowup = ref(loadEnterpriseStatusFollowup())
const authEnterpriseRegisterForm = ref(loadEnterpriseRegisterDraft())
const authEnterpriseRegisterDraftUpdatedAt = ref(
  String(readEnterpriseRegisterDraftPayload()?.updated_at || '')
)
const enterpriseApprovalUiState = loadEnterpriseApprovalUiState()
const enterpriseApprovalDialogOpen = ref(false)
const enterpriseApprovalLoading = ref(false)
const enterpriseApprovalReviewLoading = ref(false)
const enterpriseApprovalStatusFilter = ref(enterpriseApprovalUiState.status)
const enterpriseApprovalSearch = ref(enterpriseApprovalUiState.search)
const enterpriseApprovalSummary = ref({ all: 0, pending: 0, approved: 0, rejected: 0 })
const enterpriseApplications = ref([])
const enterpriseApprovalLastFetchedAt = ref('')
const enterpriseApprovalDraftOnly = ref(Boolean(enterpriseApprovalUiState.draftOnly))
const selectedEnterpriseApplicationId = ref(enterpriseApprovalUiState.selectedId)
const enterpriseApprovalReviewNote = ref('')
const enterpriseApprovalNoteDrafts = ref(enterpriseApprovalUiState.noteDrafts)
const enterpriseApprovalReviewFollowup = ref(loadEnterpriseApprovalReviewFollowup())
const accountGovernanceDialogOpen = ref(false)
const accountGovernanceLoading = ref(false)
const accountGovernanceRoleFilter = ref('all')
const accountGovernanceStatusFilter = ref('all')
const accountGovernanceSearch = ref('')
const accountGovernanceSummary = ref({
  all: 0,
  personal: 0,
  enterprise: 0,
  platform_admin: 0,
  approved: 0,
  pending: 0,
  rejected: 0,
  suspended: 0,
  deactivated: 0
})
const managedUserAccounts = ref([])
const selectedManagedUserId = ref('')
const selectedManagedUserIds = ref([])
const accountGovernanceLastFetchedAt = ref('')
const accountGovernanceActionLoading = ref(false)
const accountGovernanceSelectedTemplateKey = ref('')
const accountGovernanceSuspendReason = ref('')
const accountGovernanceSuspendNote = ref('')
const accountGovernanceSuspendDurationPreset = ref('7d')
const enterpriseRequestDialogOpen = ref(false)
const enterpriseRequestLoading = ref(false)
const enterpriseRequestActionLoading = ref(false)
const enterpriseRequestSummary = ref({ all: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 })
const enterpriseRequestStatusFilter = ref('all')
const enterpriseRequestCategoryFilter = ref('all')
const enterpriseRequestSearch = ref('')
const enterpriseRequestItems = ref([])
const enterpriseRequestRecipients = ref([])
const selectedEnterpriseRequestId = ref('')
const enterpriseRequestDraft = ref({
  category: 'request',
  title: '',
  content: '',
  target_user_id: ''
})
const enterpriseRequestResponseNote = ref('')
const enterpriseRequestLastFetchedAt = ref('')
const platformBugFeedbackDialogOpen = ref(false)
const platformBugFeedbackLoading = ref(false)
const platformBugFeedbackActionLoading = ref(false)
const platformBugFeedbackSummary = ref({ all: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 })
const platformBugFeedbackStatusFilter = ref('all')
const platformBugFeedbackCategoryFilter = ref('all')
const platformBugFeedbackSearch = ref('')
const platformBugFeedbackItems = ref([])
const selectedPlatformBugFeedbackId = ref('')
const platformBugFeedbackDraft = ref({
  category: 'ui',
  title: '',
  content: ''
})
const platformBugFeedbackResponseNote = ref('')
const platformBugFeedbackLastFetchedAt = ref('')
const platformBugFeedbackManagementMode = ref(false)
const platformAdminSurfaceMode = ref('governance')
const platformAdminEnterprisePreviewRole = ref('enterprise_admin')
const authLoginRestrictionNotice = ref(null)
const enterpriseSettingsDialogOpen = ref(false)
const enterpriseSettingsActiveTab = ref('overview')
const enterpriseSettingsSidebarCollapsed = ref(false)
const enterprisePageSettingsDialogOpen = ref(false)
const enterpriseShortcutPlannerDialogOpen = ref(false)
const shortcutEditorDraft = ref(normalizeEditableShortcutConfig(DEFAULT_EDITABLE_SHORTCUTS))
const activeShortcutBindings = ref(normalizeEditableShortcutConfig(DEFAULT_EDITABLE_SHORTCUTS))
const shortcutEditorCaptureActionKey = ref('')
const shortcutEditorStatus = ref('')
const shortcutEditorStatusType = ref('info')
const enterpriseMapEditorDialogOpen = ref(false)
const enterpriseMapEditorSaving = ref(false)
const enterpriseMapEditorDraftBlockedCells = ref([])
const enterpriseMapEditorDraftValidCells = ref(buildFullValidCellList(GRID_COLS, GRID_ROWS))
const enterpriseMapEditorDraftCols = ref(GRID_COLS)
const enterpriseMapEditorDraftRows = ref(GRID_ROWS)
const enterpriseMapEditorZoom = ref(ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT)
const enterpriseTopologyEditorDialogOpen = ref(false)
const enterpriseTopologyEditorDraft = ref(createEmptyMapTopology())
const enterpriseTopologyEditorSelectedNodeKey = ref('')
const enterpriseTopologyEditorSelectedEdgeKey = ref('')
const enterpriseTopologyEditorLinkSourceKey = ref('')
const authRoleLabel = computed(() => t(`auth_role_${authCurrentRole.value}`))
const authRoleBadgeClass = computed(() => `role-${authCurrentRole.value}`)
const isPlatformAdmin = computed(() => authCurrentRole.value === 'platform_admin')
const isPlatformAdminGovernanceMode = computed(
  () => isPlatformAdmin.value && platformAdminSurfaceMode.value === 'governance'
)
const isPlatformAdminPersonalPreviewMode = computed(
  () => isPlatformAdmin.value && platformAdminSurfaceMode.value === 'personal'
)
const isPlatformAdminEnterprisePreviewMode = computed(
  () => isPlatformAdmin.value && platformAdminSurfaceMode.value === 'enterprise'
)
const isPlatformAdminPreviewMode = computed(
  () => isPlatformAdminPersonalPreviewMode.value || isPlatformAdminEnterprisePreviewMode.value
)
const effectiveSurfaceRole = computed(() => {
  if (isPlatformAdminPersonalPreviewMode.value) return 'personal'
  if (isPlatformAdminEnterprisePreviewMode.value) return platformAdminEnterprisePreviewRole.value
  return authCurrentRole.value
})
const uiTreatAsEnterpriseRole = computed(() =>
  ['enterprise_operator', 'enterprise_logistics', 'enterprise_admin'].includes(effectiveSurfaceRole.value)
)
const enterpriseUiRole = computed(() =>
  uiTreatAsEnterpriseRole.value ? effectiveSurfaceRole.value : 'enterprise_admin'
)
const enterpriseUiApproved = computed(() =>
  isPlatformAdminEnterprisePreviewMode.value || authCurrentAccountStatus.value === 'approved'
)
const enterpriseUiRoleLabel = computed(() => t(`auth_role_${enterpriseUiRole.value}`))
const showEnterpriseSettingsToolbarEntry = computed(
  () => authIsEnterpriseRole.value || isPlatformAdminEnterprisePreviewMode.value
)
const showPlatformAdminManagementEntries = computed(() => !isPlatformAdminPreviewMode.value)
const showEnterpriseRequestToolbarEntry = computed(() =>
  authCanEnterpriseRequestSubmit.value && authIsEnterpriseRole.value && authCurrentAccountStatus.value === 'approved'
)
const showPlatformBugFeedbackToolbarEntry = computed(() =>
  authAuthenticated.value && !isPlatformAdmin.value && (authCanPlatformBugSubmit.value || authCanPlatformBugManage.value)
)
const showFeedbackBell = computed(() =>
  authAuthenticated.value &&
  !isPlatformAdmin.value &&
  (showEnterpriseRequestToolbarEntry.value || showPlatformBugFeedbackToolbarEntry.value)
)
const dashboardUnlocked = computed(() => authAuthenticated.value || authGuestAccepted.value)
const authModeText = computed(() =>
  authAuthenticated.value ? t(`auth_mode_${authCurrentRole.value}`) : t('auth_mode_guest')
)
const authEntryHintText = computed(() => {
  if (!authAuthenticated.value) return t('auth_entry_hint_guest')
  return t(`auth_entry_hint_${authCurrentRole.value}`)
})
const authAccountStatusLabel = computed(() => t(`auth_account_status_${authCurrentAccountStatus.value}`))
const shortcutPreferenceScopeKey = computed(() => {
  if (!authAuthenticated.value || authCurrentRole.value === 'guest') return 'guest'
  const currentUser = authCurrentUser.value || {}
  const username = String(currentUser?.username || authUsername.value || '').trim() || 'default'
  const organizationId = String(currentUser?.organization_id || '').trim()
  if (organizationId) {
    return `${authCurrentRole.value}:${organizationId}:${username}`
  }
  return `${authCurrentRole.value}:${username}`
})
const shortcutEditorCanEdit = computed(() => authAuthenticated.value && authCurrentRole.value !== 'guest')
const shortcutEditorConflictMap = computed(() => {
  const grouped = {}
  for (const actionKey of EDITABLE_SHORTCUT_ACTION_KEYS) {
    const keyValue = normalizeShortcutKeyValue(shortcutEditorDraft.value?.[actionKey])
    if (!keyValue) continue
    if (!grouped[keyValue]) grouped[keyValue] = []
    grouped[keyValue].push(actionKey)
  }
  return Object.fromEntries(
    Object.entries(grouped).flatMap(([keyValue, actionKeys]) =>
      actionKeys.length > 1 ? actionKeys.map(actionKey => [actionKey, keyValue]) : []
    )
  )
})
const shortcutEditorHasConflicts = computed(() => Object.keys(shortcutEditorConflictMap.value).length > 0)
const shortcutEditorHasUnsavedChanges = computed(
  () => !areEditableShortcutConfigsEqual(shortcutEditorDraft.value, activeShortcutBindings.value)
)
const shortcutGuideEntries = computed(() => [
  formatInlineMessage(t('shortcut_editor_guide_selection_cancel'), {
    key: activeShortcutBindings.value.selection_cancel
      ? formatShortcutKeyLabel(activeShortcutBindings.value.selection_cancel)
      : t('shortcut_editor_unassigned_key')
  }),
  formatInlineMessage(t('shortcut_editor_guide_algorithm_toggle'), {
    key: activeShortcutBindings.value.algorithm_toggle
      ? formatShortcutKeyLabel(activeShortcutBindings.value.algorithm_toggle)
      : t('shortcut_editor_unassigned_key')
  }),
  formatInlineMessage(t('shortcut_editor_guide_context_cancel'), {
    key: activeShortcutBindings.value.context_cancel
      ? formatShortcutKeyLabel(activeShortcutBindings.value.context_cancel)
      : t('shortcut_editor_unassigned_key')
  })
])
const shortcutEditorActionDefinitions = computed(() => [
  {
    key: 'selection_cancel',
    label: t('shortcut_editor_action_selection_cancel_title'),
    hint: t('shortcut_editor_action_selection_cancel_hint'),
    fixedHint: t('shortcut_editor_fixed_mouse_hint'),
    defaultLabel: formatShortcutKeyLabel(DEFAULT_EDITABLE_SHORTCUTS.selection_cancel)
  },
  {
    key: 'algorithm_toggle',
    label: t('shortcut_editor_action_algorithm_toggle_title'),
    hint: t('shortcut_editor_action_algorithm_toggle_hint'),
    fixedHint: '',
    defaultLabel: formatShortcutKeyLabel(DEFAULT_EDITABLE_SHORTCUTS.algorithm_toggle)
  },
  {
    key: 'context_cancel',
    label: t('shortcut_editor_action_context_cancel_title'),
    hint: t('shortcut_editor_action_context_cancel_hint'),
    fixedHint: t('shortcut_editor_fixed_mouse_hint'),
    defaultLabel: formatShortcutKeyLabel(DEFAULT_EDITABLE_SHORTCUTS.context_cancel)
  }
])
const shortcutEditorRows = computed(() =>
  shortcutEditorActionDefinitions.value.map(item => ({
    ...item,
    currentValue: normalizeShortcutKeyValue(shortcutEditorDraft.value?.[item.key]),
    currentLabel: normalizeShortcutKeyValue(shortcutEditorDraft.value?.[item.key])
      ? formatShortcutKeyLabel(shortcutEditorDraft.value?.[item.key])
      : t('shortcut_editor_unassigned_key'),
    conflictKey: shortcutEditorConflictMap.value[item.key] || '',
    isDefault: normalizeShortcutKeyValue(shortcutEditorDraft.value?.[item.key]) === DEFAULT_EDITABLE_SHORTCUTS[item.key],
    isEmpty: !normalizeShortcutKeyValue(shortcutEditorDraft.value?.[item.key])
  }))
)
const authEnterpriseRegisterValidation = computed(() => {
  const payload = {
    company_name: String(authEnterpriseRegisterForm.value.company_name || '').trim(),
    contact_name: String(authEnterpriseRegisterForm.value.contact_name || '').trim(),
    contact_email: String(authEnterpriseRegisterForm.value.contact_email || '').trim(),
    username: String(authEnterpriseRegisterForm.value.username || '').trim(),
    password: String(authEnterpriseRegisterForm.value.password || '')
  }
  const emailLooksValid = /.+@.+\..+/.test(payload.contact_email)
  const usernameValid = payload.username.length >= 4
  const passwordValid = payload.password.length >= 8
  const items = [
    {
      key: 'company_name',
      label: t('enterprise_register_company_name'),
      valid: Boolean(payload.company_name),
      message: t('auth_enterprise_register_validation_company')
    },
    {
      key: 'contact_name',
      label: t('enterprise_register_contact_name'),
      valid: Boolean(payload.contact_name),
      message: t('auth_enterprise_register_validation_contact')
    },
    {
      key: 'contact_email',
      label: t('enterprise_register_contact_email'),
      valid: emailLooksValid,
      message: t('auth_enterprise_register_validation_email')
    },
    {
      key: 'username',
      label: t('enterprise_register_username'),
      valid: usernameValid,
      message: t('auth_enterprise_register_validation_username')
    },
    {
      key: 'password',
      label: t('enterprise_register_password'),
      valid: passwordValid,
      message: t('auth_enterprise_register_validation_password')
    }
  ]
  const missing = items.filter(item => !item.valid)
  return {
    payload,
    items,
    valid: missing.length === 0,
    missingCount: missing.length,
    firstMessage: missing[0]?.message || ''
  }
})
const authPersonalRegisterValidation = computed(() => {
  const payload = {
    display_name: String(authPersonalRegisterForm.value.display_name || '').trim(),
    username: String(authPersonalRegisterForm.value.username || '').trim(),
    password: String(authPersonalRegisterForm.value.password || '')
  }
  const items = [
    {
      key: 'username',
      label: t('auth_username'),
      valid: payload.username.length >= 4,
      message: t('auth_personal_register_validation_username')
    },
    {
      key: 'password',
      label: t('auth_password'),
      valid: payload.password.length >= 8,
      message: t('auth_personal_register_validation_password')
    }
  ]
  const missing = items.filter(item => !item.valid)
  return {
    payload,
    items,
    missing,
    missingCount: missing.length,
    valid: missing.length === 0,
    firstMessage: missing[0]?.message || ''
  }
})
const authPersonalRegisterStatusText = computed(() =>
  authPersonalRegisterValidation.value.valid
    ? t('auth_personal_register_ready')
    : formatInlineMessage(t('auth_personal_register_incomplete'), { count: authPersonalRegisterValidation.value.missingCount })
)
const authEnterpriseRegisterStatusText = computed(() =>
  authEnterpriseRegisterValidation.value.valid
    ? t('auth_enterprise_register_ready')
    : formatInlineMessage(t('auth_enterprise_register_incomplete'), { count: authEnterpriseRegisterValidation.value.missingCount })
)
const authEnterpriseRegisterDraftHasContent = computed(() => {
  const draft = authEnterpriseRegisterForm.value
  return ['company_name', 'contact_name', 'contact_email', 'username']
    .some(key => Boolean(String(draft?.[key] || '').trim()))
})
const authEnterpriseRegisterDraftUpdatedText = computed(() =>
  authEnterpriseRegisterDraftUpdatedAt.value
    ? formatInlineMessage(t('auth_enterprise_register_draft_updated_at'), {
        at: formatDateTimeInline(authEnterpriseRegisterDraftUpdatedAt.value)
      })
    : ''
)
const authEnterpriseRegisterDraftDiffFields = computed(() => {
  const application = authCurrentEnterpriseApplication.value
  if (!application || !authEnterpriseRegisterDraftHasContent.value) return []
  const fieldDefinitions = [
    { key: 'company_name', label: t('enterprise_register_company_name') },
    { key: 'contact_name', label: t('enterprise_register_contact_name') },
    { key: 'contact_email', label: t('enterprise_register_contact_email') },
    { key: 'username', label: t('enterprise_register_username') }
  ]
  return fieldDefinitions
    .filter(item => {
      const draftValue = String(authEnterpriseRegisterForm.value?.[item.key] || '').trim()
      const applicationValue = String(application?.[item.key] || '').trim()
      return draftValue !== applicationValue
    })
    .map(item => item.label)
})
const authEnterpriseRegisterDraftDiffText = computed(() => {
  if (!authCurrentEnterpriseApplication.value || !authEnterpriseRegisterDraftHasContent.value) return ''
  if (!authEnterpriseRegisterDraftDiffFields.value.length) {
    return t('auth_enterprise_register_draft_compare_same')
  }
  return formatInlineMessage(t('auth_enterprise_register_draft_compare_changed'), {
    count: authEnterpriseRegisterDraftDiffFields.value.length,
    fields: authEnterpriseRegisterDraftDiffFields.value.join(' / ')
  })
})
function buildEnterpriseApplicationProgressItems(application, fallbackStatus = '') {
  if (!application || typeof application !== 'object') return []
  const normalizedStatus = String(application.status || fallbackStatus || '').trim().toLowerCase()
  const reviewStatusLabel = normalizedStatus
    ? t(`enterprise_approval_status_${normalizedStatus}`)
    : t('enterprise_application_progress_review_pending')
  let reviewValue = t('enterprise_application_progress_review_pending')
  if (application.reviewed_at) {
    reviewValue = formatInlineMessage(t('enterprise_application_progress_review_complete'), {
      status: reviewStatusLabel,
      reviewedAt: application.reviewed_at
    })
  } else if (normalizedStatus === 'rejected') {
    reviewValue = reviewStatusLabel
  }
  return [
    {
      key: 'submitted',
      label: t('enterprise_application_progress_submitted'),
      value: String(application.submitted_at || '').trim() || t('enterprise_application_progress_waiting_submission'),
      tone: application.submitted_at ? 'done' : 'pending'
    },
    {
      key: 'review',
      label: t('enterprise_application_progress_review'),
      value: reviewValue,
      tone: normalizedStatus === 'rejected'
        ? 'blocked'
        : (application.reviewed_at || normalizedStatus === 'approved' ? 'done' : 'pending')
    },
    {
      key: 'access',
      label: t('enterprise_application_progress_access'),
      value: normalizedStatus === 'approved'
        ? t('enterprise_application_progress_access_ready')
        : normalizedStatus === 'rejected'
          ? t('enterprise_application_progress_access_blocked')
          : t('enterprise_application_progress_access_locked'),
      tone: normalizedStatus === 'approved'
        ? 'done'
        : normalizedStatus === 'rejected'
          ? 'blocked'
          : 'pending'
    }
  ]
}
const authStatusNotice = computed(() => {
  if (!authAuthenticated.value) return null
  const application = authCurrentEnterpriseApplication.value
  if (authCurrentRole.value === 'platform_admin') {
    return {
      tone: 'platform',
      title: t('auth_status_notice_platform_admin_title'),
      hint: t('auth_status_notice_platform_admin_hint'),
      actionLabel: t('auth_status_notice_platform_admin_action'),
      actionKey: 'enterprise-approval',
      meta: platformApprovalPendingCount.value > 0
        ? formatInlineMessage(t('auth_status_notice_platform_admin_meta'), { count: platformApprovalPendingCount.value })
        : t('auth_status_notice_platform_admin_meta_empty')
    }
  }
  if (authIsEnterpriseRole.value && authCurrentAccountStatus.value === 'pending') {
    return {
      tone: 'pending',
      title: t('auth_status_notice_pending_title'),
      hint: t('auth_status_notice_pending_hint'),
      actionLabel: t('auth_status_notice_refresh_action'),
      actionKey: 'refresh-enterprise-status',
      meta: application?.submitted_at
        ? formatInlineMessage(t('auth_status_notice_pending_meta'), { submittedAt: application.submitted_at })
        : ''
    }
  }
  if (authIsEnterpriseRole.value && authCurrentAccountStatus.value === 'rejected') {
    return {
      tone: 'rejected',
      title: t('auth_status_notice_rejected_title'),
      hint: t('auth_status_notice_rejected_hint'),
      actionLabel: t('enterprise_application_resume_registration'),
      actionKey: 'resume-enterprise-registration',
      secondaryActionLabel: t('auth_status_notice_refresh_action'),
      secondaryActionKey: 'refresh-enterprise-status',
      meta: application?.reviewed_at
        ? formatInlineMessage(t('auth_status_notice_rejected_meta'), { reviewedAt: application.reviewed_at })
        : '',
      detail: String(application?.review_note || '').trim()
    }
  }
  if (authIsEnterpriseRole.value && authCurrentAccountStatus.value === 'approved') {
    return {
      tone: 'approved',
      title: t('auth_status_notice_approved_title'),
      hint: t('auth_status_notice_approved_hint'),
      actionLabel: t('enterprise_settings_entry'),
      actionKey: 'enterprise-settings',
      meta: authCurrentOrganizationName.value || ''
    }
  }
  return null
})
const authEnterpriseStatusFollowupVisible = computed(() => {
  if (!authAuthenticated.value || !authIsEnterpriseRole.value || !authEnterpriseStatusFollowup.value) return false
  const currentUsername = String(
    authCurrentEnterpriseApplication.value?.username || authCurrentUser.value?.username || ''
  ).trim()
  const followupUsername = String(authEnterpriseStatusFollowup.value?.username || '').trim()
  if (followupUsername && currentUsername && followupUsername !== currentUsername) return false
  return ['approved', 'rejected'].includes(String(authEnterpriseStatusFollowup.value?.status || '').trim())
})
const authEnterpriseStatusFollowupTitle = computed(() => {
  if (!authEnterpriseStatusFollowupVisible.value) return ''
  return t(
    authEnterpriseStatusFollowup.value?.status === 'approved'
      ? 'auth_enterprise_status_followup_title_approved'
      : 'auth_enterprise_status_followup_title_rejected'
  )
})
const authEnterpriseStatusFollowupHint = computed(() => {
  if (!authEnterpriseStatusFollowupVisible.value) return ''
  return t(
    authEnterpriseStatusFollowup.value?.status === 'approved'
      ? 'auth_enterprise_status_followup_hint_approved'
      : 'auth_enterprise_status_followup_hint_rejected'
  )
})
const authEnterpriseStatusFollowupNextStepText = computed(() => {
  if (!authEnterpriseStatusFollowupVisible.value) return ''
  return t(
    authEnterpriseStatusFollowup.value?.status === 'approved'
      ? 'auth_enterprise_status_followup_next_step_approved'
      : 'auth_enterprise_status_followup_next_step_rejected'
  )
})
const authEnterpriseStatusFollowupUpdatedText = computed(() =>
  authEnterpriseStatusFollowup.value?.updated_at
    ? formatInlineMessage(t('operations_last_updated'), { at: authEnterpriseStatusFollowup.value.updated_at })
    : ''
)
const enterpriseApprovalReviewFollowupVisible = computed(() =>
  authAuthenticated.value && authCurrentRole.value === 'platform_admin' && Boolean(enterpriseApprovalReviewFollowup.value)
)
const enterpriseApprovalReviewFollowupMetaText = computed(() => {
  if (!enterpriseApprovalReviewFollowupVisible.value) return ''
  return formatInlineMessage(t('enterprise_approval_followup_meta'), {
    status: t(`enterprise_approval_status_${enterpriseApprovalReviewFollowup.value?.status || 'pending'}`),
    reviewer: enterpriseApprovalReviewFollowup.value?.reviewed_by || '—',
    reviewedAt:
      enterpriseApprovalReviewFollowup.value?.reviewed_at ||
      enterpriseApprovalReviewFollowup.value?.submitted_at ||
      '—'
  })
})
const enterpriseApprovalReviewFollowupUpdatedText = computed(() =>
  enterpriseApprovalReviewFollowup.value?.updated_at
    ? formatInlineMessage(t('operations_last_updated'), { at: enterpriseApprovalReviewFollowup.value.updated_at })
    : ''
)
const enterpriseApplicationNextStepText = computed(() => {
  if (!authIsEnterpriseRole.value) return ''
  if (authCurrentAccountStatus.value === 'pending') {
    return t('enterprise_settings_application_next_step_pending')
  }
  if (authCurrentAccountStatus.value === 'rejected') {
    return t('enterprise_settings_application_next_step_rejected')
  }
  return t('enterprise_settings_application_next_step_approved')
})
const authEnterpriseRegisterExistingHint = computed(() => {
  if (!authIsEnterpriseRole.value) return ''
  if (authCurrentAccountStatus.value === 'rejected') {
    return t('auth_enterprise_register_existing_hint_rejected')
  }
  if (authCurrentAccountStatus.value === 'pending') {
    return t('auth_enterprise_register_existing_hint_pending')
  }
  return t('auth_enterprise_register_existing_hint_approved')
})
const authEnterpriseRegisterExistingPrimaryActionLabel = computed(() =>
  authCurrentAccountStatus.value === 'approved'
    ? t('auth_enterprise_register_existing_action_open_settings')
    : t('auth_enterprise_register_existing_action_use')
)
const authEnterpriseRegisterFollowupProgressItems = computed(() =>
  buildEnterpriseApplicationProgressItems(
    authEnterpriseRegisterFollowup.value,
    String(authEnterpriseRegisterFollowup.value?.status || 'pending')
  )
)
const authEnterpriseRegisterFollowupUpdatedText = computed(() =>
  authEnterpriseRegisterFollowup.value?.updated_at
    ? formatInlineMessage(t('operations_last_updated'), { at: authEnterpriseRegisterFollowup.value.updated_at })
    : ''
)
const authEnterpriseStatusFollowupProgressItems = computed(() =>
  buildEnterpriseApplicationProgressItems(
    authEnterpriseStatusFollowup.value,
    String(authEnterpriseStatusFollowup.value?.status || authCurrentAccountStatus.value || 'pending')
  )
)
const enterpriseApprovalReviewFollowupProgressItems = computed(() =>
  buildEnterpriseApplicationProgressItems(
    enterpriseApprovalReviewFollowup.value,
    String(enterpriseApprovalReviewFollowup.value?.status || 'pending')
  )
)
const enterpriseApprovalReviewFollowupNextStepText = computed(() => {
  const status = String(enterpriseApprovalReviewFollowup.value?.status || '').trim().toLowerCase()
  if (status === 'approved') return t('enterprise_approval_next_step_approved')
  if (status === 'rejected') return t('enterprise_approval_next_step_rejected')
  return t('enterprise_approval_next_step_pending')
})
const enterpriseApplicationActionItems = computed(() => {
  if (!authIsEnterpriseRole.value) return []
  const items = []
  if (authCurrentEnterpriseApplication.value?.company_name) {
    items.push({
      key: 'copy-company-name',
      label: t('enterprise_application_copy_company_name'),
      tone: 'ghost'
    })
  }
  if (authCurrentEnterpriseApplication.value?.contact_name) {
    items.push({
      key: 'copy-contact-name',
      label: t('enterprise_application_copy_contact_name'),
      tone: 'ghost'
    })
  }
  if (authCurrentEnterpriseApplication.value?.username) {
    items.push({
      key: 'copy-username',
      label: t('enterprise_application_copy_username'),
      tone: 'ghost'
    })
  }
  if (authCurrentEnterpriseApplication.value?.contact_email) {
    items.push({
      key: 'copy-contact-email',
      label: t('enterprise_application_copy_contact_email'),
      tone: 'ghost'
    })
  }
  if (authCurrentEnterpriseApplication.value?.company_name || authCurrentEnterpriseApplication.value?.username) {
    items.push({
      key: 'copy-summary',
      label: t('enterprise_application_copy_summary'),
      tone: 'ghost'
    })
  }
  if (authCurrentEnterpriseApplication.value?.review_note) {
    items.push({
      key: 'copy-review-note',
      label: t('enterprise_application_copy_review_note'),
      tone: 'ghost'
    })
  }
  if (authCurrentEnterpriseApplication.value && authCurrentAccountStatus.value !== 'approved') {
    items.push({
      key: 'edit-application',
      label: t('auth_enterprise_register_followup_edit'),
      tone: 'secondary'
    })
  }
  items.push({
    key: 'refresh-status',
    label: t('enterprise_settings_application_refresh'),
    tone: 'ghost'
  })
  if (authCurrentAccountStatus.value !== 'approved') {
    return items
  }
  if (enterpriseUiRole.value === 'enterprise_operator') {
    items.push(
      {
        key: 'switch-runtime',
        label: t('enterprise_settings_tab_runtime'),
        tone: 'secondary'
      },
      {
        key: 'jump-control',
        label: t('enterprise_settings_open_dispatch'),
        tone: 'secondary'
      },
      {
        key: 'jump-queue',
        label: t('enterprise_settings_open_queue'),
        tone: 'secondary'
      }
    )
    return items
  }
  if (enterpriseUiRole.value === 'enterprise_logistics') {
    items.push(
      {
        key: 'switch-map-profiles',
        label: t('enterprise_settings_tab_map_profiles'),
        tone: 'secondary'
      },
      {
        key: 'jump-points',
        label: t('enterprise_settings_open_points'),
        tone: 'secondary'
      },
      {
        key: 'jump-templates',
        label: t('enterprise_settings_open_templates'),
        tone: 'secondary'
      }
    )
    return items
  }
  items.push(
    {
      key: 'switch-audit',
      label: t('enterprise_settings_tab_audit'),
      tone: 'secondary'
    },
    {
      key: 'jump-audit',
      label: t('enterprise_settings_open_audit'),
      tone: 'secondary'
    },
    {
      key: 'jump-ai',
      label: t('enterprise_settings_open_ai'),
      tone: 'secondary'
    }
  )
  return items
})
const authEnterpriseApplicationProgressItems = computed(() =>
  buildEnterpriseApplicationProgressItems(authCurrentEnterpriseApplication.value, authCurrentAccountStatus.value)
)
const selectedEnterpriseApplicationProgressItems = computed(() =>
  buildEnterpriseApplicationProgressItems(selectedEnterpriseApplication.value)
)
const selectedEnterpriseApplicationNextStepText = computed(() => {
  const status = String(selectedEnterpriseApplication.value?.status || '').trim().toLowerCase()
  if (status === 'approved') return t('enterprise_approval_next_step_approved')
  if (status === 'rejected') return t('enterprise_approval_next_step_rejected')
  return t('enterprise_approval_next_step_pending')
})
const selectedEnterpriseApplicationActionItems = computed(() => {
  const application = selectedEnterpriseApplication.value
  if (!application) return []
  const status = String(application.status || '').trim().toLowerCase()
  const items = []
  if (application.company_name) {
    items.push({
      key: 'copy-company-name',
      label: t('enterprise_application_copy_company_name'),
      tone: 'ghost'
    })
  }
  if (application.contact_name) {
    items.push({
      key: 'copy-contact-name',
      label: t('enterprise_application_copy_contact_name'),
      tone: 'ghost'
    })
  }
  if (application.username) {
    items.push({
      key: 'copy-username',
      label: t('enterprise_application_copy_username'),
      tone: 'ghost'
    })
  }
  if (application.contact_email) {
    items.push({
      key: 'copy-contact-email',
      label: t('enterprise_application_copy_contact_email'),
      tone: 'ghost'
    })
  }
  if (application.review_note) {
    items.push({
      key: 'copy-review-note',
      label: t('enterprise_application_copy_review_note'),
      tone: 'ghost'
    })
  }
  if (application.company_name || application.username) {
    items.push({
      key: 'copy-summary',
      label: t('enterprise_application_copy_summary'),
      tone: 'ghost'
    })
  }
  if (status === 'approved' || status === 'rejected') {
    items.push({
      key: 'focus-pending',
      label: t('enterprise_approval_focus_pending'),
      tone: 'secondary'
    })
  }
  return items
})
const enterpriseApprovalReviewNoteTemplates = computed(() => [
  {
    key: 'approve-standard',
    label: t('enterprise_approval_note_template_approve_label'),
    value: t('enterprise_approval_note_template_approve_value')
  },
  {
    key: 'reject-followup',
    label: t('enterprise_approval_note_template_reject_label'),
    value: t('enterprise_approval_note_template_reject_value')
  },
  {
    key: 'request-more-info',
    label: t('enterprise_approval_note_template_more_info_label'),
    value: t('enterprise_approval_note_template_more_info_value')
  }
])
const enterpriseApprovalReviewNoteTrimmed = computed(() =>
  String(enterpriseApprovalReviewNote.value || '').trim()
)
const enterpriseApprovalReviewNoteLength = computed(() =>
  enterpriseApprovalReviewNoteTrimmed.value.length
)
const enterpriseApprovalCanReject = computed(() =>
  enterpriseApprovalReviewNoteLength.value > 0
)
const enterpriseApprovalCurrentDraftMeta = computed(() => {
  const applicationId = Number(selectedEnterpriseApplicationId.value || 0)
  if (!applicationId) return null
  return enterpriseApprovalNoteDrafts.value[String(applicationId)] || null
})
const enterpriseApprovalDraftCount = computed(() =>
  Object.values(enterpriseApprovalNoteDrafts.value || {}).filter(item => String(item?.text || '').trim()).length
)
const enterpriseApprovalReviewDraftUpdatedText = computed(() =>
  enterpriseApprovalCurrentDraftMeta.value?.updated_at
    ? formatInlineMessage(t('enterprise_approval_review_note_saved_at'), {
      at: formatDateTimeInline(enterpriseApprovalCurrentDraftMeta.value.updated_at)
    })
    : ''
)
const enterpriseApprovalDraftSummaryText = computed(() =>
  enterpriseApprovalDraftCount.value > 0
    ? formatInlineMessage(t('enterprise_approval_draft_summary'), {
      count: enterpriseApprovalDraftCount.value
    })
    : t('enterprise_approval_draft_summary_empty')
)
const authTitleButtonTitle = computed(() =>
  authAuthenticated.value
    ? `${t('auth_current_identity')}: ${authCurrentDisplayName.value} (${authRoleLabel.value})`
    : t('auth_open_dialog')
)
const authModalTitle = computed(() =>
  dashboardUnlocked.value ? t('auth_title') : t('auth_gate_title')
)
const authPanelModeText = computed(() =>
  dashboardUnlocked.value ? t('auth_switch_hint') : t('auth_gate_hint')
)
const authPrimaryAccounts = computed(() => {
  const preferredRoles = ['personal', 'enterprise_operator', 'enterprise_logistics', 'enterprise_admin', 'platform_admin']
  return preferredRoles
    .map(role => authDemoAccounts.find(account => account.role === role))
    .filter(Boolean)
})
const authCapabilitySet = computed(() => new Set((authCurrentCapabilities.value ?? []).map(item => String(item))))
const authCanDispatchWrite = computed(() => authCapabilitySet.value.has('dispatch.write'))
const authCanFaultWrite = computed(() => authCapabilitySet.value.has('fault.write'))
const authCanMapWrite = computed(() => authCapabilitySet.value.has('map.write'))
const authCanTemplateWrite = computed(() => authCapabilitySet.value.has('template.write'))
const authCanPointWrite = computed(() => authCapabilitySet.value.has('point.write'))
const authCanJsonWrite = computed(() => authCapabilitySet.value.has('json.write'))
const authCanExperimentWrite = computed(() => authCapabilitySet.value.has('experiment.write'))
const authCanViewAudit = computed(() => authCapabilitySet.value.has('audit.view'))
const authCanAiRender = computed(() => authCapabilitySet.value.has('ai.render'))
const authCanForceApplyMap = computed(() => authCapabilitySet.value.has('map.force_apply'))
const authCanEnterpriseApprove = computed(() => authCapabilitySet.value.has('enterprise.approve'))
const authCanSystemManage = computed(() => authCapabilitySet.value.has('system.manage'))
const authCanEnterpriseRequestSubmit = computed(() => authCapabilitySet.value.has('feedback.enterprise.submit'))
const authCanPlatformBugSubmit = computed(() => authCapabilitySet.value.has('feedback.platform.submit'))
const authCanPlatformBugManage = computed(() => authCapabilitySet.value.has('feedback.platform.manage'))
const authCanUsePlatformBugFeedback = computed(() => authCanPlatformBugSubmit.value || authCanPlatformBugManage.value)
const authIsEnterpriseRole = computed(() =>
  ['enterprise_operator', 'enterprise_logistics', 'enterprise_admin'].includes(authCurrentRole.value)
)
const canUseEnterpriseUi = computed(() => authIsEnterpriseRole.value || isPlatformAdminEnterprisePreviewMode.value)
const platformApprovalPendingCount = computed(() => Number(enterpriseApprovalSummary.value.pending || 0))
const selectedManagedUser = computed(() =>
  managedUserAccounts.value.find(item => String(item.id || '') === String(selectedManagedUserId.value || '')) || null
)
const selectedEnterpriseRequest = computed(() =>
  enterpriseRequestItems.value.find(item => String(item.id || '') === String(selectedEnterpriseRequestId.value || '')) || null
)
const selectedPlatformBugFeedback = computed(() =>
  platformBugFeedbackItems.value.find(item => String(item.id || '') === String(selectedPlatformBugFeedbackId.value || '')) || null
)
const selectedManagedUserIdSet = computed(() => new Set(selectedManagedUserIds.value.map(item => String(item || ''))))
const selectedManagedUsers = computed(() =>
  managedUserAccounts.value.filter(item => selectedManagedUserIdSet.value.has(String(item.id || '')))
)
const accountGovernanceSelectedCount = computed(() => selectedManagedUsers.value.length)
const accountGovernanceBulkSuspendableUsers = computed(() =>
  selectedManagedUsers.value.filter(item => !['suspended', 'deactivated'].includes(String(item.account_status || 'approved')))
)
const accountGovernanceBulkUnsuspendableUsers = computed(() =>
  selectedManagedUsers.value.filter(item => String(item.account_status || 'approved') === 'suspended')
)
const accountGovernanceBulkDeactivatableUsers = computed(() =>
  selectedManagedUsers.value.filter(item => String(item.account_status || 'approved') !== 'deactivated')
)
const accountGovernanceSelectionSummaryText = computed(() => {
  if (!accountGovernanceSelectedCount.value) return ''
  return formatInlineMessage(t('account_governance_selection_summary'), {
    count: accountGovernanceSelectedCount.value,
    suspendable: accountGovernanceBulkSuspendableUsers.value.length,
    unsuspendable: accountGovernanceBulkUnsuspendableUsers.value.length,
    deactivatable: accountGovernanceBulkDeactivatableUsers.value.length
  })
})
const accountGovernanceActionTemplateItems = computed(() => [
  {
    key: 'policy',
    label: t('account_governance_template_policy_label'),
    hint: t('account_governance_template_policy_hint'),
    reason: t('account_governance_template_policy_reason'),
    note: t('account_governance_template_policy_note'),
    duration: '7d'
  },
  {
    key: 'review',
    label: t('account_governance_template_review_label'),
    hint: t('account_governance_template_review_hint'),
    reason: t('account_governance_template_review_reason'),
    note: t('account_governance_template_review_note'),
    duration: '30d'
  },
  {
    key: 'security',
    label: t('account_governance_template_security_label'),
    hint: t('account_governance_template_security_hint'),
    reason: t('account_governance_template_security_reason'),
    note: t('account_governance_template_security_note'),
    duration: '1d'
  },
  {
    key: 'deactivate',
    label: t('account_governance_template_deactivate_label'),
    hint: t('account_governance_template_deactivate_hint'),
    reason: t('account_governance_template_deactivate_reason'),
    note: t('account_governance_template_deactivate_note'),
    duration: 'permanent'
  }
])
const accountGovernanceFilterSummaryText = computed(() => {
  const roleLabelMap = {
    all: t('account_governance_role_all'),
    personal: t('account_governance_role_personal'),
    enterprise: t('account_governance_role_enterprise'),
    platform_admin: t('account_governance_role_platform_admin')
  }
  const statusLabelMap = {
    all: t('account_governance_status_all'),
    approved: t('account_governance_status_approved'),
    pending: t('account_governance_status_pending'),
    rejected: t('account_governance_status_rejected'),
    suspended: t('account_governance_status_suspended'),
    deactivated: t('account_governance_status_deactivated')
  }
  return formatInlineMessage(t('account_governance_filter_summary'), {
    count: managedUserAccounts.value.length,
    role: roleLabelMap[accountGovernanceRoleFilter.value] || roleLabelMap.all,
    status: statusLabelMap[accountGovernanceStatusFilter.value] || statusLabelMap.all,
    search: String(accountGovernanceSearch.value || '').trim() || t('account_governance_filter_search_empty')
  })
})
const accountGovernanceEmptyHint = computed(() => {
  if (String(accountGovernanceSearch.value || '').trim()) {
    return t('account_governance_empty_search')
  }
  if (accountGovernanceRoleFilter.value !== 'all' || accountGovernanceStatusFilter.value !== 'all') {
    return t('account_governance_empty_filtered')
  }
  return t('account_governance_empty')
})
const accountGovernanceLastFetchedText = computed(() =>
  accountGovernanceLastFetchedAt.value
    ? formatInlineMessage(t('operations_last_updated'), { at: accountGovernanceLastFetchedAt.value })
    : ''
)
const enterpriseRequestFilterSummaryText = computed(() =>
  formatInlineMessage(t('enterprise_request_filter_summary'), {
    count: enterpriseRequestItems.value.length,
    status: t(`feedback_status_${enterpriseRequestStatusFilter.value || 'all'}`),
    category: t(`enterprise_request_category_${enterpriseRequestCategoryFilter.value || 'all'}`),
    search: String(enterpriseRequestSearch.value || '').trim() || t('enterprise_request_filter_search_empty')
  })
)
const enterpriseRequestEmptyHint = computed(() => {
  if (String(enterpriseRequestSearch.value || '').trim()) return t('enterprise_request_empty_search')
  if (enterpriseRequestStatusFilter.value !== 'all' || enterpriseRequestCategoryFilter.value !== 'all') {
    return t('enterprise_request_empty_filtered')
  }
  return t('enterprise_request_empty')
})
const enterpriseRequestLastFetchedText = computed(() =>
  enterpriseRequestLastFetchedAt.value
    ? formatInlineMessage(t('operations_last_updated'), { at: enterpriseRequestLastFetchedAt.value })
    : ''
)
const enterpriseRequestCanManageSelected = computed(() => {
  if (!selectedEnterpriseRequest.value) return false
  if (authCurrentRole.value === 'enterprise_admin' && authCurrentAccountStatus.value === 'approved') return true
  return String(selectedEnterpriseRequest.value.target_user_id || '') === String(authCurrentUser.value?.id || '')
})
const platformBugFeedbackFilterSummaryText = computed(() =>
  formatInlineMessage(t('platform_bug_feedback_filter_summary'), {
    count: platformBugFeedbackItems.value.length,
    status: t(`feedback_status_${platformBugFeedbackStatusFilter.value || 'all'}`),
    category: t(`platform_bug_feedback_category_${platformBugFeedbackCategoryFilter.value || 'all'}`),
    search: String(platformBugFeedbackSearch.value || '').trim() || t('platform_bug_feedback_filter_search_empty')
  })
)
const platformBugFeedbackEmptyHint = computed(() => {
  if (String(platformBugFeedbackSearch.value || '').trim()) return t('platform_bug_feedback_empty_search')
  if (platformBugFeedbackStatusFilter.value !== 'all' || platformBugFeedbackCategoryFilter.value !== 'all') {
    return t('platform_bug_feedback_empty_filtered')
  }
  return t('platform_bug_feedback_empty')
})
const platformBugFeedbackLastFetchedText = computed(() =>
  platformBugFeedbackLastFetchedAt.value
    ? formatInlineMessage(t('operations_last_updated'), { at: platformBugFeedbackLastFetchedAt.value })
    : ''
)
const platformBugFeedbackOpenCount = computed(() => Number(platformBugFeedbackSummary.value.open || 0))
const platformBugFeedbackCanManageSelected = computed(() =>
  authCanPlatformBugManage.value && Boolean(selectedPlatformBugFeedback.value)
)
const enterpriseToolbarStatusBadgeText = computed(() => {
  if (isPlatformAdminEnterprisePreviewMode.value) return ''
  if (!authIsEnterpriseRole.value) return ''
  if (authCurrentAccountStatus.value === 'pending') return t('auth_account_status_pending_short')
  if (authCurrentAccountStatus.value === 'rejected') return t('auth_account_status_rejected_short')
  return ''
})
const filteredEnterpriseApplications = computed(() => {
  const keyword = String(enterpriseApprovalSearch.value || '').trim().toLowerCase()
  return enterpriseApplications.value.filter(item => {
    if (enterpriseApprovalDraftOnly.value && !hasEnterpriseApprovalDraft(item.id)) {
      return false
    }
    if (!keyword) return true
    return [
      item.company_name,
      item.contact_name,
      item.contact_email,
      item.username,
      item.status
    ].some(value => String(value || '').toLowerCase().includes(keyword))
  })
})
const selectedEnterpriseApplication = computed(() =>
  filteredEnterpriseApplications.value.find(item => Number(item.id) === Number(selectedEnterpriseApplicationId.value)) || null
)
const selectedEnterpriseApplicationIndex = computed(() =>
  filteredEnterpriseApplications.value.findIndex(item => Number(item.id) === Number(selectedEnterpriseApplicationId.value))
)
const selectedEnterpriseApplicationPositionText = computed(() => {
  if (!selectedEnterpriseApplication.value || selectedEnterpriseApplicationIndex.value < 0) return ''
  return formatInlineMessage(t('enterprise_approval_position'), {
    index: selectedEnterpriseApplicationIndex.value + 1,
    total: filteredEnterpriseApplications.value.length
  })
})
const canSelectPreviousEnterpriseApplication = computed(() =>
  selectedEnterpriseApplicationIndex.value > 0
)
const canSelectNextEnterpriseApplication = computed(() =>
  selectedEnterpriseApplicationIndex.value >= 0 &&
  selectedEnterpriseApplicationIndex.value < filteredEnterpriseApplications.value.length - 1
)
const nextEnterpriseApprovalDraftApplicationId = computed(() => {
  const draftItems = filteredEnterpriseApplications.value.filter(item => hasEnterpriseApprovalDraft(item.id))
  if (!draftItems.length) return null
  const currentId = Number(selectedEnterpriseApplicationId.value || 0)
  const currentDraftIndex = draftItems.findIndex(item => Number(item.id) === currentId)
  if (currentDraftIndex === -1) {
    return draftItems[0]?.id ?? null
  }
  if (draftItems.length === 1) return null
  return draftItems[(currentDraftIndex + 1) % draftItems.length]?.id ?? null
})
const hasNextEnterpriseApprovalDraft = computed(() =>
  Number(nextEnterpriseApprovalDraftApplicationId.value || 0) > 0
)
const recentReviewedEnterpriseApplications = computed(() =>
  [...enterpriseApplications.value]
    .filter(item => item.status === 'approved' || item.status === 'rejected')
    .sort((left, right) => compareTime(right.reviewed_at || right.submitted_at, left.reviewed_at || left.submitted_at))
    .slice(0, 3)
)
const recentPendingEnterpriseApplications = computed(() =>
  [...enterpriseApplications.value]
    .filter(item => item.status === 'pending')
    .sort((left, right) => compareTime(right.submitted_at, left.submitted_at))
    .slice(0, 3)
)
const recentEnterpriseApprovalDraftApplications = computed(() =>
  [...enterpriseApplications.value]
    .filter(item => hasEnterpriseApprovalDraft(item.id))
    .sort((left, right) =>
      compareTime(
        enterpriseApprovalNoteDrafts.value[String(right.id)]?.updated_at,
        enterpriseApprovalNoteDrafts.value[String(left.id)]?.updated_at
      )
    )
    .slice(0, 3)
)
const enterpriseApprovalFilterSummaryText = computed(() => {
  const count = filteredEnterpriseApplications.value.length
  const statusLabel = t(`enterprise_approval_status_${enterpriseApprovalStatusFilter.value || 'all'}`)
  const keyword = String(enterpriseApprovalSearch.value || '').trim()
  const draftSuffix = enterpriseApprovalDraftOnly.value
    ? ` · ${t('enterprise_approval_filter_draft_active')}`
    : ''
  if (keyword) {
    return formatInlineMessage(t('enterprise_approval_filter_summary_search'), {
      count,
      status: statusLabel,
      keyword
    }) + draftSuffix
  }
  return formatInlineMessage(t('enterprise_approval_filter_summary'), {
    count,
    status: statusLabel
  }) + draftSuffix
})
const enterpriseApprovalEmptyStateHint = computed(() => {
  const hasSearch = Boolean(String(enterpriseApprovalSearch.value || '').trim())
  if (enterpriseApprovalDraftOnly.value) {
    return t('enterprise_approval_empty_drafts_hint')
  }
  if (enterpriseApprovalStatusFilter.value === 'pending' && !hasSearch) {
    return t('enterprise_approval_empty_pending_hint')
  }
  return t('enterprise_approval_empty_filtered_hint')
})
const enterpriseApprovalEmptyStateActions = computed(() => {
  const actions = []
  const hasSearch = Boolean(String(enterpriseApprovalSearch.value || '').trim())
  if (enterpriseApprovalDraftOnly.value) {
    actions.push({
      key: 'clear-draft-filter',
      label: t('enterprise_approval_filter_draft_clear'),
      tone: 'secondary'
    })
  }
  if (enterpriseApprovalStatusFilter.value !== 'pending') {
    actions.push({
      key: 'show-pending',
      label: t('enterprise_approval_focus_pending'),
      tone: 'secondary'
    })
  }
  if (enterpriseApprovalStatusFilter.value !== 'all' || hasSearch) {
    actions.push({
      key: 'show-all',
      label: t('enterprise_approval_show_all'),
      tone: 'ghost'
    })
  }
  return actions
})
const enterpriseApprovalLastFetchedText = computed(() =>
  enterpriseApprovalLastFetchedAt.value
    ? formatInlineMessage(t('operations_last_updated'), { at: enterpriseApprovalLastFetchedAt.value })
    : ''
)
const authAccountStatusLastCheckedText = computed(() =>
  authLastFetchedAt.value
    ? formatInlineMessage(t('operations_last_updated'), { at: authLastFetchedAt.value })
    : ''
)
const authEnterpriseQuickActionItems = computed(() => {
  if (!authIsEnterpriseRole.value) return []
  const application = authCurrentEnterpriseApplication.value
  const items = []
  if (application?.company_name) {
    items.push({
      key: 'copy-company-name',
      label: t('enterprise_application_copy_company_name'),
      tone: 'ghost'
    })
  }
  if (application?.contact_name) {
    items.push({
      key: 'copy-contact-name',
      label: t('enterprise_application_copy_contact_name'),
      tone: 'ghost'
    })
  }
  if (application?.username) {
    items.push({
      key: 'copy-username',
      label: t('enterprise_application_copy_username'),
      tone: 'ghost'
    })
  }
  if (application?.contact_email) {
    items.push({
      key: 'copy-contact-email',
      label: t('enterprise_application_copy_contact_email'),
      tone: 'ghost'
    })
  }
  if (application?.review_note) {
    items.push({
      key: 'copy-review-note',
      label: t('enterprise_application_copy_review_note'),
      tone: 'ghost'
    })
  }
  if (application?.company_name || application?.username) {
    items.push({
      key: 'copy-summary',
      label: t('enterprise_application_copy_summary'),
      tone: 'ghost'
    })
  }
  if (application && authCurrentAccountStatus.value !== 'approved') {
    items.push({
      key: 'edit-application',
      label: t('auth_enterprise_register_followup_edit'),
      tone: 'secondary'
    })
  }
  if (authCurrentAccountStatus.value === 'approved') {
    items.push({
      key: 'open-enterprise-settings',
      label: t('enterprise_settings_entry'),
      tone: 'secondary'
    })
  } else {
    items.push({
      key: 'refresh-status',
      label: t('auth_status_notice_refresh_action'),
      tone: 'secondary'
    })
  }
  return items
})
const authEnterpriseRegisterSnapshotActionItems = computed(() => {
  if (!authIsEnterpriseRole.value || !authCurrentEnterpriseApplication.value) return []
  const sharedItems = authEnterpriseQuickActionItems.value.filter(item => item.key !== 'open-enterprise-settings')
  if (authCurrentAccountStatus.value === 'approved') {
    return [
      {
        key: 'apply-workspace',
        label: t('enterprise_settings_apply_workspace_preset'),
        tone: 'secondary'
      },
      ...sharedItems
    ]
  }
  return sharedItems
})
const authEnterpriseQuickActionHint = computed(() => {
  if (!authIsEnterpriseRole.value) return ''
  if (authCurrentAccountStatus.value === 'approved') return t('auth_enterprise_actions_hint_approved')
  if (authCurrentAccountStatus.value === 'rejected') return t('auth_enterprise_actions_hint_rejected')
  return t('auth_enterprise_actions_hint_pending')
})
const enterpriseRoleWorkspaceActionItems = computed(() => {
  if ((!authIsEnterpriseRole.value && !isPlatformAdminEnterprisePreviewMode.value) || !enterpriseUiApproved.value) return []
  if (enterpriseUiRole.value === 'enterprise_operator') {
    return [
      {
        key: 'open-runtime',
        label: t('enterprise_settings_tab_runtime'),
        tone: 'secondary'
      },
      {
        key: 'jump-control',
        label: t('enterprise_settings_open_dispatch'),
        tone: 'ghost'
      },
      {
        key: 'jump-queue',
        label: t('enterprise_settings_open_queue'),
        tone: 'ghost'
      }
    ]
  }
  if (enterpriseUiRole.value === 'enterprise_logistics') {
    return [
      {
        key: 'open-map-profiles',
        label: t('enterprise_settings_tab_map_profiles'),
        tone: 'secondary'
      },
      {
        key: 'jump-points',
        label: t('enterprise_settings_open_points'),
        tone: 'ghost'
      },
      {
        key: 'jump-templates',
        label: t('enterprise_settings_open_templates'),
        tone: 'ghost'
      }
    ]
  }
  return [
    {
      key: 'open-audit',
      label: t('enterprise_settings_tab_audit'),
      tone: 'secondary'
    },
    {
      key: 'jump-audit',
      label: t('enterprise_settings_open_audit'),
      tone: 'ghost'
    },
    {
      key: 'jump-ai',
      label: t('enterprise_settings_open_ai'),
      tone: 'ghost'
    }
  ]
})
const enterpriseWorkspacePopupActionItems = computed(() => {
  if (!showEnterpriseWorkspaceBanner.value) return []

  const shortLabelMap = {
    apply: t('enterprise_settings_apply_workspace_preset_short'),
    'open-runtime': t('enterprise_settings_tab_runtime_short'),
    'jump-control': t('enterprise_settings_open_dispatch_short'),
    'jump-queue': t('enterprise_settings_open_queue_short'),
    'open-map-profiles': t('enterprise_settings_tab_map_profiles_short'),
    'jump-points': t('enterprise_settings_open_points_short'),
    'jump-templates': t('enterprise_settings_open_templates_short'),
    'open-audit': t('enterprise_settings_tab_audit_short'),
    'jump-audit': t('enterprise_settings_open_audit_short'),
    'jump-ai': t('enterprise_settings_open_ai_short'),
  }

  return [
    {
      key: 'apply-workspace',
      label: shortLabelMap.apply,
      tone: 'secondary',
      handler: applyCurrentEnterpriseWorkspacePreset,
    },
    ...enterpriseRoleWorkspaceActionItems.value.map(action => ({
      ...action,
      label: shortLabelMap[action.key] || action.label,
      handler: () => runEnterpriseWorkspaceAction(action.key),
    })),
  ]
})
const showEnterpriseWorkspaceBanner = computed(() =>
  canUseEnterpriseUi.value && enterpriseUiApproved.value
)
const platformRecentAuditEntries = computed(() => operationAudits.value.slice(0, 5))
const platformAdminPreviewRoleItems = computed(() => [
  { key: 'enterprise_admin', label: t('auth_role_enterprise_admin') },
  { key: 'enterprise_operator', label: t('auth_role_enterprise_operator') },
  { key: 'enterprise_logistics', label: t('auth_role_enterprise_logistics') }
])
const platformAdminPreviewTitle = computed(() => {
  if (isPlatformAdminPersonalPreviewMode.value) return t('platform_admin_preview_personal_title')
  if (isPlatformAdminEnterprisePreviewMode.value) {
    return formatInlineMessage(t('platform_admin_preview_enterprise_title'), {
      role: enterpriseUiRoleLabel.value
    })
  }
  return ''
})
const platformAdminPreviewHint = computed(() => {
  if (isPlatformAdminPersonalPreviewMode.value) return t('platform_admin_preview_personal_hint')
  if (isPlatformAdminEnterprisePreviewMode.value) return t('platform_admin_preview_enterprise_hint')
  return ''
})
const enterpriseWorkspacePopupDismissed = ref(false)
const enterpriseWorkspacePopupX = ref(null)
const enterpriseWorkspacePopupY = ref(10)
let enterpriseWorkspacePopupDragging = false
let enterpriseWorkspacePopupDragOffsetX = 0
let enterpriseWorkspacePopupDragOffsetY = 0
const showEnterpriseWorkspacePopup = computed(() =>
  showEnterpriseWorkspaceBanner.value && !enterpriseWorkspacePopupDismissed.value
)
const enterpriseWorkspacePopupStyle = computed(() => {
  if (!showEnterpriseWorkspacePopup.value || enterpriseWorkspacePopupX.value == null) return {}
  return {
    left: `${enterpriseWorkspacePopupX.value}px`,
    top: `${enterpriseWorkspacePopupY.value}px`,
    right: 'auto',
    opacity: 0.82
  }
})
const enterpriseMapEditorDraftBlockedCellSet = computed(() =>
  new Set((enterpriseMapEditorDraftBlockedCells.value || []).map(cell => blockedCellKey(cell.x, cell.y)))
)
const enterpriseMapEditorDraftValidCellSet = computed(() =>
  new Set((enterpriseMapEditorDraftValidCells.value || []).map(cell => blockedCellKey(cell.x, cell.y)))
)
const enterpriseMapEditorRows = computed(() =>
  Array.from({ length: Number(enterpriseMapEditorDraftRows.value || gridRowsValue()) }, (_, index) => index)
)
const enterpriseMapEditorCols = computed(() =>
  Array.from({ length: Number(enterpriseMapEditorDraftCols.value || gridColsValue()) }, (_, index) => index)
)
const enterpriseMapEditorBlockedCount = computed(() => enterpriseMapEditorDraftBlockedCells.value.length)
const enterpriseMapEditorValidCount = computed(() => enterpriseMapEditorDraftValidCells.value.length)
const enterpriseMapEditorIsIrregular = computed(() =>
  enterpriseMapEditorValidCount.value !== Number(enterpriseMapEditorDraftCols.value || gridColsValue()) * Number(enterpriseMapEditorDraftRows.value || gridRowsValue())
)
const enterpriseMapEditorCellSize = computed(() =>
  Math.max(16, Math.round(30 * Number(enterpriseMapEditorZoom.value || ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT)))
)
const enterpriseMapEditorZoomPercent = computed(() =>
  `${Math.round(Number(enterpriseMapEditorZoom.value || ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT) * 100)}%`
)
const enterpriseMapEditorFootprintLabel = computed(() =>
  `${Number(enterpriseMapEditorDraftCols.value || gridColsValue())} x ${Number(enterpriseMapEditorDraftRows.value || gridRowsValue())}`
)
const enterpriseMapEditorSizeLabel = computed(() =>
  enterpriseMapEditorIsIrregular.value
    ? `${t('map_shape_irregular')} · ${enterpriseMapEditorFootprintLabel.value}`
    : enterpriseMapEditorFootprintLabel.value
)
const enterpriseMapEditorGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${enterpriseMapEditorCols.value.length}, ${enterpriseMapEditorCellSize.value}px)`,
  '--enterprise-map-editor-cell-size': `${enterpriseMapEditorCellSize.value}px`
}))
const enterpriseTopologyNodeTypeOptions = computed(() => [
  { value: 'waypoint', label: t('enterprise_settings_route_topology_node_type_waypoint') },
  { value: 'station', label: t('enterprise_settings_route_topology_node_type_station') },
  { value: 'parking', label: t('enterprise_settings_route_topology_node_type_parking') },
  { value: 'charge', label: t('enterprise_settings_route_topology_node_type_charge') }
])
const enterpriseTopologyEdgeDirectionOptions = computed(() => [
  { value: 'bidirectional', label: t('enterprise_settings_route_topology_direction_bidirectional') },
  { value: 'forward', label: t('enterprise_settings_route_topology_direction_forward') },
  { value: 'reverse', label: t('enterprise_settings_route_topology_direction_reverse') }
])
const enterpriseTopologyLaneTypeOptions = computed(() => [
  { value: 'main', label: t('enterprise_settings_route_topology_lane_type_main') },
  { value: 'branch', label: t('enterprise_settings_route_topology_lane_type_branch') },
  { value: 'service', label: t('enterprise_settings_route_topology_lane_type_service') }
])
const enterpriseTopologyDraftSummary = computed(() =>
  buildMapTopologySummary(enterpriseTopologyEditorDraft.value, gridColsValue(), gridRowsValue(), validCells.value)
)
const enterpriseTopologyNodesByCell = computed(() => {
  const entries = {}
  for (const node of enterpriseTopologyEditorDraft.value?.nodes || []) {
    entries[blockedCellKey(node.x, node.y)] = node
  }
  return entries
})
const enterpriseTopologySelectedNode = computed(() =>
  (enterpriseTopologyEditorDraft.value?.nodes || []).find(node => node.key === enterpriseTopologyEditorSelectedNodeKey.value) || null
)
const enterpriseTopologySelectedEdge = computed(() =>
  (enterpriseTopologyEditorDraft.value?.edges || []).find(edge => edge.key === enterpriseTopologyEditorSelectedEdgeKey.value) || null
)
const enterpriseTopologyLinkSourceNode = computed(() =>
  (enterpriseTopologyEditorDraft.value?.nodes || []).find(node => node.key === enterpriseTopologyEditorLinkSourceKey.value) || null
)
const enterpriseTopologyGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${gridColsValue()}, 30px)`,
  '--enterprise-map-editor-cell-size': '30px'
}))
const enterpriseTopologyEdgeSvgStyle = computed(() => ({
  width: `${gridColsValue() * 30}px`,
  height: `${gridRowsValue() * 30}px`
}))
const enterpriseTopologySvgEdges = computed(() => {
  const topology = enterpriseTopologyEditorDraft.value || createEmptyMapTopology()
  const nodeMap = Object.fromEntries((topology.nodes || []).map(node => [node.key, node]))
  return (topology.edges || [])
    .map(edge => {
      const source = nodeMap[edge.source]
      const target = nodeMap[edge.target]
      if (!source || !target) return null
      return {
        ...edge,
        x1: source.x * 30 + 15,
        y1: source.y * 30 + 15,
        x2: target.x * 30 + 15,
        y2: target.y * 30 + 15
      }
    })
    .filter(Boolean)
})
const authCapabilityCards = computed(() => [
  {
    key: 'dispatch',
    label: t('auth_capability_dispatch_label'),
    hint: t('auth_capability_dispatch_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.dispatch)
  },
  {
    key: 'fault',
    label: t('auth_capability_fault_label'),
    hint: t('auth_capability_fault_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.fault)
  },
  {
    key: 'map',
    label: t('auth_capability_map_label'),
    hint: t('auth_capability_map_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.map)
  },
  {
    key: 'data',
    label: t('auth_capability_data_label'),
    hint: t('auth_capability_data_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.data)
  },
  {
    key: 'audit',
    label: t('auth_capability_audit_label'),
    hint: t('auth_capability_audit_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.audit)
  },
  {
    key: 'ai',
    label: t('auth_capability_ai_label'),
    hint: t('auth_capability_ai_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.ai)
  },
  {
    key: 'platform',
    label: t('auth_capability_platform_label'),
    hint: t('auth_capability_platform_hint'),
    enabled: Boolean(authCurrentCapabilityGroups.value?.platform)
  }
])
function enterpriseTabAccessMode(tabKey) {
  switch (String(tabKey || '')) {
    case 'overview':
      return 'workspace'
    case 'map_profiles':
      return authCanMapWrite.value ? 'manage' : 'readonly'
    case 'point_templates':
      return (authCanPointWrite.value || authCanTemplateWrite.value) ? 'manage' : 'readonly'
    case 'runtime':
      if (authCanDispatchWrite.value || authCanFaultWrite.value) return 'manage'
      if (authCanExperimentWrite.value) return 'review'
      return 'readonly'
    case 'ai':
      return authCanAiRender.value ? 'manage' : 'readonly'
    case 'audit':
      return authCanViewAudit.value ? 'review' : 'readonly'
    default:
      return 'readonly'
  }
}

function enterpriseTabAccessLabel(accessMode) {
  return t(`enterprise_settings_tab_badge_${String(accessMode || 'readonly')}`)
}

function enterpriseTabAccessHint(tabKey, accessMode = enterpriseTabAccessMode(tabKey)) {
  if (String(accessMode || '') === 'workspace') return t('enterprise_settings_tab_access_workspace_hint')
  if (String(accessMode || '') === 'manage') return t('enterprise_settings_tab_access_manage_hint')
  if (String(accessMode || '') === 'review') return t('enterprise_settings_tab_access_review_hint')
  return t('enterprise_settings_tab_access_readonly_hint')
}

const enterpriseSettingsTabDefinitions = computed(() => {
  const tabLabel = key => t(`enterprise_settings_tab_${key}`)
  const tabShortLabel = key => t(`enterprise_settings_tab_short_${key}`)
  const buildTab = (key, primary) => {
    const accessMode = enterpriseTabAccessMode(key)
    return {
      key,
      label: tabLabel(key),
      shortLabel: tabShortLabel(key),
      primary,
      accessMode,
      hint: enterpriseTabAccessHint(key, accessMode)
    }
  }
  if (enterpriseUiRole.value === 'enterprise_operator') {
    return [
      buildTab('overview', true),
      buildTab('runtime', true),
      buildTab('map_profiles', false),
      buildTab('ai', false)
    ]
  }
  if (enterpriseUiRole.value === 'enterprise_logistics') {
    return [
      buildTab('overview', false),
      buildTab('map_profiles', true),
      buildTab('point_templates', true),
      buildTab('runtime', true),
      buildTab('ai', false)
    ]
  }
  return [
    buildTab('overview', false),
    buildTab('map_profiles', false),
    buildTab('point_templates', false),
    buildTab('runtime', false),
    buildTab('ai', true),
    buildTab('audit', true)
  ]
})
const enterpriseSettingsTabKeys = computed(() => enterpriseSettingsTabDefinitions.value.map(item => item.key))
const enterpriseSettingsTabLabel = computed(() => {
  const matched = enterpriseSettingsTabDefinitions.value.find(item => item.key === enterpriseSettingsActiveTab.value)
  return matched?.label || t('enterprise_settings_title')
})
const enterpriseOverviewCards = computed(() => [
  {
    key: 'role',
    label: t('enterprise_settings_summary_role'),
    value: enterpriseUiRoleLabel.value
  },
  {
    key: 'organization',
    label: t('enterprise_settings_summary_org'),
    value: authCurrentOrganizationName.value || '—'
  },
  {
    key: 'status',
    label: t('enterprise_settings_summary_status'),
    value: authAccountStatusLabel.value
  },
  {
    key: 'backend',
    label: settingsLocale.value.mapInfoBackend,
    value: uiSettingsBackendMode.value || '—'
  }
])
const enterpriseOverviewQuickTabs = computed(() =>
  enterpriseSettingsTabDefinitions.value
    .filter(item => item.key !== 'overview')
    .map(item => ({
      key: item.key,
      label: item.label,
      accessLabel: enterpriseTabAccessLabel(item.accessMode),
      primary: Boolean(item.primary)
    }))
)
const enterpriseRoleFocus = computed(() => {
  if (enterpriseUiRole.value === 'enterprise_operator') {
    return {
      title: t('enterprise_settings_focus_operator_title'),
      hint: t('enterprise_settings_focus_operator_hint')
    }
  }
  if (enterpriseUiRole.value === 'enterprise_logistics') {
    return {
      title: t('enterprise_settings_focus_logistics_title'),
      hint: t('enterprise_settings_focus_logistics_hint')
    }
  }
  return {
    title: t('enterprise_settings_focus_admin_title'),
    hint: t('enterprise_settings_focus_admin_hint')
  }
})
function enterpriseRoleWorkspaceSectionKeys(role = enterpriseUiRole.value) {
  if (role === 'enterprise_operator') return ['control', 'queue']
  if (role === 'enterprise_logistics') return ['templates', 'points', 'experiments']
  if (role === 'enterprise_admin') return ['operations', 'ai', 'control', 'queue']
  return ['control', 'queue']
}

function enterpriseVisiblePanelSectionKeysForRole(role = enterpriseUiRole.value) {
  if (role === 'enterprise_operator') return ['control', 'queue', 'ai']
  if (role === 'enterprise_logistics') return ['templates', 'points', 'json', 'experiments', 'ai']
  if (role === 'enterprise_admin') return [...PANEL_SECTION_KEYS]
  return ['control', 'queue']
}

function enterprisePanelPreset(role = enterpriseUiRole.value) {
  if (role === 'enterprise_operator') {
    return {
      control: true,
      queue: true,
      templates: false,
      points: false,
      json: false,
      experiments: false,
      ai: true,
      operations: false
    }
  }
  if (role === 'enterprise_logistics') {
    return {
      control: false,
      queue: false,
      templates: true,
      points: true,
      json: true,
      experiments: true,
      ai: true,
      operations: false
    }
  }
  if (role === 'enterprise_admin') {
    return {
      control: true,
      queue: true,
      templates: true,
      points: true,
      json: true,
      experiments: true,
      ai: true,
      operations: true
    }
  }
  return null
}

const visiblePanelSectionKeys = computed(() => {
  if (isPlatformAdminGovernanceMode.value) return []
  if (!uiTreatAsEnterpriseRole.value) return PANEL_SECTION_KEYS
  if (!enterpriseUiApproved.value) return []
  return enterpriseVisiblePanelSectionKeysForRole(enterpriseUiRole.value)
})
const visiblePanelSectionKeySet = computed(() => new Set(visiblePanelSectionKeys.value))
const hasVisiblePanelSections = computed(() => visiblePanelSectionKeys.value.length > 0)

const enterpriseWorkspaceSectionLabels = computed(() =>
  enterpriseRoleWorkspaceSectionKeys().map(key => panelLocale.value.sections[key]).filter(Boolean)
)
const enterprisePrimaryTabKeys = computed(() =>
  enterpriseSettingsTabDefinitions.value.filter(item => item.primary).map(item => item.key)
)
const enterpriseActiveTabDefinition = computed(() =>
  enterpriseSettingsTabDefinitions.value.find(item => item.key === enterpriseSettingsActiveTab.value) || null
)
const enterpriseRoleScopeText = computed(() => {
  if (enterpriseUiRole.value === 'enterprise_operator') return t('enterprise_settings_scope_operator')
  if (enterpriseUiRole.value === 'enterprise_logistics') return t('enterprise_settings_scope_logistics')
  return t('enterprise_settings_scope_admin')
})
const enterpriseCapabilityCards = computed(() =>
  authCapabilityCards.value.filter(item => item.key !== 'platform')
)
const enterpriseEnabledCapabilityCards = computed(() =>
  enterpriseCapabilityCards.value.filter(item => item.enabled)
)
const enterpriseReadonlyCapabilityCards = computed(() =>
  enterpriseCapabilityCards.value.filter(item => !item.enabled)
)
const enterprisePointTemplateFocus = computed(() => {
  if (enterpriseUiRole.value === 'enterprise_operator') {
    return {
      title: t('enterprise_settings_point_templates_focus_operator_title'),
      hint: t('enterprise_settings_point_templates_focus_operator_hint'),
      actions: [
        { key: 'queue', label: t('enterprise_settings_open_queue') },
        { key: 'templates', label: t('enterprise_settings_open_templates') }
      ]
    }
  }
  if (enterpriseUiRole.value === 'enterprise_logistics') {
    return {
      title: t('enterprise_settings_point_templates_focus_logistics_title'),
      hint: t('enterprise_settings_point_templates_focus_logistics_hint'),
      actions: [
        { key: 'points', label: t('enterprise_settings_open_points') },
        { key: 'templates', label: t('enterprise_settings_open_templates') }
      ]
    }
  }
  return {
    title: t('enterprise_settings_point_templates_focus_admin_title'),
    hint: t('enterprise_settings_point_templates_focus_admin_hint'),
    actions: [
      { key: 'templates', label: t('enterprise_settings_open_templates') },
      { key: 'operations', label: t('enterprise_settings_open_audit') }
    ]
  }
})
const enterpriseRuntimeFocus = computed(() => {
  if (enterpriseUiRole.value === 'enterprise_operator') {
    return {
      title: t('enterprise_settings_runtime_focus_operator_title'),
      hint: t('enterprise_settings_runtime_focus_operator_hint'),
      actions: [
        { key: 'control', label: t('enterprise_settings_open_dispatch') },
        { key: 'queue', label: t('enterprise_settings_open_queue') }
      ]
    }
  }
  if (enterpriseUiRole.value === 'enterprise_logistics') {
    return {
      title: t('enterprise_settings_runtime_focus_logistics_title'),
      hint: t('enterprise_settings_runtime_focus_logistics_hint'),
      actions: [
        { key: 'experiments', label: t('enterprise_settings_open_experiments') },
        { key: 'points', label: t('enterprise_settings_open_points') }
      ]
    }
  }
  return {
    title: t('enterprise_settings_runtime_focus_admin_title'),
    hint: t('enterprise_settings_runtime_focus_admin_hint'),
    actions: [
      { key: 'operations', label: t('enterprise_settings_open_audit') },
      { key: 'ai', label: t('enterprise_settings_open_ai') }
    ]
  }
})
function buildEnterpriseActionScopeItems(actionDefinitions = []) {
  return {
    enabled: actionDefinitions.filter(item => item.enabled),
    readonly: actionDefinitions.filter(item => !item.enabled)
  }
}

const enterprisePointTemplateActionScope = computed(() =>
  buildEnterpriseActionScopeItems([
    {
      key: 'points',
      label: t('enterprise_settings_action_manage_points'),
      enabled: authCanPointWrite.value
    },
    {
      key: 'templates',
      label: t('enterprise_settings_action_manage_templates'),
      enabled: authCanTemplateWrite.value
    },
    {
      key: 'json',
      label: t('enterprise_settings_action_export_json'),
      enabled: authCanJsonWrite.value
    }
  ])
)

const enterpriseRuntimeActionScope = computed(() =>
  buildEnterpriseActionScopeItems([
    {
      key: 'dispatch',
      label: t('enterprise_settings_action_run_dispatch'),
      enabled: authCanDispatchWrite.value
    },
    {
      key: 'fault',
      label: t('enterprise_settings_action_handle_faults'),
      enabled: authCanFaultWrite.value
    },
    {
      key: 'experiment',
      label: t('enterprise_settings_action_run_experiments'),
      enabled: authCanExperimentWrite.value
    }
  ])
)

const enterpriseAiActionScope = computed(() =>
  buildEnterpriseActionScopeItems([
    {
      key: 'render',
      label: t('enterprise_settings_action_render_ai'),
      enabled: authCanAiRender.value
    },
    {
      key: 'preview',
      label: t('enterprise_settings_action_preview_ai'),
      enabled: authCanAiRender.value
    },
    {
      key: 'delete',
      label: t('enterprise_settings_action_delete_ai_records'),
      enabled: authCanAiRender.value
    }
  ])
)

const enterpriseActiveTabIsPrimary = computed(() =>
  enterprisePrimaryTabKeys.value.includes(enterpriseSettingsActiveTab.value)
)
const enterpriseActiveTabModeLabel = computed(() =>
  t(enterpriseActiveTabIsPrimary.value ? 'enterprise_settings_tab_mode_primary' : 'enterprise_settings_tab_mode_secondary')
)
const enterpriseActiveTabModeHint = computed(() =>
  enterpriseActiveTabIsPrimary.value ? enterpriseRoleScopeText.value : t('enterprise_settings_tab_mode_secondary_hint')
)
const enterpriseActiveTabAccessLabel = computed(() =>
  enterpriseTabAccessLabel(enterpriseActiveTabDefinition.value?.accessMode || 'readonly')
)
const enterpriseActiveTabAccessHint = computed(() =>
  enterpriseTabAccessHint(
    enterpriseSettingsActiveTab.value,
    enterpriseActiveTabDefinition.value?.accessMode || 'readonly'
  )
)
const enterpriseActiveTasks = computed(() =>
  tasks.value.filter(task => !['finished', 'cancelled'].includes(String(task?.status || ''))).length
)
const enterpriseOpenFaults = computed(() =>
  faultEvents.value.filter(event => String(event?.status || '') === 'open').length
)
const enterpriseBusyAgvs = computed(() =>
  agvs.value.filter(agv => !['idle', 'maintenance'].includes(String(agv?.status || ''))).length
)
const enterpriseRecentTasks = computed(() => {
  const activeTasks = tasks.value.filter(task => !['finished', 'cancelled'].includes(String(task?.status || '')))
  return sortTasks(activeTasks).slice(0, 4)
})
const enterpriseRecentFaults = computed(() =>
  faultEvents.value
    .filter(event => String(event?.status || '') === 'open')
    .slice(0, 4)
)
const enterpriseRecentCustomPoints = computed(() => customPoints.value.slice(0, 4))
const enterpriseRecentCustomTemplates = computed(() => customTaskTemplates.value.slice(0, 4))
const enterpriseRecentAiJobs = computed(() => comfyRenderJobs.value.slice(0, 4))
const enterpriseRecentAuditEntries = computed(() => operationAudits.value.slice(0, 5))
const enterpriseFilteredAuditEntries = computed(() => filteredOperationAudits.value.slice(0, 8))
const currentMapTopologySummary = computed(() =>
  buildMapTopologySummary(currentMapTopology.value, gridColsValue(), gridRowsValue(), validCells.value)
)
const enterpriseMapWorkspaceCards = computed(() => [
  {
    key: 'profile',
    label: t('enterprise_settings_summary_map_profile'),
    value: currentMapProfileLabel.value
  },
  {
    key: 'size',
    label: settingsLocale.value.mapInfoSize,
    value: mapSizeLabel.value
  },
  {
    key: 'blocked',
    label: settingsLocale.value.mapInfoBlocked,
    value: String(blockedCellCount.value)
  },
  {
    key: 'topology_nodes',
    label: t('enterprise_settings_route_topology_nodes'),
    value: String(currentMapTopologySummary.value.node_count)
  },
  {
    key: 'topology_edges',
    label: t('enterprise_settings_route_topology_edges'),
    value: String(currentMapTopologySummary.value.edge_count)
  },
  {
    key: 'profiles',
    label: t('enterprise_settings_summary_profile_count'),
    value: String(mapProfiles.value.length)
  }
])
const enterpriseMapWorkspaceMetaText = computed(() => {
  if (!mapProfileActionSummary.value) return ''
  const profileName = mapProfileActionSummary.value.profileName || currentMapProfileLabel.value || '—'
  return `${mapProfileActionSummaryTitle()} · ${profileName}`
})
const enterpriseRouteTopologyCards = computed(() => [
  {
    key: 'nodes',
    label: t('enterprise_settings_route_topology_nodes'),
    value: String(currentMapTopologySummary.value.node_count)
  },
  {
    key: 'edges',
    label: t('enterprise_settings_route_topology_edges'),
    value: String(currentMapTopologySummary.value.edge_count)
  },
  {
    key: 'stations',
    label: t('enterprise_settings_route_topology_stations'),
    value: String(currentMapTopologySummary.value.station_count)
  },
  {
    key: 'parking',
    label: t('enterprise_settings_route_topology_parking'),
    value: String(currentMapTopologySummary.value.parking_count)
  },
  {
    key: 'charge',
    label: t('enterprise_settings_route_topology_charge'),
    value: String(currentMapTopologySummary.value.charge_count)
  }
])
const enterpriseRouteTopologyMetaText = computed(() => {
  if (!currentMapTopologySummary.value.enabled) return t('enterprise_settings_route_topology_empty_hint')
  return t('enterprise_settings_route_topology_meta')
    .replace('{stations}', String(currentMapTopologySummary.value.station_count))
    .replace('{parking}', String(currentMapTopologySummary.value.parking_count))
    .replace('{charge}', String(currentMapTopologySummary.value.charge_count))
})
const enterprisePointFormDraftText = computed(() => {
  const draft = customPointForm.value || {}
  const parts = []
  if (String(draft.name || '').trim()) parts.push(String(draft.name || '').trim())
  if (String(draft.zone || '').trim()) parts.push(String(draft.zone || '').trim())
  const x = Number(draft.x)
  const y = Number(draft.y)
  if (Number.isFinite(x) && Number.isFinite(y)) {
    parts.push(`(${x}, ${y})`)
  }
  return parts.join(' · ') || pointFormStatus.value || t('enterprise_settings_workspace_ready')
})
const enterpriseTemplateFormDraftText = computed(() => {
  const name = String(taskTemplateForm.value?.name || '').trim()
  return name || taskTemplateStatus.value || t('enterprise_settings_workspace_ready')
})
const enterprisePointTemplateWorkspaceCards = computed(() => [
  {
    key: 'points-custom',
    label: t('enterprise_settings_summary_points_custom'),
    value: String(customPoints.value.length)
  },
  {
    key: 'templates-custom',
    label: t('enterprise_settings_summary_templates_custom'),
    value: String(customTaskTemplates.value.length)
  },
  {
    key: 'point-draft',
    label: t('enterprise_settings_summary_point_form'),
    value: enterprisePointFormDraftText.value
  },
  {
    key: 'template-draft',
    label: t('enterprise_settings_summary_template_form'),
    value: enterpriseTemplateFormDraftText.value
  }
])
const enterpriseRuntimeWorkspaceCards = computed(() => [
  {
    key: 'dispatch',
    label: t('enterprise_settings_summary_dispatch_mode'),
    value: currentDispatchModeLabel.value
  },
  {
    key: 'algorithm',
    label: t('enterprise_settings_runtime_algorithm_title'),
    value: algorithmText(algorithm.value)
  },
  {
    key: 'display',
    label: compareDisplayTitleLabel.value,
    value: compareDisplayMode.value === 'floating'
      ? compareDisplayFloatingLabel.value
      : compareDisplayPanelLabel.value
  },
  {
    key: 'compare',
    label: t('enterprise_settings_summary_compare'),
    value: compareEntryText.value
  }
])
const comfyRenderSourceTypeLabel = computed(() =>
  comfyRenderSourceLabelMap.value[comfyRenderSourceType.value] || '—'
)
const comfyRenderWorkflowPresetLabel = computed(() =>
  comfyRenderWorkflowPresetLabelMap.value[comfyRenderWorkflowPreset.value] || '—'
)
const comfyRenderPromptStyleLabel = computed(() =>
  comfyRenderPromptStyleLabelMap.value[comfyRenderPromptStyle.value] || '—'
)
const enterpriseAiWorkspaceCards = computed(() => [
  {
    key: 'source',
    label: t('enterprise_settings_summary_ai_source'),
    value: comfyRenderSourceTypeLabel.value
  },
  {
    key: 'preset',
    label: t('enterprise_settings_summary_ai_preset'),
    value: comfyRenderWorkflowPresetLabel.value
  },
  {
    key: 'style',
    label: t('enterprise_settings_summary_ai_style'),
    value: comfyRenderPromptStyleLabel.value
  },
  {
    key: 'templates',
    label: t('enterprise_settings_summary_ai_templates'),
    value: `${comfyRenderSavedTemplates.value.length} / ${comfyRenderSharedTemplates.value.length}`
  }
])
const operationAuditResourceFilterLabel = computed(() =>
  operationAuditResourceOptions.value.find(option => option.value === operationAuditResourceFilter.value)?.label
  || t('operations_filter_resource_all')
)
const operationAuditActionFilterLabel = computed(() =>
  operationAuditActionOptions.value.find(option => option.value === operationAuditActionFilter.value)?.label
  || t('operations_filter_action_all')
)
const enterpriseAuditWorkspaceCards = computed(() => [
  {
    key: 'resource',
    label: t('enterprise_settings_summary_audit_resource'),
    value: operationAuditResourceFilterLabel.value
  },
  {
    key: 'action',
    label: t('enterprise_settings_summary_audit_action'),
    value: operationAuditActionFilterLabel.value
  },
  {
    key: 'matches',
    label: t('enterprise_settings_summary_audit_matches'),
    value: String(enterpriseFilteredAuditEntries.value.length)
  }
])
const showAuthGate = computed(() => !authInitialized.value || !dashboardUnlocked.value)
const showAuthDialog = computed(() => showAuthGate.value || authPanelOpen.value)

function buildAuthLoginSuccessMessage(state) {
  const name = state?.user?.display_name || state?.user?.username || t('auth_role_guest')
  const role = String(state?.user?.role || state?.role || authCurrentRole.value || 'guest').trim() || 'guest'
  const base = formatInlineMessage(t('auth_login_success'), { name })
  const hint = t(`auth_entry_hint_${role}`)
  return hint ? `${base} ${hint}` : base
}

function authDemoAccountLabel(account) {
  return `${t(`auth_role_${account?.role || 'guest'}`)} · ${account?.username || ''}`
}

function formatOperatorLine(labelKey, name, role, at) {
  if (!name) return ''
  const parts = [String(name)]
  if (role) {
    parts.push(t(`auth_role_${role}`))
  }
  if (at) {
    parts.push(String(at))
  }
  return `${t(labelKey)}: ${parts.join(' · ')}`
}

function formatTaskCreatedBy(task) {
  return formatOperatorLine('task_created_by', task?.created_by, task?.created_by_role, task?.created_by_at)
}

function formatTaskLastOperator(task) {
  return formatOperatorLine('task_last_operator', task?.last_operator, task?.last_operator_role, task?.last_operator_at)
}

function formatFaultReportedBy(eventItem) {
  return formatOperatorLine('fault_reported_by', eventItem?.reported_by, eventItem?.reported_by_role, null)
}

function formatFaultResolvedBy(eventItem) {
  return formatOperatorLine('fault_resolved_by', eventItem?.resolved_by, eventItem?.resolved_by_role, null)
}

function formatMapProfileCreatedBy(profile) {
  return formatOperatorLine(
    'map_profile_created_by',
    profile?.created_by,
    profile?.created_by_role,
    profile?.created_by_at
  )
}

function formatMapProfileLastOperator(profile) {
  return formatOperatorLine(
    'map_profile_last_operator',
    profile?.last_operator,
    profile?.last_operator_role,
    profile?.last_operator_at
  )
}

function operationResourceLabel(resourceType) {
  switch (String(resourceType || '').toLowerCase()) {
    case 'task':
      return t('operations_resource_task')
    case 'fault':
      return t('operations_resource_fault')
    case 'map_profile':
      return t('operations_resource_map_profile')
    case 'map_layout':
      return t('operations_resource_map_layout')
    case 'map_preset':
      return t('operations_resource_map_preset')
    case 'comfy_render_job':
      return t('operations_resource_ai_render')
    case 'agv':
      return t('operations_resource_agv')
    case 'enterprise_application':
      return t('operations_resource_enterprise_application')
    case 'user_account':
      return t('operations_resource_user_account')
    case 'enterprise_request':
      return t('operations_resource_enterprise_request')
    case 'platform_bug_feedback':
      return t('operations_resource_platform_bug_feedback')
    default:
      return t('operations_resource_all')
  }
}

function operationActionLabel(action) {
  switch (String(action || '').toLowerCase()) {
    case 'create':
      return t('operations_action_create')
    case 'import':
      return t('operations_action_import')
    case 'save':
      return t('operations_action_save')
    case 'delete':
      return t('operations_action_delete')
    case 'delete_finished':
      return t('operations_action_delete_finished')
    case 'delete_orphaned':
      return t('operations_action_delete_orphaned')
    case 'finish':
      return t('operations_action_finish')
    case 'schedule':
      return t('operations_action_schedule')
    case 'report':
      return t('operations_action_report')
    case 'resolve':
      return t('operations_action_resolve')
    case 'apply':
      return t('operations_action_apply')
    case 'force_apply':
      return t('operations_action_force_apply')
    case 'resize':
      return t('operations_action_resize')
    case 'reset':
      return t('operations_action_reset')
    case 'emergency_stop':
      return t('operations_action_emergency_stop')
    case 'resume':
      return t('operations_action_resume')
    case 'to_maintenance':
      return t('operations_action_to_maintenance')
    case 'return_to_service':
      return t('operations_action_return_to_service')
    case 'fault_interrupt':
      return t('operations_action_fault_interrupt')
    case 'render':
      return t('operations_action_render')
    case 'approve':
      return t('operations_action_approve')
    case 'reject':
      return t('operations_action_reject')
    case 'status.update':
      return t('operations_action_status_update')
    case 'user.register.personal':
      return t('operations_action_user_register_personal')
    case 'user.export':
      return t('operations_action_user_export')
    case 'user.suspend':
      return t('operations_action_user_suspend')
    case 'user.unsuspend':
      return t('operations_action_user_unsuspend')
    case 'user.deactivate':
      return t('operations_action_user_deactivate')
    default:
      return String(action || '')
  }
}

function optionalTranslation(key, fallback = '') {
  const translated = t(key)
  if (!translated || translated === key) return fallback || String(key || '')
  return translated
}

function operationAuditRoleLabel(role) {
  const normalizedRole = String(role || '').trim()
  if (!normalizedRole) return ''
  return optionalTranslation(`auth_role_${normalizedRole}`, normalizedRole)
}

function operationAuditCategoryLabel(resourceType, category) {
  const normalizedResourceType = String(resourceType || '').toLowerCase()
  const normalizedCategory = String(category || '').trim().toLowerCase()
  if (!normalizedCategory || normalizedCategory === 'all') return ''
  if (normalizedResourceType === 'enterprise_request') {
    return optionalTranslation(`enterprise_request_category_${normalizedCategory}`, normalizedCategory)
  }
  if (normalizedResourceType === 'platform_bug_feedback') {
    return optionalTranslation(`platform_bug_feedback_category_${normalizedCategory}`, normalizedCategory)
  }
  return normalizedCategory
}

function operationAuditStatusLabel(resourceType, status) {
  const normalizedResourceType = String(resourceType || '').toLowerCase()
  const normalizedStatus = String(status || '').trim().toLowerCase()
  if (!normalizedStatus || normalizedStatus === 'all') return ''
  if (normalizedResourceType === 'enterprise_application') {
    return optionalTranslation(`enterprise_approval_status_${normalizedStatus}`, normalizedStatus)
  }
  if (normalizedResourceType === 'user_account') {
    return optionalTranslation(`account_governance_status_${normalizedStatus}`, normalizedStatus)
  }
  if (normalizedResourceType === 'enterprise_request' || normalizedResourceType === 'platform_bug_feedback') {
    return optionalTranslation(`feedback_status_${normalizedStatus}`, normalizedStatus)
  }
  return normalizedStatus
}

function formatOperationAuditTitle(entry) {
  return `${operationActionLabel(entry?.action)} · ${operationResourceLabel(entry?.resource_type)}`
}

function formatOperationAuditOperator(entry) {
  const name = entry?.operator_display_name || entry?.operator_username || t('auth_role_guest')
  const role = entry?.operator_role ? t(`auth_role_${entry.operator_role}`) : t('auth_role_guest')
  return `${name} · ${role}`
}

function formatOperationAuditResourceRef(entry) {
  const normalizedResourceType = String(entry?.resource_type || '').toLowerCase()
  const metadata = entry?.metadata && typeof entry.metadata === 'object' ? entry.metadata : {}
  const resourceType = operationResourceLabel(normalizedResourceType)
  const resourceId = entry?.resource_id ? `#${entry.resource_id}` : ''

  if (normalizedResourceType === 'enterprise_application') {
    const companyName = String(metadata.company_name || '').trim()
    const username = String(metadata.username || '').trim()
    return [companyName, username].filter(Boolean).join(' · ') || (resourceId ? `${resourceType} ${resourceId}` : resourceType)
  }

  if (normalizedResourceType === 'user_account') {
    const username = String(metadata.target_username || metadata.username || entry?.resource_id || '').trim()
    const role = operationAuditRoleLabel(metadata.target_role || metadata.role)
    return [username, role].filter(Boolean).join(' · ') || (resourceId ? `${resourceType} ${resourceId}` : resourceType)
  }

  if (normalizedResourceType === 'enterprise_request' || normalizedResourceType === 'platform_bug_feedback') {
    const category = operationAuditCategoryLabel(normalizedResourceType, metadata.category)
    const status = operationAuditStatusLabel(normalizedResourceType, metadata.status)
    const primary = resourceId ? `${resourceType} ${resourceId}` : resourceType
    return [primary, category, status].filter(Boolean).join(' · ')
  }

  return resourceId ? `${resourceType} ${resourceId}` : resourceType
}

function formatOperationAuditMetadata(entry) {
  const normalizedResourceType = String(entry?.resource_type || '').toLowerCase()
  const metadata = entry?.metadata
  if (!metadata || typeof metadata !== 'object') return ''

  const parts = []
  if (normalizedResourceType === 'enterprise_application') {
    if (metadata.status) {
      parts.push(`${t('enterprise_approval_status_label')}: ${operationAuditStatusLabel(normalizedResourceType, metadata.status)}`)
    }
    if (metadata.review_note) {
      parts.push(`${t('enterprise_settings_application_review_note')}: ${metadata.review_note}`)
    }
  }
  if (normalizedResourceType === 'user_account') {
    const username = String(metadata.target_username || metadata.username || '').trim()
    const role = operationAuditRoleLabel(metadata.target_role || metadata.role)
    if (username) {
      parts.push(`${t('account_governance_field_username')}: ${username}`)
    }
    if (role) {
      parts.push(`${t('account_governance_field_role')}: ${role}`)
    }
    if (metadata.reason) {
      parts.push(`${t('account_governance_suspension_reason')}: ${metadata.reason}`)
    }
    if (metadata.note) {
      parts.push(`${t('account_governance_suspension_note')}: ${metadata.note}`)
    }
    if (metadata.permanent) {
      parts.push(`${t('account_governance_suspend_duration')}: ${t('account_governance_suspend_duration_permanent')}`)
    } else if (metadata.duration_days) {
      parts.push(`${t('account_governance_suspend_duration')}: ${metadata.duration_days}`)
    }
  }
  if (normalizedResourceType === 'enterprise_request' || normalizedResourceType === 'platform_bug_feedback') {
    const category = operationAuditCategoryLabel(normalizedResourceType, metadata.category)
    const status = operationAuditStatusLabel(normalizedResourceType, metadata.status)
    if (category) {
      const categoryLabelKey = normalizedResourceType === 'enterprise_request'
        ? 'enterprise_request_field_category'
        : 'platform_bug_feedback_field_category'
      parts.push(`${t(categoryLabelKey)}: ${category}`)
    }
    if (status) {
      parts.push(`${t('enterprise_approval_status_label')}: ${status}`)
    }
    if (metadata.target_username) {
      parts.push(`${t('account_governance_field_username')}: ${metadata.target_username}`)
    }
    if (metadata.response_note) {
      const noteLabelKey = normalizedResourceType === 'enterprise_request'
        ? 'enterprise_request_field_response_note'
        : 'account_governance_suspension_note'
      parts.push(`${t(noteLabelKey)}: ${metadata.response_note}`)
    }
  }
  if (metadata.algorithm) {
    parts.push(`${t('algorithm')}: ${algorithmText(metadata.algorithm)}`)
  }
  if (metadata.mode) {
    parts.push(`${panelLocale.value.currentMode}: ${metadata.mode === 'manual' ? t('dispatch_manual') : t('dispatch_auto')}`)
  }
  if (metadata.agv_id) {
    parts.push(`AGV #${metadata.agv_id}`)
  }
  if (metadata.fault_type) {
    parts.push(`${faultLocale.value.faultType}: ${faultTypeText(metadata.fault_type)}`)
  }
  if (metadata.grid_cols && metadata.grid_rows) {
    parts.push(`${t('operations_meta_size')}: ${metadata.grid_cols} x ${metadata.grid_rows}`)
  }
  if (metadata.requested_name && metadata.resolved_name && metadata.requested_name !== metadata.resolved_name) {
    parts.push(formatInlineMessage(t('operations_meta_renamed'), metadata))
  }
  if (metadata.relocated_agv_count) {
    parts.push(formatInlineMessage(t('operations_meta_relocated_agvs'), { count: metadata.relocated_agv_count }))
  }
  if (metadata.trimmed_blocked_cells_count) {
    parts.push(formatInlineMessage(t('operations_meta_trimmed_blocked'), { count: metadata.trimmed_blocked_cells_count }))
  }
  if (metadata.blocked_count !== undefined) {
    parts.push(formatInlineMessage(t('operations_meta_blocked_count'), { count: metadata.blocked_count }))
  }
  if (metadata.skipped_occupied_count) {
    parts.push(formatInlineMessage(t('operations_meta_skipped_occupied'), { count: metadata.skipped_occupied_count }))
  }
  if (metadata.stage) {
    parts.push(`${t('task_stages')}: ${metadata.stage}`)
  }

  if (parts.length > 0) return parts.join(' · ')

  return Object.entries(metadata)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ')
}

const operationAuditResourceOptions = computed(() => [
  { value: 'all', label: t('operations_resource_all') },
  { value: 'task', label: t('operations_resource_task') },
  { value: 'fault', label: t('operations_resource_fault') },
  { value: 'map_profile', label: t('operations_resource_map_profile') },
  { value: 'map_layout', label: t('operations_resource_map_layout') },
  { value: 'map_preset', label: t('operations_resource_map_preset') },
  { value: 'comfy_render_job', label: t('operations_resource_ai_render') },
  { value: 'agv', label: t('operations_resource_agv') },
  { value: 'enterprise_application', label: t('operations_resource_enterprise_application') },
  { value: 'user_account', label: t('operations_resource_user_account') },
  { value: 'enterprise_request', label: t('operations_resource_enterprise_request') },
  { value: 'platform_bug_feedback', label: t('operations_resource_platform_bug_feedback') }
])

const operationAuditActionOptions = computed(() => [
  { value: 'all', label: t('operations_action_all') },
  { value: 'create', label: t('operations_action_create') },
  { value: 'import', label: t('operations_action_import') },
  { value: 'save', label: t('operations_action_save') },
  { value: 'delete', label: t('operations_action_delete') },
  { value: 'delete_finished', label: t('operations_action_delete_finished') },
  { value: 'delete_orphaned', label: t('operations_action_delete_orphaned') },
  { value: 'finish', label: t('operations_action_finish') },
  { value: 'schedule', label: t('operations_action_schedule') },
  { value: 'report', label: t('operations_action_report') },
  { value: 'resolve', label: t('operations_action_resolve') },
  { value: 'apply', label: t('operations_action_apply') },
  { value: 'force_apply', label: t('operations_action_force_apply') },
  { value: 'resize', label: t('operations_action_resize') },
  { value: 'reset', label: t('operations_action_reset') },
  { value: 'emergency_stop', label: t('operations_action_emergency_stop') },
  { value: 'resume', label: t('operations_action_resume') },
  { value: 'to_maintenance', label: t('operations_action_to_maintenance') },
  { value: 'return_to_service', label: t('operations_action_return_to_service') },
  { value: 'fault_interrupt', label: t('operations_action_fault_interrupt') },
  { value: 'render', label: t('operations_action_render') },
  { value: 'approve', label: t('operations_action_approve') },
  { value: 'reject', label: t('operations_action_reject') },
  { value: 'status.update', label: t('operations_action_status_update') },
  { value: 'user.register.personal', label: t('operations_action_user_register_personal') },
  { value: 'user.export', label: t('operations_action_user_export') },
  { value: 'user.suspend', label: t('operations_action_user_suspend') },
  { value: 'user.unsuspend', label: t('operations_action_user_unsuspend') },
  { value: 'user.deactivate', label: t('operations_action_user_deactivate') }
])

const filteredOperationAudits = computed(() =>
  operationAudits.value.filter(entry => {
    if (operationAuditResourceFilter.value !== 'all' && entry.resource_type !== operationAuditResourceFilter.value) {
      return false
    }
    if (operationAuditActionFilter.value !== 'all' && entry.action !== operationAuditActionFilter.value) {
      return false
    }
    return true
  })
)
const selectedOperationAuditIdSet = computed(() =>
  new Set(selectedOperationAuditIds.value.map(id => Number(id)).filter(id => Number.isFinite(id) && id > 0))
)

watch([operationAuditResourceFilter, operationAuditActionFilter], () => {
  selectedOperationAuditIds.value = []
})

watch(operationAudits, entries => {
  const validIds = new Set((entries || []).map(entry => Number(entry.id)).filter(id => Number.isFinite(id) && id > 0))
  selectedOperationAuditIds.value = selectedOperationAuditIds.value.filter(id => validIds.has(Number(id)))
})

watch([authCurrentRole, authCurrentAccountStatus], ([nextRole, nextStatus], [prevRole, prevStatus]) => {
  if (nextRole !== prevRole || nextStatus !== prevStatus) {
    enterpriseWorkspacePopupDismissed.value = false
  }
})

watch(showEnterpriseWorkspacePopup, visible => {
  if (visible) {
    void ensureEnterpriseWorkspacePopupPosition()
  } else {
    stopEnterpriseWorkspacePopupDrag()
  }
})

const selectedAgv = computed(() => {
  if (!selectedAgvId.value) return null
  return displayAgvs.value.find(agv => agv.id === selectedAgvId.value) ?? null
})
const selectedBackendAgv = computed(() => {
  if (!selectedAgv.value || selectedAgv.value.source !== 'backend') return null
  return selectedAgv.value
})
const maintenanceBackendAgvs = computed(() =>
  agvs.value
    .filter(agv => agv.status === 'maintenance')
    .sort((a, b) => a.id - b.id)
)

function normalizeAgvMotionNumber(value, fallback = 0) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

function clampMotionProgress(value) {
  return Math.max(0, Math.min(1, normalizeAgvMotionNumber(value, 0)))
}

function isEnterpriseContinuousMotionEnabled() {
  return uiTreatAsEnterpriseRole.value
}

function isBackendAgvMotionActive(agv, nowMs = Date.now()) {
  if (!isEnterpriseContinuousMotionEnabled()) return false
  const startedMs = Date.parse(String(agv?.motion_started_at || ''))
  const durationMs = Math.max(0, normalizeAgvMotionNumber(agv?.motion_duration_ms, 0))
  const sourceX = normalizeAgvMotionNumber(agv?.motion_source_x, normalizeAgvMotionNumber(agv?.render_x, agv?.x))
  const sourceY = normalizeAgvMotionNumber(agv?.motion_source_y, normalizeAgvMotionNumber(agv?.render_y, agv?.y))
  const targetX = normalizeAgvMotionNumber(agv?.motion_target_x, agv?.x)
  const targetY = normalizeAgvMotionNumber(agv?.motion_target_y, agv?.y)
  if (!Number.isFinite(startedMs) || durationMs <= 0) return false
  if (sourceX === targetX && sourceY === targetY) return false
  return nowMs < startedMs + durationMs
}

function resolveRenderedBackendAgv(agv, nowMs = agvAnimationNow.value) {
  const enterpriseMotionEnabled = isEnterpriseContinuousMotionEnabled()
  const sourceX = normalizeAgvMotionNumber(agv?.motion_source_x, normalizeAgvMotionNumber(agv?.render_x, agv?.x))
  const sourceY = normalizeAgvMotionNumber(agv?.motion_source_y, normalizeAgvMotionNumber(agv?.render_y, agv?.y))
  const targetX = normalizeAgvMotionNumber(agv?.motion_target_x, agv?.x)
  const targetY = normalizeAgvMotionNumber(agv?.motion_target_y, agv?.y)
  const renderX = normalizeAgvMotionNumber(agv?.render_x, agv?.x)
  const renderY = normalizeAgvMotionNumber(agv?.render_y, agv?.y)
  const heading = normalizeAgvMotionNumber(agv?.heading, 0)
  const startedMs = Date.parse(String(agv?.motion_started_at || ''))
  const durationMs = Math.max(0, normalizeAgvMotionNumber(agv?.motion_duration_ms, 0))
  const timeProgress =
    Number.isFinite(startedMs) && durationMs > 0 ? clampMotionProgress((nowMs - startedMs) / durationMs) : null
  const progress = timeProgress ?? clampMotionProgress(agv?.edge_progress)
  const motionState = String(agv?.motion_state || agv?.status || 'idle')
  const shouldAnimate =
    enterpriseMotionEnabled &&
    String(agv?.current_edge || '').trim() &&
    durationMs > 0 &&
    Number.isFinite(startedMs) &&
    (sourceX !== targetX || sourceY !== targetY)

  const displayX = shouldAnimate ? sourceX + (targetX - sourceX) * progress : enterpriseMotionEnabled ? renderX : normalizeAgvMotionNumber(agv?.x)
  const displayY = shouldAnimate ? sourceY + (targetY - sourceY) * progress : enterpriseMotionEnabled ? renderY : normalizeAgvMotionNumber(agv?.y)

  return {
    ...agv,
    source: 'backend',
    displayX,
    displayY,
    displayHeading: heading,
    displayProgress: progress,
    motionState
  }
}

function formatEnterpriseMotionStateLabel(motionState) {
  const normalized = String(motionState || 'idle').trim().toLowerCase()
  if (locale.value === 'ja') {
    if (normalized === 'charging') return '充電中'
    if (normalized === 'waiting_for_charge') return '充電へ移動'
    if (normalized === 'idle_returning') return '回庫中'
    if (normalized === 'yielding') return '譲り待機'
    if (normalized === 'waiting') return '待機'
    if (normalized === 'running') return '走行'
    if (normalized === 'relocating') return '移動'
    return '待機中'
  }
  if (locale.value === 'en') {
    if (normalized === 'charging') return 'Charging'
    if (normalized === 'waiting_for_charge') return 'Heading To Charge'
    if (normalized === 'idle_returning') return 'Returning To Parking'
    if (normalized === 'yielding') return 'Yielding'
    if (normalized === 'waiting') return 'Waiting'
    if (normalized === 'running') return 'Running'
    if (normalized === 'relocating') return 'Relocating'
    return 'Idle'
  }
  if (normalized === 'charging') return '充电中'
  if (normalized === 'waiting_for_charge') return '前往充电'
  if (normalized === 'idle_returning') return '回仓中'
  if (normalized === 'yielding') return '让行等待'
  if (normalized === 'waiting') return '等待中'
  if (normalized === 'running') return '运行中'
  if (normalized === 'relocating') return '前往起点'
  return '空闲'
}

function formatEnterpriseAgvRuntimeHint(agv) {
  if (!uiTreatAsEnterpriseRole.value || agv?.source !== 'backend') return ''
  const parts = [`AGV #${agv.id}`]
  parts.push(formatEnterpriseMotionStateLabel(agv.motionState))
  if (Number.isFinite(Number(agv?.battery_level))) {
    const batteryText =
      locale.value === 'ja'
        ? `充電 ${Math.round(Number(agv.battery_level))}%`
        : locale.value === 'en'
          ? `Battery ${Math.round(Number(agv.battery_level))}%`
          : `电量 ${Math.round(Number(agv.battery_level))}%`
    parts.push(batteryText)
  }
  if (String(agv?.auto_target_type || '').trim()) {
    if (locale.value === 'ja') {
      parts.push(agv.auto_target_type === 'charge' ? '目標: 充電点' : '目標: 停車点')
    } else if (locale.value === 'en') {
      parts.push(agv.auto_target_type === 'charge' ? 'Target: Charge' : 'Target: Parking')
    } else {
      parts.push(agv.auto_target_type === 'charge' ? '目标: 充电点' : '目标: 回仓点')
    }
  }
  if (String(agv?.current_edge || '').trim()) {
    if (locale.value === 'ja') {
      parts.push(`辺: ${agv.current_edge}`)
    } else if (locale.value === 'en') {
      parts.push(`Edge: ${agv.current_edge}`)
    } else {
      parts.push(`路段: ${agv.current_edge}`)
    }
  }
  return parts.join(' · ')
}

const enterpriseAgvMotionActive = computed(() =>
  agvs.value.some(agv => isBackendAgvMotionActive(agv, agvAnimationNow.value))
)

const displayAgvs = computed(() => {
  const backendAgvs = agvs.value
    .filter(agv => agv.status !== 'maintenance')
    .map(agv => resolveRenderedBackendAgv(agv))
  const localDisplayAgvs = localAgvs.value.map(agv => ({
    ...agv,
    displayX: normalizeAgvMotionNumber(agv?.x),
    displayY: normalizeAgvMotionNumber(agv?.y),
    displayHeading: 0,
    displayProgress: 1,
    motionState: String(agv?.status || 'idle')
  }))
  return [...backendAgvs, ...localDisplayAgvs]
})
const selectedAgvTask = computed(() => {
  if (!selectedBackendAgv.value) return null
  return (
    tasks.value.find(task => task.agv_id === selectedBackendAgv.value.id && ['assigned', 'running'].includes(task.status)) ??
    null
  )
})
const manualDispatchReady = computed(() => {
  if (dispatchMode.value !== 'manual') return true
  return Boolean(
    selectedBackendAgv.value &&
      isSchedulableIdleAgvStatus(selectedBackendAgv.value.status)
  )
})
const filteredFaultEvents = computed(() => {
  if (faultEventFilter.value === 'all') return faultEvents.value
  return faultEvents.value.filter(event => event.status === faultEventFilter.value)
})

const manualPathToStartPoints = computed(() => toSvgPoints(manualPathToStart.value))
const manualPathToEndPoints = computed(() => toSvgPoints(manualPathToEnd.value))
const autoPathToStartPoints = computed(() => toSvgPoints(autoPathToStart.value))
const autoPathToEndPoints = computed(() => toSvgPoints(autoPathToEnd.value))
const manualPathToStartArrows = computed(() => toArrowSegments(manualPathToStart.value))
const manualPathToEndArrows = computed(() => toArrowSegments(manualPathToEnd.value))
const autoPathToStartArrows = computed(() => toArrowSegments(autoPathToStart.value))
const autoPathToEndArrows = computed(() => toArrowSegments(autoPathToEnd.value))
const isCompactLayout = computed(() => windowWidth.value <= 960)
const shouldShowAutoPath = computed(() => dispatchMode.value === 'auto' && showAutoPath.value)
const suppressAutoRuntimeVisuals = computed(
  () =>
    dispatchMode.value === 'auto' &&
    ((taskBuilderMode.value === 'single' && autoDraftPicking.value) ||
      (taskBuilderMode.value === 'chain' && taskChainMapPickActive.value))
)
const showAutoRuntimeVisuals = computed(() => shouldShowAutoPath.value && !suppressAutoRuntimeVisuals.value)
const layoutStyle = computed(() =>
  isCompactLayout.value
    ? {}
    : {
        gridTemplateColumns: `minmax(0, 1fr) 10px ${panelWidth.value}px`
      }
)
const pageTopStyle = computed(() =>
  isCompactLayout.value
    ? {}
    : {
        gridTemplateColumns: `minmax(0, 1fr) 10px ${panelWidth.value}px`,
        '--page-top-height': '156px'
      }
)
const mapStageStyle = computed(() => ({
  width: `${mapWidth.value}px`,
  height: `${mapHeight.value}px`,
  transform: `translate(${mapOffsetX.value}px, ${mapOffsetY.value}px) scale(${mapZoom.value})`
}))
const mapZoomLabel = computed(() => `${Math.round(mapZoom.value * 100)}%`)
const minimapScale = computed(() => (mapWidth.value > 0 ? MINIMAP_WIDTH / mapWidth.value : 1))
const minimapHeight = computed(() => mapHeight.value * minimapScale.value)
const minimapCellSize = computed(() => CELL_SIZE * minimapScale.value)
const validCellSet = computed(
  () => new Set(validCells.value.map(cell => blockedCellKey(cell.x, cell.y)))
)
const blockedCellSet = computed(
  () => new Set(blockedCells.value.map(cell => `${cell.x},${cell.y}`))
)
const navigationBlockedCellSet = computed(() => {
  const blocked = new Set(blockedCellSet.value)
  for (let y = 0; y < gridRowsValue(); y += 1) {
    for (let x = 0; x < gridColsValue(); x += 1) {
      const key = blockedCellKey(x, y)
      if (!validCellSet.value.has(key)) {
        blocked.add(key)
      }
    }
  }
  return blocked
})
const occupiedCellSet = computed(() => {
  const keys = new Set()
  for (const agv of displayAgvs.value) {
    if (Number.isInteger(agv?.x) && Number.isInteger(agv?.y)) {
      keys.add(blockedCellKey(agv.x, agv.y))
    }
  }
  return keys
})
const obstacleMutationLocked = computed(
  () =>
    agvs.value.some(agv => ['running', 'relocating'].includes(agv.status)) ||
    tasks.value.some(task => ['assigned', 'running'].includes(task.status))
  )
const blockedCellCount = computed(() => blockedCells.value.length)
const validCellCount = computed(() => validCells.value.length)
const mapIsIrregular = computed(() => validCellCount.value !== gridColsValue() * gridRowsValue())
const mapSizeLabel = computed(() =>
  mapIsIrregular.value ? t('map_shape_irregular') : `${currentGridCols.value} x ${currentGridRows.value}`
)
const mapValidCells = computed(() => (mapIsIrregular.value ? validCells.value : []))
const mapVoidCells = computed(() => {
  if (!mapIsIrregular.value) return []
  const cells = []
  for (let y = 0; y < gridRowsValue(); y += 1) {
    for (let x = 0; x < gridColsValue(); x += 1) {
      if (!validCellSet.value.has(blockedCellKey(x, y))) {
        cells.push({ x, y })
      }
    }
  }
  return cells
})
const selectedObstaclePresetInfo = computed(
  () => obstaclePresets.value.find(preset => preset.key === selectedObstaclePreset.value) ?? null
)
const appliedObstaclePresetInfo = computed(
  () => obstaclePresets.value.find(preset => preset.key === appliedObstacleSceneKey.value) ?? null
)
const currentObstaclePresetLabel = computed(() => {
  if (appliedObstaclePresetInfo.value) return obstaclePresetName(appliedObstaclePresetInfo.value)
  if (locale.value === 'ja') return 'カスタム'
  if (locale.value === 'zh') return '自定义'
  return 'Custom'
})
const currentMapProfileLabel = computed(() => {
  if (currentMapProfile.value) return localizedMapProfileField(currentMapProfile.value?.name)
  if (locale.value === 'ja') return '未识别'
  if (locale.value === 'zh') return '未识别'
  return 'Unknown'
})
const currentMapProfileDescription = computed(() => localizedMapProfileField(currentMapProfile.value?.description))
const previewedMapProfile = computed(
  () => mapProfiles.value.find(profile => profile.key === mapProfilePreviewingKey.value) ?? null
)
const mapSizeResizeStatusLabel = computed(() => {
  if (mapSizeResizeReady.value) return settingsLocale.value.mapInfoResizeReady
  if (mapSizeResizeLockReason.value === 'active_tasks_and_busy_agvs') {
    return settingsLocale.value.mapInfoResizeBlockedBoth
  }
  if (mapSizeResizeLockReason.value === 'active_tasks_present') {
    return settingsLocale.value.mapInfoResizeBlockedTasks
  }
  if (mapSizeResizeLockReason.value === 'agvs_not_idle') {
    return settingsLocale.value.mapInfoResizeBlockedAgvs
  }
  return settingsLocale.value.mapInfoResizeUnknown
})
const mapResizePreviewStatusLabel = computed(() => {
  if (!mapResizePreview.value) return settingsLocale.value.resizePreviewNoResult
  return mapResizePreview.value.can_apply
    ? settingsLocale.value.resizePreviewReady
    : settingsLocale.value.resizePreviewBlocked
})
const mapResizeRequestedCols = computed(() =>
  sanitizeGridDimensionInput(mapResizePreviewColsInput.value, gridColsValue())
)
const mapResizeRequestedRows = computed(() =>
  sanitizeGridDimensionInput(mapResizePreviewRowsInput.value, gridRowsValue())
)
const mapResizeRequestedSizeLabel = computed(
  () => `${mapResizeRequestedCols.value} x ${mapResizeRequestedRows.value}`
)
function buildMapResizeReasonItem(blocker) {
  const base = {
    key: blocker,
    text: blocker,
    targetSectionKey: ''
  }
  switch (blocker) {
    case 'active_tasks_present':
      return {
        ...base,
        text: settingsLocale.value.resizeReasonActiveTasks
      }
    case 'agvs_not_idle':
      return {
        ...base,
        text: settingsLocale.value.resizeReasonBusyAgvs
      }
    case 'agvs_out_of_bounds':
      return {
        ...base,
        text: settingsLocale.value.resizeReasonOverflowAgvs,
        targetSectionKey: 'agv'
      }
    case 'points_out_of_bounds':
      return {
        ...base,
        text: settingsLocale.value.resizeReasonOverflowPoints,
        targetSectionKey: 'points'
      }
    case 'templates_out_of_bounds':
      return {
        ...base,
        text: settingsLocale.value.resizeReasonOverflowTemplates,
        targetSectionKey: 'templates'
      }
    case 'blocked_cells_out_of_bounds':
      return {
        ...base,
        text: settingsLocale.value.resizeReasonOverflowObstacles,
        targetSectionKey: 'obstacles'
      }
    default:
      return base
  }
}

const mapResizePreviewReasonItems = computed(() => {
  if (!Array.isArray(mapResizePreview.value?.blockers)) return []
  return mapResizePreview.value.blockers.map(buildMapResizeReasonItem)
})

function createPreviewFocusCell(x, y) {
  const cell = {
    x: Number(x),
    y: Number(y)
  }
  return isWithinCurrentGrid(cell) ? cell : null
}

function resolveTemplateOverflowFocusCell(item) {
  const requestedCols = Math.max(
    1,
    Number(mapResizePreview.value?.requested_grid_cols ?? mapResizePreviewCols.value ?? gridColsValue())
  )
  const requestedRows = Math.max(
    1,
    Number(mapResizePreview.value?.requested_grid_rows ?? mapResizePreviewRows.value ?? gridRowsValue())
  )
  const template = taskTemplates.value.find(templateItem => String(templateItem.id) === String(item?.id))
  if (!template) return null

  const stages =
    Array.isArray(template.stages) && template.stages.length > 0
      ? template.stages.map((stage, index) => ({
          ...createTaskChainStage(stage),
          index: Number.isInteger(Number(stage?.index)) ? Number(stage.index) : index
        }))
      : [{ ...createTaskChainStage(template), index: 0 }]
  const invalidIndexes = Array.isArray(item?.invalid_stage_indexes)
    ? item.invalid_stage_indexes.map(index => Number(index))
    : []

  for (const invalidIndex of invalidIndexes) {
    const stage = stages.find(stageItem => stageItem.index === invalidIndex) ?? stages[invalidIndex]
    if (!stage) continue

    const candidates = [
      {
        x: stage.start_x,
        y: stage.start_y,
        invalid:
          !isValidGridCoordinate(stage.start_x, requestedCols) ||
          !isValidGridCoordinate(stage.start_y, requestedRows)
      },
      {
        x: stage.end_x,
        y: stage.end_y,
        invalid:
          !isValidGridCoordinate(stage.end_x, requestedCols) ||
          !isValidGridCoordinate(stage.end_y, requestedRows)
      }
    ]

    const invalidCandidate = candidates.find(candidate => candidate.invalid)
    if (invalidCandidate) {
      const focusCell = createPreviewFocusCell(invalidCandidate.x, invalidCandidate.y)
      if (focusCell) return focusCell
    }

    const fallbackCandidate = candidates
      .map(candidate => createPreviewFocusCell(candidate.x, candidate.y))
      .find(Boolean)
    if (fallbackCandidate) return fallbackCandidate
  }

  return null
}

const mapResizePreviewDetailSections = computed(() => {
  if (!mapResizePreview.value) return []

  const sections = []
  const agvItems = Array.isArray(mapResizePreview.value.agv_overflows)
    ? mapResizePreview.value.agv_overflows.map(item => ({
        key: `agv-${item.id}-${item.x}-${item.y}`,
        text: `#${item.id} · (${item.x}, ${item.y}) · ${String(item.status || '').toUpperCase()}`,
        focus: createPreviewFocusCell(item.x, item.y)
      }))
    : []
  const pointItems = Array.isArray(mapResizePreview.value.point_overflows)
    ? mapResizePreview.value.point_overflows.map(item => ({
        key: `point-${item.id}`,
        text: `${item.name} · (${item.x}, ${item.y})`,
        focus: createPreviewFocusCell(item.x, item.y)
      }))
    : []
  const templateItems = Array.isArray(mapResizePreview.value.template_overflows)
    ? mapResizePreview.value.template_overflows.map(item => ({
        key: `template-${item.id}`,
        text: `${item.name} · ${settingsLocale.value.resizePreviewTemplateStages}: ${(item.invalid_stage_indexes ?? []).map(index => Number(index) + 1).join(', ') || '—'}`,
        focus: resolveTemplateOverflowFocusCell(item)
      }))
    : []
  const obstacleItems = Array.isArray(mapResizePreview.value.blocked_overflows)
    ? mapResizePreview.value.blocked_overflows.map(item => ({
        key: `blocked-${item.x}-${item.y}`,
        text: `(${item.x}, ${item.y})`,
        focus: createPreviewFocusCell(item.x, item.y)
      }))
    : []

  if (agvItems.length > 0) {
    sections.push({
      key: 'agv',
      title: settingsLocale.value.resizePreviewOverflowAgvs,
      items: agvItems,
    })
  }
  if (pointItems.length > 0) {
    sections.push({
      key: 'points',
      title: settingsLocale.value.resizePreviewOverflowPoints,
      items: pointItems,
    })
  }
  if (templateItems.length > 0) {
    sections.push({
      key: 'templates',
      title: settingsLocale.value.resizePreviewOverflowTemplates,
      items: templateItems,
    })
  }
  if (obstacleItems.length > 0) {
    sections.push({
      key: 'obstacles',
      title: settingsLocale.value.resizePreviewOverflowObstacles,
      items: obstacleItems,
    })
  }
  return sections
})
const mapResizePreviewMatchesInput = computed(() => {
  if (!mapResizePreview.value) return false
  return (
    Number(mapResizePreview.value.requested_grid_cols) === mapResizeRequestedCols.value &&
    Number(mapResizePreview.value.requested_grid_rows) === mapResizeRequestedRows.value
  )
})
const canApplyMapResize = computed(() => {
  if (obstacleLayoutDirty.value) return false
  if (!mapResizePreview.value?.can_apply) return false
  if (!mapResizePreviewMatchesInput.value) return false
  return (
    mapResizeRequestedCols.value !== gridColsValue() ||
    mapResizeRequestedRows.value !== gridRowsValue()
  )
})
const selectedObstaclePresetDeletable = computed(() => Boolean(selectedObstaclePresetInfo.value?.deletable))
const syncedBlockedCellSet = computed(
  () => new Set(syncedBlockedCells.value.map(cell => `${cell.x},${cell.y}`))
)
const syncedValidCellSet = computed(
  () => new Set(syncedValidCells.value.map(cell => `${cell.x},${cell.y}`))
)
const obstacleLayoutDirty = computed(() => {
  if (blockedCellCount.value !== syncedBlockedCells.value.length) return true
  for (const key of blockedCellSet.value) {
    if (!syncedBlockedCellSet.value.has(key)) return true
  }
  if (validCellCount.value !== syncedValidCells.value.length) return true
  for (const key of validCellSet.value) {
    if (!syncedValidCellSet.value.has(key)) return true
  }
  return false
})
const minimapManualPathToStartPoints = computed(() =>
  toSvgPoints(manualPathToStart.value, minimapCellSize.value)
)
const minimapManualPathToEndPoints = computed(() =>
  toSvgPoints(manualPathToEnd.value, minimapCellSize.value)
)
const minimapAutoPathToStartPoints = computed(() =>
  toSvgPoints(autoPathToStart.value, minimapCellSize.value)
)
const minimapAutoPathToEndPoints = computed(() =>
  toSvgPoints(autoPathToEnd.value, minimapCellSize.value)
)
const minimapViewportStyle = computed(() => {
  const scale = minimapScale.value
  const visibleWidth = Math.min(mapWidth.value, mapViewportWidth.value / mapZoom.value)
  const visibleHeight = Math.min(mapHeight.value, mapViewportHeight.value / mapZoom.value)
  const visibleX = clampValue(-mapOffsetX.value / mapZoom.value, 0, mapWidth.value - visibleWidth)
  const visibleY = clampValue(-mapOffsetY.value / mapZoom.value, 0, mapHeight.value - visibleHeight)

  return {
    left: `${visibleX * scale}px`,
    top: `${visibleY * scale}px`,
    width: `${visibleWidth * scale}px`,
    height: `${visibleHeight * scale}px`
  }
})
const pointLibrary = computed(() => [...builtinPoints.value, ...customPoints.value])
const taskTemplates = computed(() => [...builtinTemplates.value, ...customTaskTemplates.value])
const currentDispatchModeLabel = computed(() =>
  dispatchMode.value === 'auto' ? panelLocale.value.modeAuto : panelLocale.value.modeManual
)
const currentDispatchModeHint = computed(() =>
  dispatchMode.value === 'auto' ? panelLocale.value.modeAutoHint : panelLocale.value.modeManualHint
)
const dispatchModeAutoLabel = computed(() => panelLocale.value.modeAuto || t('dispatch_auto'))
const dispatchModeManualLabel = computed(() => panelLocale.value.modeManual || t('dispatch_manual'))
const faultLocale = computed(() => localeTexts.value.fault ?? LOCALE_TEXTS.en.fault)
const panelSummaryLocale = computed(() => localeTexts.value.panelSummary ?? LOCALE_TEXTS.en.panelSummary)
const settingsLocale = computed(() => localeTexts.value.settings ?? LOCALE_TEXTS.en.settings)
const compareDisplayTitleLabel = computed(() => settingsLocale.value.compareDisplay || 'Display Mode')
const compareDisplayPanelLabel = computed(() => settingsLocale.value.compareDisplayPanel || 'Side Panel')
const compareDisplayFloatingLabel = computed(() => settingsLocale.value.compareDisplayFloating || 'Floating Window')
const {
  statusColor,
  statusText,
  compactStatusText,
  taskStatusText,
  algorithmText,
  faultTypeText,
  faultSeverityText,
  faultEventTypeText,
  faultEventStatusText,
  moveToMaintenanceText,
  returnToServiceText,
  maintenanceListTitleText,
  formatTaskMeta,
  formatTaskAgv,
  formatTaskStageProgress,
  formatTaskCurrentStage,
  formatTaskTime,
  formatTaskCompactSummary,
  formatDispatchReason,
  formatTaskAlgorithm,
  formatTaskPathStats,
  formatTaskInitialPoint,
  blockedTaskAlertText,
  isRecoveryRequiredTask,
  isCellOccupiedTimeoutTask,
  retryFromCurrentButtonText,
  retryFromCurrentQueuedText,
  agvRecoveryJumpButtonText,
  formatTaskLastAction,
  taskLastActionLabel,
  isTaskReasonAlert,
  recoveryActionText,
  recoveryQueuedText,
  countRetryableBlockedTasks
} = useTaskTextFormatters({
  locale,
  t,
  faultLocale,
  taskChainLocale,
  isTaskChain,
  overallTaskStart,
  overallTaskEnd,
  currentTaskStage,
  normalizeTaskStages,
  localizeDispatchReason,
  obstacleEditMode,
  obstacleLayoutDirty,
  obstacleSaveRequiredText,
  hasIdleAgv,
  agvs,
  taskDispatchOrigin,
  algorithm,
  agvRecoveryJumpTargetAgvId
})
const currentTaskBuilderModeCompactLabel = computed(() =>
  taskBuilderMode.value === 'chain' ? taskBuilderLocale.value.chainCompact : taskBuilderLocale.value.singleCompact
)
const taskChainMapPickStageCountInput = computed({
  get: () => taskChainMapPickStageCount.value,
  set: value => {
    setTaskChainMapPickStageCount(value)
  }
})
const taskChainRequiredPointCount = computed(() => taskChainMapPickStageCount.value + 1)
const currentTaskBuilderHint = computed(() => {
  if (dispatchMode.value !== 'manual') {
    return taskBuilderMode.value === 'chain' ? taskChainLocale.value.hint : taskBuilderLocale.value.singleHint
  }

  if (!selectedBackendAgv.value) {
    if (locale.value === 'ja') {
      return '手動派車では先に空き AGV を選択してください。'
    }
    if (locale.value === 'zh') {
      return '手动派车需要先选中一台空闲 AGV。'
    }
    return 'Manual dispatch requires selecting one idle AGV first.'
  }

  if (taskBuilderMode.value === 'single' && manualDispatchStep.value === 'awaiting_end') {
    if (locale.value === 'ja') {
      return '手動派車の始点を選択済みです。続けて終点を選択してください。'
    }
    if (locale.value === 'zh') {
      return '已选定手动派车起点，请继续选择终点。'
    }
    return 'The manual dispatch start point is selected. Choose the end point next.'
  }

  if (taskBuilderMode.value === 'chain') {
    if (locale.value === 'ja') {
      return '手動派車では選択中 AGV の初期位置から第1段の始点へ先に就位し、その後に設定した多段タスクを実行します。'
    }
    if (locale.value === 'zh') {
      return '手动派车会先从所选 AGV 的初始点就位到第一段起点，再执行你设置的多段任务。'
    }
    return 'Manual dispatch first relocates the selected AGV from its initial position to the first stage start, then runs the configured multi-stage task.'
  }

  if (locale.value === 'ja') {
    return '手動派車では AGV の初期位置からタスク始点へ先に就位し、その後に始点から終点まで実行します。'
  }
  if (locale.value === 'zh') {
    return '手动派车会先从所选 AGV 的初始点到任务起点就位，再执行起点到终点的任务。'
  }
  return 'Manual dispatch first relocates the selected AGV from its initial position to the task start, then executes the route to the end point.'
})
const taskBuilderTitleText = computed(() => {
  if (dispatchMode.value !== 'manual') return taskBuilderLocale.value.title
  if (locale.value === 'ja') return '手動派車'
  if (locale.value === 'zh') return '手动派车'
  return 'Manual Dispatch'
})
const singleTaskStartLabelX = computed(() => {
  return t('form_start_x')
})
const singleTaskStartLabelY = computed(() => {
  return t('form_start_y')
})
const singleTaskEndLabelX = computed(() => {
  return t('form_end_x')
})
const singleTaskEndLabelY = computed(() => {
  return t('form_end_y')
})
const singleTaskSubmitText = computed(() => {
  if (dispatchMode.value !== 'manual') return t('add_task')
  if (locale.value === 'ja') return '手動派車を実行'
  if (locale.value === 'zh') return '执行手动派车'
  return 'Dispatch Manually'
})
const chainTaskSubmitText = computed(() => {
  if (dispatchMode.value !== 'manual') return taskChainLocale.value.createTask
  if (locale.value === 'ja') return '多段手動派車を実行'
  if (locale.value === 'zh') return '执行多段手动派车'
  return 'Dispatch Multi-stage Task'
})
const taskChainMapPickStatusText = computed(() => {
  if (dispatchMode.value === 'manual' && !selectedBackendAgv.value) {
    if (locale.value === 'ja') {
      return '先に空き AGV を選択してから多段選点を開始してください。'
    }
    if (locale.value === 'zh') {
      return '请先选中一台空闲 AGV，再开始多段选点。'
    }
    return 'Select one idle AGV before starting multi-point manual dispatch.'
  }

  if (!taskChainMapPickActive.value) {
    return taskChainMapPickUiLocale.value.idle(taskChainRequiredPointCount.value, taskChainMapPickStageCount.value)
  }

  return taskChainMapPickUiLocale.value.status(
    taskChainMapPickPoints.value.length,
    taskChainRequiredPointCount.value,
    taskChainMapPickStageCount.value
  )
})
const manualDispatchOriginText = computed(() => {
  if (dispatchMode.value !== 'manual' || !selectedBackendAgv.value) return ''
  if (locale.value === 'ja') {
    return `初期位置: AGV #${selectedBackendAgv.value.id} (${selectedBackendAgv.value.x}, ${selectedBackendAgv.value.y})`
  }
  if (locale.value === 'zh') {
    return `初始点: AGV #${selectedBackendAgv.value.id} (${selectedBackendAgv.value.x}, ${selectedBackendAgv.value.y})`
  }
  return `Initial point: AGV #${selectedBackendAgv.value.id} (${selectedBackendAgv.value.x}, ${selectedBackendAgv.value.y})`
})

const {
  findLatestActiveTask,
  autoDisplayTask,
  manualDisplayTask,
  manualChainRoutePoints,
  autoChainRoutePoints,
  minimapManualChainRoutePoints,
  minimapAutoChainRoutePoints,
  chainMidMarkers
} = useTaskDisplayState({
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
})

const autoDraftMarkerDisplayActive = computed(() => {
  if (dispatchMode.value !== 'auto') return false
  if (taskBuilderMode.value === 'chain' && taskChainMapPickActive.value) return true
  return mapDraftPrimedMode.value === 'auto' || autoDraftPicking.value
})
const manualDraftMarkerDisplayActive = computed(() => {
  if (dispatchMode.value !== 'manual') return false
  if (taskBuilderMode.value === 'chain' && taskChainMapPickActive.value) return true
  return mapDraftPrimedMode.value === 'manual' || manualDraftPicking.value || manualDispatchStep.value === 'awaiting_end'
})
const manualDraftDisplayEndMarker = computed(() => {
  if (!manualDraftMarkerDisplayActive.value) return null
  if (
    taskBuilderMode.value === 'chain' &&
    taskChainMapPickActive.value &&
    taskChainMapPickPoints.value.length < taskChainRequiredPointCount.value
  ) {
    return null
  }
  return endPoint.value
})
const autoDraftDisplayEndMarker = computed(() => {
  if (!autoDraftMarkerDisplayActive.value) return null
  if (
    taskBuilderMode.value === 'chain' &&
    taskChainMapPickActive.value &&
    taskChainMapPickPoints.value.length < taskChainRequiredPointCount.value
  ) {
    return null
  }
  return endPoint.value
})
const activeRuntimeDisplayTask = computed(() => {
  if (preferredRuntimeDisplayMode.value === 'manual') {
    return manualDisplayTask.value ?? autoDisplayTask.value ?? null
  }
  return autoDisplayTask.value ?? manualDisplayTask.value ?? null
})
const runtimeDisplayMarkerVariant = computed(() => {
  const task = activeRuntimeDisplayTask.value
  if (!task) return null
  return task.dispatch_mode === 'manual' ? 'manual' : 'auto'
})
const runtimeDisplayStartMarker = computed(() => {
  const task = activeRuntimeDisplayTask.value
  if (!task) return null
  return resolveTaskDisplayStartMarker(task)
})
const runtimeDisplayEndMarker = computed(() => {
  const task = activeRuntimeDisplayTask.value
  if (!task) return null
  if (runtimeDisplayMarkerVariant.value === 'auto') {
    if (Number(task.total_stages ?? 1) > 1) {
      return resolveTaskOverallEndMarker(task)
    }
    return resolveTaskEndMarker(task) ?? resolveTaskDisplayEndMarker(task)
  }
  return resolveTaskDisplayEndMarker(task)
})
const activeDisplayMarkerVariant = computed(() => {
  if (autoDraftMarkerDisplayActive.value) return 'auto'
  if (manualDraftMarkerDisplayActive.value) return 'manual'
  return runtimeDisplayMarkerVariant.value
})
const activeDisplayStartMarker = computed(() => {
  if (autoDraftMarkerDisplayActive.value) return startPoint.value
  if (manualDraftMarkerDisplayActive.value) return startPoint.value
  return runtimeDisplayStartMarker.value
})
const activeDisplayEndMarker = computed(() => {
  if (autoDraftMarkerDisplayActive.value) return autoDraftDisplayEndMarker.value
  if (manualDraftMarkerDisplayActive.value) return manualDraftDisplayEndMarker.value
  return runtimeDisplayEndMarker.value
})
const minimapDisplayStartMarker = computed(() => activeDisplayStartMarker.value)
const minimapDisplayEndMarker = computed(() => activeDisplayEndMarker.value)

function buildManualTaskCreateMeta(manualAgv, reason = 'waiting_for_bound_agv') {
  if (!manualAgv) return {}
  return {
    dispatch_mode: 'manual',
    preferred_agv_id: manualAgv.id,
    dispatch_origin_x: Number(manualAgv.x),
    dispatch_origin_y: Number(manualAgv.y),
    dispatch_algorithm: algorithm.value,
    dispatch_reason: reason
  }
}

function manualTaskQueuedText(task) {
  const agvId = task?.preferred_agv_id ?? task?.agv_id ?? selectedBackendAgv.value?.id ?? '?'
  if (locale.value === 'ja') {
    return `タスクは作成されました。指定 AGV #${agvId} の空きを待って自動実行します。`
  }
  if (locale.value === 'zh') {
    return `任务已创建，正在等待指定 AGV #${agvId} 空闲后自动执行。`
  }
  return `Task created. Waiting for bound AGV #${agvId} to become idle before execution.`
}

function autoTaskQueuedText(task) {
  const taskId = task?.id ?? '?'
  if (locale.value === 'ja') {
    return `タスク #${taskId} を自動調度キューへ追加しました。空き AGV が出るまで待機します。`
  }
  if (locale.value === 'zh') {
    return `任务 #${taskId} 已加入自动调度队列，正在等待空闲 AGV。`
  }
  return `Task #${taskId} was added to the auto dispatch queue and is waiting for an idle AGV.`
}

function mergeTaskDisplayPayload(taskPayload, fallbackTask = null) {
  if (!taskPayload) return fallbackTask
  if (!fallbackTask) return taskPayload
  return {
    ...fallbackTask,
    ...taskPayload,
    stages: Array.isArray(taskPayload.stages) && taskPayload.stages.length > 0 ? taskPayload.stages : fallbackTask.stages,
    overall_start_x:
      taskPayload.overall_start_x ?? fallbackTask.overall_start_x ?? fallbackTask.start_x ?? taskPayload.start_x,
    overall_start_y:
      taskPayload.overall_start_y ?? fallbackTask.overall_start_y ?? fallbackTask.start_y ?? taskPayload.start_y,
    overall_end_x: taskPayload.overall_end_x ?? fallbackTask.overall_end_x ?? fallbackTask.end_x ?? taskPayload.end_x,
    overall_end_y: taskPayload.overall_end_y ?? fallbackTask.overall_end_y ?? fallbackTask.end_y ?? taskPayload.end_y
  }
}

function applyTaskDisplayMarkers(taskPayload, fallbackTask = null) {
  const task = mergeTaskDisplayPayload(taskPayload, fallbackTask)
  if (!task) return
  startPoint.value = resolveTaskDisplayStartMarker(task)
  endPoint.value = resolveTaskDisplayEndMarker(task)
}

async function handleManualScheduleFailure(createdTaskId, scheduleData) {
  await fetchTasks()
  const latestTask = tasks.value.find(task => task.id === createdTaskId)

  if (latestTask?.status === 'blocked') {
    window.alert(blockedTaskAlertText(latestTask))
    manualDraftPicking.value = false
    trackedManualTaskId.value = null
    manualDispatchStep.value = 'idle'
    clearManualDestination()
    return false
  }

  if (latestTask && ['assigned', 'running'].includes(latestTask.status)) {
    manualPathToStart.value = latestTask.path_to_start ?? []
    manualPathToEnd.value = latestTask.path_to_end ?? []
    preferredRuntimeDisplayMode.value = 'manual'
    manualDraftPicking.value = false
    trackedManualTaskId.value = latestTask.id
    applyTaskDisplayMarkers(latestTask)
    manualDispatchStep.value = 'running'
    bumpManualPreviewMinVisible()
    await fetchAgvs()
    return true
  }

  if (latestTask?.status === 'pending') {
    preferredRuntimeDisplayMode.value = 'manual'
    manualDraftPicking.value = false
    trackedManualTaskId.value = latestTask.id
    applyTaskDisplayMarkers(latestTask)
    manualDispatchStep.value = 'running'
    bumpManualPreviewMinVisible()
    window.alert(manualTaskQueuedText(latestTask))
    return true
  }

  window.alert(localizeApiErrorDetail(scheduleData?.detail, t('task_manual_unreachable')))
  manualDraftPicking.value = false
  trackedManualTaskId.value = null
  manualDispatchStep.value = 'idle'
  clearManualDestination()
  return false
}
const taskChainMapPickButtonText = computed(() =>
  taskChainMapPickActive.value ? taskChainMapPickUiLocale.value.cancel : taskChainMapPickUiLocale.value.start
)
const currentCompareHint = computed(() =>
  taskBuilderMode.value === 'chain'
    ? algorithmCompareLocale.value.hintChain
    : algorithmCompareLocale.value.hintSingle
)
const recommendedCompareAlgorithm = computed(() => {
  const results = pathCompareResult.value?.results
  if (!results) return null
  const simple = results.simple
  const astar = results.astar
  if (simple?.reachable && !astar?.reachable) return 'simple'
  if (!simple?.reachable && astar?.reachable) return 'astar'
  if (!simple?.reachable && !astar?.reachable) return null
  if ((astar?.total_length ?? Number.POSITIVE_INFINITY) < (simple?.total_length ?? Number.POSITIVE_INFINITY)) {
    return 'astar'
  }
  return 'simple'
})
const compareEntryText = computed(() => {
  if (!pathCompareResult.value) {
    return algorithmCompareLocale.value.title
  }

  if (recommendedCompareAlgorithm.value) {
    return `${algorithmCompareLocale.value.title} · ${algorithmCompareLocale.value.recommended} ${algorithmText(recommendedCompareAlgorithm.value)}`
  }

  return `${algorithmCompareLocale.value.title} · ${algorithmCompareLocale.value.unreachable}`
})
const compareResultEntries = computed(() => Object.entries(pathCompareResult.value?.results ?? {}))
const experimentRecordCount = computed(() => experimentRecords.value.length)
const compareFloatingStyle = computed(() => ({
  left: `${compareFloatingX.value}px`,
  top: `${compareFloatingY.value}px`,
  opacity: compareFloatingOpacity.value
}))
const panelSummaryModes = computed(() => [
  { key: 'hidden', label: panelSummaryLocale.value.hidden },
  { key: 'compact', label: panelSummaryLocale.value.compact },
  { key: 'full', label: panelSummaryLocale.value.full }
])
const areAllPanelSectionsExpanded = computed(() =>
  visiblePanelSectionKeys.value.length > 0 && visiblePanelSectionKeys.value.every(key => Boolean(panelSections.value[key]))
)
const areAllPanelSectionsCollapsed = computed(() =>
  visiblePanelSectionKeys.value.every(key => !panelSections.value[key])
)
const pendingTaskCount = computed(() => tasks.value.filter(task => task.status === 'pending').length)
const runningTaskCount = computed(() => tasks.value.filter(task => task.status === 'running').length)
const obstacleSummaryText = computed(() => {
  if (locale.value === 'ja') {
    return `障害セル ${blockedCellCount.value} マス`
  }
  if (locale.value === 'zh') {
    return `障碍格 ${blockedCellCount.value} 个`
  }
  return `${blockedCellCount.value} blocked cells`
})
const algorithmHintText = computed(() => {
  if (locale.value === 'ja') {
    return algorithm.value === 'astar'
      ? `A* は障害物を回避して経路探索します。${obstacleSummaryText.value}。`
      : `直線経路は簡易マンハッタン経路のみを試すため、障害物で失敗する場合があります。${obstacleSummaryText.value}。`
  }
  if (locale.value === 'zh') {
    return algorithm.value === 'astar'
      ? `A* 会绕开障碍搜索可达路径。${obstacleSummaryText.value}。`
      : `直线路径只尝试简化曼哈顿直行，遇到障碍时可能失败。${obstacleSummaryText.value}。`
  }
  return algorithm.value === 'astar'
    ? `A* searches around blocked cells. ${obstacleSummaryText.value}.`
    : `Simple routing only follows a direct Manhattan trace and may fail on blocked cells. ${obstacleSummaryText.value}.`
})
const selectedAgvSummaryText = computed(() => {
  if (!selectedAgv.value) return panelSummaryLocale.value.noAgv
  return `#${selectedAgv.value.id} / ${statusText(selectedAgv.value.status)} / (${selectedAgv.value.x},${selectedAgv.value.y})`
})
const compactSelectedAgvText = computed(() => {
  if (!selectedAgv.value) return panelSummaryLocale.value.noAgvCompact
  return `#${selectedAgv.value.id}${compactStatusText(selectedAgv.value.status)}`
})
const toolbarSelectedAgvText = computed(() => {
  if (!selectedAgv.value) {
    if (locale.value === 'ja') return '未選択'
    if (locale.value === 'zh') return '未选车'
    return 'No AGV'
  }
  return `#${selectedAgv.value.id} ${compactStatusText(selectedAgv.value.status)}`
})
const toolbarSelectedAgvTitle = computed(() => {
  if (!selectedAgv.value) return selectedAgvSummaryText.value
  return `AGV ${selectedAgvSummaryText.value}`
})
const panelSummaryItems = computed(() => [
  {
    key: 'mode',
    label: panelSummaryLocale.value.mode,
    value: currentDispatchModeLabel.value,
    sectionKey: 'control',
    interactive: 'mode'
  },
  {
    key: 'agv',
    label: panelSummaryLocale.value.selectedAgv,
    value: selectedAgvSummaryText.value,
    sectionKey: 'control'
  },
  {
    key: 'zoom',
    label: panelSummaryLocale.value.zoom,
    value: mapZoomLabel.value,
    sectionKey: 'control',
    interactive: 'zoom'
  },
  {
    key: 'pending',
    label: panelSummaryLocale.value.pending,
    value: String(pendingTaskCount.value),
    sectionKey: 'queue'
  },
  {
    key: 'running',
    label: panelSummaryLocale.value.running,
    value: String(runningTaskCount.value),
    sectionKey: 'queue'
  }
])
const panelSummaryCompactItems = computed(() => [
  {
    key: 'mode',
    value: dispatchMode.value === 'auto' ? panelSummaryLocale.value.autoShort : panelSummaryLocale.value.manualShort,
    sectionKey: 'control',
    interactive: 'mode'
  },
  {
    key: 'agv',
    value: compactSelectedAgvText.value,
    sectionKey: 'control'
  },
  {
    key: 'zoom',
    value: mapZoomLabel.value,
    sectionKey: 'control',
    interactive: 'zoom'
  },
  {
    key: 'pending',
    value:
      locale.value === 'en'
        ? `PEND ${pendingTaskCount.value}`
        : locale.value === 'ja'
          ? `未割${pendingTaskCount.value}`
          : `待分${pendingTaskCount.value}`,
    sectionKey: 'queue'
  },
  {
    key: 'running',
    value:
      locale.value === 'en'
        ? `RUN ${runningTaskCount.value}`
        : locale.value === 'ja'
          ? `実行${runningTaskCount.value}`
          : `运行${runningTaskCount.value}`,
    sectionKey: 'queue'
  }
])
const showPanelSummary = computed(() => panelSummaryMode.value !== 'hidden')
const normalizedPanelSearch = computed(() => panelSearch.value.trim().toLowerCase())
const matchedTaskIds = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  return tasks.value
    .filter(task =>
      matchesSearchFields(
        [
          task.id,
          task.status,
          taskStatusText(task.status),
          formatTaskMeta(task),
          formatTaskStageProgress(task),
          formatTaskCurrentStage(task),
          formatTaskAgv(task),
          formatDispatchReason(task),
          task.priority
        ],
        keyword
      )
    )
    .map(task => task.id)
})
const matchedTemplateIds = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  return taskTemplates.value
    .filter(template =>
      matchesSearchFields(
        [
          taskTemplateName(template),
          taskTemplateTypeText(template),
          formatTemplateMeta(template),
          formatTemplateStageCount(template),
          template.priority,
          ...normalizeTemplateStages(template).flatMap(stage => [
            stage.label,
            stage.start_x,
            stage.start_y,
            stage.end_x,
            stage.end_y
          ])
        ],
        keyword
      )
    )
    .map(template => template.id)
})
const matchedPointIds = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  return pointLibrary.value
    .filter(point =>
      matchesSearchFields(
        [pointName(point), pointZone(point), `${point.x},${point.y}`, `${point.x} ${point.y}`, ...(point.aliases ?? [])],
        keyword
      )
    )
    .map(point => point.id)
})
const matchedExperimentRecordIds = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  return experimentRecords.value
    .filter(record =>
      matchesSearchFields(
        [
          record.scene_name,
          record.route_summary,
          record.current_algorithm,
          record.recommended_algorithm,
          record.saved_at,
          ...(record.algorithms ?? []).flatMap(item => [item.algorithm, item.reachable_text, String(item.total_length ?? '')])
        ],
        keyword
      )
    )
    .map(record => record.id)
})
const matchedOperationAuditIds = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  return operationAudits.value
    .filter(entry =>
      matchesSearchFields(
        [
          entry.id,
          entry.resource_type,
          entry.resource_id,
          entry.action,
          operationResourceLabel(entry.resource_type),
          operationActionLabel(entry.action),
          formatOperationAuditOperator(entry),
          formatOperationAuditResourceRef(entry),
          formatOperationAuditMetadata(entry),
          entry.performed_at,
        ],
        keyword
      )
    )
    .map(entry => entry.id)
})
const matchedComfyJobIds = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  return comfyRenderJobs.value
    .filter(job =>
      matchesSearchFields(
        [
          job.id,
          job.source_type,
          job.source_ref,
          job.created_by,
          job.created_at,
          job.status,
          job.error_message,
        ],
        keyword
      )
    )
    .map(job => job.id)
})
const panelSearchResults = computed(() => {
  const keyword = normalizedPanelSearch.value
  if (!keyword) return []

  const results = []
  const sections = [
    {
      key: 'control',
      label: panelLocale.value.sections.control,
      matched: matchesSearchFields(
        [
          panelLocale.value.sections.control,
          panelLocale.value.currentMode,
          currentDispatchModeLabel.value,
          currentDispatchModeHint.value,
          taskBuilderLocale.value.title,
          taskBuilderLocale.value.single,
          taskBuilderLocale.value.chain,
          taskChainLocale.value.title,
          t('task_form'),
          t('dispatch')
        ],
        keyword
      ),
      count: 0
    },
    {
      key: 'queue',
      label: panelLocale.value.sections.queue,
      matched: matchedTaskIds.value.length > 0 || matchesSearchFields([panelLocale.value.sections.queue, t('tasks')], keyword),
      count: matchedTaskIds.value.length
    },
    {
      key: 'templates',
      label: panelLocale.value.sections.templates,
      matched:
        matchedTemplateIds.value.length > 0 ||
        matchesSearchFields([panelLocale.value.sections.templates, t('template_library')], keyword),
      count: matchedTemplateIds.value.length
    },
    {
      key: 'points',
      label: panelLocale.value.sections.points,
      matched:
        matchedPointIds.value.length > 0 ||
        matchesSearchFields([panelLocale.value.sections.points, t('point_library')], keyword),
      count: matchedPointIds.value.length
    },
    {
      key: 'json',
      label: panelLocale.value.sections.json,
      matched: matchesSearchFields([panelLocale.value.sections.json, t('json_tools')], keyword),
      count: 0
    },
    {
      key: 'experiments',
      label: panelLocale.value.sections.experiments,
      matched:
        matchedExperimentRecordIds.value.length > 0 ||
        matchesSearchFields([panelLocale.value.sections.experiments, experimentLocale.value.title], keyword),
      count: matchedExperimentRecordIds.value.length
    },
    {
      key: 'ai',
      label: panelLocale.value.sections.ai,
      matched:
        matchedComfyJobIds.value.length > 0 ||
        matchesSearchFields([panelLocale.value.sections.ai, t('ai_render_title')], keyword),
      count: matchedComfyJobIds.value.length
    },
    {
      key: 'operations',
      label: panelLocale.value.sections.operations,
      matched:
        matchedOperationAuditIds.value.length > 0 ||
        matchesSearchFields([panelLocale.value.sections.operations, t('operations_title')], keyword),
      count: matchedOperationAuditIds.value.length
    }
  ]

  for (const section of sections) {
    if (!visiblePanelSectionKeySet.value.has(section.key)) continue
    if (!section.matched) continue
    results.push({
      ...section,
      text:
        section.count > 0
          ? `${section.label} (${section.count} ${panelSearchLocale.value.hits})`
          : section.label
    })
  }

  return results
})
const matchedPanelSectionKeys = computed(() => panelSearchResults.value.map(item => item.key))
const filteredPoints = computed(() => {
  const keyword = pointSearch.value.trim().toLowerCase()
  if (!keyword) return pointLibrary.value

  return pointLibrary.value.filter(point => {
    const fields = [
      point.id,
      pointName(point),
      pointZone(point),
      `${point.x},${point.y}`,
      `${point.x} ${point.y}`,
      ...(point.aliases ?? [])
    ]

    return fields.some(value => String(value).toLowerCase().includes(keyword))
  })
})

const taskGroups = computed(() => {
  const groups = [
    { key: 'pending', title: t('queue_pending') },
    { key: 'blocked', title: t('queue_blocked') },
    { key: 'assigned', title: t('queue_assigned') },
    { key: 'running', title: t('queue_running') },
    { key: 'finished', title: t('queue_finished') }
  ]

  return groups.map(group => ({
    ...group,
    tasks: sortTasks(
      tasks.value.filter(task => task.status === group.key && taskMatchesQueueFilter(task)),
      group.key
    )
  }))
})

const orphanedTaskCount = computed(() => tasks.value.filter(task => isTaskOrphaned(task)).length)

function isBlockedCell(x, y) {
  return navigationBlockedCellSet.value.has(blockedCellKey(x, y))
}

function isTaskOrphaned(task) {
  if (!task || !['assigned', 'running'].includes(task.status)) return false
  const relatedAgv =
    (task.agv_id ? agvs.value.find(agv => agv.id === task.agv_id) : null) ??
    agvs.value.find(agv => agv.task_id === task.id)
  return !relatedAgv
}

function taskMatchesQueueFilter(task) {
  if (taskQueueViewFilter.value === 'orphaned') {
    return isTaskOrphaned(task)
  }
  return true
}

function formatCompareStageLengths(result) {
  if (!result?.stage_results?.length) return ''
  return result.stage_results
    .map(stage => {
      if (!stage.reachable) {
        return `${stage.index + 1}: X`
      }
      return `${stage.index + 1}: ${stage.path_length}`
    })
    .join(' | ')
}

function formatCompareResultStatus(result) {
  if (!result) return ''
  return result.reachable ? algorithmCompareLocale.value.reachable : algorithmCompareLocale.value.unreachable
}

function compareResultBadgeText(key) {
  if (algorithm.value === key) {
    return algorithmCompareLocale.value.apply
  }
  if (recommendedCompareAlgorithm.value === key) {
    return algorithmCompareLocale.value.recommended
  }
  return algorithmCompareLocale.value.switchTo
}

function formatExperimentSavedAt(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function formatDateTimeInline(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function formatExperimentAlgorithms(record) {
  return (record.algorithms ?? [])
    .map(item => {
      const label = item.reachable
        ? `${algorithmText(item.algorithm)} / ${algorithmCompareLocale.value.total}: ${item.total_length ?? '--'}`
        : `${algorithmText(item.algorithm)} / ${algorithmCompareLocale.value.unreachable}`
      return label
    })
    .join(' | ')
}

function formatExperimentCardTitle(record, index) {
  const seq = Math.max(experimentRecords.value.length - Number(index ?? 0), 1)
  const scene = record?.scene_name || '--'
  if (locale.value === 'ja') return `${experimentLocale.value.recordPrefix} ${seq} · ${scene}`
  if (locale.value === 'zh') return `${experimentLocale.value.recordPrefix} ${seq} · ${scene}`
  return `${experimentLocale.value.recordPrefix} ${seq} · ${scene}`
}

function taskRecoveryActionId(taskId, mode) {
  return `${taskId}:${mode}`
}

function isTaskRecoveryBusy(taskId, mode = null) {
  if (!taskRecoveryActionKey.value) return false
  if (!mode) return taskRecoveryActionKey.value.startsWith(`${taskId}:`)
  return taskRecoveryActionKey.value === taskRecoveryActionId(taskId, mode)
}

function buildTaskChainPayloadFromPoints(points) {
  if (points.length < taskChainRequiredPointCount.value) return null
  if (points.length < taskChainMapPickStageCount.value + 1) return null

  return {
    priority: Number(taskForm.value.priority),
    stages: Array.from({ length: taskChainMapPickStageCount.value }, (_, index) => ({
      label: taskChainStages.value[index]?.label ?? null,
      start_x: points[index].x,
      start_y: points[index].y,
      end_x: points[index + 1].x,
      end_y: points[index + 1].y
    }))
  }
}

function isQueueGroupCollapsed(groupKey) {
  return Boolean(queueGroupsCollapsed.value[groupKey])
}

function toggleQueueGroup(groupKey) {
  queueGroupsCollapsed.value = {
    ...queueGroupsCollapsed.value,
    [groupKey]: !queueGroupsCollapsed.value[groupKey]
  }
}

function isTaskCardFolded(taskId) {
  return Boolean(taskCardCollapsed.value[String(taskId)])
}

function toggleTaskCard(taskId) {
  const key = String(taskId)
  taskCardCollapsed.value = {
    ...taskCardCollapsed.value,
    [key]: !taskCardCollapsed.value[key]
  }
}

function areGroupTaskCardsCollapsed(group) {
  return group.tasks.length > 0 && group.tasks.every(task => isTaskCardFolded(task.id))
}

function areGroupTaskCardsExpanded(group) {
  return group.tasks.length > 0 && group.tasks.every(task => !isTaskCardFolded(task.id))
}

function setQueueGroupTaskCardsCollapsed(group, collapsed) {
  if (!group?.tasks?.length) return

  const nextState = { ...taskCardCollapsed.value }
  for (const task of group.tasks) {
    nextState[String(task.id)] = collapsed
  }
  taskCardCollapsed.value = nextState
}

function pointName(point) {
  return point.customName ?? t(point.nameKey)
}

function pointZone(point) {
  return point.customZone ?? t(point.zoneKey)
}

function pointTypeText(point) {
  return point.custom ? t('point_custom') : t('point_builtin')
}

function taskTemplateName(template) {
  return template.customName ?? t(template.nameKey)
}

function taskTemplateTypeText(template) {
  return template.custom ? t('template_custom') : t('template_builtin')
}

function normalizeTemplateStages(template) {
  return normalizeTemplateStagesRaw(template, {
    createTaskChainStage,
    gridCols: gridColsValue(),
    gridRows: gridRowsValue()
  })
}

function buildTemplateFromStages({
  id = `task_template_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  name,
  priority,
  stages,
  custom = true
}) {
  return buildTemplateFromStagesRaw(
    { id, name, priority, stages, custom },
    {
      normalizeStages: normalizeTemplateStages,
      clampPriority: value => clampValue(value, 1, 5)
    }
  )
}

function formatTemplateMeta(template) {
  const stages = normalizeTemplateStages(template)
  const firstStage = stages[0]
  const lastStage = stages[stages.length - 1]
  return `${t('task_start')} (${firstStage.start_x}, ${firstStage.start_y}) -> ${t('task_end')} (${lastStage.end_x}, ${lastStage.end_y})`
}

function formatTemplateStageCount(template) {
  const stages = normalizeTemplateStages(template)
  if (stages.length <= 1) return ''
  return `${taskChainLocale.value.stageCount}: ${stages.length}`
}

function buildTaskTemplateSignature(template) {
   return buildTaskTemplateSignatureRaw(template, {
    normalizeStages: normalizeTemplateStages
  })
}

function normalizeImportedTaskTemplate(template) {
  return normalizeImportedTaskTemplateRaw(template, {
    normalizeStages: normalizeTemplateStages,
    buildTemplate: params => buildTemplateFromStages(params)
  })
}

function formatTemplateJsonSummary(primaryLabel, primaryCount, skippedCount = 0) {
  return formatTemplateJsonSummaryRaw(primaryLabel, primaryCount, skippedCount, {
    separator: locale.value === 'en' ? ', ' : '，',
    skippedLabel: templateJsonLocale.value.skipped
  })
}

function matchesSearchFields(fields, keyword) {
  if (!keyword) return false
  return fields.some(value => String(value ?? '').toLowerCase().includes(keyword))
}

const {
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
} = useLocalPersistence({
  storageKeys: {
    panelSections: PANEL_SECTION_STORAGE_KEY,
    panelSummaryMode: PANEL_SUMMARY_MODE_STORAGE_KEY,
    taskQueueView: TASK_QUEUE_VIEW_STORAGE_KEY,
    experimentRecords: EXPERIMENT_RECORDS_STORAGE_KEY,
    customPoints: CUSTOM_POINTS_STORAGE_KEY,
    mapDisplay: MAP_DISPLAY_STORAGE_KEY,
    taskTemplates: TASK_TEMPLATE_STORAGE_KEY
  },
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
  showGuideCenterOnLoad,
  compareDisplayMode,
  compareFloatingOpacity,
  clampValue,
  normalizeCustomPoints: parsed =>
    normalizeStoredCustomPoints(parsed, {
      gridCols: gridColsValue(),
      gridRows: gridRowsValue(),
      isValidGridCoordinate
    }),
  templateFromStored: template =>
    buildTemplateFromStages({
      id: typeof template?.id === 'string' ? template.id : undefined,
      name: template?.customName,
      priority: template?.priority,
      stages: normalizeTemplateStages(template),
      custom: true
      })
  })

const {
  backendMode: uiSettingsBackendMode,
  fetchUiSettings
} = useUiSettingsBackend({
  API_BASE,
  panelSections,
  showMinimap,
  showMarkerIcons,
  showPathArrows,
  showStatusLegend,
  statusLegendLayout,
  statusLegendOpacity,
  compareDisplayMode,
  clampValue
})

const {
  fillTaskJsonExample,
  downloadTaskJsonExample,
  saveCurrentExperimentRecord,
  exportCurrentCompareResultJson,
  exportCurrentCompareResultCsv,
  exportAllExperimentRecordsJson,
  exportAllExperimentRecordsCsv,
  exportExperimentRecord,
  deleteExperimentRecord,
  clearExperimentRecords
} = useDataExportActions({
  jsonText,
  jsonStatus,
  taskJsonLocale,
  taskJsonExampleFileLocale,
  buildTaskJsonExamplePayload,
  experimentRecords,
  experimentStatus,
  experimentStatusType,
  experimentLocale,
  panelSections,
  buildCompareSnapshot,
  experimentCsvRowsFromRecords,
  rowsToCsv
})

function pruneTaskCardCollapsedState() {
  const visibleIds = new Set(tasks.value.map(task => String(task.id)))
  const nextState = Object.fromEntries(
    Object.entries(taskCardCollapsed.value).filter(([taskId]) => visibleIds.has(taskId))
  )

  if (Object.keys(nextState).length !== Object.keys(taskCardCollapsed.value).length) {
    taskCardCollapsed.value = nextState
  }
}

function buildBlockedBatchRetrySummary(total, scheduledCount, queuedCount, failedCount) {
  if (locale.value === 'ja') {
    return `到達不可タスク ${total} 件を処理しました。即時再試行 ${scheduledCount} 件、待機 ${queuedCount} 件、失敗 ${failedCount} 件。`
  }
  if (locale.value === 'zh') {
    return `已处理 ${total} 个不可达任务：立即重试 ${scheduledCount} 个，等待空闲 AGV ${queuedCount} 个，失败 ${failedCount} 个。`
  }
  return `Processed ${total} blocked tasks: ${scheduledCount} retried now, ${queuedCount} queued, ${failedCount} failed.`
}

function hideTaskBuilderJumpButton() {
  taskTemplateJumpReady.value = false
  if (taskBuilderJumpTimer) {
    clearTimeout(taskBuilderJumpTimer)
    taskBuilderJumpTimer = null
  }
}

function showTaskBuilderJumpButton() {
  taskTemplateJumpReady.value = true
  if (taskBuilderJumpTimer) {
    clearTimeout(taskBuilderJumpTimer)
  }
  taskBuilderJumpTimer = setTimeout(() => {
    taskTemplateJumpReady.value = false
    taskBuilderJumpTimer = null
  }, 5000)
}

function hideAgvRecoveryJumpButton() {
  agvRecoveryJumpReady.value = false
  agvRecoveryJumpTargetAgvId.value = null
  if (agvRecoveryJumpTimer) {
    clearTimeout(agvRecoveryJumpTimer)
    agvRecoveryJumpTimer = null
  }
}

function showAgvRecoveryJumpButton(agvId) {
  if (!agvId) return
  agvRecoveryJumpTargetAgvId.value = agvId
  agvRecoveryJumpReady.value = true
  if (agvRecoveryJumpTimer) {
    clearTimeout(agvRecoveryJumpTimer)
  }
  agvRecoveryJumpTimer = setTimeout(() => {
    agvRecoveryJumpReady.value = false
    agvRecoveryJumpTimer = null
  }, 5000)
}

function hideFloatingToast() {
  floatingToastVisible.value = false
  floatingToastMessage.value = ''
  floatingToastType.value = 'info'
  if (floatingToastTimer) {
    clearTimeout(floatingToastTimer)
    floatingToastTimer = null
  }
}

function showFloatingToast(message, type = 'info', durationMs = 3200) {
  if (!message) return
  floatingToastMessage.value = String(message)
  floatingToastType.value = type
  floatingToastVisible.value = true
  if (floatingToastTimer) {
    clearTimeout(floatingToastTimer)
  }
  floatingToastTimer = setTimeout(() => {
    floatingToastVisible.value = false
    floatingToastTimer = null
  }, durationMs)
}

async function handleAuthLogin() {
  try {
    const state = await loginWithAuthSession()
    authLoginRestrictionNotice.value = null
    const nextRole = String(state?.user?.role || state?.role || '').trim()
    authGuestAccepted.value = Boolean(state?.authenticated)
    authPanelOpen.value = false
    authDialogView.value = 'login'
    authEnterpriseRegisterFollowup.value = null
    if (nextRole.startsWith('enterprise_')) {
      applyEnterprisePanelPreset(nextRole, { silent: true })
    }
    await fetchOperationAudits({ force: true })
    showFloatingToast(buildAuthLoginSuccessMessage(state), 'success')
  } catch (error) {
    authLoginRestrictionNotice.value = buildAuthLoginRestrictionNotice(error?.detail)
    showFloatingToast(error?.message || t('auth_login_failed'), 'error')
  }
}

async function handleAuthLogout() {
  try {
    await logoutFromAuthSession()
    authGuestAccepted.value = false
    authPanelOpen.value = false
    authDialogView.value = 'login'
    enterpriseApprovalDialogOpen.value = false
    accountGovernanceDialogOpen.value = false
    authEnterpriseRegisterFollowup.value = null
    operationAudits.value = []
    operationAuditLastFetchedAt.value = ''
    enterpriseApplications.value = []
    selectedEnterpriseApplicationId.value = null
    showFloatingToast(t('auth_logout_success'), 'success')
  } catch (error) {
    showFloatingToast(error?.message || t('auth_logout_failed'), 'error')
  }
}

function handleAuthDemoFill(account) {
  authDialogView.value = 'login'
  fillDemoAccount(account)
}

async function handleAuthQuickLogin(account) {
  fillDemoAccount(account)
  try {
    const state = await loginWithAuthSession(account?.username, account?.password)
    const nextRole = String(state?.user?.role || state?.role || '').trim()
    authGuestAccepted.value = Boolean(state?.authenticated)
    authPanelOpen.value = false
    authDialogView.value = 'login'
    authEnterpriseRegisterFollowup.value = null
    if (nextRole.startsWith('enterprise_')) {
      applyEnterprisePanelPreset(nextRole, { silent: true })
    }
    await fetchOperationAudits({ force: true })
    showFloatingToast(buildAuthLoginSuccessMessage(state), 'success')
  } catch (error) {
    showFloatingToast(error?.message || t('auth_login_failed'), 'error')
  }
}

function enterGuestMode() {
  authGuestAccepted.value = true
  authPanelOpen.value = false
  authDialogView.value = 'login'
  operationAudits.value = []
  operationAuditLastFetchedAt.value = ''
  showFloatingToast(`${t('auth_guest_entered')} ${t('auth_entry_hint_guest')}`, 'info')
}

function resetPersonalRegisterForm() {
  authPersonalRegisterForm.value = {
    display_name: '',
    username: '',
    password: ''
  }
}

function resetEnterpriseRegisterForm() {
  authEnterpriseRegisterForm.value = {
    company_name: '',
    contact_name: '',
    contact_email: '',
    username: '',
    password: ''
  }
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.removeItem(ENTERPRISE_REGISTER_DRAFT_STORAGE_KEY)
  }
}

function clearEnterpriseRegisterDraft() {
  resetEnterpriseRegisterForm()
  authEnterpriseRegisterDraftUpdatedAt.value = ''
  showFloatingToast(t('auth_enterprise_register_draft_cleared'), 'info')
}

watch(
  authEnterpriseRegisterForm,
  value => {
    if (typeof window === 'undefined' || !window.localStorage) return
    const nextDraft = {
      company_name: String(value?.company_name || '').trim(),
      contact_name: String(value?.contact_name || '').trim(),
      contact_email: String(value?.contact_email || '').trim(),
      username: String(value?.username || '').trim()
    }
    const hasContent = Object.values(nextDraft).some(item => Boolean(item))
    if (!hasContent) {
      window.localStorage.removeItem(ENTERPRISE_REGISTER_DRAFT_STORAGE_KEY)
      authEnterpriseRegisterDraftUpdatedAt.value = ''
      return
    }
    const updatedAt = new Date().toISOString()
    authEnterpriseRegisterDraftUpdatedAt.value = updatedAt
    window.localStorage.setItem(
      ENTERPRISE_REGISTER_DRAFT_STORAGE_KEY,
      JSON.stringify({
        ...nextDraft,
        updated_at: updatedAt
      })
    )
  },
  { deep: true }
)

watch(
  authDialogView,
  nextView => {
    if (nextView !== 'enterprise-register') return
    if (!authEnterpriseRegisterDraftHasContent.value) return
    const draftMeta = readEnterpriseRegisterDraftPayload()
    authEnterpriseRegisterDraftUpdatedAt.value = String(draftMeta?.updated_at || '')
    authEnterpriseRegisterForm.value = {
      ...loadEnterpriseRegisterDraft(),
      password: authEnterpriseRegisterForm.value.password || ''
    }
  }
)

watch(
  authEnterpriseRegisterFollowup,
  nextValue => {
    if (typeof window === 'undefined' || !window.localStorage) return
    if (!nextValue) {
      window.localStorage.removeItem(ENTERPRISE_REGISTER_FOLLOWUP_STORAGE_KEY)
      return
    }
    window.localStorage.removeItem(ENTERPRISE_REGISTER_DRAFT_STORAGE_KEY)
    authEnterpriseRegisterDraftUpdatedAt.value = ''
    window.localStorage.setItem(
      ENTERPRISE_REGISTER_FOLLOWUP_STORAGE_KEY,
      JSON.stringify({
        company_name: String(nextValue?.company_name || '').trim(),
        username: String(nextValue?.username || '').trim(),
        contact_name: String(nextValue?.contact_name || '').trim(),
        contact_email: String(nextValue?.contact_email || '').trim(),
        submitted_at: nextValue?.submitted_at || null,
        status: String(nextValue?.status || 'pending').trim() || 'pending',
        updated_at: nextValue?.updated_at || new Date().toISOString()
      })
    )
  }
)

watch(
  authEnterpriseStatusFollowup,
  nextValue => {
    if (typeof window === 'undefined' || !window.localStorage) return
    if (!nextValue) {
      window.localStorage.removeItem(ENTERPRISE_STATUS_FOLLOWUP_STORAGE_KEY)
      return
    }
    window.localStorage.setItem(
      ENTERPRISE_STATUS_FOLLOWUP_STORAGE_KEY,
      JSON.stringify({
        ...nextValue,
        updated_at: nextValue.updated_at || new Date().toISOString()
      })
    )
  },
  { deep: true }
)

watch(
  enterpriseApprovalReviewFollowup,
  nextValue => {
    if (typeof window === 'undefined' || !window.localStorage) return
    if (!nextValue) {
      window.localStorage.removeItem(ENTERPRISE_APPROVAL_REVIEW_FOLLOWUP_STORAGE_KEY)
      return
    }
    window.localStorage.setItem(
      ENTERPRISE_APPROVAL_REVIEW_FOLLOWUP_STORAGE_KEY,
      JSON.stringify({
        ...nextValue,
        updated_at: nextValue.updated_at || new Date().toISOString()
      })
    )
  },
  { deep: true }
)

watch(
  [
    authAuthenticated,
    authCurrentRole,
    authCurrentAccountStatus,
    authCurrentEnterpriseApplication
  ],
  () => {
    if (!authAuthenticated.value || !authIsEnterpriseRole.value || !authCurrentEnterpriseApplication.value) return
    syncEnterpriseRegisterFollowupFromApplication(authCurrentEnterpriseApplication.value, authCurrentAccountStatus.value)
  },
  { deep: true }
)

function switchAuthDialogView(view) {
  authDialogView.value = ['login', 'personal-register', 'enterprise-register'].includes(view)
    ? view
    : 'login'
  if (authDialogView.value !== 'login') {
    authLoginRestrictionNotice.value = null
  }
}

function fillEnterpriseRegisterFormFromApplication(application = authCurrentEnterpriseApplication.value) {
  if (!application) return false
  const companyName = String(application?.company_name || authCurrentOrganizationName.value || '').trim()
  const contactName = String(application?.contact_name || '').trim()
  const contactEmail = String(application?.contact_email || '').trim()
  const username = String(application?.username || '').trim()
  if (!companyName && !contactName && !contactEmail && !username) return false
  authEnterpriseRegisterForm.value = {
    company_name: companyName,
    contact_name: contactName,
    contact_email: contactEmail,
    username,
    password: ''
  }
  return true
}

function useCurrentEnterpriseApplicationForRegisterDraft() {
  const hydrated = fillEnterpriseRegisterFormFromApplication(authCurrentEnterpriseApplication.value)
  if (!hydrated) {
    showFloatingToast(t('auth_enterprise_register_failed'), 'warning')
    return
  }
  switchAuthDialogView('enterprise-register')
  showFloatingToast(t('auth_enterprise_register_existing_used'), 'success')
}

function resumeEnterpriseRegistrationFromApplication(application = authCurrentEnterpriseApplication.value, { closeSettings = false } = {}) {
  const hydrated = fillEnterpriseRegisterFormFromApplication(application)
  if (!hydrated) {
    showFloatingToast(t('auth_enterprise_register_failed'), 'warning')
    return
  }
  authEnterpriseRegisterFollowup.value = null
  if (closeSettings) {
    closeEnterpriseSettingsDialog()
  }
  authPanelOpen.value = true
  switchAuthDialogView('enterprise-register')
  showFloatingToast(
    formatInlineMessage(t('enterprise_application_resume_registration_ok'), {
      company: String(application?.company_name || authCurrentOrganizationName.value || '—')
    }),
    'success'
  )
}

async function runAuthEnterpriseRegisterExistingPrimaryAction() {
  if (authCurrentAccountStatus.value === 'approved') {
    await openEnterpriseSettingsDialog()
    return
  }
  resumeEnterpriseRegistrationFromApplication(authCurrentEnterpriseApplication.value)
}

async function handleEnterpriseRegister() {
  const payload = authEnterpriseRegisterValidation.value.payload
  if (!authEnterpriseRegisterValidation.value.valid) {
    showFloatingToast(authEnterpriseRegisterValidation.value.firstMessage || t('auth_enterprise_register_failed'), 'warning')
    return
  }
  authEnterpriseRegisterLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/auth/register-enterprise`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise registration failed')
    }
    authUsername.value = payload.username
    authPassword.value = payload.password
    const application = data?.application || {}
    authEnterpriseRegisterFollowup.value = {
      company_name: application.company_name || payload.company_name,
      username: application.username || payload.username,
      contact_name: application.contact_name || payload.contact_name,
      contact_email: application.contact_email || payload.contact_email,
      submitted_at: application.submitted_at || null,
      status: application.status || 'pending',
      updated_at: new Date().toISOString()
    }
    switchAuthDialogView('login')
    showFloatingToast(
      formatInlineMessage(t('auth_enterprise_register_success'), {
        company: payload.company_name
      }),
      'success'
    )
    resetEnterpriseRegisterForm()
  } catch (error) {
    showFloatingToast(error?.message || t('auth_enterprise_register_failed'), 'error')
  } finally {
    authEnterpriseRegisterLoading.value = false
  }
}

async function signInEnterpriseRegisterFollowup() {
  if (!authEnterpriseRegisterFollowup.value) return
  await handleAuthLogin()
}

function continueEnterpriseRegisterFollowupEditing() {
  if (!authEnterpriseRegisterFollowup.value) return
  resumeEnterpriseRegistrationFromApplication(authEnterpriseRegisterFollowup.value)
}

function dismissEnterpriseRegisterFollowup() {
  if (!authEnterpriseRegisterFollowup.value) return
  authEnterpriseRegisterFollowup.value = null
  showFloatingToast(t('auth_enterprise_register_followup_dismissed'), 'info')
}

async function handlePersonalRegister() {
  const payload = authPersonalRegisterValidation.value.payload
  if (!authPersonalRegisterValidation.value.valid) {
    showFloatingToast(authPersonalRegisterValidation.value.firstMessage || t('auth_personal_register_failed'), 'warning')
    return
  }
  try {
    const state = await registerPersonalWithAuthSession(payload)
    authGuestAccepted.value = Boolean(state?.authenticated)
    authPanelOpen.value = false
    authDialogView.value = 'login'
    resetPersonalRegisterForm()
    showFloatingToast(
      formatInlineMessage(t('auth_personal_register_success'), {
        username: payload.username
      }),
      'success'
    )
  } catch (error) {
    showFloatingToast(error?.message || t('auth_personal_register_failed'), 'error')
  }
}

function syncEnterpriseRegisterFollowupFromApplication(application, statusFallback = authCurrentAccountStatus.value) {
  const currentFollowup = authEnterpriseRegisterFollowup.value
  const normalizedApplication = normalizeEnterpriseApplicationSnapshot(application, statusFallback)
  if (!currentFollowup || !normalizedApplication) return
  const followupUsername = String(currentFollowup.username || '').trim()
  if (followupUsername && normalizedApplication.username && followupUsername !== normalizedApplication.username) {
    return
  }
  const nextFollowup = {
    company_name: normalizedApplication.company_name || currentFollowup.company_name,
    username: normalizedApplication.username || currentFollowup.username,
    contact_name: normalizedApplication.contact_name || currentFollowup.contact_name,
    contact_email: normalizedApplication.contact_email || currentFollowup.contact_email,
    submitted_at: normalizedApplication.submitted_at || currentFollowup.submitted_at || null,
    status: normalizedApplication.status || currentFollowup.status || 'pending',
    updated_at: new Date().toISOString()
  }
  authEnterpriseRegisterFollowup.value = nextFollowup
}

function buildEnterpriseStatusFollowup(application, statusFallback = authCurrentAccountStatus.value) {
  const normalized = normalizeEnterpriseApplicationSnapshot(application, statusFallback)
  if (!normalized) return null
  return {
    ...normalized,
    updated_at: new Date().toISOString()
  }
}

function dismissEnterpriseStatusFollowup() {
  if (!authEnterpriseStatusFollowup.value) return
  authEnterpriseStatusFollowup.value = null
  showFloatingToast(t('auth_enterprise_status_followup_dismissed'), 'info')
}

function dismissEnterpriseApprovalReviewFollowup() {
  if (!enterpriseApprovalReviewFollowup.value) return
  enterpriseApprovalReviewFollowup.value = null
  showFloatingToast(t('enterprise_approval_followup_dismissed'), 'info')
}

async function refreshEnterpriseAccountStatus() {
  const previousStatus = String(authCurrentAccountStatus.value || 'approved')
  try {
    const state = await fetchAuthMe({ silent: false })
    authGuestAccepted.value = Boolean(state?.authenticated)
    const nextStatus = String(state?.user?.account_status || previousStatus)
    const nextApplication = normalizeEnterpriseApplicationSnapshot(
      state?.user?.enterprise_application,
      nextStatus
    )
    syncEnterpriseRegisterFollowupFromApplication(nextApplication, nextStatus)
    if (previousStatus !== nextStatus) {
      if (nextApplication && ['approved', 'rejected'].includes(nextStatus)) {
        authEnterpriseStatusFollowup.value = buildEnterpriseStatusFollowup(nextApplication, nextStatus)
      }
      showFloatingToast(t(`auth_account_status_refresh_${nextStatus}`), 'success')
      return
    }
    showFloatingToast(t('auth_account_status_refresh_ok'), 'success')
  } catch (error) {
    showFloatingToast(error?.message || t('auth_account_status_refresh_failed'), 'error')
  }
}

async function copyTextToClipboard(text) {
  const normalizedText = String(text || '')
  if (!normalizedText) return false
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(normalizedText)
      return true
    }
  } catch (error) {
    console.warn('Clipboard API write failed, fallback to textarea copy.', error)
  }
  try {
    const textarea = document.createElement('textarea')
    textarea.value = normalizedText
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    textarea.style.pointerEvents = 'none'
    document.body.appendChild(textarea)
    textarea.select()
    const copied = document.execCommand('copy')
    document.body.removeChild(textarea)
    return copied
  } catch (error) {
    console.error('Clipboard fallback copy failed:', error)
    return false
  }
}

async function copyEnterpriseApplicationUsername(application = authCurrentEnterpriseApplication.value) {
  const username = String(application?.username || '').trim()
  if (!username) return
  const copied = await copyTextToClipboard(username)
  if (copied) {
    showFloatingToast(
      formatInlineMessage(t('enterprise_application_copy_username_ok'), {
        company: String(application?.company_name || authCurrentOrganizationName.value || '—'),
        username
      }),
      'success'
    )
    return
  }
  showFloatingToast(t('enterprise_application_copy_username_failed'), 'error')
}

async function copyEnterpriseApplicationCompanyName(application = authCurrentEnterpriseApplication.value) {
  const companyName = String(application?.company_name || authCurrentOrganizationName.value || '').trim()
  if (!companyName) return
  const copied = await copyTextToClipboard(companyName)
  if (copied) {
    showFloatingToast(
      formatInlineMessage(t('enterprise_application_copy_company_name_ok'), {
        company: companyName
      }),
      'success'
    )
    return
  }
  showFloatingToast(t('enterprise_application_copy_company_name_failed'), 'error')
}

async function copyEnterpriseApplicationContactName(application = authCurrentEnterpriseApplication.value) {
  const contactName = String(application?.contact_name || '').trim()
  if (!contactName) return
  const copied = await copyTextToClipboard(contactName)
  if (copied) {
    showFloatingToast(
      formatInlineMessage(t('enterprise_application_copy_contact_name_ok'), {
        company: String(application?.company_name || authCurrentOrganizationName.value || '—'),
        contact: contactName
      }),
      'success'
    )
    return
  }
  showFloatingToast(t('enterprise_application_copy_contact_name_failed'), 'error')
}

function buildEnterpriseApplicationSummaryText(application = authCurrentEnterpriseApplication.value) {
  const lines = []
  const companyName = String(application?.company_name || authCurrentOrganizationName.value || '').trim()
  const contactName = String(application?.contact_name || '').trim()
  const contactEmail = String(application?.contact_email || '').trim()
  const username = String(application?.username || '').trim()
  const status = String(application?.status || authCurrentAccountStatus.value || '').trim()
  const submittedAt = String(application?.submitted_at || '').trim()
  const reviewedAt = String(application?.reviewed_at || '').trim()
  const reviewedBy = String(application?.reviewed_by || '').trim()
  const reviewNote = String(application?.review_note || '').trim()

  if (companyName) lines.push(`${t('enterprise_register_company_name')}: ${companyName}`)
  if (contactName) lines.push(`${t('enterprise_register_contact_name')}: ${contactName}`)
  if (contactEmail) lines.push(`${t('enterprise_register_contact_email')}: ${contactEmail}`)
  if (username) lines.push(`${t('enterprise_register_username')}: ${username}`)
  if (status) lines.push(`${t('enterprise_settings_summary_status')}: ${t(`enterprise_approval_status_${status}`)}`)
  if (submittedAt) lines.push(`${t('enterprise_settings_application_submitted_at')}: ${submittedAt}`)
  if (reviewedAt) lines.push(`${t('enterprise_settings_application_reviewed_at')}: ${reviewedAt}`)
  if (reviewedBy) lines.push(`${t('enterprise_settings_application_reviewed_by')}: ${reviewedBy}`)
  if (reviewNote) lines.push(`${t('enterprise_settings_application_review_note')}: ${reviewNote}`)

  return lines.join('\n')
}

async function copyEnterpriseApplicationSummary(application = authCurrentEnterpriseApplication.value) {
  const summaryText = buildEnterpriseApplicationSummaryText(application)
  if (!summaryText) return
  const copied = await copyTextToClipboard(summaryText)
  if (copied) {
    showFloatingToast(
      formatInlineMessage(t('enterprise_application_copy_summary_ok'), {
        company: String(application?.company_name || authCurrentOrganizationName.value || '—')
      }),
      'success'
    )
    return
  }
  showFloatingToast(t('enterprise_application_copy_summary_failed'), 'error')
}

async function copyEnterpriseApplicationReviewNote(application = authCurrentEnterpriseApplication.value) {
  const reviewNote = String(application?.review_note || '').trim()
  if (!reviewNote) return
  const copied = await copyTextToClipboard(reviewNote)
  if (copied) {
    showFloatingToast(
      formatInlineMessage(t('enterprise_application_copy_review_note_ok'), {
        company: String(application?.company_name || authCurrentOrganizationName.value || '—')
      }),
      'success'
    )
    return
  }
  showFloatingToast(t('enterprise_application_copy_review_note_failed'), 'error')
}

async function copyEnterpriseApplicationContactEmail(application = selectedEnterpriseApplication.value) {
  const email = String(application?.contact_email || '').trim()
  if (!email) return
  const copied = await copyTextToClipboard(email)
  if (copied) {
    showFloatingToast(
      formatInlineMessage(t('enterprise_application_copy_contact_email_ok'), {
        company: String(application?.company_name || authCurrentOrganizationName.value || '—'),
        email
      }),
      'success'
    )
    return
  }
  showFloatingToast(t('enterprise_application_copy_contact_email_failed'), 'error')
}

async function fetchEnterpriseApplications({ forceSelectFirst = false, preferredSelectedId = null } = {}) {
  if (!authCanEnterpriseApprove.value) return
  enterpriseApprovalLoading.value = true
  try {
    const response = await fetch(
      `${API_BASE}/auth/enterprise-applications?status=${encodeURIComponent(enterpriseApprovalStatusFilter.value || 'all')}`,
      {
        headers: buildAuthHeaders()
      }
    )
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise applications request failed')
    }
    enterpriseApplications.value = Array.isArray(data?.items) ? data.items : []
    enterpriseApprovalSummary.value = data?.summary ?? { all: 0, pending: 0, approved: 0, rejected: 0 }
    enterpriseApprovalLastFetchedAt.value = new Date().toISOString()
    if (preferredSelectedId != null && enterpriseApplications.value.some(item => Number(item.id) === Number(preferredSelectedId))) {
      selectedEnterpriseApplicationId.value = Number(preferredSelectedId)
    } else if (forceSelectFirst || !selectedEnterpriseApplication.value) {
      selectedEnterpriseApplicationId.value = enterpriseApplications.value[0]?.id ?? null
    } else if (!enterpriseApplications.value.some(item => Number(item.id) === Number(selectedEnterpriseApplicationId.value))) {
      selectedEnterpriseApplicationId.value = enterpriseApplications.value[0]?.id ?? null
    }
  } catch (error) {
    showFloatingToast(error?.message || t('enterprise_approval_load_failed'), 'error')
  } finally {
    enterpriseApprovalLoading.value = false
  }
}

async function openEnterpriseApprovalDialog({ status = '', selectedId = null, resetSearch = false, draftOnly = null } = {}) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'enterprise.approve', buildCapabilityDeniedMessage('platform'))) return
  enterpriseApprovalDialogOpen.value = true
  if (resetSearch) {
    enterpriseApprovalSearch.value = ''
  }
  if (draftOnly == null && (selectedId != null || String(status || '').trim())) {
    enterpriseApprovalDraftOnly.value = false
  }
  if (draftOnly != null) {
    enterpriseApprovalDraftOnly.value = Boolean(draftOnly)
  }
  enterpriseApprovalReviewNote.value = ''
  if (String(status || '').trim()) {
    enterpriseApprovalStatusFilter.value = String(status).trim()
  }
  await fetchEnterpriseApplications({ forceSelectFirst: selectedId == null, preferredSelectedId: selectedId })
}

async function openEnterpriseApprovalDialogForItem(applicationId, status = 'pending') {
  const normalizedId = Number(applicationId || 0)
  if (!normalizedId) {
    await openEnterpriseApprovalDialog({ status, draftOnly: false })
    return
  }
  await openEnterpriseApprovalDialog({ status, selectedId: normalizedId, draftOnly: false })
}

async function openEnterpriseApprovalDraftWorkspace(preferredSelectedId = null) {
  await openEnterpriseApprovalDialog({
    status: 'all',
    selectedId: preferredSelectedId,
    resetSearch: true,
    draftOnly: true
  })
}

function closeEnterpriseApprovalDialog() {
  enterpriseApprovalDialogOpen.value = false
  enterpriseApprovalReviewNote.value = ''
}

function resetEnterpriseApprovalFilters() {
  enterpriseApprovalStatusFilter.value = 'pending'
  enterpriseApprovalSearch.value = ''
  enterpriseApprovalDraftOnly.value = false
  selectedEnterpriseApplicationId.value = null
}

function setEnterpriseApprovalStatusFilter(nextStatus = 'all') {
  enterpriseApprovalStatusFilter.value = String(nextStatus || 'all')
}

function toggleEnterpriseApprovalDraftOnly() {
  enterpriseApprovalDraftOnly.value = !enterpriseApprovalDraftOnly.value
}

async function runEnterpriseApprovalEmptyStateAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'clear-draft-filter':
      enterpriseApprovalDraftOnly.value = false
      return
    case 'show-pending':
      await focusEnterpriseApprovalPendingQueue()
      return
    case 'show-all':
      enterpriseApprovalStatusFilter.value = 'all'
      enterpriseApprovalSearch.value = ''
      await fetchEnterpriseApplications({ forceSelectFirst: false })
      return
    default:
      return
  }
}

async function focusEnterpriseApprovalPendingQueue() {
  enterpriseApprovalStatusFilter.value = 'pending'
  enterpriseApprovalSearch.value = ''
  enterpriseApprovalDraftOnly.value = false
  await fetchEnterpriseApplications({ forceSelectFirst: true })
}

function selectEnterpriseApprovalByOffset(offset = 1) {
  if (!selectedEnterpriseApplication.value) return
  const nextIndex = selectedEnterpriseApplicationIndex.value + Number(offset || 0)
  if (nextIndex < 0 || nextIndex >= filteredEnterpriseApplications.value.length) return
  selectedEnterpriseApplicationId.value = filteredEnterpriseApplications.value[nextIndex]?.id ?? null
}

function selectPreviousEnterpriseApplication() {
  selectEnterpriseApprovalByOffset(-1)
}

function selectNextEnterpriseApplication() {
  selectEnterpriseApprovalByOffset(1)
}

function selectNextEnterpriseApprovalDraft() {
  const nextId = Number(nextEnterpriseApprovalDraftApplicationId.value || 0)
  if (!nextId) return
  selectedEnterpriseApplicationId.value = nextId
}

async function refreshEnterpriseApprovalSnapshot() {
  await fetchEnterpriseApplications({ forceSelectFirst: false })
}

function buildEnterpriseApprovalExportFilename(prefix = 'agv-enterprise-applications') {
  const statusPart = enterpriseApprovalStatusFilter.value && enterpriseApprovalStatusFilter.value !== 'all'
    ? enterpriseApprovalStatusFilter.value
    : 'all'
  const draftPart = enterpriseApprovalDraftOnly.value ? 'drafts' : 'allitems'
  const searchPart = String(enterpriseApprovalSearch.value || '').trim()
    ? 'search'
    : 'full'
  return `${prefix}-${statusPart}-${draftPart}-${searchPart}`
}

function buildEnterpriseApprovalExportPayload() {
  return filteredEnterpriseApplications.value.map(item => ({
    id: item.id,
    company_name: item.company_name,
    contact_name: item.contact_name,
    contact_email: item.contact_email,
    username: item.username,
    status: item.status,
    submitted_at: item.submitted_at || '',
    reviewed_at: item.reviewed_at || '',
    reviewed_by: item.reviewed_by || '',
    review_note: item.review_note || ''
  }))
}

function exportEnterpriseApplicationsJson() {
  const payload = buildEnterpriseApprovalExportPayload()
  if (!payload.length) {
    showFloatingToast(t('enterprise_approval_export_empty'), 'info')
    return
  }
  downloadJsonFile(
    `${buildEnterpriseApprovalExportFilename()}.json`,
    JSON.stringify(
        {
          exported_at: new Date().toISOString(),
          status_filter: enterpriseApprovalStatusFilter.value,
          draft_only: enterpriseApprovalDraftOnly.value,
          search: String(enterpriseApprovalSearch.value || '').trim(),
          items: payload
        },
      null,
      2
    )
  )
  showFloatingToast(t('enterprise_approval_export_json_ok'), 'success')
}

function exportEnterpriseApplicationsCsv() {
  const rows = buildEnterpriseApprovalExportPayload()
  if (!rows.length) {
    showFloatingToast(t('enterprise_approval_export_empty'), 'info')
    return
  }
  downloadCsvFile(`${buildEnterpriseApprovalExportFilename()}.csv`, rowsToCsv(rows))
  showFloatingToast(t('enterprise_approval_export_csv_ok'), 'success')
}

async function fetchManagedUserAccounts({ forceSelectFirst = false, preferredSelectedId = '' } = {}) {
  if (!authCanSystemManage.value) {
    managedUserAccounts.value = []
    accountGovernanceLastFetchedAt.value = ''
    return
  }
  if (accountGovernanceLoading.value) return
  accountGovernanceLoading.value = true
  try {
    const params = new URLSearchParams({
      role: accountGovernanceRoleFilter.value || 'all',
      status: accountGovernanceStatusFilter.value || 'all',
      search: String(accountGovernanceSearch.value || '').trim(),
      limit: '200'
    })
    const response = await fetch(`${API_BASE}/auth/users?${params.toString()}`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Managed user request failed')
    }
    managedUserAccounts.value = Array.isArray(data?.items) ? data.items : []
    accountGovernanceSummary.value = data?.summary ?? accountGovernanceSummary.value
    accountGovernanceLastFetchedAt.value = new Date().toISOString()
    selectedManagedUserIds.value = selectedManagedUserIds.value.filter(id =>
      managedUserAccounts.value.some(item => String(item.id || '') === String(id || ''))
    )
    const preferredId = String(preferredSelectedId || '')
    if (preferredId && managedUserAccounts.value.some(item => String(item.id || '') === preferredId)) {
      selectedManagedUserId.value = preferredId
    } else if (
      forceSelectFirst ||
      !managedUserAccounts.value.some(item => String(item.id || '') === String(selectedManagedUserId.value || ''))
    ) {
      selectedManagedUserId.value = String(managedUserAccounts.value[0]?.id || '')
    }
  } catch (error) {
    console.error('Fetch managed user accounts error:', error)
    showFloatingToast(error?.message || t('account_governance_fetch_failed'), 'error')
  } finally {
    accountGovernanceLoading.value = false
  }
}

async function openAccountGovernanceDialog({ role = '', status = '', selectedId = '', resetSearch = false } = {}) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'system.manage', buildCapabilityDeniedMessage('platform'))) return
  accountGovernanceDialogOpen.value = true
  if (resetSearch) {
    accountGovernanceSearch.value = ''
  }
  if (String(role || '').trim()) {
    accountGovernanceRoleFilter.value = String(role).trim()
  }
  if (String(status || '').trim()) {
    accountGovernanceStatusFilter.value = String(status).trim()
  }
  await fetchManagedUserAccounts({ forceSelectFirst: !String(selectedId || '').trim(), preferredSelectedId: selectedId })
}

function closeAccountGovernanceDialog() {
  if (accountGovernanceSearchTimer) {
    clearTimeout(accountGovernanceSearchTimer)
    accountGovernanceSearchTimer = null
  }
  resetAccountGovernanceActionDraft()
  selectedManagedUserIds.value = []
  accountGovernanceDialogOpen.value = false
}

function resetEnterpriseRequestDraft() {
  enterpriseRequestDraft.value = {
    category: 'request',
    title: '',
    content: '',
    target_user_id: String(enterpriseRequestRecipients.value[0]?.id || '')
  }
  enterpriseRequestResponseNote.value = ''
}

async function fetchEnterpriseRequestRecipients() {
  if (!authCanEnterpriseRequestSubmit.value) {
    enterpriseRequestRecipients.value = []
    return
  }
  const response = await fetch(`${API_BASE}/feedback/enterprise/recipients`, {
    headers: buildAuthorizedHeaders()
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw createApiError(data, 'Enterprise request recipients failed')
  }
  enterpriseRequestRecipients.value = Array.isArray(data?.items) ? data.items : []
  if (
    !enterpriseRequestDraft.value.target_user_id ||
    !enterpriseRequestRecipients.value.some(item => String(item.id || '') === String(enterpriseRequestDraft.value.target_user_id || ''))
  ) {
    enterpriseRequestDraft.value = {
      ...enterpriseRequestDraft.value,
      target_user_id: String(enterpriseRequestRecipients.value[0]?.id || '')
    }
  }
}

async function fetchEnterpriseRequests({ forceSelectFirst = false, preferredSelectedId = '' } = {}) {
  if (!authCanEnterpriseRequestSubmit.value) {
    enterpriseRequestItems.value = []
    enterpriseRequestSummary.value = { all: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 }
    enterpriseRequestLastFetchedAt.value = ''
    return
  }
  if (enterpriseRequestLoading.value) return
  enterpriseRequestLoading.value = true
  try {
    const params = new URLSearchParams({
      status: enterpriseRequestStatusFilter.value || 'all',
      category: enterpriseRequestCategoryFilter.value || 'all',
      search: String(enterpriseRequestSearch.value || '').trim(),
      limit: '120'
    })
    const response = await fetch(`${API_BASE}/feedback/enterprise/requests?${params.toString()}`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise request fetch failed')
    }
    enterpriseRequestItems.value = Array.isArray(data?.items) ? data.items : []
    enterpriseRequestSummary.value = data?.summary ?? enterpriseRequestSummary.value
    enterpriseRequestLastFetchedAt.value = new Date().toISOString()
    const preferredId = String(preferredSelectedId || '')
    if (preferredId && enterpriseRequestItems.value.some(item => String(item.id || '') === preferredId)) {
      selectedEnterpriseRequestId.value = preferredId
    } else if (
      forceSelectFirst ||
      !enterpriseRequestItems.value.some(item => String(item.id || '') === String(selectedEnterpriseRequestId.value || ''))
    ) {
      selectedEnterpriseRequestId.value = String(enterpriseRequestItems.value[0]?.id || '')
    }
  } catch (error) {
    console.error('Fetch enterprise requests error:', error)
    showFloatingToast(error?.message || t('enterprise_request_fetch_failed'), 'error')
  } finally {
    enterpriseRequestLoading.value = false
  }
}

async function openEnterpriseRequestDialog({ status = '', category = '', selectedId = '' } = {}) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'feedback.enterprise.submit', t('enterprise_request_requires_enterprise'))) return
  enterpriseRequestDialogOpen.value = true
  if (String(status || '').trim()) enterpriseRequestStatusFilter.value = String(status).trim()
  if (String(category || '').trim()) enterpriseRequestCategoryFilter.value = String(category).trim()
  try {
    await fetchEnterpriseRequestRecipients()
    await fetchEnterpriseRequests({ forceSelectFirst: !String(selectedId || '').trim(), preferredSelectedId: selectedId })
    if (!enterpriseRequestDraft.value.target_user_id) {
      enterpriseRequestDraft.value = {
        ...enterpriseRequestDraft.value,
        target_user_id: String(enterpriseRequestRecipients.value[0]?.id || '')
      }
    }
  } catch (error) {
    console.error('Open enterprise request dialog error:', error)
    showFloatingToast(error?.message || t('enterprise_request_fetch_failed'), 'error')
  }
}

function closeEnterpriseRequestDialog() {
  enterpriseRequestDialogOpen.value = false
  enterpriseRequestResponseNote.value = ''
}

function resetEnterpriseRequestFilters() {
  enterpriseRequestStatusFilter.value = 'all'
  enterpriseRequestCategoryFilter.value = 'all'
  enterpriseRequestSearch.value = ''
}

async function submitEnterpriseRequest() {
  if (!authCanEnterpriseRequestSubmit.value) return
  const payload = {
    category: String(enterpriseRequestDraft.value.category || '').trim() || 'request',
    title: String(enterpriseRequestDraft.value.title || '').trim(),
    content: String(enterpriseRequestDraft.value.content || '').trim(),
    target_user_id: String(enterpriseRequestDraft.value.target_user_id || '').trim()
  }
  if (!payload.title || !payload.content || !payload.target_user_id) {
    showFloatingToast(t('enterprise_request_fields_required'), 'error')
    return
  }
  enterpriseRequestActionLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/feedback/enterprise/requests`, {
      method: 'POST',
      headers: buildAuthorizedHeaders({
        'Content-Type': 'application/json'
      }),
      body: JSON.stringify(payload)
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise request create failed')
    }
    resetEnterpriseRequestDraft()
    await fetchEnterpriseRequests({ forceSelectFirst: true, preferredSelectedId: data?.item?.id })
    showFloatingToast(t('enterprise_request_submit_ok'), 'success')
  } catch (error) {
    console.error('Submit enterprise request error:', error)
    showFloatingToast(error?.message || t('enterprise_request_submit_failed'), 'error')
  } finally {
    enterpriseRequestActionLoading.value = false
  }
}

async function updateSelectedEnterpriseRequestStatus(status) {
  if (!selectedEnterpriseRequest.value || !enterpriseRequestCanManageSelected.value) return
  enterpriseRequestActionLoading.value = true
  try {
    const response = await fetch(
      `${API_BASE}/feedback/enterprise/requests/${encodeURIComponent(selectedEnterpriseRequest.value.id)}/status`,
      {
        method: 'POST',
        headers: buildAuthorizedHeaders({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify({
          status,
          response_note: String(enterpriseRequestResponseNote.value || '').trim() || null
        })
      }
    )
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise request update failed')
    }
    enterpriseRequestResponseNote.value = String(data?.item?.response_note || '')
    await fetchEnterpriseRequests({ forceSelectFirst: false, preferredSelectedId: selectedEnterpriseRequest.value.id })
    showFloatingToast(t('enterprise_request_status_update_ok'), 'success')
  } catch (error) {
    console.error('Update enterprise request status error:', error)
    showFloatingToast(error?.message || t('enterprise_request_status_update_failed'), 'error')
  } finally {
    enterpriseRequestActionLoading.value = false
  }
}

async function fetchPlatformBugFeedback({ forceSelectFirst = false, preferredSelectedId = '' } = {}) {
  if (!authCanPlatformBugSubmit.value && !authCanPlatformBugManage.value) {
    platformBugFeedbackItems.value = []
    platformBugFeedbackSummary.value = { all: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 }
    platformBugFeedbackLastFetchedAt.value = ''
    platformBugFeedbackManagementMode.value = false
    return
  }
  if (platformBugFeedbackLoading.value) return
  platformBugFeedbackLoading.value = true
  try {
    const params = new URLSearchParams({
      status: platformBugFeedbackStatusFilter.value || 'all',
      category: platformBugFeedbackCategoryFilter.value || 'all',
      search: String(platformBugFeedbackSearch.value || '').trim(),
      limit: '120'
    })
    const response = await fetch(`${API_BASE}/feedback/platform-bugs?${params.toString()}`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Platform bug feedback fetch failed')
    }
    platformBugFeedbackItems.value = Array.isArray(data?.items) ? data.items : []
    platformBugFeedbackSummary.value = data?.summary ?? platformBugFeedbackSummary.value
    platformBugFeedbackManagementMode.value = Boolean(data?.management)
    platformBugFeedbackLastFetchedAt.value = new Date().toISOString()
    const preferredId = String(preferredSelectedId || '')
    if (preferredId && platformBugFeedbackItems.value.some(item => String(item.id || '') === preferredId)) {
      selectedPlatformBugFeedbackId.value = preferredId
    } else if (
      forceSelectFirst ||
      !platformBugFeedbackItems.value.some(item => String(item.id || '') === String(selectedPlatformBugFeedbackId.value || ''))
    ) {
      selectedPlatformBugFeedbackId.value = String(platformBugFeedbackItems.value[0]?.id || '')
    }
  } catch (error) {
    console.error('Fetch platform bug feedback error:', error)
    showFloatingToast(error?.message || t('platform_bug_feedback_fetch_failed'), 'error')
  } finally {
    platformBugFeedbackLoading.value = false
  }
}

async function openPlatformBugFeedbackDialog({ status = '', category = '', selectedId = '' } = {}) {
  if (!authAuthenticated.value) {
    authPanelOpen.value = true
    showFloatingToast(t('auth_action_requires_login'), 'warning')
    return
  }
  if (!authCanUsePlatformBugFeedback.value) {
    authPanelOpen.value = true
    showFloatingToast(t('auth_permission_denied'), 'warning')
    return
  }
  platformBugFeedbackDialogOpen.value = true
  if (String(status || '').trim()) platformBugFeedbackStatusFilter.value = String(status).trim()
  if (String(category || '').trim()) platformBugFeedbackCategoryFilter.value = String(category).trim()
  await fetchPlatformBugFeedback({ forceSelectFirst: !String(selectedId || '').trim(), preferredSelectedId: selectedId })
}

function closePlatformBugFeedbackDialog() {
  platformBugFeedbackDialogOpen.value = false
  platformBugFeedbackResponseNote.value = ''
}

function resetPlatformBugFeedbackFilters() {
  platformBugFeedbackStatusFilter.value = 'all'
  platformBugFeedbackCategoryFilter.value = 'all'
  platformBugFeedbackSearch.value = ''
}

async function submitPlatformBugFeedback() {
  const payload = {
    category: String(platformBugFeedbackDraft.value.category || '').trim() || 'ui',
    title: String(platformBugFeedbackDraft.value.title || '').trim(),
    content: String(platformBugFeedbackDraft.value.content || '').trim()
  }
  if (!payload.title || !payload.content) {
    showFloatingToast(t('platform_bug_feedback_fields_required'), 'error')
    return
  }
  platformBugFeedbackActionLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/feedback/platform-bugs`, {
      method: 'POST',
      headers: buildAuthorizedHeaders({
        'Content-Type': 'application/json'
      }),
      body: JSON.stringify(payload)
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Platform bug feedback create failed')
    }
    platformBugFeedbackDraft.value = {
      category: 'ui',
      title: '',
      content: ''
    }
    await fetchPlatformBugFeedback({ forceSelectFirst: true, preferredSelectedId: data?.item?.id })
    showFloatingToast(t('platform_bug_feedback_submit_ok'), 'success')
  } catch (error) {
    console.error('Submit platform bug feedback error:', error)
    showFloatingToast(error?.message || t('platform_bug_feedback_submit_failed'), 'error')
  } finally {
    platformBugFeedbackActionLoading.value = false
  }
}

async function updateSelectedPlatformBugFeedbackStatus(status) {
  if (!selectedPlatformBugFeedback.value || !platformBugFeedbackCanManageSelected.value) return
  platformBugFeedbackActionLoading.value = true
  try {
    const response = await fetch(
      `${API_BASE}/feedback/platform-bugs/${encodeURIComponent(selectedPlatformBugFeedback.value.id)}/status`,
      {
        method: 'POST',
        headers: buildAuthorizedHeaders({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify({
          status,
          response_note: String(platformBugFeedbackResponseNote.value || '').trim() || null
        })
      }
    )
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Platform bug feedback update failed')
    }
    platformBugFeedbackResponseNote.value = String(data?.item?.response_note || '')
    await fetchPlatformBugFeedback({ forceSelectFirst: false, preferredSelectedId: selectedPlatformBugFeedback.value.id })
    showFloatingToast(t('platform_bug_feedback_status_update_ok'), 'success')
  } catch (error) {
    console.error('Update platform bug feedback status error:', error)
    showFloatingToast(error?.message || t('platform_bug_feedback_status_update_failed'), 'error')
  } finally {
    platformBugFeedbackActionLoading.value = false
  }
}

function resetAccountGovernanceFilters() {
  accountGovernanceRoleFilter.value = 'all'
  accountGovernanceStatusFilter.value = 'all'
  accountGovernanceSearch.value = ''
}

function enterPlatformAdminGovernanceMode() {
  platformAdminSurfaceMode.value = 'governance'
  enterpriseSettingsDialogOpen.value = false
  enterprisePageSettingsDialogOpen.value = false
  enterpriseMapEditorDialogOpen.value = false
}

function enterPlatformAdminPersonalPreviewMode() {
  if (!isPlatformAdmin.value) return
  platformAdminSurfaceMode.value = 'personal'
  enterpriseSettingsDialogOpen.value = false
  enterprisePageSettingsDialogOpen.value = false
}

function enterPlatformAdminEnterprisePreviewMode(role = 'enterprise_admin') {
  if (!isPlatformAdmin.value) return
  const normalizedRole = ['enterprise_admin', 'enterprise_operator', 'enterprise_logistics'].includes(role)
    ? role
    : 'enterprise_admin'
  platformAdminEnterprisePreviewRole.value = normalizedRole
  platformAdminSurfaceMode.value = 'enterprise'
  enterpriseSettingsDialogOpen.value = false
  enterprisePageSettingsDialogOpen.value = false
  applyEnterprisePanelPreset(normalizedRole, { silent: true })
}

function toggleManagedUserSelection(userId, forceValue = null) {
  const normalizedId = String(userId || '').trim()
  if (!normalizedId) return
  const current = new Set(selectedManagedUserIds.value.map(item => String(item || '')))
  const nextChecked = forceValue === null ? !current.has(normalizedId) : Boolean(forceValue)
  if (nextChecked) {
    current.add(normalizedId)
  } else {
    current.delete(normalizedId)
  }
  selectedManagedUserIds.value = Array.from(current)
}

function selectAllManagedUsers() {
  selectedManagedUserIds.value = managedUserAccounts.value.map(item => String(item.id || '')).filter(Boolean)
}

function clearSelectedManagedUsers() {
  selectedManagedUserIds.value = []
}

function buildManagedUserExportFilename(prefix = 'agv-managed-accounts') {
  return `${prefix}-${accountGovernanceRoleFilter.value || 'all'}-${accountGovernanceStatusFilter.value || 'all'}-${
    String(accountGovernanceSearch.value || '').trim() ? 'search' : 'full'
  }`
}

function buildManagedUserExportRows(items = managedUserAccounts.value) {
  return items.map(item => ({
    id: item.id,
    username: item.username,
    display_name: item.display_name || '',
    role: item.role,
    active: item.active !== false,
    builtin: item.builtin !== false,
    organization_id: item.organization_id || '',
    organization_name: item.organization_name || '',
    account_status: item.account_status || 'approved',
    created_at: item.created_at || '',
    last_login_at: item.last_login_at || '',
    governance_updated_at: item.governance_updated_at || '',
    suspended_at: item.suspended_at || '',
    suspended_until: item.suspended_until || '',
    suspended_by: item.suspended_by || '',
    suspension_reason: item.suspension_reason || '',
    suspension_note: item.suspension_note || '',
    deactivated_at: item.deactivated_at || '',
    deactivated_by: item.deactivated_by || '',
    enterprise_application_status: item.enterprise_application?.status || '',
    enterprise_application_submitted_at: item.enterprise_application?.submitted_at || '',
    enterprise_application_reviewed_at: item.enterprise_application?.reviewed_at || '',
    enterprise_contact_email: item.enterprise_application?.contact_email || '',
    enterprise_review_note: item.enterprise_application?.review_note || ''
  }))
}

function resetAccountGovernanceActionDraft() {
  accountGovernanceSelectedTemplateKey.value = ''
  accountGovernanceSuspendReason.value = ''
  accountGovernanceSuspendNote.value = ''
  accountGovernanceSuspendDurationPreset.value = '7d'
}

function applyAccountGovernanceActionTemplate(templateKey) {
  const matched = accountGovernanceActionTemplateItems.value.find(item => item.key === templateKey)
  if (!matched) return
  accountGovernanceSelectedTemplateKey.value = matched.key
  accountGovernanceSuspendReason.value = matched.reason
  accountGovernanceSuspendNote.value = matched.note
  accountGovernanceSuspendDurationPreset.value = matched.duration
}

function buildAuthLoginRestrictionNotice(detail) {
  const errorCode = String(detail?.error_code || '')
  if (!['auth_account_suspended', 'auth_account_deactivated'].includes(errorCode)) return null
  const reason = String(detail?.reason || '').trim()
  const note = String(detail?.note || '').trim()
  const suspendedUntil = String(detail?.suspended_until || '').trim()
  const meta = errorCode === 'auth_account_suspended'
    ? (
        suspendedUntil
          ? formatInlineMessage(t('auth_login_restriction_until'), { at: suspendedUntil })
          : t('auth_login_restriction_permanent')
      )
    : ''
  const detailParts = []
  if (reason) {
    detailParts.push(formatInlineMessage(t('auth_login_restriction_reason'), { reason }))
  }
  if (note) {
    detailParts.push(formatInlineMessage(t('auth_login_restriction_note'), { note }))
  }
  return {
    tone: errorCode === 'auth_account_suspended' ? 'rejected' : 'platform',
    title: errorCode === 'auth_account_suspended'
      ? t('auth_login_restriction_suspended_title')
      : t('auth_login_restriction_deactivated_title'),
    hint: errorCode === 'auth_account_suspended'
      ? t('auth_login_restriction_suspended_hint')
      : t('auth_login_restriction_deactivated_hint'),
    meta,
    detail: detailParts.join(' · ')
  }
}

function buildAuthSessionRefreshNotice(previousUser = null) {
  const username = String(previousUser?.username || '').trim()
  return {
    tone: 'platform',
    title: t('auth_session_refresh_title'),
    hint: t('auth_session_refresh_hint'),
    meta: username
      ? formatInlineMessage(t('auth_session_refresh_meta'), { username })
      : '',
    detail: ''
  }
}

async function syncAuthGovernanceState() {
  if (authGovernanceSyncTimer === null || authLoading.value || !authInitialized.value || !authAuthenticated.value) return
  const wasAuthenticated = Boolean(authAuthenticated.value)
  const previousUser = wasAuthenticated
    ? {
        id: String(authCurrentUser.value?.id || ''),
        username: String(authCurrentUser.value?.username || ''),
        account_status: String(authCurrentAccountStatus.value || '')
      }
    : null
  const previousGovernanceUpdatedAt = String(authCurrentUser.value?.governance_updated_at || '')
  let nextState = null
  try {
    nextState = await fetchAuthMe({ silent: false, preserveOnFailure: true })
  } catch (error) {
    if (wasAuthenticated && [401, 403].includes(Number(error?.status || 0))) {
      resetAuthStateWithAuthSession()
      authPanelOpen.value = true
      switchAuthDialogView('login')
      authLoginRestrictionNotice.value = buildAuthSessionRefreshNotice(previousUser)
      showFloatingToast(t('auth_session_refresh_toast'), 'info')
    }
    return
  }
  const isAuthenticated = Boolean(nextState?.authenticated)
  const nextGovernanceUpdatedAt = String(nextState?.user?.governance_updated_at || '')
  const nextStatus = String(nextState?.user?.account_status || '')
  if (wasAuthenticated && !isAuthenticated) {
    authPanelOpen.value = true
    switchAuthDialogView('login')
    authLoginRestrictionNotice.value = buildAuthSessionRefreshNotice(previousUser)
    showFloatingToast(t('auth_session_refresh_toast'), 'info')
    return
  }
  if (
    wasAuthenticated &&
    isAuthenticated &&
    previousGovernanceUpdatedAt &&
    nextGovernanceUpdatedAt &&
    previousGovernanceUpdatedAt !== nextGovernanceUpdatedAt
  ) {
    const nextUsername = String(nextState?.user?.username || '')
    const previousStatus = String(previousUser?.account_status || '')
    if (nextStatus !== previousStatus && nextUsername === previousUser?.username) {
      showFloatingToast(
        formatInlineMessage(t('auth_session_status_changed_toast'), {
          status: t(`auth_account_status_${nextStatus}`)
        }),
        'info'
      )
    } else {
      showFloatingToast(t('auth_session_refresh_updated_toast'), 'info')
    }
  }
}

async function exportManagedUserAccounts(format = 'json') {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'system.manage', buildCapabilityDeniedMessage('platform'))) return
  const params = new URLSearchParams({
    role: accountGovernanceRoleFilter.value || 'all',
    status: accountGovernanceStatusFilter.value || 'all',
    search: String(accountGovernanceSearch.value || '').trim()
  })
  try {
    const response = await fetch(`${API_BASE}/auth/users/export?${params.toString()}`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Managed user export failed')
    }
    const items = Array.isArray(data?.items) ? data.items : []
    if (!items.length) {
      showFloatingToast(t('account_governance_export_empty'), 'info')
      return
    }
    const rows = buildManagedUserExportRows(items)
    if (format === 'csv') {
      downloadCsvFile(`${buildManagedUserExportFilename()}.csv`, rowsToCsv(rows))
      showFloatingToast(t('account_governance_export_csv_ok'), 'success')
      return
    }
    downloadJsonFile(
      `${buildManagedUserExportFilename()}.json`,
      JSON.stringify(
        {
          exported_at: data?.exported_at || new Date().toISOString(),
          role_filter: data?.role || accountGovernanceRoleFilter.value,
          status_filter: data?.status || accountGovernanceStatusFilter.value,
          search: data?.search || String(accountGovernanceSearch.value || '').trim(),
          summary: data?.summary || accountGovernanceSummary.value,
          items: rows
        },
        null,
        2
      )
    )
    showFloatingToast(t('account_governance_export_json_ok'), 'success')
  } catch (error) {
    showFloatingToast(error?.message || t('account_governance_export_failed'), 'error')
  }
}

async function suspendManagedUserAccount() {
  const target = selectedManagedUser.value
  if (!target) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'system.manage', buildCapabilityDeniedMessage('platform'))) return
  accountGovernanceActionLoading.value = true
  try {
    const durationMap = {
      '1d': { duration_days: 1, permanent: false },
      '7d': { duration_days: 7, permanent: false },
      '30d': { duration_days: 30, permanent: false },
      permanent: { duration_days: null, permanent: true }
    }
    const durationPayload = durationMap[accountGovernanceSuspendDurationPreset.value] || durationMap['7d']
    const response = await fetch(`${API_BASE}/auth/users/${encodeURIComponent(target.id)}/suspend`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        reason: String(accountGovernanceSuspendReason.value || '').trim(),
        note: String(accountGovernanceSuspendNote.value || '').trim(),
        duration_days: durationPayload.duration_days,
        permanent: durationPayload.permanent
      })
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Suspend managed user failed')
    }
    resetAccountGovernanceActionDraft()
    await fetchManagedUserAccounts({ forceSelectFirst: false, preferredSelectedId: target.id })
    showFloatingToast(
      formatInlineMessage(t('account_governance_suspend_ok'), {
        username: target.username || target.display_name || target.id
      }),
      'success'
    )
  } catch (error) {
    showFloatingToast(error?.message || t('account_governance_action_failed'), 'error')
  } finally {
    accountGovernanceActionLoading.value = false
  }
}

async function unsuspendManagedUserAccount() {
  const target = selectedManagedUser.value
  if (!target) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'system.manage', buildCapabilityDeniedMessage('platform'))) return
  accountGovernanceActionLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/auth/users/${encodeURIComponent(target.id)}/unsuspend`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Unsuspend managed user failed')
    }
    await fetchManagedUserAccounts({ forceSelectFirst: false, preferredSelectedId: target.id })
    showFloatingToast(
      formatInlineMessage(t('account_governance_unsuspend_ok'), {
        username: target.username || target.display_name || target.id
      }),
      'success'
    )
  } catch (error) {
    showFloatingToast(error?.message || t('account_governance_action_failed'), 'error')
  } finally {
    accountGovernanceActionLoading.value = false
  }
}

async function deactivateManagedUserAccount() {
  const target = selectedManagedUser.value
  if (!target) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'system.manage', buildCapabilityDeniedMessage('platform'))) return
  accountGovernanceActionLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/auth/users/${encodeURIComponent(target.id)}/deactivate`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        reason: String(accountGovernanceSuspendReason.value || '').trim(),
        note: String(accountGovernanceSuspendNote.value || '').trim()
      })
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Deactivate managed user failed')
    }
    await fetchManagedUserAccounts({ forceSelectFirst: false, preferredSelectedId: target.id })
    showFloatingToast(
      formatInlineMessage(t('account_governance_deactivate_ok'), {
        username: target.username || target.display_name || target.id
      }),
      'success'
    )
  } catch (error) {
    showFloatingToast(error?.message || t('account_governance_action_failed'), 'error')
  } finally {
    accountGovernanceActionLoading.value = false
  }
}

async function runManagedUserBulkAction(action = 'suspend') {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'system.manage', buildCapabilityDeniedMessage('platform'))) return
  const targetUsers = (
    action === 'unsuspend'
      ? accountGovernanceBulkUnsuspendableUsers.value
      : action === 'deactivate'
        ? accountGovernanceBulkDeactivatableUsers.value
        : accountGovernanceBulkSuspendableUsers.value
  )
  if (!targetUsers.length) {
    showFloatingToast(t('account_governance_bulk_none_eligible'), 'info')
    return
  }
  const count = targetUsers.length
  const confirmKey = action === 'unsuspend'
    ? 'account_governance_bulk_unsuspend_confirm'
    : action === 'deactivate'
      ? 'account_governance_bulk_deactivate_confirm'
      : 'account_governance_bulk_suspend_confirm'
  if (!window.confirm(formatInlineMessage(t(confirmKey), { count }))) return

  const durationMap = {
    '1d': { duration_days: 1, permanent: false },
    '7d': { duration_days: 7, permanent: false },
    '30d': { duration_days: 30, permanent: false },
    permanent: { duration_days: null, permanent: true }
  }
  const durationPayload = durationMap[accountGovernanceSuspendDurationPreset.value] || durationMap['7d']
  const failedUsers = []
  let successCount = 0
  accountGovernanceActionLoading.value = true
  try {
    for (const item of targetUsers) {
      try {
        let response
        if (action === 'unsuspend') {
          response = await fetch(`${API_BASE}/auth/users/${encodeURIComponent(item.id)}/unsuspend`, {
            method: 'POST',
            headers: buildAuthorizedHeaders()
          })
        } else if (action === 'deactivate') {
          response = await fetch(`${API_BASE}/auth/users/${encodeURIComponent(item.id)}/deactivate`, {
            method: 'POST',
            headers: buildAuthorizedJsonHeaders(),
            body: JSON.stringify({
              reason: String(accountGovernanceSuspendReason.value || '').trim(),
              note: String(accountGovernanceSuspendNote.value || '').trim()
            })
          })
        } else {
          response = await fetch(`${API_BASE}/auth/users/${encodeURIComponent(item.id)}/suspend`, {
            method: 'POST',
            headers: buildAuthorizedJsonHeaders(),
            body: JSON.stringify({
              reason: String(accountGovernanceSuspendReason.value || '').trim(),
              note: String(accountGovernanceSuspendNote.value || '').trim(),
              duration_days: durationPayload.duration_days,
              permanent: durationPayload.permanent
            })
          })
        }
        const data = await response.json().catch(() => null)
        if (!response.ok) {
          throw createApiError(data, `Managed user bulk ${action} failed`)
        }
        successCount += 1
      } catch (error) {
        failedUsers.push(item.display_name || item.username || item.id)
        console.error(`Managed user bulk ${action} error:`, error)
      }
    }
    await fetchManagedUserAccounts({ forceSelectFirst: false, preferredSelectedId: selectedManagedUserId.value })
    if (!successCount) {
      showFloatingToast(t('account_governance_bulk_none_eligible'), 'warning')
      return
    }
    clearSelectedManagedUsers()
    resetAccountGovernanceActionDraft()
    const successKey = action === 'unsuspend'
      ? 'account_governance_bulk_unsuspend_ok'
      : action === 'deactivate'
        ? 'account_governance_bulk_deactivate_ok'
        : 'account_governance_bulk_suspend_ok'
    if (failedUsers.length) {
      showFloatingToast(
        formatInlineMessage(t('account_governance_bulk_partial'), {
          ok: successCount,
          failed: failedUsers.slice(0, 3).join(' / ')
        }),
        'warning'
      )
      return
    }
    showFloatingToast(formatInlineMessage(t(successKey), { count: successCount }), 'success')
  } finally {
    accountGovernanceActionLoading.value = false
  }
}

function saveEnterpriseApprovalUiState() {
  if (typeof window === 'undefined' || !window.localStorage) return
  window.localStorage.setItem(
    ENTERPRISE_APPROVAL_UI_STORAGE_KEY,
      JSON.stringify({
        status: enterpriseApprovalStatusFilter.value,
        search: String(enterpriseApprovalSearch.value || ''),
        draftOnly: enterpriseApprovalDraftOnly.value,
        selectedId: selectedEnterpriseApplicationId.value ?? null,
        noteDrafts: enterpriseApprovalNoteDrafts.value
      })
  )
}

function hasEnterpriseApprovalDraft(applicationId) {
  const normalizedId = Number(applicationId || 0)
  if (!normalizedId) return false
  return Boolean(String(enterpriseApprovalNoteDrafts.value[String(normalizedId)]?.text || '').trim())
}

function clearEnterpriseApprovalCurrentDraft() {
  const applicationId = Number(selectedEnterpriseApplicationId.value || 0)
  if (!applicationId || !hasEnterpriseApprovalDraft(applicationId)) return
  const nextDrafts = { ...enterpriseApprovalNoteDrafts.value }
  delete nextDrafts[String(applicationId)]
  enterpriseApprovalNoteDrafts.value = nextDrafts
  enterpriseApprovalReviewNote.value = ''
  showFloatingToast(t('enterprise_approval_clear_current_draft_ok'), 'info')
}

function clearAllEnterpriseApprovalDrafts() {
  if (!enterpriseApprovalDraftCount.value) return
  enterpriseApprovalNoteDrafts.value = {}
  enterpriseApprovalReviewNote.value = ''
  showFloatingToast(t('enterprise_approval_clear_all_drafts_ok'), 'info')
}

function preferredEnterpriseSettingsTab(role = enterpriseUiRole.value) {
  if (role === 'enterprise_operator') return 'runtime'
  if (role === 'enterprise_logistics') return 'map_profiles'
  if (role === 'enterprise_admin') return 'audit'
  return 'overview'
}

function loadEnterpriseSettingsTabPreference(role = enterpriseUiRole.value) {
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_SETTINGS_TAB_STORAGE_KEY)
    if (!raw) return ''
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return ''
    const saved = String(parsed[String(role || '')] || '').trim()
    return enterpriseSettingsTabKeys.value.includes(saved) ? saved : ''
  } catch (error) {
    console.error('Load enterprise settings tab preference error:', error)
    return ''
  }
}

function loadEnterpriseSettingsSidebarPreference() {
  try {
    const raw = window.localStorage.getItem(ENTERPRISE_SETTINGS_SIDEBAR_STORAGE_KEY)
    if (!raw) return false
    const parsed = JSON.parse(raw)
    return Boolean(parsed?.collapsed)
  } catch (error) {
    console.error('Load enterprise settings sidebar preference error:', error)
    return false
  }
}

function saveEnterpriseSettingsSidebarPreference(collapsed = enterpriseSettingsSidebarCollapsed.value) {
  try {
    window.localStorage.setItem(
      ENTERPRISE_SETTINGS_SIDEBAR_STORAGE_KEY,
      JSON.stringify({ collapsed: Boolean(collapsed) })
    )
  } catch (error) {
    console.error('Save enterprise settings sidebar preference error:', error)
  }
}

function saveEnterpriseSettingsTabPreference(role = enterpriseUiRole.value, tab = enterpriseSettingsActiveTab.value) {
  try {
    const normalizedRole = String(role || '').trim()
    const normalizedTab = String(tab || '').trim()
    if (!normalizedRole || !enterpriseSettingsTabKeys.value.includes(normalizedTab)) return
    const raw = window.localStorage.getItem(ENTERPRISE_SETTINGS_TAB_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : {}
    const next = parsed && typeof parsed === 'object' ? { ...parsed } : {}
    next[normalizedRole] = normalizedTab
    window.localStorage.setItem(ENTERPRISE_SETTINGS_TAB_STORAGE_KEY, JSON.stringify(next))
  } catch (error) {
    console.error('Save enterprise settings tab preference error:', error)
  }
}

function loadShortcutBindingsForScope(scopeKey = shortcutPreferenceScopeKey.value) {
  const payload = readShortcutPreferencePayload()
  const normalizedScope = String(scopeKey || 'guest')
  if (!Object.prototype.hasOwnProperty.call(payload, normalizedScope)) {
    return normalizeEditableShortcutConfig(DEFAULT_EDITABLE_SHORTCUTS)
  }
  return normalizeEditableShortcutConfig(payload?.[normalizedScope], { allowEmpty: true })
}

function persistShortcutBindingsForScope(config, scopeKey = shortcutPreferenceScopeKey.value) {
  if (typeof window === 'undefined' || !window.localStorage) return
  try {
    const payload = readShortcutPreferencePayload()
    payload[String(scopeKey || 'guest')] = normalizeEditableShortcutConfig(config, { allowEmpty: true })
    window.localStorage.setItem(SHORTCUT_PREFERENCES_STORAGE_KEY, JSON.stringify(payload))
  } catch (error) {
    console.error('Save shortcut preferences error:', error)
  }
}

function resetShortcutEditorDraftStatus(message = '', type = 'info') {
  shortcutEditorStatus.value = message
  shortcutEditorStatusType.value = type
}

function startShortcutCapture(actionKey) {
  if (!shortcutEditorCanEdit.value) return
  shortcutEditorCaptureActionKey.value = String(actionKey || '')
  resetShortcutEditorDraftStatus(t('shortcut_editor_capture_hint'), 'info')
}

function stopShortcutCapture() {
  shortcutEditorCaptureActionKey.value = ''
}

function applyCapturedShortcutKey(actionKey, keyValue) {
  const normalizedActionKey = String(actionKey || '')
  if (!normalizedActionKey) return
  const normalizedKey = normalizeShortcutKeyValue(keyValue)
  if (!normalizedKey) return
  if (normalizedKey === 'P') {
    resetShortcutEditorDraftStatus(t('shortcut_editor_reserved_key'), 'error')
    return
  }
  shortcutEditorDraft.value = {
    ...shortcutEditorDraft.value,
    [normalizedActionKey]: normalizedKey
  }
  shortcutEditorCaptureActionKey.value = ''
  resetShortcutEditorDraftStatus('', 'info')
}

function restoreShortcutEditorActionDefault(actionKey) {
  const normalizedActionKey = String(actionKey || '')
  if (!normalizedActionKey) return
  shortcutEditorDraft.value = {
    ...shortcutEditorDraft.value,
    [normalizedActionKey]: DEFAULT_EDITABLE_SHORTCUTS[normalizedActionKey] || ''
  }
  if (shortcutEditorCaptureActionKey.value === normalizedActionKey) {
    shortcutEditorCaptureActionKey.value = ''
  }
  resetShortcutEditorDraftStatus(t('shortcut_editor_item_restored'), 'info')
}

function clearShortcutEditorActionBinding(actionKey) {
  const normalizedActionKey = String(actionKey || '')
  if (!normalizedActionKey) return
  shortcutEditorDraft.value = {
    ...shortcutEditorDraft.value,
    [normalizedActionKey]: ''
  }
  if (shortcutEditorCaptureActionKey.value === normalizedActionKey) {
    shortcutEditorCaptureActionKey.value = ''
  }
  resetShortcutEditorDraftStatus(t('shortcut_editor_item_cleared'), 'info')
}

function restoreShortcutEditorDefaults() {
  shortcutEditorDraft.value = normalizeEditableShortcutConfig(DEFAULT_EDITABLE_SHORTCUTS)
  shortcutEditorCaptureActionKey.value = ''
  resetShortcutEditorDraftStatus(t('shortcut_editor_restored_pending'), 'info')
}

function saveShortcutEditorDraft() {
  if (!shortcutEditorCanEdit.value) return
  if (shortcutEditorHasConflicts.value) {
    resetShortcutEditorDraftStatus(t('shortcut_editor_conflict'), 'error')
    return
  }
  const normalized = normalizeEditableShortcutConfig(shortcutEditorDraft.value, { allowEmpty: true })
  activeShortcutBindings.value = normalized
  shortcutEditorDraft.value = { ...normalized }
  persistShortcutBindingsForScope(normalized)
  shortcutEditorCaptureActionKey.value = ''
  resetShortcutEditorDraftStatus(t('shortcut_editor_saved'), 'success')
  showFloatingToast(t('shortcut_editor_saved'), 'success')
}

function confirmDiscardShortcutEditorChanges() {
  if (!shortcutEditorCanEdit.value || !shortcutEditorHasUnsavedChanges.value) return true
  return window.confirm(t('shortcut_editor_unsaved_close_confirm'))
}

function applyEnterprisePanelPreset(role = enterpriseUiRole.value, { silent = false } = {}) {
  const preset = enterprisePanelPreset(role)
  if (!preset) return false
  panelSections.value = {
    ...panelSections.value,
    ...preset
  }
  if (!silent) {
    showFloatingToast(t('enterprise_settings_apply_workspace_success'), 'success')
  }
  return true
}

async function openEnterpriseSettingsDialog(targetTab = '') {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dashboard.view', t('enterprise_settings_requires_enterprise'))) return
  if (!canUseEnterpriseUi.value) {
    showFloatingToast(t('enterprise_settings_requires_enterprise'), 'error')
    return
  }
  const availableKeys = enterpriseSettingsTabKeys.value
  const rememberedTab = loadEnterpriseSettingsTabPreference()
  const preferredTab = String(targetTab || '').trim() || rememberedTab || preferredEnterpriseSettingsTab()
  enterpriseSettingsSidebarCollapsed.value = loadEnterpriseSettingsSidebarPreference()
  enterpriseSettingsActiveTab.value = availableKeys.includes(preferredTab)
    ? preferredTab
    : (availableKeys[0] || 'overview')
  enterpriseSettingsDialogOpen.value = true
  if (authCanAiRender.value) {
    void fetchComfyCheckpoints()
    if (enterpriseSettingsActiveTab.value === 'ai') {
      void fetchComfyRenderJobs({ force: true })
      void fetchComfySharedTemplates({ force: true })
    }
  }
  if (authCanViewAudit.value) {
    requestOperationAuditRefresh({ force: true })
  }
}

function closeEnterpriseSettingsDialog() {
  if (enterpriseShortcutPlannerDialogOpen.value && !closeEnterpriseShortcutPlannerDialog()) return
  enterprisePageSettingsDialogOpen.value = false
  enterpriseMapEditorDialogOpen.value = false
  enterpriseTopologyEditorDialogOpen.value = false
  enterpriseSettingsDialogOpen.value = false
}

function openEnterprisePageSettingsDialog() {
  enterprisePageSettingsDialogOpen.value = true
}

function closeEnterprisePageSettingsDialog() {
  enterprisePageSettingsDialogOpen.value = false
}

function openEnterpriseShortcutPlannerDialog() {
  shortcutEditorDraft.value = { ...activeShortcutBindings.value }
  shortcutEditorCaptureActionKey.value = ''
  resetShortcutEditorDraftStatus('', 'info')
  enterpriseShortcutPlannerDialogOpen.value = true
}

function closeEnterpriseShortcutPlannerDialog() {
  if (!confirmDiscardShortcutEditorChanges()) {
    resetShortcutEditorDraftStatus(t('shortcut_editor_unsaved_changes'), 'error')
    return false
  }
  shortcutEditorCaptureActionKey.value = ''
  resetShortcutEditorDraftStatus('', 'info')
  enterpriseShortcutPlannerDialogOpen.value = false
  return true
}

function switchEnterpriseSettingsTab(nextTab) {
  if (!enterpriseSettingsTabKeys.value.includes(nextTab)) return
  enterpriseSettingsActiveTab.value = nextTab
  saveEnterpriseSettingsTabPreference(authCurrentRole.value, nextTab)
  if (nextTab === 'ai' && authCanAiRender.value) {
    void fetchComfyCheckpoints()
    void fetchComfyRenderJobs({ force: true })
    void fetchComfySharedTemplates({ force: true })
  }
  if (nextTab === 'audit' && authCanViewAudit.value) {
    requestOperationAuditRefresh({ force: true })
  }
}

async function jumpFromEnterpriseSettings(sectionKey) {
  closeEnterpriseSettingsDialog()
  await nextTick()
  await jumpToPanelSearchResult(sectionKey)
}

async function applyCurrentEnterpriseWorkspacePreset() {
  applyEnterprisePanelPreset(authCurrentRole.value, { silent: false })
}

async function applyEnterpriseWorkspaceFromAuth() {
  await applyCurrentEnterpriseWorkspacePreset()
  if (dashboardUnlocked.value) {
    authPanelOpen.value = false
  }
}

function setEnterpriseSettingsSidebarCollapsed(collapsed) {
  enterpriseSettingsSidebarCollapsed.value = Boolean(collapsed)
  saveEnterpriseSettingsSidebarPreference(enterpriseSettingsSidebarCollapsed.value)
}

function toggleEnterpriseSettingsSidebar() {
  setEnterpriseSettingsSidebarCollapsed(!enterpriseSettingsSidebarCollapsed.value)
}

async function runEnterpriseWorkspaceAction(actionKey, { closeAuth = false, closeSettings = false } = {}) {
  if (closeSettings) {
    closeEnterpriseSettingsDialog()
  }
  if (closeAuth && dashboardUnlocked.value) {
    authPanelOpen.value = false
  }
  switch (String(actionKey || '')) {
    case 'open-runtime':
      await nextTick()
      await openEnterpriseSettingsDialog('runtime')
      return
    case 'open-map-profiles':
      await nextTick()
      await openEnterpriseSettingsDialog('map_profiles')
      return
    case 'open-audit':
      await nextTick()
      await openEnterpriseSettingsDialog('audit')
      return
    case 'jump-control':
      await nextTick()
      await jumpToPanelSearchResult('control')
      return
    case 'jump-queue':
      await nextTick()
      await jumpToPanelSearchResult('queue')
      return
    case 'jump-points':
      await nextTick()
      await jumpToPanelSearchResult('points')
      return
    case 'jump-templates':
      await nextTick()
      await jumpToPanelSearchResult('templates')
      return
    case 'jump-audit':
      await nextTick()
      await jumpToPanelSearchResult('operations')
      return
    case 'jump-ai':
      await nextTick()
      await jumpToPanelSearchResult('ai')
      return
    default:
      return
  }
}

async function runEnterpriseStatusFollowupAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'copy-summary':
      await copyEnterpriseApplicationSummary(authEnterpriseStatusFollowup.value)
      return
    case 'copy-review-note':
      await copyEnterpriseApplicationReviewNote(authEnterpriseStatusFollowup.value)
      return
    case 'resume-registration':
      resumeEnterpriseRegistrationFromApplication(authEnterpriseStatusFollowup.value)
      return
    case 'open-enterprise-settings':
      await openEnterpriseSettingsDialog()
      return
    case 'apply-workspace':
      await applyCurrentEnterpriseWorkspacePreset()
      return
    case 'dismiss':
      dismissEnterpriseStatusFollowup()
      return
    default:
      return
  }
}

async function runEnterpriseApplicationAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'copy-company-name':
      await copyEnterpriseApplicationCompanyName(authCurrentEnterpriseApplication.value)
      return
    case 'copy-contact-name':
      await copyEnterpriseApplicationContactName(authCurrentEnterpriseApplication.value)
      return
    case 'copy-review-note':
      await copyEnterpriseApplicationReviewNote(authCurrentEnterpriseApplication.value)
      return
    case 'copy-summary':
      await copyEnterpriseApplicationSummary(authCurrentEnterpriseApplication.value)
      return
    case 'copy-username':
      copyEnterpriseApplicationUsername(authCurrentEnterpriseApplication.value)
      return
    case 'copy-contact-email':
      await copyEnterpriseApplicationContactEmail(authCurrentEnterpriseApplication.value)
      return
    case 'refresh-status':
      await refreshEnterpriseAccountStatus()
      return
    case 'edit-application':
    case 'resume-registration':
      resumeEnterpriseRegistrationFromApplication(authCurrentEnterpriseApplication.value, { closeSettings: true })
      return
    case 'apply-workspace':
      await applyCurrentEnterpriseWorkspacePreset()
      return
    case 'switch-runtime':
      switchEnterpriseSettingsTab('runtime')
      return
    case 'switch-map-profiles':
      switchEnterpriseSettingsTab('map_profiles')
      return
    case 'switch-audit':
      switchEnterpriseSettingsTab('audit')
      return
    case 'jump-control':
      await runEnterpriseWorkspaceAction('jump-control', { closeSettings: true })
      return
    case 'jump-queue':
      await runEnterpriseWorkspaceAction('jump-queue', { closeSettings: true })
      return
    case 'jump-points':
      await runEnterpriseWorkspaceAction('jump-points', { closeSettings: true })
      return
    case 'jump-templates':
      await runEnterpriseWorkspaceAction('jump-templates', { closeSettings: true })
      return
    case 'jump-audit':
      await runEnterpriseWorkspaceAction('jump-audit', { closeSettings: true })
      return
    case 'jump-ai':
      await runEnterpriseWorkspaceAction('jump-ai', { closeSettings: true })
      return
    case 'open-runtime':
    case 'open-map-profiles':
    case 'open-audit':
      await runEnterpriseWorkspaceAction(actionKey, { closeSettings: true })
      return
    default:
      return
  }
}

async function runEnterpriseApprovalFollowupAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'copy-company-name':
      await copyEnterpriseApplicationCompanyName(enterpriseApprovalReviewFollowup.value)
      return
    case 'copy-username':
      await copyEnterpriseApplicationUsername(enterpriseApprovalReviewFollowup.value)
      return
    case 'copy-contact-email':
      await copyEnterpriseApplicationContactEmail(enterpriseApprovalReviewFollowup.value)
      return
    case 'open-detail':
      if (enterpriseApprovalReviewFollowup.value?.id) {
        await openEnterpriseApprovalDialogForItem(
          enterpriseApprovalReviewFollowup.value.id,
          enterpriseApprovalReviewFollowup.value.status || 'all'
        )
      }
      return
    case 'copy-summary':
      await copyEnterpriseApplicationSummary(enterpriseApprovalReviewFollowup.value)
      return
    case 'focus-pending':
      await openEnterpriseApprovalDialog({ status: 'pending', resetSearch: true, draftOnly: false })
      return
    case 'dismiss':
      dismissEnterpriseApprovalReviewFollowup()
      return
    default:
      return
  }
}

async function runEnterpriseApprovalAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'copy-company-name':
      await copyEnterpriseApplicationCompanyName(selectedEnterpriseApplication.value)
      return
    case 'copy-contact-name':
      await copyEnterpriseApplicationContactName(selectedEnterpriseApplication.value)
      return
    case 'copy-review-note':
      await copyEnterpriseApplicationReviewNote(selectedEnterpriseApplication.value)
      return
    case 'copy-summary':
      await copyEnterpriseApplicationSummary(selectedEnterpriseApplication.value)
      return
    case 'copy-username':
      await copyEnterpriseApplicationUsername(selectedEnterpriseApplication.value)
      return
    case 'copy-contact-email':
      await copyEnterpriseApplicationContactEmail(selectedEnterpriseApplication.value)
      return
    case 'focus-pending':
      await focusEnterpriseApprovalPendingQueue()
      return
    default:
      return
  }
}

function applyEnterpriseApprovalReviewNoteTemplate(templateKey) {
  const matched = enterpriseApprovalReviewNoteTemplates.value.find(item => item.key === String(templateKey || ''))
  if (!matched) return
  enterpriseApprovalReviewNote.value = matched.value
}

function clearEnterpriseApprovalReviewNote() {
  enterpriseApprovalReviewNote.value = ''
}

async function runAuthEnterpriseQuickAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'copy-company-name':
      await copyEnterpriseApplicationCompanyName(authCurrentEnterpriseApplication.value)
      return
    case 'copy-contact-name':
      await copyEnterpriseApplicationContactName(authCurrentEnterpriseApplication.value)
      return
    case 'copy-review-note':
      await copyEnterpriseApplicationReviewNote(authCurrentEnterpriseApplication.value)
      return
    case 'copy-summary':
      await copyEnterpriseApplicationSummary(authCurrentEnterpriseApplication.value)
      return
    case 'copy-username':
      await copyEnterpriseApplicationUsername(authCurrentEnterpriseApplication.value)
      return
    case 'copy-contact-email':
      await copyEnterpriseApplicationContactEmail(authCurrentEnterpriseApplication.value)
      return
    case 'refresh-status':
      await refreshEnterpriseAccountStatus()
      return
    case 'edit-application':
    case 'resume-registration':
      resumeEnterpriseRegistrationFromApplication(authCurrentEnterpriseApplication.value)
      return
    case 'open-enterprise-settings':
      await openEnterpriseSettingsDialog()
      return
    case 'apply-workspace':
      await applyCurrentEnterpriseWorkspacePreset()
      return
    case 'open-runtime':
    case 'open-map-profiles':
    case 'open-audit':
    case 'jump-control':
    case 'jump-queue':
    case 'jump-points':
    case 'jump-templates':
    case 'jump-audit':
    case 'jump-ai':
      await runEnterpriseWorkspaceAction(actionKey, { closeAuth: true })
      return
    default:
      return
  }
}

async function runAuthEnterpriseRegisterExistingAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'use-current-application':
      useCurrentEnterpriseApplicationForRegisterDraft()
      return
    default:
      await runAuthEnterpriseQuickAction(actionKey)
      return
  }
}

async function runAuthStatusNoticeAction(actionKey) {
  switch (String(actionKey || '')) {
    case 'enterprise-approval':
      await openEnterpriseApprovalDialog()
      return
    case 'refresh-enterprise-status':
      await refreshEnterpriseAccountStatus()
      return
    case 'enterprise-settings':
      await openEnterpriseSettingsDialog()
      return
    case 'resume-enterprise-registration':
      resumeEnterpriseRegistrationFromApplication(authCurrentEnterpriseApplication.value)
      return
    default:
      return
  }
}

async function reviewEnterpriseApplication(decision) {
  const applicationId = Number(selectedEnterpriseApplicationId.value || 0)
  if (!applicationId) return
  if (decision === 'reject' && !enterpriseApprovalCanReject.value) {
    showFloatingToast(t('enterprise_approval_reject_requires_note'), 'warning')
    return
  }
  enterpriseApprovalReviewLoading.value = true
  try {
    const response = await fetch(
      `${API_BASE}/auth/enterprise-applications/${applicationId}/${decision === 'reject' ? 'reject' : 'approve'}`,
      {
        method: 'POST',
        headers: buildAuthHeaders({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify({
          review_note: enterpriseApprovalReviewNoteTrimmed.value || null
        })
      }
    )
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise application review failed')
    }
    const reviewedApplication = data?.application ?? null
    if (reviewedApplication) {
      enterpriseApprovalReviewFollowup.value = buildEnterpriseStatusFollowup(reviewedApplication, reviewedApplication?.status)
    }
    const draftKey = String(applicationId)
    if (enterpriseApprovalNoteDrafts.value[draftKey]) {
      const nextDrafts = { ...enterpriseApprovalNoteDrafts.value }
      delete nextDrafts[draftKey]
      enterpriseApprovalNoteDrafts.value = nextDrafts
    }
    enterpriseApprovalReviewNote.value = ''
    await fetchEnterpriseApplications({ forceSelectFirst: false })
    const remainingFiltered = filteredEnterpriseApplications.value
    if (remainingFiltered.some(item => Number(item.id) === applicationId)) {
      selectedEnterpriseApplicationId.value = applicationId
    } else if (remainingFiltered.length > 0) {
      selectedEnterpriseApplicationId.value = remainingFiltered[0].id
    } else {
      selectedEnterpriseApplicationId.value = null
    }
    showFloatingToast(
      decision === 'reject'
        ? formatInlineMessage(t('enterprise_approval_reject_success_detail'), {
            company: reviewedApplication?.company_name || '—',
            username: reviewedApplication?.username || '—'
          })
        : formatInlineMessage(t('enterprise_approval_approve_success_detail'), {
            company: reviewedApplication?.company_name || '—',
            username: reviewedApplication?.username || '—'
          }),
      'success'
    )
  } catch (error) {
    showFloatingToast(error?.message || t('enterprise_approval_review_failed'), 'error')
  } finally {
    enterpriseApprovalReviewLoading.value = false
  }
}

function ensureAuthenticatedOperation(
  message = t('auth_action_requires_login'),
  requiredCapability = '',
  deniedMessage = t('auth_permission_denied')
) {
  if (!authAuthenticated.value) {
    authPanelOpen.value = true
    showFloatingToast(message, 'warning')
    return false
  }
  if (requiredCapability && !authCapabilitySet.value.has(String(requiredCapability))) {
    authPanelOpen.value = true
    showFloatingToast(deniedMessage, 'warning')
    return false
  }
  return true
}

function buildAuthCapabilityStateText(enabled) {
  return enabled ? t('auth_capability_enabled') : t('auth_capability_disabled')
}

function capabilityLabel(groupKey) {
  switch (groupKey) {
    case 'dispatch':
      return t('auth_capability_dispatch_label')
    case 'fault':
      return t('auth_capability_fault_label')
    case 'map':
      return t('auth_capability_map_label')
    case 'data':
      return t('auth_capability_data_label')
    case 'audit':
      return t('auth_capability_audit_label')
    case 'ai':
      return t('auth_capability_ai_label')
    case 'platform':
      return t('auth_capability_platform_label')
    default:
      return t('auth_current_identity')
  }
}

function buildCapabilityDeniedMessage(groupKey) {
  return formatInlineMessage(t('auth_capability_group_locked'), {
    group: capabilityLabel(groupKey)
  })
}

function buildCapabilityLockedTitle(groupKey, enabled) {
  if (enabled) return ''
  if (!authAuthenticated.value) return t('auth_action_requires_login')
  return buildCapabilityDeniedMessage(groupKey)
}

function canApplyMapProfileWithCapability(profile) {
  return canForceApplyMapProfile(profile) ? authCanForceApplyMap.value : authCanMapWrite.value
}

function buildMapProfileApplyTitle(profile) {
  if (isCurrentMapProfile(profile)) return ''
  if (canForceApplyMapProfile(profile)) {
    if (!authAuthenticated.value) return t('auth_action_requires_login')
    return authCanForceApplyMap.value ? '' : t('auth_map_force_apply_denied')
  }
  return buildCapabilityLockedTitle('map', authCanMapWrite.value)
}

function buildOperationsHintText() {
  if (authCanViewAudit.value) return t('operations_hint')
  const enterpriseReadonlyHint = buildEnterprisePanelReadonlyHint('audit')
  if (enterpriseReadonlyHint) return enterpriseReadonlyHint
  if (authAuthenticated.value) return t('operations_permission_hint')
  return t('operations_login_hint')
}

function buildAiRenderHintText() {
  if (authCanAiRender.value) return t('ai_render_hint')
  if (authAuthenticated.value) return t('ai_render_permission_hint')
  return t('ai_render_requires_login')
}

function buildOperationsEntryActionText() {
  return authAuthenticated.value ? t('auth_switch_account') : t('auth_sign_in')
}

function buildCapabilityReadonlyHint(groupKey) {
  return formatInlineMessage(
    authAuthenticated.value ? t('auth_capability_readonly_hint') : t('auth_capability_requires_login_readonly'),
    { group: capabilityLabel(groupKey) }
  )
}

function buildEnterprisePanelReadonlyHint(groupKey) {
  if (!authAuthenticated.value || !authIsEnterpriseRole.value) return ''
  const role = authCurrentRole.value
  if (role === 'enterprise_operator') {
    if (groupKey === 'map') return t('enterprise_main_panel_hint_map_operator')
    if (groupKey === 'data') return t('enterprise_main_panel_hint_data_operator')
    if (groupKey === 'audit') return t('enterprise_main_panel_hint_audit_operator')
  }
  if (role === 'enterprise_logistics') {
    if (groupKey === 'dispatch') return t('enterprise_main_panel_hint_dispatch_logistics')
    if (groupKey === 'fault') return t('enterprise_main_panel_hint_fault_logistics')
    if (groupKey === 'audit') return t('enterprise_main_panel_hint_audit_logistics')
  }
  return ''
}

function openAuthDialog() {
  authDialogView.value = 'login'
  authPanelOpen.value = true
}

function saveCurrentTaskTemplateWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  saveCurrentTaskAsTemplate()
}

function saveCurrentTaskChainTemplateWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  saveCurrentTaskChainAsTemplate()
}

function importTaskTemplatesFromJsonWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  importTaskTemplatesFromJson()
}

function exportTaskTemplatesToJsonWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  exportTaskTemplatesToJson()
}

function downloadTemplateJsonFileWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  downloadTemplateJsonFile()
}

function clearTemplateJsonTextWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  clearTemplateJsonText()
}

function addCustomPointWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'point.write', buildCapabilityDeniedMessage('data'))) return
  addCustomPoint()
}

function deleteCustomPointWithAuth(point) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'point.write', buildCapabilityDeniedMessage('data'))) return
  deleteCustomPoint(point)
}

function saveCurrentExperimentRecordWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  saveCurrentExperimentRecord()
}

function exportCurrentCompareResultJsonWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  exportCurrentCompareResultJson()
}

function exportCurrentCompareResultCsvWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  exportCurrentCompareResultCsv()
}

function exportAllExperimentRecordsJsonWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  exportAllExperimentRecordsJson()
}

function exportAllExperimentRecordsCsvWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  exportAllExperimentRecordsCsv()
}

function clearExperimentRecordsWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  clearExperimentRecords()
}

function deleteExperimentRecordWithAuth(recordId) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'experiment.write', buildCapabilityDeniedMessage('data'))) return
  deleteExperimentRecord(recordId)
}

function resetOperationAuditFilters() {
  operationAuditResourceFilter.value = 'all'
  operationAuditActionFilter.value = 'all'
}

function dismissEnterpriseWorkspacePopup() {
  enterpriseWorkspacePopupDismissed.value = true
  showFloatingToast(t('enterprise_workspace_popup_reopen_hint'), 'info')
}

function resetEnterpriseWorkspacePopupPosition() {
  const paneEl = mapPaneRef.value
  const popupEl = enterpriseWorkspacePopupRef.value
  if (!paneEl || !popupEl) {
    enterpriseWorkspacePopupX.value = null
    enterpriseWorkspacePopupY.value = 12
    return
  }
  const paneRect = paneEl.getBoundingClientRect()
  const popupRect = popupEl.getBoundingClientRect()
  enterpriseWorkspacePopupX.value = Math.max(14, paneRect.left + paneRect.width - popupRect.width - 14)
  enterpriseWorkspacePopupY.value = 12
}

async function ensureEnterpriseWorkspacePopupPosition() {
  await nextTick()
  resetEnterpriseWorkspacePopupPosition()
}

function reopenEnterpriseWorkspacePopup() {
  if (!showEnterpriseWorkspaceBanner.value) return
  enterpriseWorkspacePopupDismissed.value = false
  void ensureEnterpriseWorkspacePopupPosition()
}

function startEnterpriseWorkspacePopupDrag(event) {
  if (!showEnterpriseWorkspacePopup.value) return
  if (event.button !== 0) return
  if (event.target.closest('button')) return

  const popupEl = enterpriseWorkspacePopupRef.value
  if (!popupEl) return

  if (enterpriseWorkspacePopupX.value == null) {
    resetEnterpriseWorkspacePopupPosition()
  }

  enterpriseWorkspacePopupDragging = true
  enterpriseWorkspacePopupDragOffsetX = event.clientX - (enterpriseWorkspacePopupX.value ?? 14)
  enterpriseWorkspacePopupDragOffsetY = event.clientY - enterpriseWorkspacePopupY.value
  event.preventDefault()
}

function syncEnterpriseWorkspacePopupDrag(event) {
  if (!enterpriseWorkspacePopupDragging) return false
  const popupEl = enterpriseWorkspacePopupRef.value
  if (!popupEl) return false

  const popupRect = popupEl.getBoundingClientRect()
  const nextX = event.clientX - enterpriseWorkspacePopupDragOffsetX
  const nextY = event.clientY - enterpriseWorkspacePopupDragOffsetY
  const maxX = Math.max(14, window.innerWidth - popupRect.width - 14)
  const maxY = Math.max(12, window.innerHeight - popupRect.height - 14)
  enterpriseWorkspacePopupX.value = clampValue(nextX, 14, maxX)
  enterpriseWorkspacePopupY.value = clampValue(nextY, 12, maxY)
  return true
}

function stopEnterpriseWorkspacePopupDrag() {
  enterpriseWorkspacePopupDragging = false
}

function openEnterpriseMapEditorDialog() {
  enterpriseMapEditorDraftCols.value = gridColsValue()
  enterpriseMapEditorDraftRows.value = gridRowsValue()
  enterpriseMapEditorDraftValidCells.value = normalizeValidCellList(validCells.value)
  enterpriseMapEditorDraftBlockedCells.value = normalizeBlockedCellList(blockedCells.value)
  enterpriseMapEditorZoom.value = ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT
  enterpriseMapEditorDialogOpen.value = true
}

function closeEnterpriseMapEditorDialog() {
  enterpriseMapEditorDialogOpen.value = false
}

function resetEnterpriseMapEditorDraft() {
  enterpriseMapEditorDraftCols.value = gridColsValue()
  enterpriseMapEditorDraftRows.value = gridRowsValue()
  enterpriseMapEditorDraftValidCells.value = normalizeValidCellList(validCells.value)
  enterpriseMapEditorDraftBlockedCells.value = normalizeBlockedCellList(blockedCells.value)
}

function canResizeEnterpriseMapEditorTo(nextCols, nextRows) {
  const cols = Math.max(1, Math.round(Number(nextCols) || 1))
  const rows = Math.max(1, Math.round(Number(nextRows) || 1))
  if (cols > 30 || rows > 24) return false

  const currentCols = Math.max(1, Math.round(Number(enterpriseMapEditorDraftCols.value || gridColsValue()) || 1))
  const currentRows = Math.max(1, Math.round(Number(enterpriseMapEditorDraftRows.value || gridRowsValue()) || 1))
  const isShrinking = cols < currentCols || rows < currentRows
  if (!isShrinking) return true

  const protectedCells = Array.from(protectedMapCellSet.value).map(key => {
    const [x, y] = key.split(',').map(Number)
    return { x, y }
  })
  const requiredCells = [
    ...enterpriseMapEditorDraftValidCells.value,
    ...protectedCells
  ]

  return requiredCells.every(cell => cell.x < cols && cell.y < rows)
}

function clampEnterpriseMapEditorZoom(value) {
  return clampValue(
    Number(value) || ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT,
    ENTERPRISE_MAP_EDITOR_ZOOM_MIN,
    ENTERPRISE_MAP_EDITOR_ZOOM_MAX
  )
}

function adjustEnterpriseMapEditorZoom(delta) {
  enterpriseMapEditorZoom.value = clampEnterpriseMapEditorZoom(
    Number(enterpriseMapEditorZoom.value || ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT) + Number(delta || 0)
  )
}

function resetEnterpriseMapEditorZoom() {
  enterpriseMapEditorZoom.value = ENTERPRISE_MAP_EDITOR_ZOOM_DEFAULT
}

function handleEnterpriseMapEditorWheel(event) {
  if (!enterpriseMapEditorDialogOpen.value) return
  const direction = Number(event?.deltaY) < 0 ? 1 : -1
  adjustEnterpriseMapEditorZoom(direction * ENTERPRISE_MAP_EDITOR_ZOOM_STEP)
}

function resizeEnterpriseMapEditorDraft(axis, delta) {
  const nextCols = axis === 'cols'
    ? Number(enterpriseMapEditorDraftCols.value || gridColsValue()) + Number(delta || 0)
    : Number(enterpriseMapEditorDraftCols.value || gridColsValue())
  const nextRows = axis === 'rows'
    ? Number(enterpriseMapEditorDraftRows.value || gridRowsValue()) + Number(delta || 0)
    : Number(enterpriseMapEditorDraftRows.value || gridRowsValue())

  if (!canResizeEnterpriseMapEditorTo(nextCols, nextRows)) return

  enterpriseMapEditorDraftCols.value = Math.max(1, Math.round(nextCols))
  enterpriseMapEditorDraftRows.value = Math.max(1, Math.round(nextRows))
  enterpriseMapEditorDraftValidCells.value = enterpriseMapEditorDraftValidCells.value
    .filter(cell => cell.x < enterpriseMapEditorDraftCols.value && cell.y < enterpriseMapEditorDraftRows.value)
  enterpriseMapEditorDraftBlockedCells.value = enterpriseMapEditorDraftBlockedCells.value
    .filter(cell => cell.x < enterpriseMapEditorDraftCols.value && cell.y < enterpriseMapEditorDraftRows.value)
}

function isEnterpriseMapEditorCellValid(x, y) {
  return enterpriseMapEditorDraftValidCellSet.value.has(blockedCellKey(x, y))
}

function isEnterpriseTopologyCellValid(x, y) {
  return validCellSet.value.has(blockedCellKey(x, y))
}

function isEnterpriseMapEditorCellBlocked(x, y) {
  return enterpriseMapEditorDraftBlockedCellSet.value.has(blockedCellKey(x, y))
}

function isEnterpriseMapEditorCellLocked(x, y) {
  return isProtectedMapCell(x, y)
}

function applyEnterpriseMapEditorCell(cell, event) {
  if (!cell) return
  const { x, y } = cell
  if (isEnterpriseMapEditorCellLocked(x, y)) return

  const key = blockedCellKey(x, y)
  const valid = enterpriseMapEditorDraftValidCellSet.value.has(key)

  if (event?.ctrlKey || event?.metaKey) {
    if (!valid) return
    if (enterpriseMapEditorDraftBlockedCellSet.value.has(key)) {
      enterpriseMapEditorDraftBlockedCells.value = enterpriseMapEditorDraftBlockedCells.value
        .filter(item => blockedCellKey(item.x, item.y) !== key)
      return
    }
    enterpriseMapEditorDraftBlockedCells.value = normalizeBlockedCellList([
      ...enterpriseMapEditorDraftBlockedCells.value,
      { x, y }
    ])
    return
  }

  if (valid) {
    enterpriseMapEditorDraftValidCells.value = enterpriseMapEditorDraftValidCells.value
      .filter(item => blockedCellKey(item.x, item.y) !== key)
    enterpriseMapEditorDraftBlockedCells.value = enterpriseMapEditorDraftBlockedCells.value
      .filter(item => blockedCellKey(item.x, item.y) !== key)
    return
  }

  enterpriseMapEditorDraftValidCells.value = normalizeValidCellList([
    ...enterpriseMapEditorDraftValidCells.value,
    { x, y }
  ], enterpriseMapEditorDraftCols.value, enterpriseMapEditorDraftRows.value)
}

async function saveEnterpriseMapEditorDraft() {
  if (enterpriseMapEditorSaving.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return
  if (!ensureObstacleMutationAllowed()) return
  if (!enterpriseMapEditorDraftValidCells.value.length) {
    showFloatingToast(t('enterprise_settings_map_editor_shape_required'), 'error')
    return
  }

  enterpriseMapEditorSaving.value = true
  try {
    const ok = await saveBlockedCells(
      enterpriseMapEditorDraftBlockedCells.value,
      enterpriseMapEditorDraftValidCells.value,
      enterpriseMapEditorDraftCols.value,
      enterpriseMapEditorDraftRows.value
    )
    if (ok) {
      closeEnterpriseMapEditorDialog()
      showFloatingToast(t('enterprise_settings_map_editor_saved'), 'success')
    }
  } finally {
    enterpriseMapEditorSaving.value = false
  }
}

function openEnterpriseTopologyEditorDialog() {
  try {
    enterpriseTopologyEditorDraft.value = cloneMapTopology(currentMapTopology.value, gridColsValue(), gridRowsValue(), validCells.value)
    enterpriseTopologyEditorSelectedNodeKey.value = ''
    enterpriseTopologyEditorSelectedEdgeKey.value = ''
    enterpriseTopologyEditorLinkSourceKey.value = ''
    enterpriseTopologyEditorDialogOpen.value = true
  } catch (error) {
    console.error('Open enterprise topology editor error:', error)
    showFloatingToast(
      t('enterprise_settings_route_topology_open_failed') || 'Unable to open route topology right now.',
      'error'
    )
  }
}

function closeEnterpriseTopologyEditorDialog() {
  enterpriseTopologyEditorDialogOpen.value = false
  enterpriseTopologyEditorSelectedNodeKey.value = ''
  enterpriseTopologyEditorSelectedEdgeKey.value = ''
  enterpriseTopologyEditorLinkSourceKey.value = ''
}

function resetEnterpriseTopologyEditorDraft() {
  enterpriseTopologyEditorDraft.value = cloneMapTopology(currentMapTopology.value, gridColsValue(), gridRowsValue(), validCells.value)
  enterpriseTopologyEditorSelectedNodeKey.value = ''
  enterpriseTopologyEditorSelectedEdgeKey.value = ''
  enterpriseTopologyEditorLinkSourceKey.value = ''
}

function selectEnterpriseTopologyNode(nodeKey) {
  enterpriseTopologyEditorSelectedNodeKey.value = String(nodeKey || '')
  enterpriseTopologyEditorSelectedEdgeKey.value = ''
}

function selectEnterpriseTopologyEdge(edgeKey) {
  enterpriseTopologyEditorSelectedEdgeKey.value = String(edgeKey || '')
  enterpriseTopologyEditorSelectedNodeKey.value = ''
}

function updateEnterpriseTopologyNode(patch = {}) {
  if (!authCanMapWrite.value) return
  const selectedKey = enterpriseTopologyEditorSelectedNodeKey.value
  if (!selectedKey) return
  enterpriseTopologyEditorDraft.value = normalizeMapTopology({
    ...enterpriseTopologyEditorDraft.value,
    nodes: (enterpriseTopologyEditorDraft.value?.nodes || []).map(node =>
      node.key === selectedKey ? { ...node, ...patch } : node
    )
  }, gridColsValue(), gridRowsValue(), validCells.value)
}

function updateEnterpriseTopologyEdge(patch = {}) {
  if (!authCanMapWrite.value) return
  const selectedKey = enterpriseTopologyEditorSelectedEdgeKey.value
  if (!selectedKey) return
  enterpriseTopologyEditorDraft.value = normalizeMapTopology({
    ...enterpriseTopologyEditorDraft.value,
    edges: (enterpriseTopologyEditorDraft.value?.edges || []).map(edge =>
      edge.key === selectedKey ? { ...edge, ...patch } : edge
    )
  }, gridColsValue(), gridRowsValue(), validCells.value)
}

function toggleEnterpriseTopologyLinkSource() {
  if (!authCanMapWrite.value) return
  if (!enterpriseTopologySelectedNode.value) return
  enterpriseTopologyEditorLinkSourceKey.value = enterpriseTopologyEditorLinkSourceKey.value === enterpriseTopologySelectedNode.value.key
    ? ''
    : enterpriseTopologySelectedNode.value.key
}

function removeSelectedEnterpriseTopologyNode() {
  if (!authCanMapWrite.value) return
  const selectedNode = enterpriseTopologySelectedNode.value
  if (!selectedNode) return
  enterpriseTopologyEditorDraft.value = normalizeMapTopology({
    ...enterpriseTopologyEditorDraft.value,
    nodes: (enterpriseTopologyEditorDraft.value?.nodes || []).filter(node => node.key !== selectedNode.key),
    edges: (enterpriseTopologyEditorDraft.value?.edges || []).filter(edge => edge.source !== selectedNode.key && edge.target !== selectedNode.key)
  }, gridColsValue(), gridRowsValue(), validCells.value)
  if (enterpriseTopologyEditorLinkSourceKey.value === selectedNode.key) {
    enterpriseTopologyEditorLinkSourceKey.value = ''
  }
  enterpriseTopologyEditorSelectedNodeKey.value = ''
}

function removeSelectedEnterpriseTopologyEdge() {
  if (!authCanMapWrite.value) return
  const selectedEdge = enterpriseTopologySelectedEdge.value
  if (!selectedEdge) return
  enterpriseTopologyEditorDraft.value = normalizeMapTopology({
    ...enterpriseTopologyEditorDraft.value,
    edges: (enterpriseTopologyEditorDraft.value?.edges || []).filter(edge => edge.key !== selectedEdge.key)
  }, gridColsValue(), gridRowsValue(), validCells.value)
  enterpriseTopologyEditorSelectedEdgeKey.value = ''
}

function applyEnterpriseTopologyCell(cell) {
  if (!cell) return
  if (!isValidMapCell(cell.x, cell.y)) return
  const existingNode = findMapTopologyNodeAtCell(enterpriseTopologyEditorDraft.value, cell.x, cell.y)
  if (!authCanMapWrite.value) {
    if (existingNode) selectEnterpriseTopologyNode(existingNode.key)
    return
  }
  if (existingNode) {
    if (enterpriseTopologyEditorLinkSourceKey.value && enterpriseTopologyEditorLinkSourceKey.value !== existingNode.key) {
      const edgeKey = buildMapTopologyEdgeKey(
        enterpriseTopologyEditorDraft.value,
        enterpriseTopologyEditorLinkSourceKey.value,
        existingNode.key
      )
      enterpriseTopologyEditorDraft.value = normalizeMapTopology({
        ...enterpriseTopologyEditorDraft.value,
        edges: [
          ...(enterpriseTopologyEditorDraft.value?.edges || []),
          {
            key: edgeKey,
            source: enterpriseTopologyEditorLinkSourceKey.value,
            target: existingNode.key,
            direction: 'bidirectional',
            lane_type: 'main',
            weight: 1,
            speed_multiplier: 1
          }
        ]
      }, gridColsValue(), gridRowsValue(), validCells.value)
      enterpriseTopologyEditorSelectedEdgeKey.value = edgeKey
      enterpriseTopologyEditorSelectedNodeKey.value = ''
      enterpriseTopologyEditorLinkSourceKey.value = ''
      return
    }
    selectEnterpriseTopologyNode(existingNode.key)
    return
  }

  const nodeKey = buildMapTopologyNodeKey(enterpriseTopologyEditorDraft.value, cell.x, cell.y)
  enterpriseTopologyEditorDraft.value = normalizeMapTopology({
    ...enterpriseTopologyEditorDraft.value,
    nodes: [
      ...(enterpriseTopologyEditorDraft.value?.nodes || []),
      {
        key: nodeKey,
        x: cell.x,
        y: cell.y,
        label: null,
        node_type: 'waypoint'
      }
    ]
  }, gridColsValue(), gridRowsValue(), validCells.value)
  selectEnterpriseTopologyNode(nodeKey)
}

async function saveEnterpriseTopologyEditorDraft() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return
  const normalizedTopology = normalizeMapTopology(
    enterpriseTopologyEditorDraft.value,
    gridColsValue(),
    gridRowsValue(),
    validCells.value
  )
  const ok = await saveBlockedCells(
    blockedCells.value,
    validCells.value,
    gridColsValue(),
    gridRowsValue(),
    normalizedTopology
  )
  if (ok) {
    enterpriseTopologyEditorDraft.value = normalizedTopology
    closeEnterpriseTopologyEditorDialog()
    showFloatingToast(t('enterprise_settings_route_topology_saved'), 'success')
  }
}

function normalizeOperationAuditEntryIds(entries = []) {
  return [...new Set(
    (entries || [])
      .map(entry => Number(entry?.id))
      .filter(id => Number.isFinite(id) && id > 0)
  )]
}

function isOperationAuditSelected(entry) {
  return selectedOperationAuditIdSet.value.has(Number(entry?.id))
}

function toggleOperationAuditSelection(entry) {
  const auditId = Number(entry?.id)
  if (!Number.isFinite(auditId) || auditId <= 0) return
  if (selectedOperationAuditIdSet.value.has(auditId)) {
    selectedOperationAuditIds.value = selectedOperationAuditIds.value.filter(id => Number(id) !== auditId)
    return
  }
  selectedOperationAuditIds.value = [...selectedOperationAuditIds.value, auditId]
}

function clearSelectedOperationAudits() {
  selectedOperationAuditIds.value = []
}

function areAllVisibleOperationAuditsSelected(entries = []) {
  const ids = normalizeOperationAuditEntryIds(entries)
  return ids.length > 0 && ids.every(id => selectedOperationAuditIdSet.value.has(id))
}

function selectedVisibleOperationAuditCount(entries = []) {
  return normalizeOperationAuditEntryIds(entries).filter(id => selectedOperationAuditIdSet.value.has(id)).length
}

function toggleSelectVisibleOperationAudits(entries = []) {
  const ids = normalizeOperationAuditEntryIds(entries)
  if (!ids.length) return
  if (ids.every(id => selectedOperationAuditIdSet.value.has(id))) {
    selectedOperationAuditIds.value = selectedOperationAuditIds.value.filter(id => !ids.includes(Number(id)))
    return
  }
  selectedOperationAuditIds.value = [...new Set([...selectedOperationAuditIds.value, ...ids])]
}

function buildOperationAuditExportPayload(entries = filteredOperationAudits.value) {
  return (entries || []).map(entry => ({
    id: entry.id,
    resource_type: entry.resource_type ?? '',
    resource_label: operationResourceLabel(entry.resource_type),
    resource_id: entry.resource_id ?? '',
    resource_ref: formatOperationAuditResourceRef(entry),
    action: entry.action ?? '',
    action_label: operationActionLabel(entry.action),
    operator: formatOperationAuditOperator(entry),
    performed_at: entry.performed_at ?? '',
    metadata_summary: formatOperationAuditMetadata(entry)
  }))
}

function buildOperationAuditExportFilename(prefix = 'agv-operation-audit') {
  const resourcePart = operationAuditResourceFilter.value && operationAuditResourceFilter.value !== 'all'
    ? operationAuditResourceFilter.value
    : 'all'
  const actionPart = operationAuditActionFilter.value && operationAuditActionFilter.value !== 'all'
    ? operationAuditActionFilter.value
    : 'all'
  return `${prefix}-${resourcePart}-${actionPart}`
}

function exportFilteredOperationAuditsJson() {
  const payload = buildOperationAuditExportPayload()
  if (!payload.length) {
    showFloatingToast(t('operations_export_empty'), 'info')
    return
  }
  downloadJsonFile(
    `${buildOperationAuditExportFilename()}.json`,
    JSON.stringify(
      {
        exported_at: new Date().toISOString(),
        resource_filter: operationAuditResourceFilter.value,
        action_filter: operationAuditActionFilter.value,
        items: payload
      },
      null,
      2
    )
  )
  showFloatingToast(t('operations_export_json_ok'), 'success')
}

function exportFilteredOperationAuditsCsv() {
  const rows = buildOperationAuditExportPayload()
  if (!rows.length) {
    showFloatingToast(t('operations_export_empty'), 'info')
    return
  }
  downloadCsvFile(`${buildOperationAuditExportFilename()}.csv`, rowsToCsv(rows))
  showFloatingToast(t('operations_export_csv_ok'), 'success')
}

function exportFilteredOperationAuditsJsonWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'audit.view', buildCapabilityDeniedMessage('audit'))) return
  exportFilteredOperationAuditsJson()
}

function exportFilteredOperationAuditsCsvWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'audit.view', buildCapabilityDeniedMessage('audit'))) return
  exportFilteredOperationAuditsCsv()
}

function createTaskFromTemplateWithAuth(template) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  createTaskFromTemplate(template)
}

function deleteTaskTemplateWithAuth(template) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  deleteTaskTemplate(template)
}

function exportTasksToJsonWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'json.write', buildCapabilityDeniedMessage('data'))) return
  exportTasksToJson()
}

function clearJsonTextWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'json.write', buildCapabilityDeniedMessage('data'))) return
  clearJsonText()
}

function toggleObstacleEditModeWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return
  toggleObstacleEditMode()
}

function triggerObstacleLayoutImportWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return
  triggerObstacleLayoutImport()
}

function buildAuthorizedHeaders(headers = {}) {
  return buildAuthHeaders(headers)
}

function buildAuthorizedJsonHeaders(headers = {}) {
  return buildAuthorizedHeaders({
    'Content-Type': 'application/json',
    ...headers
  })
}

async function fetchOperationAudits({ force = false } = {}) {
  if (!authAuthenticated.value || !authCanViewAudit.value) {
    operationAudits.value = []
    operationAuditLastFetchedAt.value = ''
    return
  }
  if (operationAuditLoading.value) return
  if (!force && !panelSections.value.operations) return

  operationAuditLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/auth/operations?limit=80`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json()
    if (!response.ok) {
      throw createApiError(data, 'Operation audit request failed')
    }
    operationAudits.value = Array.isArray(data?.items) ? data.items : []
    operationAuditLastFetchedAt.value = new Date().toISOString()
  } catch (error) {
    console.error('Fetch operation audits error:', error)
    if (force) {
      showFloatingToast(error?.message || t('operations_load_failed'), 'error')
    }
  } finally {
    operationAuditLoading.value = false
  }
}

async function deleteOperationAuditWithAuth(entry) {
  if (!entry?.id) return
  if (!authAuthenticated.value || !authCanViewAudit.value) {
    openAuthDialog()
    return
  }
  if (!window.confirm(t('operations_delete_confirm'))) return

  const auditId = Number(entry.id)
  deletingOperationAuditId.value = auditId
  try {
    await deleteOperationAuditRequest(auditId)
    operationAudits.value = operationAudits.value.filter(item => Number(item.id) !== auditId)
    selectedOperationAuditIds.value = selectedOperationAuditIds.value.filter(id => Number(id) !== auditId)
    showFloatingToast(t('operations_delete_ok'), 'success')
  } catch (error) {
    console.error('Delete operation audit error:', error)
    showFloatingToast(error?.message || t('operations_delete_failed'), 'error')
  } finally {
    deletingOperationAuditId.value = null
  }
}

async function deleteOperationAuditRequest(auditId) {
  const response = await fetch(`${API_BASE}/auth/operations/${auditId}`, {
    method: 'DELETE',
    headers: buildAuthorizedHeaders()
  })
  const data = await response.json()
  if (!response.ok) {
    throw createApiError(data, 'Delete operation audit failed')
  }
  return data
}

async function deleteSelectedOperationAuditsWithAuth(entries = filteredOperationAudits.value) {
  if (!authAuthenticated.value || !authCanViewAudit.value) {
    openAuthDialog()
    return
  }
  const targetIds = normalizeOperationAuditEntryIds(entries).filter(id => selectedOperationAuditIdSet.value.has(id))
  if (!targetIds.length) {
    showFloatingToast(t('operations_bulk_delete_empty'), 'info')
    return
  }
  if (!window.confirm(formatInlineMessage(t('operations_bulk_delete_confirm'), { count: targetIds.length }))) return

  operationAuditBulkDeleting.value = true
  const deletedIds = []
  let failedCount = 0
  try {
    for (const auditId of targetIds) {
      try {
        await deleteOperationAuditRequest(auditId)
        deletedIds.push(auditId)
      } catch (error) {
        failedCount += 1
        console.error(`Delete operation audit ${auditId} error:`, error)
      }
    }

    if (deletedIds.length) {
      operationAudits.value = operationAudits.value.filter(item => !deletedIds.includes(Number(item.id)))
      selectedOperationAuditIds.value = selectedOperationAuditIds.value.filter(id => !deletedIds.includes(Number(id)))
    }

    if (failedCount > 0) {
      showFloatingToast(
        formatInlineMessage(t('operations_bulk_delete_partial'), {
          deleted: deletedIds.length,
          failed: failedCount
        }),
        deletedIds.length ? 'info' : 'error'
      )
      return
    }

    showFloatingToast(formatInlineMessage(t('operations_bulk_delete_ok'), { count: deletedIds.length }), 'success')
  } finally {
    operationAuditBulkDeleting.value = false
  }
}

function requestOperationAuditRefresh({ force = false } = {}) {
  if (!authAuthenticated.value || !authCanViewAudit.value) {
    operationAudits.value = []
    return
  }
  if (!force && !panelSections.value.operations) return
  if (operationAuditRefreshPending) return
  operationAuditRefreshPending = true
  queueMicrotask(() => {
    operationAuditRefreshPending = false
    void fetchOperationAudits({ force })
  })
}

const comfyRenderSourceOptions = computed(() => [
  { value: 'map_profile', label: t('ai_render_source_map_profile') },
  { value: 'point_template_export', label: t('ai_render_source_point_template') },
  { value: 'experiment_records', label: t('ai_render_source_experiment_records') },
  { value: 'map_profile_diff', label: t('ai_render_source_map_profile_diff') },
  { value: 'custom_json', label: t('ai_render_source_custom_json') }
])
const comfyRenderWorkflowPresetOptions = computed(() => [
  { value: 'preview', label: t('ai_render_preset_preview') },
  { value: 'showcase', label: t('ai_render_preset_showcase') },
  { value: 'sdxl_showcase', label: t('ai_render_preset_sdxl_showcase') }
])
const comfyRenderPromptStyleOptions = computed(() => [
  { value: 'report', label: t('ai_render_style_report') },
  { value: 'industrial_realistic', label: t('ai_render_style_industrial_realistic') },
  { value: 'infographic', label: t('ai_render_style_infographic') }
])
const comfyRenderSourceLabelMap = computed(() =>
  comfyRenderSourceOptions.value.reduce((acc, option) => {
    acc[option.value] = option.label
    return acc
  }, {})
)
const comfyRenderWorkflowPresetLabelMap = computed(() =>
  comfyRenderWorkflowPresetOptions.value.reduce((acc, option) => {
    acc[option.value] = option.label
    return acc
  }, {})
)
const comfyRenderPromptStyleLabelMap = computed(() =>
  comfyRenderPromptStyleOptions.value.reduce((acc, option) => {
    acc[option.value] = option.label
    return acc
  }, {})
)
function parseComfySourceJsonSafe(rawText) {
  const trimmed = String(rawText || '').trim()
  if (!trimmed) return null
  try {
    const parsed = JSON.parse(trimmed)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null
  } catch {
    return null
  }
}

function buildComfyBuiltinRecommendationDecision(sourceType, inputPayload) {
  const normalizedSourceType = String(sourceType || 'custom_json').trim() || 'custom_json'
  const payload = inputPayload && typeof inputPayload === 'object' && !Array.isArray(inputPayload) ? inputPayload : {}

  if (normalizedSourceType === 'map_profile') {
    const gridCols = Number(payload.grid_cols || 0)
    const gridRows = Number(payload.grid_rows || 0)
    const blockedCount = Array.isArray(payload.blocked_cells)
      ? payload.blocked_cells.length
      : Number(payload.blocked_count || 0)
    const mapArea = gridCols * gridRows

    if (mapArea >= 120 || blockedCount >= 18) {
      return {
        key: 'showcase_realistic',
        reasonKey: 'map_profile_large_layout'
      }
    }
    return {
      key: 'preview_report',
      reasonKey: 'map_profile_compact_layout'
    }
  }

  if (normalizedSourceType === 'point_template_export') {
    const pointCount = Array.isArray(payload.points) ? payload.points.length : 0
    const templateCount = Array.isArray(payload.templates) ? payload.templates.length : 0
    if (templateCount >= 4 || pointCount >= 12) {
      return {
        key: 'preview_report',
        reasonKey: 'point_template_dense_planning'
      }
    }
    return {
      key: 'showcase_realistic',
      reasonKey: 'point_template_light_planning'
    }
  }

  if (normalizedSourceType === 'experiment_records') {
    const recordCount = Array.isArray(payload.records) ? payload.records.length : 0
    if (recordCount >= 3) {
      return {
        key: 'showcase_infographic',
        reasonKey: 'experiment_multi_record'
      }
    }
    return {
      key: 'preview_report',
      reasonKey: 'experiment_single_record'
    }
  }

  if (normalizedSourceType === 'map_profile_diff') {
    const relocatedCount = Array.isArray(payload.relocated_agvs)
      ? payload.relocated_agvs.length
      : Number(payload.relocated_agv_count || 0)
    const trimmedCount = Array.isArray(payload.trimmed_blocked_cells)
      ? payload.trimmed_blocked_cells.length
      : Number(payload.trimmed_blocked_count || 0)
    const totalChanges = relocatedCount + trimmedCount
    if (totalChanges >= 4) {
      return {
        key: 'showcase_infographic',
        reasonKey: 'map_diff_many_changes'
      }
    }
    return {
      key: 'preview_report',
      reasonKey: 'map_diff_few_changes'
    }
  }

  const payloadKeys = Object.keys(payload)
  const lowerKeys = payloadKeys.map(key => key.toLowerCase())
  if (lowerKeys.some(key => ['records', 'metrics', 'compare', 'summary'].includes(key))) {
    return {
      key: 'showcase_infographic',
      reasonKey: 'custom_metrics'
    }
  }
  if (lowerKeys.some(key => ['grid_cols', 'grid_rows', 'blocked_cells', 'layout', 'map'].includes(key))) {
    return {
      key: 'showcase_realistic',
      reasonKey: 'custom_layout'
    }
  }
  if (lowerKeys.some(key => ['points', 'templates', 'stages', 'waypoints'].includes(key))) {
    return {
      key: 'preview_report',
      reasonKey: 'custom_planning'
    }
  }
  return {
    key: 'showcase_realistic',
    reasonKey: 'custom_generic'
  }
}

const comfyRenderSourcePayloadPreview = computed(() =>
  parseComfySourceJsonSafe(comfyRenderInputJsonText.value)
)
const comfyRenderBuiltinTemplates = computed(() => {
  const sourceLabels = comfyRenderSourceLabelMap.value
  const presetLabels = comfyRenderWorkflowPresetLabelMap.value
  const styleLabels = comfyRenderPromptStyleLabelMap.value
  const recommendedSourcesByTemplate = {
    preview_report: ['point_template_export', 'map_profile_diff'],
    showcase_realistic: ['map_profile', 'custom_json'],
    showcase_infographic: ['experiment_records'],
    sdxl_hero: ['map_profile']
  }
  const buildTemplate = (key, label, hint, workflowPreset, promptStyle) => {
    const recommendedSourceKeys = recommendedSourcesByTemplate[key] || []
    return {
      key,
      label,
      hint,
      workflowPreset,
      workflowPresetLabel: presetLabels[workflowPreset] || workflowPreset,
      promptStyle,
      promptStyleLabel: styleLabels[promptStyle] || promptStyle,
      recommendedSources: recommendedSourceKeys.map(sourceKey => sourceLabels[sourceKey]).filter(Boolean)
    }
  }
  return [
    buildTemplate(
      'preview_report',
      t('ai_render_builtin_preview_report'),
      t('ai_render_builtin_preview_report_hint'),
      'preview',
      'report'
    ),
    buildTemplate(
      'showcase_realistic',
      t('ai_render_builtin_showcase_realistic'),
      t('ai_render_builtin_showcase_realistic_hint'),
      'showcase',
      'industrial_realistic'
    ),
    buildTemplate(
      'showcase_infographic',
      t('ai_render_builtin_showcase_infographic'),
      t('ai_render_builtin_showcase_infographic_hint'),
      'showcase',
      'infographic'
    ),
    buildTemplate(
      'sdxl_hero',
      t('ai_render_builtin_sdxl_hero'),
      t('ai_render_builtin_sdxl_hero_hint'),
      'sdxl_showcase',
      'industrial_realistic'
    )
  ]
})
const comfyRenderRecommendedBuiltinDecision = computed(() =>
  buildComfyBuiltinRecommendationDecision(
    comfyRenderSourceType.value,
    comfyRenderSourcePayloadPreview.value
  )
)
const comfyRenderRecommendedBuiltinTemplate = computed(() => {
  const targetKey = comfyRenderRecommendedBuiltinDecision.value?.key || 'showcase_realistic'
  return comfyRenderBuiltinTemplates.value.find(item => item.key === targetKey) || comfyRenderBuiltinTemplates.value[0] || null
})
const comfyRenderRecommendedBuiltinReasonText = computed(() => {
  const reasonKey = comfyRenderRecommendedBuiltinDecision.value?.reasonKey
  if (!reasonKey) return ''
  return t(`ai_render_recommend_reason_${reasonKey}`)
})
const comfyRenderSelectedBuiltinTemplate = computed(() =>
  comfyRenderBuiltinTemplates.value.find(item => item.key === comfyRenderBuiltinTemplateKey.value) ||
  comfyRenderRecommendedBuiltinTemplate.value ||
  comfyRenderBuiltinTemplates.value[0] ||
  null
)
const comfyRenderSelectedBuiltinTemplateMatchesRecommendation = computed(() =>
  Boolean(
    comfyRenderSelectedBuiltinTemplate.value?.key &&
    comfyRenderSelectedBuiltinTemplate.value?.key === comfyRenderRecommendedBuiltinTemplate.value?.key
  )
)
const comfyRenderWorkflowPresetConfig = computed(() =>
  getComfyWorkflowPresetConfig(comfyRenderWorkflowPreset.value)
)
const comfyRenderPromptStyleConfig = computed(() =>
  getComfyPromptStyleConfig(comfyRenderPromptStyle.value)
)
const comfyRenderWorkflowPresetSummary = computed(() =>
  formatInlineMessage(t('ai_render_workflow_preset_summary'), {
    size: `${comfyRenderWorkflowPresetConfig.value.width} x ${comfyRenderWorkflowPresetConfig.value.height}`,
    steps: comfyRenderWorkflowPresetConfig.value.steps
  })
)
const comfyRenderPromptStyleSummary = computed(() =>
  formatInlineMessage(t('ai_render_style_summary'), {
    tone: (comfyRenderPromptStyleConfig.value.promptFragments || []).slice(0, 2).join(', ')
  })
)
const comfyRenderRecommendedCheckpointSummary = computed(() =>
  formatInlineMessage(t('ai_render_checkpoint_recommendation'), {
    checkpoint: preferredComfyCheckpointName(comfyRenderAvailableCheckpoints.value, comfyRenderWorkflowPreset.value)
  })
)
const comfyRenderSelectedTemplate = computed(() =>
  comfyRenderSavedTemplates.value.find(item => String(item.id) === String(comfyRenderSelectedTemplateId.value || '')) || null
)
const comfyRenderHasCustomTemplates = computed(() => comfyRenderSavedTemplates.value.length > 0)
const comfyRenderSelectedSharedTemplate = computed(() =>
  comfyRenderSharedTemplates.value.find(item => String(item.id) === String(comfyRenderSelectedSharedTemplateId.value || '')) || null
)
const comfyRenderHasSharedTemplates = computed(() => comfyRenderSharedTemplates.value.length > 0)

function buildAiRenderSharedTemplatesHintText() {
  if (authCurrentRole.value === 'platform_admin') {
    return t('ai_render_shared_templates_hint_platform')
  }
  if (authCurrentOrganizationName.value) {
    return formatInlineMessage(t('ai_render_shared_templates_hint_org'), {
      organization: authCurrentOrganizationName.value
    })
  }
  return t('ai_render_shared_templates_hint')
}

function setComfyRenderStatus(message = '', type = 'info') {
  comfyRenderStatus.value = String(message || '')
  comfyRenderStatusType.value = type
}

function stringifyPrettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2)
}

function buildCurrentComfyTemplatePayload() {
  return {
    sourceType: String(comfyRenderSourceType.value || 'custom_json'),
    sourceRef: String(comfyRenderSourceRef.value || '').trim(),
    checkpointName: String(comfyRenderCheckpointName.value || '').trim(),
    workflowPreset: String(comfyRenderWorkflowPreset.value || COMFY_WORKFLOW_PRESET_DEFAULT),
    promptStyle: String(comfyRenderPromptStyle.value || COMFY_PROMPT_STYLE_DEFAULT),
    promptText: String(comfyRenderPromptText.value || '').trim(),
    inputJsonText: String(comfyRenderInputJsonText.value || '').trim(),
    workflowJsonText: String(comfyRenderWorkflowJsonText.value || '').trim()
  }
}

function normalizeComfyTemplateRecord(record) {
  if (!record || typeof record !== 'object') return null
  const id = String(record.id || '').trim() || `comfy_template_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  const name = String(record.name || '').trim()
  if (!name) return null
  return {
    id,
    name,
    sourceType: String(record.sourceType || 'custom_json'),
    sourceRef: String(record.sourceRef || '').trim(),
    checkpointName: String(record.checkpointName || '').trim(),
    workflowPreset: String(record.workflowPreset || COMFY_WORKFLOW_PRESET_DEFAULT),
    promptStyle: String(record.promptStyle || COMFY_PROMPT_STYLE_DEFAULT),
    promptText: String(record.promptText || '').trim(),
    inputJsonText: String(record.inputJsonText || '').trim(),
    workflowJsonText: String(record.workflowJsonText || '').trim(),
    createdAt: String(record.createdAt || new Date().toISOString()),
    updatedAt: String(record.updatedAt || new Date().toISOString())
  }
}

function normalizeComfySharedTemplateRecord(record) {
  const normalized = normalizeComfyTemplateRecord(record)
  if (!normalized) return null
  return {
    ...normalized,
    createdBy: String(record.created_by || record.createdBy || '').trim(),
    scope: String(record.scope || '').trim() || 'organization',
    scopeLabel: String(record.scope_label || record.scopeLabel || '').trim() || 'organization',
    editable: Boolean(record.editable)
  }
}

function loadComfyWorkflowTemplates() {
  try {
    const raw = window.localStorage.getItem(COMFY_WORKFLOW_TEMPLATE_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return
    comfyRenderSavedTemplates.value = parsed
      .map(item => normalizeComfyTemplateRecord(item))
      .filter(Boolean)
      .sort((a, b) => compareTime(b.updatedAt, a.updatedAt))
  } catch (error) {
    console.error('Load comfy workflow templates error:', error)
  }
}

function saveComfyWorkflowTemplates() {
  try {
    window.localStorage.setItem(
      COMFY_WORKFLOW_TEMPLATE_STORAGE_KEY,
      JSON.stringify(comfyRenderSavedTemplates.value)
    )
  } catch (error) {
    console.error('Save comfy workflow templates error:', error)
  }
}

function upsertSharedComfyTemplateRecord(record) {
  const normalized = normalizeComfySharedTemplateRecord(record)
  if (!normalized) return null
  const nextTemplates = comfyRenderSharedTemplates.value.filter(item => String(item.id) !== normalized.id)
  nextTemplates.unshift(normalized)
  comfyRenderSharedTemplates.value = nextTemplates.sort((a, b) => compareTime(b.updatedAt, a.updatedAt))
  return normalized
}

function uniqueComfyTemplateName(baseName, excludeId = '') {
  const normalizedBase = String(baseName || '').trim() || t('ai_render_template_default_name')
  const existing = comfyRenderSavedTemplates.value.filter(
    item => String(item.id) !== String(excludeId || '')
  )
  if (!existing.some(item => item.name === normalizedBase)) {
    return normalizedBase
  }
  let counter = 2
  while (existing.some(item => item.name === `${normalizedBase} (${counter})`)) {
    counter += 1
  }
  return `${normalizedBase} (${counter})`
}

function applyComfyTemplateRecord(record) {
  const normalized = normalizeComfyTemplateRecord(record)
  if (!normalized) return false
  comfyRenderSelectedTemplateId.value = normalized.id
  comfyRenderTemplateName.value = normalized.name
  comfyRenderSourceType.value = normalized.sourceType
  comfyRenderSourceRef.value = normalized.sourceRef
  comfyRenderWorkflowPreset.value = normalized.workflowPreset
  comfyRenderPromptStyle.value = normalized.promptStyle
  comfyRenderCheckpointName.value =
    normalized.checkpointName ||
    preferredComfyCheckpointName(comfyRenderAvailableCheckpoints.value, normalized.workflowPreset)
  comfyRenderPromptText.value = normalized.promptText
  comfyRenderInputJsonText.value = normalized.inputJsonText
  comfyRenderWorkflowJsonText.value = normalized.workflowJsonText
  return true
}

function applySelectedSharedTemplate() {
  if (!comfyRenderSelectedSharedTemplate.value) {
    setComfyRenderStatus(t('ai_render_shared_template_select_required'), 'error')
    return
  }
  if (applyComfyTemplateRecord(comfyRenderSelectedSharedTemplate.value)) {
    comfyRenderTemplateName.value = comfyRenderSelectedSharedTemplate.value.name
    setComfyRenderStatus(t('ai_render_shared_template_applied'), 'success')
  }
}

async function rebuildCurrentComfyWorkflowDraft({
  workflowPreset = comfyRenderWorkflowPreset.value,
  promptStyle = comfyRenderPromptStyle.value,
  checkpointName = comfyRenderCheckpointName.value,
  replacePrompt = true
} = {}) {
  await fetchComfyCheckpoints()
  if (comfyRenderSourceType.value === 'map_profile' && !String(comfyRenderSourceRef.value || '').trim()) {
    comfyRenderSourceRef.value = String(currentMapProfile.value?.key || '').trim()
  }
  const nextPrompt = buildDefaultComfyPromptText({
    sourceType: comfyRenderSourceType.value,
    sourceRef: comfyRenderSourceRef.value,
    presetKey: workflowPreset,
    styleKey: promptStyle
  })
  if (replacePrompt || !String(comfyRenderPromptText.value || '').trim()) {
    comfyRenderPromptText.value = nextPrompt
  }
  const resolvedCheckpoint =
    String(checkpointName || '').trim() ||
    preferredComfyCheckpointName(comfyRenderAvailableCheckpoints.value, workflowPreset)
  comfyRenderCheckpointName.value = resolvedCheckpoint
  comfyRenderWorkflowJsonText.value = stringifyPrettyJson(
    buildDefaultComfyWorkflowTemplate({
      checkpointName: resolvedCheckpoint,
      promptText: comfyRenderPromptText.value,
      sourceType: comfyRenderSourceType.value,
      sourceRef: comfyRenderSourceRef.value,
      presetKey: workflowPreset,
      styleKey: promptStyle
    })
  )
}

function preferredComfyCheckpointName(
  names = comfyRenderAvailableCheckpoints.value,
  presetKey = comfyRenderWorkflowPreset.value
) {
  const normalized = Array.isArray(names)
    ? names.map(item => String(item || '').trim()).filter(Boolean)
    : []
  const preferredOrder =
    String(presetKey || '').trim().toLowerCase() === 'sdxl_showcase'
      ? [
          'juggernautxl.2j0I.safetensors',
          'DreamShaper_8_pruned.safetensors',
          'majicmixRealistic_v7.safetensors'
        ]
      : [
          'DreamShaper_8_pruned.safetensors',
          'majicmixRealistic_v7.safetensors',
          'juggernautxl.2j0I.safetensors'
        ]
  if (!normalized.length) return preferredOrder[0]
  return (
    preferredOrder.find(name => normalized.includes(name)) ||
    normalized[0]
  )
}

watch(comfyRenderWorkflowPreset, (nextPreset, previousPreset) => {
  const available = comfyRenderAvailableCheckpoints.value
  const current = String(comfyRenderCheckpointName.value || '').trim()
  const previousPreferred = preferredComfyCheckpointName(available, previousPreset)
  const nextPreferred = preferredComfyCheckpointName(available, nextPreset)
  if (!current || !available.includes(current) || current === previousPreferred) {
    comfyRenderCheckpointName.value = nextPreferred
  }
})

watch(
  comfyRenderRecommendedBuiltinTemplate,
  nextTemplate => {
    if (!nextTemplate) return
    const currentKey = String(comfyRenderBuiltinTemplateKey.value || '').trim()
    const exists = comfyRenderBuiltinTemplates.value.some(item => item.key === currentKey)
    if (!exists) {
      comfyRenderBuiltinTemplateKey.value = nextTemplate.key
    }
  },
  { immediate: true }
)

function buildComfyRenderInputSummary(sourceType, sourceRef, inputPayload) {
  const summary = {
    source_type: String(sourceType || 'custom_json'),
    top_level_keys:
      inputPayload && typeof inputPayload === 'object' && !Array.isArray(inputPayload)
        ? Object.keys(inputPayload).sort()
        : []
  }
  if (sourceRef) {
    summary.source_ref = String(sourceRef)
  }
  if (sourceType === 'point_template_export') {
    summary.point_count = Array.isArray(inputPayload?.points) ? inputPayload.points.length : 0
    summary.template_count = Array.isArray(inputPayload?.templates) ? inputPayload.templates.length : 0
  }
  if (sourceType === 'experiment_records') {
    summary.record_count = Array.isArray(inputPayload?.records) ? inputPayload.records.length : 0
  }
  if (sourceType === 'map_profile_diff') {
    summary.relocated_agv_count = Number(inputPayload?.relocated_agv_count || 0)
    summary.trimmed_blocked_cells_count = Number(inputPayload?.trimmed_blocked_cells_count || 0)
  }
  return summary
}

function formatComfyRenderStatus(status) {
  return t(`ai_render_status_${String(status || 'submitted').toLowerCase()}`)
}

function formatComfyRenderSource(job) {
  const typeLabel =
    comfyRenderSourceOptions.value.find(option => option.value === job?.source_type)?.label ||
    String(job?.source_type || '')
  const sourceRef = String(job?.source_ref || '').trim()
  return sourceRef ? `${typeLabel} · ${sourceRef}` : typeLabel
}

function formatComfyRenderAssetActionLabel(job, assetIndex) {
  const assetCount = Array.isArray(job?.asset_urls) ? job.asset_urls.length : 0
  if (assetCount <= 1) return t('ai_render_result_preview')
  return `${t('ai_render_result_preview')} ${Number(assetIndex) + 1}`
}

function formatPanelComfyRenderJobMeta(job) {
  return `${job?.created_by || 'system'} · ${job?.created_at || '—'}`
}

function formatEnterpriseComfyRenderJobMeta(job) {
  return formatDateTimeInline(job?.created_at) || '—'
}

const comfyRenderLastFetchedText = computed(() =>
  comfyRenderLastFetchedAt.value
    ? formatInlineMessage(t('operations_last_updated'), { at: comfyRenderLastFetchedAt.value })
    : ''
)

const comfyRenderSelectedSharedTemplateMetaText = computed(() => {
  if (!comfyRenderSelectedSharedTemplate.value) return ''
  return formatInlineMessage(t('ai_render_shared_template_meta'), {
    scope: t(
      `ai_render_shared_scope_${comfyRenderSelectedSharedTemplate.value.scopeLabel || comfyRenderSelectedSharedTemplate.value.scope || 'organization'}`
    ),
    createdBy: comfyRenderSelectedSharedTemplate.value.createdBy || 'system',
    updatedAt: formatDateTimeInline(comfyRenderSelectedSharedTemplate.value.updatedAt)
  })
})

function openComfyRenderAssetPreview(job, assetUrl, assetIndex = 0) {
  comfyRenderPreviewUrl.value = String(assetUrl || '').trim()
  comfyRenderPreviewTitle.value = `${formatComfyRenderSource(job)} · ${t('ai_render_result_preview')} ${Number(assetIndex) + 1}`
  comfyRenderPreviewJobId.value = Number(job?.id || 0) || null
  comfyRenderPreviewVisible.value = Boolean(comfyRenderPreviewUrl.value)
}

function closeComfyRenderAssetPreview() {
  comfyRenderPreviewVisible.value = false
  comfyRenderPreviewUrl.value = ''
  comfyRenderPreviewTitle.value = ''
  comfyRenderPreviewJobId.value = null
}

function saveCurrentComfyTemplate() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  const requestedName = String(comfyRenderTemplateName.value || '').trim()
  const existingId = String(comfyRenderSelectedTemplateId.value || '').trim()
  const existingTemplate = comfyRenderSavedTemplates.value.find(item => String(item.id) === existingId)
  const normalizedPayload = normalizeComfyTemplateRecord({
    id: existingId || undefined,
    name: uniqueComfyTemplateName(
      requestedName || existingTemplate?.name || t('ai_render_template_default_name'),
      existingId
    ),
    ...buildCurrentComfyTemplatePayload(),
    createdAt: existingTemplate?.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString()
  })
  if (!normalizedPayload) {
    setComfyRenderStatus(t('ai_render_template_save_failed'), 'error')
    return
  }
  const nextTemplates = comfyRenderSavedTemplates.value.filter(item => String(item.id) !== normalizedPayload.id)
  nextTemplates.unshift(normalizedPayload)
  comfyRenderSavedTemplates.value = nextTemplates.sort((a, b) => compareTime(b.updatedAt, a.updatedAt))
  saveComfyWorkflowTemplates()
  comfyRenderSelectedTemplateId.value = normalizedPayload.id
  comfyRenderTemplateName.value = normalizedPayload.name
  setComfyRenderStatus(t('ai_render_template_saved'), 'success')
}

function applySelectedComfyTemplate() {
  if (!comfyRenderSelectedTemplate.value) {
    setComfyRenderStatus(t('ai_render_template_select_required'), 'error')
    return
  }
  if (applyComfyTemplateRecord(comfyRenderSelectedTemplate.value)) {
    setComfyRenderStatus(t('ai_render_template_applied'), 'success')
  }
}

function exportSelectedComfyTemplate() {
  if (!comfyRenderSelectedTemplate.value) {
    setComfyRenderStatus(t('ai_render_template_select_required'), 'error')
    return
  }
  downloadJsonFile(
    `agv-comfy-template-${String(comfyRenderSelectedTemplate.value.name).replace(/[^a-zA-Z0-9]+/g, '_') || 'template'}.json`,
    JSON.stringify(comfyRenderSelectedTemplate.value, null, 2)
  )
  setComfyRenderStatus(t('ai_render_template_exported'), 'success')
}

function deleteSelectedComfyTemplate() {
  if (!comfyRenderSelectedTemplate.value) {
    setComfyRenderStatus(t('ai_render_template_select_required'), 'error')
    return
  }
  if (!window.confirm(t('ai_render_template_delete_confirm'))) return
  const deletingId = String(comfyRenderSelectedTemplate.value.id)
  comfyRenderSavedTemplates.value = comfyRenderSavedTemplates.value.filter(item => String(item.id) !== deletingId)
  saveComfyWorkflowTemplates()
  comfyRenderSelectedTemplateId.value = ''
  comfyRenderTemplateName.value = ''
  setComfyRenderStatus(t('ai_render_template_deleted'), 'success')
}

async function fetchComfySharedTemplates({ force = false } = {}) {
  if (!authAuthenticated.value || !authCanAiRender.value) {
    comfyRenderSharedTemplates.value = []
    comfyRenderSelectedSharedTemplateId.value = ''
    return
  }
  if (comfyRenderSharedTemplatesLoading.value) return
  if (!force && comfyRenderSharedTemplates.value.length > 0) return
  comfyRenderSharedTemplatesLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/ai/comfyui/templates`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json()
    if (!response.ok) {
      throw createApiError(data, 'Shared Comfy workflow template request failed')
    }
    comfyRenderSharedTemplates.value = Array.isArray(data?.items)
      ? data.items.map(item => normalizeComfySharedTemplateRecord(item)).filter(Boolean)
      : []
    if (
      comfyRenderSelectedSharedTemplateId.value &&
      !comfyRenderSharedTemplates.value.some(item => String(item.id) === String(comfyRenderSelectedSharedTemplateId.value))
    ) {
      comfyRenderSelectedSharedTemplateId.value = ''
    }
  } catch (error) {
    console.error('Fetch shared comfy workflow templates error:', error)
    if (force) {
      setComfyRenderStatus(error?.message || t('ai_render_shared_templates_load_failed'), 'error')
    }
  } finally {
    comfyRenderSharedTemplatesLoading.value = false
  }
}

async function saveCurrentComfySharedTemplate() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  comfyRenderSharedTemplateSaving.value = true
  try {
    const existingTemplate = comfyRenderSelectedSharedTemplate.value
    const response = await fetch(`${API_BASE}/ai/comfyui/templates`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        id: existingTemplate?.editable ? existingTemplate.id : null,
        name:
          String(comfyRenderTemplateName.value || '').trim() ||
          existingTemplate?.name ||
          t('ai_render_template_default_name'),
        ...buildCurrentComfyTemplatePayload()
      })
    })
    const data = await response.json()
    if (!response.ok) {
      throw createApiError(data, 'Shared Comfy workflow template save failed')
    }
    const saved = upsertSharedComfyTemplateRecord(data?.template)
    if (!saved) {
      throw new Error(t('ai_render_shared_template_save_failed'))
    }
    comfyRenderSelectedSharedTemplateId.value = saved.id
    comfyRenderTemplateName.value = saved.name
    setComfyRenderStatus(t('ai_render_shared_template_saved'), 'success')
  } catch (error) {
    console.error('Save shared comfy workflow template error:', error)
    setComfyRenderStatus(error?.message || t('ai_render_shared_template_save_failed'), 'error')
  } finally {
    comfyRenderSharedTemplateSaving.value = false
  }
}

async function deleteSelectedSharedTemplate() {
  if (!comfyRenderSelectedSharedTemplate.value) {
    setComfyRenderStatus(t('ai_render_shared_template_select_required'), 'error')
    return
  }
  if (!comfyRenderSelectedSharedTemplate.value.editable) {
    setComfyRenderStatus(t('auth_permission_denied_default'), 'error')
    return
  }
  if (!window.confirm(t('ai_render_shared_template_delete_confirm'))) return
  try {
    const response = await fetch(
      `${API_BASE}/ai/comfyui/templates/${encodeURIComponent(comfyRenderSelectedSharedTemplate.value.id)}`,
      {
        method: 'DELETE',
        headers: buildAuthorizedHeaders()
      }
    )
    const data = await response.json()
    if (!response.ok) {
      throw createApiError(data, 'Shared Comfy workflow template delete failed')
    }
    const deletingId = String(comfyRenderSelectedSharedTemplate.value.id)
    comfyRenderSharedTemplates.value = comfyRenderSharedTemplates.value.filter(item => String(item.id) !== deletingId)
    comfyRenderSelectedSharedTemplateId.value = ''
    setComfyRenderStatus(t('ai_render_shared_template_deleted'), 'success')
  } catch (error) {
    console.error('Delete shared comfy workflow template error:', error)
    setComfyRenderStatus(error?.message || t('ai_render_shared_template_delete_failed'), 'error')
  }
}

async function onComfyTemplateFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    const normalized = normalizeComfyTemplateRecord({
      ...parsed,
      id: undefined,
      name: uniqueComfyTemplateName(parsed?.name || file.name.replace(/\.[^.]+$/, ''))
    })
    if (!normalized) {
      throw new Error(t('ai_render_template_import_failed'))
    }
    comfyRenderSavedTemplates.value = [normalized, ...comfyRenderSavedTemplates.value].sort((a, b) =>
      compareTime(b.updatedAt, a.updatedAt)
    )
    saveComfyWorkflowTemplates()
    applyComfyTemplateRecord(normalized)
    setComfyRenderStatus(t('ai_render_template_imported'), 'success')
  } catch (error) {
    console.error('Import comfy workflow template error:', error)
    setComfyRenderStatus(error?.message || t('ai_render_template_import_failed'), 'error')
  }
}

function parseJsonObjectOrThrow(rawText, fallbackValue, errorMessage) {
  const trimmed = String(rawText || '').trim()
  if (!trimmed) {
    return fallbackValue
  }
  try {
    const parsed = JSON.parse(trimmed)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(errorMessage)
    }
    return parsed
  } catch {
    throw new Error(errorMessage)
  }
}

async function buildComfySourcePayload() {
  const sourceType = comfyRenderSourceType.value
  if (sourceType === 'map_profile') {
    const targetProfileKey = String(comfyRenderSourceRef.value || currentMapProfile.value?.key || '').trim()
    if (!targetProfileKey) {
      throw new Error(t('ai_render_source_ref_required'))
    }
    const response = await fetch(`${API_BASE}/status/map/profile/${encodeURIComponent(targetProfileKey)}`)
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Map profile request failed')
    }
    return {
      sourceRef: targetProfileKey,
      inputPayload: data ?? {}
    }
  }

  if (sourceType === 'point_template_export') {
    return {
      sourceRef: null,
      inputPayload: {
        points: pointLibrary.value,
        templates: taskTemplates.value
      }
    }
  }

  if (sourceType === 'experiment_records') {
    return {
      sourceRef: null,
      inputPayload: {
        records: experimentRecords.value
      }
    }
  }

  if (sourceType === 'map_profile_diff') {
    if (!mapProfileActionSummary.value) {
      throw new Error(t('ai_render_source_diff_unavailable'))
    }
    return {
      sourceRef: String(mapProfileActionSummary.value?.profile_key || mapProfileActionSummary.value?.profileKey || '').trim() || null,
      inputPayload: mapProfileActionSummary.value
    }
  }

  return {
    sourceRef: String(comfyRenderSourceRef.value || '').trim() || null,
    inputPayload: parseJsonObjectOrThrow(
      comfyRenderInputJsonText.value,
      {},
      t('ai_render_parse_input_failed')
    )
  }
}

async function loadComfySourcePayload() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  try {
    const built = await buildComfySourcePayload()
    comfyRenderSourceRef.value = built.sourceRef || ''
    comfyRenderInputJsonText.value = stringifyPrettyJson(built.inputPayload)
    setComfyRenderStatus(t('ai_render_source_loaded'), 'success')
  } catch (error) {
    setComfyRenderStatus(error?.message || t('ai_render_load_source_failed'), 'error')
  }
}

async function fetchComfyCheckpoints({ force = false } = {}) {
  if (!authAuthenticated.value || !authCanAiRender.value) {
    comfyRenderAvailableCheckpoints.value = []
    comfyRenderCheckpointName.value = ''
    return
  }
  if (comfyRenderCheckpointsLoading.value) return
  if (!force && comfyRenderAvailableCheckpoints.value.length > 0) return

  comfyRenderCheckpointsLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/ai/comfyui/checkpoints`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Comfy checkpoint request failed')
    }
    const items = Array.isArray(data?.items) ? data.items.map(item => String(item || '').trim()).filter(Boolean) : []
    comfyRenderAvailableCheckpoints.value = items
    const preferred = String(data?.preferred || preferredComfyCheckpointName(items)).trim()
    if (!String(comfyRenderCheckpointName.value || '').trim() || !items.includes(String(comfyRenderCheckpointName.value || '').trim())) {
      comfyRenderCheckpointName.value = preferred
    }
  } catch (error) {
    console.error('Fetch ComfyUI checkpoints error:', error)
    comfyRenderAvailableCheckpoints.value = []
    if (!String(comfyRenderCheckpointName.value || '').trim()) {
      comfyRenderCheckpointName.value = preferredComfyCheckpointName([])
    }
  } finally {
    comfyRenderCheckpointsLoading.value = false
  }
}

async function loadDefaultComfyWorkflow() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  try {
    await rebuildCurrentComfyWorkflowDraft()
    setComfyRenderStatus(t('ai_render_default_workflow_loaded'), 'success')
  } catch (error) {
    setComfyRenderStatus(error?.message || t('ai_render_submit_failed'), 'error')
  }
}

async function applyBuiltinComfyTemplate(templateKey) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  const matched = comfyRenderBuiltinTemplates.value.find(item => item.key === templateKey)
  if (!matched) {
    setComfyRenderStatus(t('ai_render_template_select_required'), 'error')
    return
  }
  try {
    comfyRenderWorkflowPreset.value = matched.workflowPreset
    comfyRenderPromptStyle.value = matched.promptStyle
    comfyRenderTemplateName.value = matched.label
    comfyRenderSelectedTemplateId.value = ''
    await rebuildCurrentComfyWorkflowDraft({
      workflowPreset: matched.workflowPreset,
      promptStyle: matched.promptStyle,
      checkpointName: preferredComfyCheckpointName(comfyRenderAvailableCheckpoints.value, matched.workflowPreset)
    })
    comfyRenderBuiltinTemplatesOverviewVisible.value = false
    setComfyRenderStatus(t('ai_render_builtin_applied'), 'success')
  } catch (error) {
    setComfyRenderStatus(error?.message || t('ai_render_submit_failed'), 'error')
  }
}

async function applySelectedBuiltinComfyTemplate() {
  if (!comfyRenderSelectedBuiltinTemplate.value) {
    setComfyRenderStatus(t('ai_render_template_select_required'), 'error')
    return
  }
  await applyBuiltinComfyTemplate(comfyRenderSelectedBuiltinTemplate.value.key)
}

function openComfyBuiltinTemplateOverview() {
  comfyRenderBuiltinTemplatesOverviewVisible.value = true
}

function closeComfyBuiltinTemplateOverview() {
  comfyRenderBuiltinTemplatesOverviewVisible.value = false
}

async function fetchComfyRenderJobs({ force = false } = {}) {
  if (!authAuthenticated.value || !authCanAiRender.value) {
    comfyRenderJobs.value = []
    comfyRenderLastFetchedAt.value = ''
    return
  }
  if (comfyRenderLoading.value) return
  if (!force && !panelSections.value.ai) return

  comfyRenderLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/ai/comfyui/jobs?limit=24`, {
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Comfy render job request failed')
    }
    comfyRenderJobs.value = Array.isArray(data?.items) ? data.items : []
    comfyRenderLastFetchedAt.value = new Date().toISOString()
  } catch (error) {
    console.error('Fetch ComfyUI render jobs error:', error)
    if (force) {
      showFloatingToast(error?.message || t('ai_render_load_failed'), 'error')
    }
  } finally {
    comfyRenderLoading.value = false
  }
}

async function submitComfyRenderJob() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  if (comfyRenderSubmitting.value) return

  comfyRenderSubmitting.value = true
  try {
    const { sourceRef, inputPayload } = await buildComfySourcePayload()
    const workflowPayload = parseJsonObjectOrThrow(
      comfyRenderWorkflowJsonText.value,
      {},
      t('ai_render_parse_workflow_failed')
    )
    const response = await fetch(`${API_BASE}/ai/comfyui/render`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        source_type: comfyRenderSourceType.value,
        source_ref: sourceRef,
        input_payload: inputPayload,
        input_summary: buildComfyRenderInputSummary(comfyRenderSourceType.value, sourceRef, inputPayload),
        prompt_text: String(comfyRenderPromptText.value || '').trim() || null,
        workflow_payload: workflowPayload
      })
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Comfy render submit failed')
    }
    setComfyRenderStatus(t('ai_render_submit_success'), 'success')
    showFloatingToast(t('ai_render_submit_success'), 'success')
    await fetchComfyRenderJobs({ force: true })
  } catch (error) {
    setComfyRenderStatus(error?.message || t('ai_render_submit_failed'), 'error')
    showFloatingToast(error?.message || t('ai_render_submit_failed'), 'error')
  } finally {
    comfyRenderSubmitting.value = false
  }
}

async function deleteComfyRenderJob(jobId) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'ai.render', buildCapabilityDeniedMessage('ai'))) return
  if (!jobId || deletingComfyJobId.value === jobId) return
  if (!window.confirm(t('ai_render_delete_confirm'))) return

  deletingComfyJobId.value = jobId
  try {
    const response = await fetch(`${API_BASE}/ai/comfyui/jobs/${jobId}`, {
      method: 'DELETE',
      headers: buildAuthorizedHeaders()
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Comfy render delete failed')
    }
    if (Number(jobId) && Number(jobId) === Number(comfyRenderPreviewJobId.value || 0)) {
      closeComfyRenderAssetPreview()
    }
    setComfyRenderStatus(t('ai_render_delete_success'), 'success')
    showFloatingToast(t('ai_render_delete_success'), 'success')
    await fetchComfyRenderJobs({ force: true })
  } catch (error) {
    setComfyRenderStatus(error?.message || t('ai_render_delete_failed'), 'error')
    showFloatingToast(error?.message || t('ai_render_delete_failed'), 'error')
  } finally {
    deletingComfyJobId.value = null
  }
}

function pulseFaultSelectedCard() {
  faultSelectedAgvPulse.value = true
  if (faultSelectedAgvPulseTimer) {
    clearTimeout(faultSelectedAgvPulseTimer)
  }
  faultSelectedAgvPulseTimer = setTimeout(() => {
    faultSelectedAgvPulse.value = false
    faultSelectedAgvPulseTimer = null
  }, 2200)
}

async function focusTaskBuilder(mode = taskBuilderMode.value) {
  taskBuilderMode.value = mode
  await jumpToPanelSearchResult('control')
  await nextTick()
  const panelElement = panelRef.value
  const builderElement = taskBuilderRef.value
  if (panelElement && builderElement) {
    const panelRect = panelElement.getBoundingClientRect()
    const builderRect = builderElement.getBoundingClientRect()
    const top = Math.max(panelElement.scrollTop + (builderRect.top - panelRect.top) - 12, 0)
    panelElement.scrollTo({ top, behavior: 'smooth' })
  }
  hideTaskBuilderJumpButton()
}

async function jumpToRecoveryAgvCard() {
  const targetAgvId = agvRecoveryJumpTargetAgvId.value
  if (!targetAgvId) return
  selectedAgvId.value = targetAgvId
  showFaultReportForm.value = false
  await jumpToPanelSearchResult('control')
  await nextTick()

  const panelElement = panelRef.value
  const faultCardElement = faultSelectedAgvCardRef.value
  if (panelElement && faultCardElement) {
    const panelRect = panelElement.getBoundingClientRect()
    const cardRect = faultCardElement.getBoundingClientRect()
    const top = Math.max(panelElement.scrollTop + (cardRect.top - panelRect.top) - 10, 0)
    panelElement.scrollTo({ top, behavior: 'smooth' })
  }
  pulseFaultSelectedCard()
  hideAgvRecoveryJumpButton()
}

function toggleDispatchModeFromSummary() {
  dispatchMode.value = dispatchMode.value === 'auto' ? 'manual' : 'auto'
}

function setDispatchModeFromEnterprise(nextMode) {
  const normalizedMode = String(nextMode || '').toLowerCase()
  if (!['auto', 'manual'].includes(normalizedMode)) return
  if (
    !ensureAuthenticatedOperation(
      t('auth_action_requires_login'),
      'dispatch.write',
      buildCapabilityDeniedMessage('dispatch')
    )
  ) {
    return
  }
  dispatchMode.value = normalizedMode
}

function setRuntimeAlgorithmFromEnterprise(nextAlgorithm) {
  const normalizedAlgorithm = String(nextAlgorithm || '').toLowerCase()
  if (!['simple', 'astar'].includes(normalizedAlgorithm)) return
  if (
    !ensureAuthenticatedOperation(
      t('auth_action_requires_login'),
      'experiment.write',
      buildCapabilityDeniedMessage('data')
    )
  ) {
    return
  }
  algorithm.value = normalizedAlgorithm
}

function setCompareDisplayModeFromEnterprise(nextMode) {
  const normalizedMode = String(nextMode || '').toLowerCase()
  if (!['panel', 'floating'].includes(normalizedMode)) return
  compareDisplayMode.value = normalizedMode
}

function buildTemplateExportPayload() {
  return buildTemplateExportPayloadRaw(customTaskTemplates.value, {
    normalizeStages: normalizeTemplateStages
  })
}

async function hydratePointTemplateBackend() {
  const legacyCustomPoints = [...customPoints.value]
  const legacyCustomTemplates = [...customTaskTemplates.value]

  const pointsOk = await fetchPointLibraryFromBackend()
  if (pointsOk) {
    await syncLegacyCustomPointsToBackend(legacyCustomPoints)
  }

  const templatesOk = await fetchTaskTemplatesFromBackend()
  if (templatesOk) {
    await syncLegacyCustomTemplatesToBackend(legacyCustomTemplates)
  }
}

const {
  fetchPointLibraryFromBackend,
  fetchTaskTemplatesFromBackend,
  savePointToBackend,
  deletePointFromBackend,
  saveTemplateToBackend,
  saveTemplatesBatchToBackend,
  deleteTemplateFromBackend,
  syncLegacyCustomPointsToBackend,
  syncLegacyCustomTemplatesToBackend
} = usePointTemplateBackend({
  API_BASE,
  GRID_COLS: currentGridCols,
  GRID_ROWS: currentGridRows,
  defaultPoints: DEFAULT_POINT_LIBRARY,
  defaultTemplates: DEFAULT_TASK_TEMPLATES,
  builtinPoints,
  builtinTemplates,
  pointsLoadedFromApi,
  templatesLoadedFromApi,
  customPoints,
  customTaskTemplates,
  normalizeTemplateStages,
  isValidGridCoordinate,
  createApiError
})

const {
  applyPointToTaskForm,
  addCustomPoint,
  deleteCustomPoint,
  onTemplateApplyClick,
  onTemplateApplyDoubleClick,
  saveCurrentTaskAsTemplate,
  saveCurrentTaskChainAsTemplate,
  deleteTaskTemplate,
  exportTaskTemplatesToJson,
  clearTemplateJsonText,
  importTaskTemplatesFromJson,
  downloadTemplateJsonFile,
  handleTemplateFileChange
} = useTemplatePointActions({
  t,
  GRID_COLS: currentGridCols,
  GRID_ROWS: currentGridRows,
  taskForm,
  taskChainStages,
  taskBuilderMode,
  taskTemplateForm,
  customPointForm,
  customPoints,
  customTaskTemplates,
  pointFormStatus,
  pointFormStatusType,
  taskTemplateStatus,
  taskTemplateStatusType,
  templateJsonText,
  templateJsonStatus,
  templateJsonStatusType,
  taskBuilderLocale,
  templateJsonLocale,
  normalizeTemplateStages,
  buildTemplateFromStages,
  buildTaskTemplateSignature,
  normalizeImportedTaskTemplate,
  formatTemplateJsonSummary,
  buildTemplateExportPayload,
  isValidGridCoordinate,
  createTaskChainStage,
  buildCustomPoint,
  savePointToBackend,
  deletePointFromBackend,
  saveTemplateToBackend,
  saveTemplatesBatchToBackend,
  deleteTemplateFromBackend,
  syncManualDispatchBuilderState,
  hideTaskBuilderJumpButton,
  showTaskBuilderJumpButton,
  focusTaskBuilder
})

function togglePanelSection(sectionKey) {
  panelSections.value = {
    ...panelSections.value,
    [sectionKey]: !panelSections.value[sectionKey]
  }
}

function setAllPanelSections(expanded) {
  const nextSections = { ...panelSections.value }
  for (const key of visiblePanelSectionKeys.value) {
    nextSections[key] = expanded
  }
  panelSections.value = nextSections
}

function hasIdleAgv() {
  return agvs.value.some(agv => isSchedulableIdleAgvStatus(agv?.status))
}

function isSchedulableIdleAgvStatus(status) {
  return ['idle', 'idle_returning'].includes(String(status || ''))
}

function hasPendingTask() {
  return tasks.value.some(task => task.status === 'pending')
}

function hasActiveTask() {
  return tasks.value.some(task => task.status === 'assigned' || task.status === 'running')
}

const { tryAutoSchedule, tryManualBoundSchedule, scheduleAutoIfReady } = useDispatchScheduler({
  API_BASE,
  GRID_COLS: currentGridCols,
  GRID_ROWS: currentGridRows,
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
})

function clearAutoPaths() {
  autoPathToStart.value = []
  autoPathToEnd.value = []
}

function clearAutoMarkers() {
  mapDraftPrimedMode.value = null
  autoDraftPicking.value = false
  startPoint.value = null
  endPoint.value = null
}

function clearManualDestination() {
  mapDraftPrimedMode.value = null
  manualDraftPicking.value = false
  endPoint.value = null
  manualPathToStart.value = []
  manualPathToEnd.value = []
}

function clearManualPaths() {
  manualPathToStart.value = []
  manualPathToEnd.value = []
}

function clearManualDispatchPreview() {
  if (manualPreviewHoldTimer) {
    clearTimeout(manualPreviewHoldTimer)
    manualPreviewHoldTimer = null
  }
  mapDraftPrimedMode.value = null
  manualDraftPicking.value = false
  trackedManualTaskId.value = null
  manualDispatchStep.value = 'idle'
  manualPreviewMinVisibleUntil.value = 0
  taskChainMapPickActive.value = false
  taskChainMapPickPoints.value = []
  startPoint.value = null
  endPoint.value = null
  clearManualPaths()
}

function bumpManualPreviewMinVisible(durationMs = 1400) {
  manualPreviewMinVisibleUntil.value = Date.now() + durationMs
}

function cancelSelection() {
  selectedAgvId.value = null
  clearManualDispatchPreview()
  clearManualDestination()
  showFaultReportForm.value = false
}

function getSelectedManualDispatchAgv(alertOnFailure = true) {
  if (dispatchMode.value !== 'manual') return null
  if (!selectedBackendAgv.value) {
    if (alertOnFailure) {
      window.alert(currentTaskBuilderHint.value)
    }
    return null
  }
  if (!isSchedulableIdleAgvStatus(selectedBackendAgv.value.status)) {
    if (alertOnFailure) {
      if (locale.value === 'ja') {
        window.alert('手動派車では待機中または回庫中の AGV を指定できます。')
      } else if (locale.value === 'zh') {
        window.alert('手动派车只能指定空闲或回仓中的 AGV。')
      } else {
        window.alert('Manual dispatch can only target idle or returning AGVs.')
      }
    }
    return null
  }
  return selectedBackendAgv.value
}

const {
  addTaskChainStage,
  removeTaskChainStage,
  resetTaskChainStages,
  setTaskChainMapPickStageCount,
  toggleTaskBuilderMode,
  cancelTaskChainMapPick,
  toggleTaskChainMapPick
} = useTaskBuilderState({
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
})

function syncManualDispatchBuilderState() {
  const agv = getSelectedManualDispatchAgv(false)
  if (!agv || trackedManualTaskId.value) return
}

function syncDisplayedPathsFromTasks() {
  const autoTask = findLatestActiveTask('auto')
  if (autoTask) {
    autoPathToStart.value = autoTask.path_to_start ?? []
    autoPathToEnd.value = autoTask.path_to_end ?? []
  } else {
    clearAutoPaths()
  }

  const manualTask = manualDisplayTask.value
  if (manualTask) {
    manualPathToStart.value = manualTask.path_to_start ?? []
    manualPathToEnd.value = manualTask.path_to_end ?? []
  } else {
    const shouldHoldManualPreview =
      Boolean(trackedManualTaskId.value) && manualPreviewMinVisibleUntil.value > Date.now()
    const shouldHoldAutoDraft =
      dispatchMode.value === 'auto' &&
      (autoDraftPicking.value || taskChainMapPickActive.value || mapDraftPrimedMode.value === 'auto')
    if (!shouldHoldManualPreview) {
      clearManualPaths()
      if (
        dispatchMode.value === 'auto' &&
        !shouldHoldAutoDraft &&
        !manualDisplayTask.value
      ) {
        startPoint.value = null
        endPoint.value = null
      }
    }
  }
}

function isCellOccupied(x, y) {
  return displayAgvs.value.some(agv => agv.x === x && agv.y === y)
}

const protectedMapCellSet = computed(() => {
  const keys = new Set()

  for (const agv of displayAgvs.value) {
    if (Number.isInteger(agv?.x) && Number.isInteger(agv?.y)) {
      keys.add(blockedCellKey(agv.x, agv.y))
    }
  }

  for (const point of pointLibrary.value) {
    if (Number.isInteger(point?.x) && Number.isInteger(point?.y)) {
      keys.add(blockedCellKey(point.x, point.y))
    }
  }

  for (const task of tasks.value) {
    const stages = Array.isArray(task?.stages) && task.stages.length ? task.stages : [task]
    for (const stage of stages) {
      if (Number.isInteger(stage?.start_x) && Number.isInteger(stage?.start_y)) {
        keys.add(blockedCellKey(stage.start_x, stage.start_y))
      }
      if (Number.isInteger(stage?.end_x) && Number.isInteger(stage?.end_y)) {
        keys.add(blockedCellKey(stage.end_x, stage.end_y))
      }
    }
  }

  for (const template of taskTemplates.value) {
    const stages = Array.isArray(template?.stages) && template.stages.length ? template.stages : [template]
    for (const stage of stages) {
      if (Number.isInteger(stage?.start_x) && Number.isInteger(stage?.start_y)) {
        keys.add(blockedCellKey(stage.start_x, stage.start_y))
      }
      if (Number.isInteger(stage?.end_x) && Number.isInteger(stage?.end_y)) {
        keys.add(blockedCellKey(stage.end_x, stage.end_y))
      }
    }
  }

  return keys
})

function isProtectedMapCell(x, y) {
  return protectedMapCellSet.value.has(blockedCellKey(x, y))
}

const {
  syncPanelWidth,
  resetMapView,
  changeMapZoom,
  clampMapTransform,
  updateMapViewportMetrics,
  focusMapAtWorld,
  getCellFromEvent,
  getCellFromClient,
  onMapWheel,
  startPanelResize,
  onMinimapMouseDown,
  onWindowResize,
  handleGlobalMouseMove,
  handleGlobalMouseUp
} = useMapViewport({
  constants: {
    MAP_WIDTH: mapWidth,
    MAP_HEIGHT: mapHeight,
    MINIMAP_WIDTH,
    MIN_ZOOM,
    MAX_ZOOM,
    CELL_SIZE,
    GRID_COLS: currentGridCols,
    GRID_ROWS: currentGridRows
  },
  refs: {
    layoutRef,
    mapViewportRef,
    minimapRef,
    windowWidth,
    panelWidth,
    isCompactLayout,
    mapZoom,
    mapOffsetX,
    mapOffsetY,
    mapViewportWidth,
    mapViewportHeight
  },
  clampValue
})

const {
  previewTaskId,
  previewStart,
  previewEnd,
  previewPath,
  previewPathPoints,
  previewPathArrows,
  canPreviewTask,
  refreshTaskPreview,
  clearPreview,
  onTaskHover,
  onTaskLeave
} = useTaskPreview({
  algorithm,
  GRID_COLS: currentGridCols,
  GRID_ROWS: currentGridRows,
  isBlockedCell,
  currentTaskStage,
  taskRemainingWaypoints,
  resolveTaskDisplayStartMarker,
  resolveTaskDisplayEndMarker,
  toSvgPoints,
  toArrowSegments
})

const minimapPreviewPathPoints = computed(() => toSvgPoints(previewPath.value, minimapCellSize.value))

function blockedCellAlertText() {
  if (locale.value === 'ja') return '障害セルまたは無効セルは始点・終点・中継点に設定できません。'
  if (locale.value === 'zh') return '障碍格或无效网格不能作为起点、终点或中转点。'
  return 'Blocked or inactive cells cannot be used as start, end, or transfer points.'
}

function onAgvClick(agv, event) {
  event.stopPropagation()
  if (agv.source !== 'backend') return
  mapDraftPrimedMode.value = null
  selectedAgvId.value = agv.id
  if (dispatchMode.value !== 'manual') return
  if (!isSchedulableIdleAgvStatus(agv?.status)) return
  preferredRuntimeDisplayMode.value = 'manual'
  manualDraftPicking.value = false
  syncManualDispatchBuilderState()
  clearManualDestination()
}

function onMapMouseDown(event) {
  if (event.button !== 0) return
  if (event.target.closest('.agv') || event.target.closest('.minimap')) return

  if (obstacleEditMode.value) {
    event.preventDefault()
    const cell = getCellFromEvent(event)
    if (!cell) return
    if (!isValidMapCell(cell.x, cell.y)) return
    obstaclePaintMode = blockedCellSet.value.has(blockedCellKey(cell.x, cell.y)) ? 'remove' : 'add'
    obstaclePaintActive = true
    obstaclePaintLastKey = ''
    applyObstaclePaintAt(cell.x, cell.y, obstaclePaintMode)
    ignoreNextMapClick = true
    window.setTimeout(() => {
      if (ignoreNextMapClick) {
        ignoreNextMapClick = false
      }
    }, 260)
    return
  }

  if (taskBuilderMode.value === 'single') {
    if (dispatchMode.value === 'auto') {
      preferredRuntimeDisplayMode.value = 'auto'
      mapDraftPrimedMode.value = 'auto'
      if (!autoDraftPicking.value && !startPoint.value) {
        endPoint.value = null
      }
    } else if (dispatchMode.value === 'manual' && isSchedulableIdleAgvStatus(selectedBackendAgv.value?.status)) {
      preferredRuntimeDisplayMode.value = 'manual'
      mapDraftPrimedMode.value = 'manual'
      if (!manualDraftPicking.value && manualDispatchStep.value !== 'awaiting_end') {
        endPoint.value = null
      }
    }
  }

  mapPanCandidate = true
  mapPanMoved = false
  mapPanStartX = event.clientX
  mapPanStartY = event.clientY
  mapPanOriginX = mapOffsetX.value
  mapPanOriginY = mapOffsetY.value
}

function onMapDoubleClick(event) {
  if (obstacleEditMode.value) {
    if (clickTimer) {
      clearTimeout(clickTimer)
      clickTimer = null
    }
    return
  }
  if (taskChainMapPickActive.value) return
  if (ignoreNextMapClick) {
    ignoreNextMapClick = false
    return
  }
  if (clickTimer) {
    clearTimeout(clickTimer)
    clickTimer = null
  }
  mapDraftPrimedMode.value = null
  if (dispatchMode.value === 'auto' && taskBuilderMode.value === 'single') {
    clearAutoMarkers()
  }

  const cell = getCellFromEvent(event)
  if (!cell) return
  const { x, y } = cell
  if (isBlockedCell(x, y)) {
    window.alert(blockedCellAlertText())
    return
  }
  if (isCellOccupied(x, y)) return

  localAgvs.value.push({
    id: localNextId++,
    x,
    y,
    status: 'idle',
    source: 'local'
  })
}

function onMapClick(event) {
  if (ignoreNextMapClick) {
    ignoreNextMapClick = false
    mapDraftPrimedMode.value = null
    return
  }
  if (clickTimer) return
  const cell = getCellFromEvent(event)
  if (!cell) {
    mapDraftPrimedMode.value = null
    return
  }
  const { x, y } = cell
  if (dispatchMode.value === 'auto' && taskBuilderMode.value === 'single') {
    autoDraftPicking.value = true
    mapDraftPrimedMode.value = null
  } else if (dispatchMode.value === 'manual' && taskBuilderMode.value === 'single') {
    manualDraftPicking.value = true
    mapDraftPrimedMode.value = null
  }
  clickTimer = setTimeout(() => {
    clickTimer = null
    handleSingleClick(x, y)
  }, 220)
}

function toggleMapSettings() {
  showMapSettings.value = !showMapSettings.value
}

function openPageSettingsFromEnterpriseSettings() {
  openEnterprisePageSettingsDialog()
}

function handlePanelSummaryItemClick(item) {
  if (item.interactive !== 'zoom') {
    summaryZoomArmed.value = false
  }

  if (item.interactive === 'mode') {
    toggleDispatchModeFromSummary()
    return
  }

  if (item.interactive === 'zoom') {
    if (panelSummaryMode.value === 'full') {
      summaryZoomArmed.value = true
      return
    }
    return
  }

  void jumpToPanelSearchResult(item.sectionKey)
}

function handlePanelSummaryItemWheel(event, item, modeVariant) {
  if (item.interactive !== 'zoom') return

  if (modeVariant === 'compact') {
    event.preventDefault()
    event.stopPropagation()
    changeMapZoom(event.deltaY)
    return
  }

  if (modeVariant === 'full' && summaryZoomArmed.value) {
    event.preventDefault()
    event.stopPropagation()
    changeMapZoom(event.deltaY)
  }
}

function handlePanelSummaryItemMouseLeave(item) {
  if (panelSummaryMode.value === 'full' && item.interactive === 'zoom') {
    summaryZoomArmed.value = false
  }
}

function handlePanelSummaryItemDoubleClick(event, item) {
  if (item.interactive !== 'zoom') return
  event.preventDefault()
  event.stopPropagation()
  summaryZoomArmed.value = false
  resetMapView()
}

function handleSingleClick(x, y) {
  mapDraftPrimedMode.value = null
  if (obstacleEditMode.value) {
    toggleBlockedCellAt(x, y)
    return
  }

  if (isBlockedCell(x, y)) {
    if (dispatchMode.value === 'auto' && taskBuilderMode.value === 'single') {
      clearAutoMarkers()
    }
    if (dispatchMode.value === 'manual') {
      manualDraftPicking.value = false
    }
    window.alert(blockedCellAlertText())
    return
  }

  if (taskBuilderMode.value === 'chain' && taskChainMapPickActive.value) {
    if (dispatchMode.value === 'manual' && !getSelectedManualDispatchAgv()) return
    void handleTaskChainMapClick(x, y)
    return
  }

  if (dispatchMode.value === 'manual') {
    const agv = getSelectedManualDispatchAgv()
    if (!agv) return
    manualDraftPicking.value = true
    startPoint.value = { x: agv.x, y: agv.y }
    endPoint.value = null
    manualPathToStart.value = []
    manualPathToEnd.value = []
    void confirmAndSchedule(x, y, agv.id)
    return
  }

  autoDraftPicking.value = true
  if (!startPoint.value) {
    startPoint.value = { x, y }
    return
  }

  if (!endPoint.value) {
    void confirmAndSchedule(x, y)
    return
  }

  startPoint.value = { x, y }
  endPoint.value = null
  manualPathToStart.value = []
  manualPathToEnd.value = []
}

async function handleTaskChainMapClick(x, y) {
  if (isBlockedCell(x, y)) {
    window.alert(blockedCellAlertText())
    return
  }

  const manualAgv = dispatchMode.value === 'manual' ? getSelectedManualDispatchAgv() : null
  if (dispatchMode.value === 'manual' && !manualAgv) return

  const requiredPoints = taskChainRequiredPointCount.value
  const nextPoints = [...taskChainMapPickPoints.value, { x, y }].slice(0, requiredPoints)
  taskChainMapPickPoints.value = nextPoints
  startPoint.value = nextPoints[0] ?? null
  endPoint.value = nextPoints.at(-1) ?? null

  if (nextPoints.length < requiredPoints) return

  const ok = window.confirm(t('confirm_dispatch'))
  if (!ok) {
    taskChainMapPickPoints.value = nextPoints.slice(0, -1)
    startPoint.value = taskChainMapPickPoints.value[0] ?? null
    endPoint.value = taskChainMapPickPoints.value.at(-1) ?? null
    return
  }

  const payload = buildTaskChainPayloadFromPoints(nextPoints)
  if (!payload) return

  const created = await submitTaskPayload(payload)
  if (created) {
    taskChainMapPickActive.value = false
    taskChainMapPickPoints.value = []
    if (dispatchMode.value === 'auto') {
      clearAutoMarkers()
    }
  }
}

async function confirmAndSchedule(x, y, agvId = null) {
  const ok = window.confirm(t('confirm_dispatch'))
  if (!ok) {
    if (dispatchMode.value === 'manual') {
      manualDraftPicking.value = false
      clearManualDestination()
    } else if (dispatchMode.value === 'auto') {
      clearAutoMarkers()
    }
    return
  }
  endPoint.value = { x, y }
  if (dispatchMode.value === 'manual') {
    manualDispatchStep.value = 'running'
    bumpManualPreviewMinVisible()
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 180))
  }
  await createTaskAndSchedule(agvId)
}

async function createTaskAndSchedule(agvId) {
  if (!startPoint.value || !endPoint.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }

  const manualAgv = dispatchMode.value === 'manual' ? getSelectedManualDispatchAgv(false) : null
  const isManualFlow = dispatchMode.value === 'manual' && Boolean(manualAgv)
  try {
    autoScheduleGuard.value = true
    const createRes = await fetch(`${API_BASE}/task/create`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        start_x: startPoint.value.x,
        start_y: startPoint.value.y,
        end_x: endPoint.value.x,
        end_y: endPoint.value.y,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue(),
        priority: taskPriority.value,
        ...(isManualFlow ? buildManualTaskCreateMeta(manualAgv) : {})
      })
    })
    const createData = await createRes.json()
    if (!createRes.ok) {
      throw createApiError(createData, 'Task create failed')
    }

    if (!isManualFlow && !hasIdleAgv()) {
      await fetchTasks()
      clearAutoMarkers()
      showFloatingToast(autoTaskQueuedText(createData.task), 'info')
      return
    }

    const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        task_id: createData.task.id,
        agv_id: isManualFlow ? agvId : null,
        schedule_mode: isManualFlow ? 'manual' : 'auto',
        algorithm: algorithm.value,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const scheduleData = await scheduleRes.json()
    if (!scheduleRes.ok) {
      if (isManualFlow) {
        await handleManualScheduleFailure(createData.task.id, scheduleData)
        return
      }
      await fetchTasks()
      const latestTask = tasks.value.find(task => task.id === createData.task.id)
      if (scheduleData?.detail?.error_code === 'no_idle_agv' && latestTask?.status === 'pending') {
        clearAutoMarkers()
        showFloatingToast(autoTaskQueuedText(latestTask), 'info')
        return
      }
      if (latestTask?.status === 'blocked') {
        window.alert(blockedTaskAlertText(latestTask))
      } else {
        window.alert(localizeApiErrorDetail(scheduleData?.detail, t('task_manual_unreachable')))
      }
      clearAutoMarkers()
      return
    }

    const resolvedMode = scheduleData?.task?.dispatch_mode ?? (isManualFlow ? 'manual' : 'auto')
    if (resolvedMode === 'manual') {
      preferredRuntimeDisplayMode.value = 'manual'
      applyTaskDisplayMarkers(scheduleData.task, createData.task)
      manualPathToStart.value = scheduleData.path_to_start ?? []
      manualPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
      trackedManualTaskId.value = scheduleData.task.id
      manualDraftPicking.value = false
      bumpManualPreviewMinVisible()
    } else {
      preferredRuntimeDisplayMode.value = 'auto'
      autoPathToStart.value = scheduleData.path_to_start ?? []
      autoPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
      clearAutoMarkers()
    }

    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Schedule error:', error)
    if (isManualFlow) {
      manualDraftPicking.value = false
      trackedManualTaskId.value = null
      manualDispatchStep.value = 'idle'
      clearManualDestination()
    }
    window.alert(error instanceof Error ? error.message : String(error))
  } finally {
    autoScheduleGuard.value = false
  }
}

function openGuideCenter() {
  showGuideCenter.value = true
}

function closeGuideCenter() {
  showGuideCenter.value = false
  showFloatingToast(guideCenterLocale.value.reopenHint || 'Press H to reopen the guide.', 'info')
}

function toggleFeedbackBellMenu() {
  feedbackBellMenuOpen.value = !feedbackBellMenuOpen.value
}

function closeFeedbackBellMenu() {
  feedbackBellMenuOpen.value = false
}

async function openEnterpriseRequestDialogFromBell() {
  closeFeedbackBellMenu()
  await openEnterpriseRequestDialog()
}

async function openPlatformBugFeedbackDialogFromBell() {
  closeFeedbackBellMenu()
  await openPlatformBugFeedbackDialog()
}

function onPanelScroll() {
  showPanelBackToTop.value = (panelRef.value?.scrollTop ?? 0) > 140
}

function scrollPanelToTop() {
  panelRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function onGlobalMouseMove(event) {
  if (syncEnterpriseWorkspacePopupDrag(event)) {
    return
  }

  if (compareFloatingDragging) {
    compareFloatingX.value = Math.max(event.clientX - compareFloatingDragOffsetX, 12)
    compareFloatingY.value = Math.max(event.clientY - compareFloatingDragOffsetY, 12)
    return
  }

  if (handleGlobalMouseMove(event)) {
    return
  }

  if (obstaclePaintActive) {
    const cell = getCellFromClient(event.clientX, event.clientY)
    if (!cell) return
    applyObstaclePaintAt(cell.x, cell.y, obstaclePaintMode)
    return
  }

  if (!mapPanCandidate) return

  const dx = event.clientX - mapPanStartX
  const dy = event.clientY - mapPanStartY
  if (!mapPanMoved && Math.hypot(dx, dy) < 4) return

  mapPanMoved = true
  isMapPanning.value = true
  mapOffsetX.value = mapPanOriginX + dx
  mapOffsetY.value = mapPanOriginY + dy
  clampMapTransform()
}

function onGlobalMouseUp() {
  stopEnterpriseWorkspacePopupDrag()

  if (compareFloatingDragging) {
    compareFloatingDragging = false
  }

  handleGlobalMouseUp()

  if (obstaclePaintActive) {
    stopObstaclePaint()
  }

  if (mapPanCandidate) {
    if (mapPanMoved) {
      ignoreNextMapClick = true
      if (!startPoint.value && !endPoint.value) {
        mapDraftPrimedMode.value = null
      }
    }
    mapPanCandidate = false
    mapPanMoved = false
    isMapPanning.value = false
  }
}

async function deleteTask(task) {
  if (!isTaskDeletable(task)) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  const confirmText = isTaskActiveAndBound(task) ? t('confirm_delete_active_task') : t('confirm_delete_task')
  const ok = window.confirm(confirmText)
  if (!ok) return

  try {
    const res = await fetch(`${API_BASE}/task/${task.id}`, {
      method: 'DELETE',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Delete failed')
    }
    if (previewTaskId.value === task.id) {
      clearPreview()
    }
    await Promise.all([fetchTasks(), fetchAgvs()])
    showFloatingToast(t('task_deleted_ok'), 'success')
  } catch (error) {
    console.error('Delete task error:', error)
    showFloatingToast(error?.message || t('task_delete_failed'), 'error')
  }
}

function isTaskDeletable(task) {
  return Boolean(task)
}

function isTaskActiveAndBound(task) {
  if (!task || !['assigned', 'running'].includes(task.status)) return false
  const relatedAgv =
    (task.agv_id ? agvs.value.find(agv => agv.id === task.agv_id) : null) ??
    agvs.value.find(agv => agv.task_id === task.id)
  return Boolean(relatedAgv)
}

function buildTaskExportFilename(prefix) {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  return `${prefix}-${timestamp}.json`
}

async function exportFinishedTasksToJson() {
  const finishedCount = tasks.value.filter(task => task.status === 'finished').length
  if (finishedCount === 0) {
    showFloatingToast(t('queue_no_finished_tasks'), 'info')
    return
  }

  try {
    const res = await fetch(`${API_BASE}/task/export_json?status=finished`)
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Finished task export failed')
    }
    downloadJsonFile(buildTaskExportFilename('agv-finished-tasks'), JSON.stringify(data, null, 2))
    showFloatingToast(t('finished_tasks_exported'), 'success')
  } catch (error) {
    console.error('Export finished tasks error:', error)
    showFloatingToast(error?.message || t('task_export_failed'), 'error')
  }
}

async function deleteFinishedTasks() {
  const finishedCount = tasks.value.filter(task => task.status === 'finished').length
  if (finishedCount === 0) {
    showFloatingToast(t('queue_no_finished_tasks'), 'info')
    return
  }
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  if (!window.confirm(t('confirm_delete_finished_tasks'))) {
    return
  }

  try {
    const res = await fetch(`${API_BASE}/task/finished`, {
      method: 'DELETE',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Delete finished tasks failed')
    }
    if (previewTaskId.value && !tasks.value.some(task => task.id === previewTaskId.value && task.status !== 'finished')) {
      clearPreview()
    }
    await fetchTasks()
    showFloatingToast(t('finished_tasks_deleted'), 'success')
  } catch (error) {
    console.error('Delete finished tasks error:', error)
    showFloatingToast(error?.message || t('task_delete_failed'), 'error')
  }
}

async function deleteOrphanedTasks() {
  if (orphanedTaskCount.value === 0) {
    showFloatingToast(t('queue_no_orphaned_tasks'), 'info')
    return
  }
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  if (!window.confirm(t('confirm_delete_orphaned_tasks'))) {
    return
  }

  try {
    const res = await fetch(`${API_BASE}/task/orphaned`, {
      method: 'DELETE',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Delete orphaned tasks failed')
    }
    await fetchTasks()
    if (previewTaskId.value && !tasks.value.some(task => task.id === previewTaskId.value && isTaskOrphaned(task))) {
      clearPreview()
    }
    showFloatingToast(t('orphaned_tasks_deleted'), 'success')
  } catch (error) {
    console.error('Delete orphaned tasks error:', error)
    showFloatingToast(error?.message || t('task_delete_failed'), 'error')
  }
}

async function recoverBlockedTask(task, mode) {
  if (!task || task.status !== 'blocked') return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  hideTaskBuilderJumpButton()
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }
  if (mode === 'bound' && !task.preferred_agv_id) {
    if (locale.value === 'ja') window.alert('このタスクに原車バインド情報がありません。改派を使用してください。')
    else if (locale.value === 'zh') window.alert('该任务没有原车绑定信息，请使用“改派执行”。')
    else window.alert('No bound AGV is available for this task. Please use reassign.')
    return
  }

  taskRecoveryActionKey.value = taskRecoveryActionId(task.id, mode)
  try {
    const preferredAlgorithm = String(task.dispatch_algorithm || algorithm.value || 'simple').toLowerCase()
    const res = await fetch(`${API_BASE}/schedule/recover_blocked/${task.id}`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        mode,
        algorithm: preferredAlgorithm,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Recover blocked task failed')
    }

    if (data?.queued) {
      if (mode === 'bound') {
        const jumpAgvId = data?.task?.preferred_agv_id ?? task.preferred_agv_id ?? null
        if (jumpAgvId) {
          showAgvRecoveryJumpButton(jumpAgvId)
        }
      }
      showFloatingToast(recoveryQueuedText(mode, task, data?.algorithm), 'info')
      await Promise.all([fetchAgvs(), fetchTasks()])
      return
    }

    const dispatchModeValue = data?.task?.dispatch_mode ?? task.dispatch_mode ?? 'auto'
    if (dispatchModeValue === 'manual') {
      preferredRuntimeDisplayMode.value = 'manual'
      const recoveredAgvId = data?.agv?.id ?? data?.task?.agv_id ?? task.preferred_agv_id
      if (recoveredAgvId) {
        selectedAgvId.value = recoveredAgvId
      }
      manualPathToStart.value = data.path_to_start ?? []
      manualPathToEnd.value = data.path_to_end ?? data.path ?? []
      trackedManualTaskId.value = data?.task?.id ?? task.id
      applyTaskDisplayMarkers(data?.task, task)
      manualDispatchStep.value = 'running'
      bumpManualPreviewMinVisible()
    } else {
      preferredRuntimeDisplayMode.value = 'auto'
      autoPathToStart.value = data.path_to_start ?? []
      autoPathToEnd.value = data.path_to_end ?? data.path ?? []
    }

    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Recover blocked task error:', error)
    window.alert(error instanceof Error ? error.message : String(error))
    await fetchTasks()
  } finally {
    taskRecoveryActionKey.value = ''
  }
}

async function retryBlockedTaskFromCurrent(task, algorithmName = null) {
  if (task.status !== 'blocked') return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }
  const selectedAlgorithm = String(algorithmName || task.dispatch_algorithm || algorithm.value || 'simple').toLowerCase()
  taskRecoveryActionKey.value = taskRecoveryActionId(task.id, 'retry_current')
  try {
    const res = await fetch(`${API_BASE}/schedule/retry_blocked_from_current/${task.id}`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        algorithm: selectedAlgorithm,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Retry task from current failed')
    }

    const isManualRetry = (data?.task?.dispatch_mode ?? task.dispatch_mode) === 'manual'
    if (data?.queued) {
      const boundAgvId = data?.task?.preferred_agv_id ?? task.preferred_agv_id ?? null
      if (boundAgvId) {
        selectedAgvId.value = boundAgvId
        showAgvRecoveryJumpButton(boundAgvId)
      }
      showFloatingToast(retryFromCurrentQueuedText(task, data?.algorithm), 'info')
      await Promise.all([fetchAgvs(), fetchTasks()])
      return
    }

    if (isManualRetry) {
      preferredRuntimeDisplayMode.value = 'manual'
      if (data?.task?.agv_id ?? task.preferred_agv_id) {
        selectedAgvId.value = data?.task?.agv_id ?? task.preferred_agv_id
      }
      manualPathToStart.value = data.path_to_start ?? []
      manualPathToEnd.value = data.path_to_end ?? data.path ?? []
      trackedManualTaskId.value = data?.task?.id ?? task.id
      applyTaskDisplayMarkers(data?.task, task)
      manualDispatchStep.value = 'running'
      bumpManualPreviewMinVisible()
    } else {
      preferredRuntimeDisplayMode.value = 'auto'
      autoPathToStart.value = data.path_to_start ?? []
      autoPathToEnd.value = data.path_to_end ?? data.path ?? []
    }

    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Retry blocked task from current error:', error)
    window.alert(error instanceof Error ? error.message : String(error))
    await fetchTasks()
  } finally {
    taskRecoveryActionKey.value = ''
  }
}

async function retryBlockedTaskWithAStar(task) {
  if (task.status !== 'blocked') return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }

  taskRecoveryActionKey.value = taskRecoveryActionId(task.id, 'retry_astar')
  try {
    const shouldRetryFromCurrent = isCellOccupiedTimeoutTask(task)
    const retryEndpoint = shouldRetryFromCurrent
      ? `${API_BASE}/schedule/retry_blocked_from_current/${task.id}`
      : `${API_BASE}/schedule/retry_blocked/${task.id}`
    const res = await fetch(retryEndpoint, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        algorithm: 'astar',
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Retry task with A* failed')
    }

    const isManualRetry = (data?.task?.dispatch_mode ?? task.dispatch_mode) === 'manual'
    if (data?.queued) {
      if (isManualRetry) {
        const boundAgvId = data?.task?.preferred_agv_id ?? task.preferred_agv_id ?? null
        if (boundAgvId) {
          selectedAgvId.value = boundAgvId
          if (shouldRetryFromCurrent) {
            showAgvRecoveryJumpButton(boundAgvId)
          }
        }
      } else {
        clearAutoPaths()
      }
      if (shouldRetryFromCurrent) {
        showFloatingToast(retryFromCurrentQueuedText(task, data?.algorithm), 'info')
      } else {
        window.alert(t('task_retry_astar_queued'))
      }
    } else if (isManualRetry) {
      preferredRuntimeDisplayMode.value = 'manual'
      if (data?.task?.agv_id ?? task.preferred_agv_id) {
        selectedAgvId.value = data?.task?.agv_id ?? task.preferred_agv_id
      }
      manualPathToStart.value = data.path_to_start ?? []
      manualPathToEnd.value = data.path_to_end ?? data.path ?? []
      trackedManualTaskId.value = data?.task?.id ?? task.id
      applyTaskDisplayMarkers(data?.task, task)
    } else {
      preferredRuntimeDisplayMode.value = 'auto'
      autoPathToStart.value = data.path_to_start ?? []
      autoPathToEnd.value = data.path_to_end ?? data.path ?? []
    }
    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Retry blocked task error:', error)
    window.alert(error instanceof Error ? error.message : String(error))
    await fetchTasks()
  } finally {
    taskRecoveryActionKey.value = ''
  }
}

async function retryAllBlockedTasksWithAStar(taskGroup) {
  const blockedTasks = (taskGroup?.tasks ?? []).filter(
    task => task.status === 'blocked' && !isRecoveryRequiredTask(task)
  )
  if (blockedTasks.length === 0) return
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }

  let scheduledCount = 0
  let queuedCount = 0
  let failedCount = 0

  for (const task of blockedTasks) {
    try {
      const retryEndpoint = isCellOccupiedTimeoutTask(task)
        ? `${API_BASE}/schedule/retry_blocked_from_current/${task.id}`
        : `${API_BASE}/schedule/retry_blocked/${task.id}`
      const res = await fetch(retryEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          algorithm: 'astar',
          grid_cols: gridColsValue(),
          grid_rows: gridRowsValue()
        })
      })
      const data = await res.json()
      if (!res.ok) {
        failedCount += 1
        continue
      }

      if (data?.queued) {
        queuedCount += 1
      } else {
        scheduledCount += 1
        preferredRuntimeDisplayMode.value = 'auto'
        autoPathToStart.value = data.path_to_start ?? []
        autoPathToEnd.value = data.path_to_end ?? data.path ?? []
      }
    } catch (error) {
      console.error('Retry all blocked tasks error:', error)
      failedCount += 1
    }
  }

  await Promise.all([fetchAgvs(), fetchTasks()])
  window.alert(buildBlockedBatchRetrySummary(blockedTasks.length, scheduledCount, queuedCount, failedCount))
}

async function submitTaskPayload(payload) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return false
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return false
  }
  const manualAgv = dispatchMode.value === 'manual' ? getSelectedManualDispatchAgv() : null
  if (dispatchMode.value === 'manual' && !manualAgv) {
    return false
  }
  const hasStages = Array.isArray(payload.stages) && payload.stages.length > 0
  if (hasStages) {
    const normalizedStages = payload.stages
      .map(stage => ({
        ...stage,
        start_x: Number(stage.start_x),
        start_y: Number(stage.start_y),
        end_x: Number(stage.end_x),
        end_y: Number(stage.end_y),
        label: String(stage.label ?? '').trim() || null
      }))
      .filter(
        stage =>
          isValidGridCoordinate(stage.start_x, gridColsValue()) &&
          isValidGridCoordinate(stage.start_y, gridRowsValue()) &&
          isValidGridCoordinate(stage.end_x, gridColsValue()) &&
          isValidGridCoordinate(stage.end_y, gridRowsValue())
      )

    if (normalizedStages.length !== payload.stages.length || normalizedStages.length === 0) {
      window.alert(t('point_form_invalid_coords'))
      return false
    }
    if (
      normalizedStages.some(
        stage =>
          isBlockedCell(stage.start_x, stage.start_y) ||
          isBlockedCell(stage.end_x, stage.end_y)
      )
    ) {
      window.alert(blockedCellAlertText())
      return false
    }
    payload = {
      priority: Number(payload.priority),
      stages: normalizedStages
    }
  } else if (
    Number.isNaN(Number(payload.start_x)) ||
    Number.isNaN(Number(payload.start_y)) ||
    Number.isNaN(Number(payload.end_x)) ||
    Number.isNaN(Number(payload.end_y))
  ) {
    window.alert(t('point_form_invalid_coords'))
    return false
  } else if (
    !isValidGridCoordinate(Number(payload.start_x), gridColsValue()) ||
    !isValidGridCoordinate(Number(payload.start_y), gridRowsValue()) ||
    !isValidGridCoordinate(Number(payload.end_x), gridColsValue()) ||
    !isValidGridCoordinate(Number(payload.end_y), gridRowsValue())
  ) {
    window.alert(t('point_form_invalid_coords'))
    return false
  } else if (
    isBlockedCell(Number(payload.start_x), Number(payload.start_y)) ||
    isBlockedCell(Number(payload.end_x), Number(payload.end_y))
  ) {
    window.alert(blockedCellAlertText())
    return false
  }

  if (dispatchMode.value === 'manual' && manualAgv) {
    payload = {
      ...payload,
      ...buildManualTaskCreateMeta(manualAgv)
    }
  }

  const shouldGuardAutoSchedule = dispatchMode.value === 'manual'
  try {
    if (shouldGuardAutoSchedule) {
      autoScheduleGuard.value = true
    }
    const res = await fetch(`${API_BASE}/task/create`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        ...payload,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Create task failed')
    }
    await fetchTasks()
    let createdTask = data.task
    if (dispatchMode.value === 'auto') {
      await tryAutoSchedule()
      await fetchTasks()
      createdTask = tasks.value.find(task => task.id === data.task?.id) ?? data.task
      if (createdTask?.status === 'blocked') {
        window.alert(blockedTaskAlertText(createdTask))
      }
      return createdTask
    }

    if (dispatchMode.value === 'manual' && manualAgv) {
      const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
        method: 'POST',
        headers: buildAuthorizedJsonHeaders(),
        body: JSON.stringify({
          task_id: data.task.id,
          agv_id: manualAgv.id,
          schedule_mode: 'manual',
          algorithm: algorithm.value,
          grid_cols: gridColsValue(),
          grid_rows: gridRowsValue()
        })
      })
      const scheduleData = await scheduleRes.json()
      if (!scheduleRes.ok) {
        return await handleManualScheduleFailure(data.task.id, scheduleData)
      }

      applyTaskDisplayMarkers(scheduleData.task, data.task)
      manualPathToStart.value = scheduleData.path_to_start ?? []
      manualPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
      trackedManualTaskId.value = scheduleData.task.id
      manualDispatchStep.value = 'running'
      bumpManualPreviewMinVisible()
      await Promise.all([fetchAgvs(), fetchTasks()])
      return tasks.value.find(task => task.id === scheduleData.task.id) ?? scheduleData.task
    }
    return createdTask
  } catch (error) {
    console.error('Create task form error:', error)
    if (dispatchMode.value === 'manual') {
      manualDispatchStep.value = startPoint.value ? 'awaiting_end' : 'idle'
    }
    window.alert(error instanceof Error ? error.message : String(error))
    return false
  } finally {
    if (shouldGuardAutoSchedule) {
      autoScheduleGuard.value = false
    }
  }
}

function clearPathCompare() {
  pathCompareResult.value = null
  pathCompareError.value = ''
}

function currentSceneLabel() {
  if (!obstacleLayoutDirty.value && appliedObstaclePresetInfo.value) {
    return obstaclePresetName(appliedObstaclePresetInfo.value)
  }

  if (locale.value === 'ja') return 'カスタム障害レイアウト'
  if (locale.value === 'zh') return '自定义障碍布局'
  return 'Custom obstacle layout'
}

function buildRouteSummaryFromPayload(payload) {
  if (!payload) return ''
  if (Array.isArray(payload.stages)) {
    return payload.stages
      .map(stage => `(${stage.start_x},${stage.start_y})->(${stage.end_x},${stage.end_y})`)
      .join(' | ')
  }
  return `(${payload.start_x},${payload.start_y})->(${payload.end_x},${payload.end_y})`
}

function formatStageLengthsForExport(stageResults) {
  if (!Array.isArray(stageResults) || stageResults.length === 0) return ''
  return stageResults
    .map(stage =>
      stage.reachable ? `${Number(stage.index) + 1}:${stage.path_length}` : `${Number(stage.index) + 1}:X`
    )
    .join('|')
}

function buildCompareSnapshot() {
  if (!pathCompareResult.value) return null

  const payload = buildPathComparePayload()
  const appliedSceneKey = obstacleLayoutDirty.value ? 'custom' : appliedObstacleSceneKey.value
  const algorithms = ['simple', 'astar'].map(key => {
    const result = pathCompareResult.value?.results?.[key] ?? null
    return {
      algorithm: key,
      reachable: Boolean(result?.reachable),
      reachable_text: formatCompareResultStatus(result),
      total_length: result?.total_length ?? null,
      failed_stage_index: result?.failed_stage_index ?? null,
      failed_stage_label:
        result?.failed_stage_index === null || result?.failed_stage_index === undefined
          ? ''
          : Number(result.failed_stage_index) + 1,
      stage_lengths: formatStageLengthsForExport(result?.stage_results),
      stage_results: result?.stage_results ?? []
    }
  })

  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    saved_at: new Date().toISOString(),
    scene_key: appliedSceneKey,
    scene_name: currentSceneLabel(),
    grid_cols: gridColsValue(),
    grid_rows: gridRowsValue(),
    obstacle_count: blockedCellCount.value,
    task_mode: taskBuilderMode.value,
    stage_count: pathCompareResult.value?.stage_count ?? (Array.isArray(payload?.stages) ? payload.stages.length : 1),
    route_summary: buildRouteSummaryFromPayload(payload),
    current_algorithm: algorithm.value,
    recommended_algorithm: recommendedCompareAlgorithm.value,
    payload,
    algorithms
  }
}

function experimentCsvRowsFromRecords(records) {
  return records.flatMap(record =>
    (record.algorithms ?? []).map(item => ({
      record_id: record.id,
      saved_at: record.saved_at,
      scene_key: record.scene_key ?? '',
      scene_name: record.scene_name ?? '',
      grid_cols: record.grid_cols ?? '',
      grid_rows: record.grid_rows ?? '',
      task_mode: record.task_mode ?? '',
      stage_count: record.stage_count ?? '',
      route_summary: record.route_summary ?? '',
      obstacle_count: record.obstacle_count ?? '',
      current_algorithm: record.current_algorithm ?? '',
      recommended_algorithm: record.recommended_algorithm ?? '',
      algorithm: item.algorithm ?? '',
      reachable: item.reachable ? 'true' : 'false',
      reachable_text: item.reachable_text ?? '',
      total_length: item.total_length ?? '',
      failed_stage: item.failed_stage_label ?? '',
      stage_lengths: item.stage_lengths ?? ''
    }))
  )
}

function buildPathComparePayload() {
  if (taskBuilderMode.value === 'chain') {
    const stages = taskChainStages.value.map(stage => ({
      label: String(stage.label ?? '').trim() || null,
      start_x: Number(stage.start_x),
      start_y: Number(stage.start_y),
      end_x: Number(stage.end_x),
      end_y: Number(stage.end_y)
    }))

    if (
      stages.length < 2 ||
      stages.some(
        stage =>
          !isValidGridCoordinate(stage.start_x, gridColsValue()) ||
          !isValidGridCoordinate(stage.start_y, gridRowsValue()) ||
          !isValidGridCoordinate(stage.end_x, gridColsValue()) ||
          !isValidGridCoordinate(stage.end_y, gridRowsValue())
      )
    ) {
      return null
    }

    return {
      stages,
      grid_cols: gridColsValue(),
      grid_rows: gridRowsValue()
    }
  }

  const payload = {
    start_x: Number(taskForm.value.start_x),
    start_y: Number(taskForm.value.start_y),
    end_x: Number(taskForm.value.end_x),
    end_y: Number(taskForm.value.end_y),
    grid_cols: gridColsValue(),
    grid_rows: gridRowsValue()
  }

  if (
    !isValidGridCoordinate(payload.start_x, gridColsValue()) ||
    !isValidGridCoordinate(payload.start_y, gridRowsValue()) ||
    !isValidGridCoordinate(payload.end_x, gridColsValue()) ||
    !isValidGridCoordinate(payload.end_y, gridRowsValue())
  ) {
    return null
  }

  return payload
}

async function compareCurrentRoute() {
  if (!(await ensureBlockedCellsSynced())) {
    pathCompareError.value = obstacleSaveRequiredText()
    return
  }
  const payload = buildPathComparePayload()
  if (!payload) {
    pathCompareError.value = algorithmCompareLocale.value.invalid
    pathCompareResult.value = null
    return
  }

  pathCompareLoading.value = true
  pathCompareError.value = ''
  try {
    const res = await fetch(`${API_BASE}/schedule/compare_path`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Compare path failed')
    }
    pathCompareResult.value = data
  } catch (error) {
    console.error('Compare path error:', error)
    pathCompareError.value = error instanceof Error ? error.message : String(error)
    pathCompareResult.value = null
  } finally {
    pathCompareLoading.value = false
  }
}

function applyComparedAlgorithm(nextAlgorithm) {
  algorithm.value = nextAlgorithm
}

function toggleAlgorithmMode() {
  algorithm.value = algorithm.value === 'simple' ? 'astar' : 'simple'
}

const {
  jumpToPanelSearchResult,
  shouldAutoRefreshFloatingCompare,
  stopFloatingCompareRefresh,
  requestFloatingCompareRefresh,
  clearPanelSearch,
  handleCompareEntryClick,
  toggleComparePanelExpanded,
  closeFloatingCompare,
  disposePanelCompareUi
} = usePanelCompareUi({
  nextTick,
  panelSections,
  panelRef,
  controlSectionRef,
  queueSectionRef,
  templatesSectionRef,
  pointsSectionRef,
  jsonSectionRef,
  experimentsSectionRef,
  aiSectionRef,
  operationsSectionRef,
  focusedPanelSection,
  comparePanelExpanded,
  comparePanelRef,
  compareDisplayMode,
  showFloatingCompare,
  compareEntryButtonRef,
  compareFloatingX,
  compareFloatingY,
  pathCompareLoading,
  panelSearch,
  compareCurrentRoute
})

function startFloatingCompareDrag(event) {
  if (event.button !== 0) return
  compareFloatingDragging = true
  compareFloatingDragOffsetX = event.clientX - compareFloatingX.value
  compareFloatingDragOffsetY = event.clientY - compareFloatingY.value
}

async function addTaskFromForm() {
  const payload = {
    start_x: Number(taskForm.value.start_x),
    start_y: Number(taskForm.value.start_y),
    end_x: Number(taskForm.value.end_x),
    end_y: Number(taskForm.value.end_y),
    priority: Number(taskForm.value.priority)
  }

  const created = await submitTaskPayload(payload)
  if (created) {
    hideTaskBuilderJumpButton()
  }
}

async function addTaskChainFromForm() {
  if (taskChainStages.value.length < 2) return
  const created = await submitTaskPayload({
    priority: Number(taskForm.value.priority),
    stages: taskChainStages.value
  })
  if (created) {
    hideTaskBuilderJumpButton()
    resetTaskChainStages()
  }
}

async function createTaskFromTemplate(template) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'dispatch.write', buildCapabilityDeniedMessage('dispatch'))) return
  hideTaskBuilderJumpButton()
  const stages = normalizeTemplateStages(template)
  if (stages.length > 1) {
    await submitTaskPayload({
      priority: Number(template.priority),
      stages
    })
    return
  }

  const firstStage = stages[0]
  await submitTaskPayload({
    start_x: Number(firstStage.start_x),
    start_y: Number(firstStage.start_y),
    end_x: Number(firstStage.end_x),
    end_y: Number(firstStage.end_y),
    priority: Number(template.priority)
  })
}

async function importTasksFromJson(rawText = jsonText.value) {
  const jsonPayload = String(rawText || '').trim()
  if (!jsonPayload) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'json.write', buildCapabilityDeniedMessage('data'))) return
  jsonStatus.value = ''

  let parsed
  try {
    parsed = JSON.parse(jsonPayload)
  } catch {
    jsonStatus.value = t('json_import_fail')
    return
  }

  const taskItems = Array.isArray(parsed) ? parsed : parsed?.tasks
  if (!Array.isArray(taskItems)) {
    jsonStatus.value = t('json_import_fail')
    return
  }

  function buildTaskJsonImportFailureText(detail) {
    const reasonText = localizeApiErrorDetail(detail, t('json_import_fail'))
    if (
      detail &&
      typeof detail === 'object' &&
      ['stage_blocked', 'stage_out_of_grid'].includes(String(detail.error_code || ''))
    ) {
      return formatInlineMessage(t('json_import_map_hint'), { reason: reasonText })
    }
    return reasonText
  }

  try {
    const res = await fetch(`${API_BASE}/task/import_json`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({ tasks: taskItems })
    })
    const data = await res.json()
    if (!res.ok) {
      jsonStatus.value = buildTaskJsonImportFailureText(data?.detail)
      return
    }
    jsonStatus.value = t('json_import_ok')
    await fetchTasks()
    await tryAutoSchedule()
  } catch (error) {
    console.error('Import json error:', error)
    jsonStatus.value = error instanceof Error && error.message ? error.message : t('json_import_fail')
  }
}

async function exportTasksToJson() {
  jsonStatus.value = ''
  try {
    const res = await fetch(`${API_BASE}/task/export_json`)
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Export failed')
    }
    jsonText.value = JSON.stringify(data, null, 2)
  } catch (error) {
    console.error('Export json error:', error)
  }
}

function clearJsonText() {
  jsonText.value = ''
  jsonStatus.value = ''
}

function setObstacleLayoutStatus(type, message) {
  obstacleLayoutStatusType.value = type
  obstacleLayoutStatus.value = message
}

function obstacleSaveRequiredText() {
  if (locale.value === 'ja') return '障害レイアウトに未保存の変更があります。先に保存してください。'
  if (locale.value === 'zh') return '当前障碍布局有未保存修改，请先点击“保存障碍”。'
  return 'The obstacle layout has unsaved changes. Please save it first.'
}

function confirmDiscardObstacleChangesText() {
  if (locale.value === 'ja') return '未保存の障害変更があります。破棄して新しいレイアウトを適用しますか？'
  if (locale.value === 'zh') return '当前有未保存的障碍修改，是否放弃这些修改并继续应用新布局？'
  return 'There are unsaved obstacle changes. Discard them and continue?'
}

function obstacleImportedPendingSaveText() {
  if (locale.value === 'ja') return '障害レイアウトを読み込みました。「保存障害」で反映するか、そのままプリセットとして保存できます。'
  if (locale.value === 'zh') return '已导入障碍布局。你可以先“保存障碍”再使用，也可以直接把当前导入布局保存为预设。'
  return 'Obstacle layout imported. Save it to the map or store the imported layout directly as a preset.'
}

function invalidObstacleLayoutText() {
  if (locale.value === 'ja') return '障害レイアウト JSON の形式が正しくありません。'
  if (locale.value === 'zh') return '障碍布局 JSON 格式无效。'
  return 'Invalid obstacle layout JSON.'
}

function obstacleMutationLockedText() {
  if (locale.value === 'ja') return '実行中または到着待ちの AGV があるため、障害レイアウトは変更できません。タスク完了後に再試行してください。'
  if (locale.value === 'zh') return '当前存在运行中或就位中的 AGV，禁止修改障碍布局。请等待任务完成后再操作。'
  return 'Obstacle layout changes are blocked while AGVs are running or relocating. Wait until active tasks finish.'
}

function obstaclePresetNamePromptText() {
  if (locale.value === 'ja') return 'カスタム障害プリセット名を入力してください。'
  if (locale.value === 'zh') return '请输入自定义障碍预设名称。'
  return 'Enter a name for the custom obstacle preset.'
}

function obstaclePresetNameRequiredText() {
  if (locale.value === 'ja') return 'プリセット名は空にできません。'
  if (locale.value === 'zh') return '预设名称不能为空。'
  return 'Preset name cannot be empty.'
}

function defaultImportedObstaclePresetName() {
  if (locale.value === 'ja') return '読み込みレイアウト'
  if (locale.value === 'zh') return '导入布局'
  return 'Imported Layout'
}

function obstacleImportSaveAsPresetText() {
  if (locale.value === 'ja') return '読み込みをプリセット保存'
  if (locale.value === 'zh') return '导入另存预设'
  return 'Save Import as Preset'
}

function sanitizeObstaclePresetName(value) {
  const trimmed = String(value ?? '').trim()
  const fileName = trimmed.split(/[\\/]/).pop() ?? ''
  const withoutExtension = fileName.replace(/\.[^.]+$/, '').trim()
  return withoutExtension || defaultImportedObstaclePresetName()
}

function rememberImportedObstacleLayoutPreset(sourceName = '') {
  importedObstacleLayoutPendingPreset.value = true
  importedObstaclePresetSuggestedName.value = sanitizeObstaclePresetName(sourceName)
}

function clearImportedObstacleLayoutPreset() {
  importedObstacleLayoutPendingPreset.value = false
  importedObstaclePresetSuggestedName.value = ''
}

function obstaclePresetDeleteConfirmText() {
  if (locale.value === 'ja') return '現在のカスタム障害プリセットを削除しますか？'
  if (locale.value === 'zh') return '确定删除当前自定义障碍预设吗？'
  return 'Delete the current custom obstacle preset?'
}

function obstacleSkippedOccupiedText(count) {
  if (!count) return ''
  if (locale.value === 'ja') return `AGV が占有中の ${count} マスは障害から除外しました。`
  if (locale.value === 'zh') return `已跳过 ${count} 个被 AGV 占用的障碍格。`
  return `Skipped ${count} obstacle cells currently occupied by AGVs.`
}

function mergeObstacleStatusMessage(baseMessage, skippedCount = 0) {
  const skippedText = obstacleSkippedOccupiedText(skippedCount)
  if (!skippedText) return baseMessage
  return `${baseMessage} ${skippedText}`
}

function applyGridSizeFromPayload(payload) {
  if (Number.isInteger(Number(payload?.grid_cols))) {
    currentGridCols.value = Number(payload.grid_cols)
  }
  if (Number.isInteger(Number(payload?.grid_rows))) {
    currentGridRows.value = Number(payload.grid_rows)
  }
  if (Array.isArray(payload?.valid_cells)) {
    const normalizedValidCells = normalizeValidCellList(
      payload.valid_cells.map(cell => ({
        x: Number(cell?.x),
        y: Number(cell?.y)
      })),
      gridColsValue(),
      gridRowsValue()
    )
    validCells.value = normalizedValidCells
    syncedValidCells.value = normalizedValidCells
  }
  if (!mapResizePreview.value && !mapResizePreviewDirty.value) {
    setMapResizePreviewDraft(currentGridCols.value, currentGridRows.value)
  }
}

async function importTasksFromJsonFile(event) {
  const file = event?.target?.files?.[0]
  if (event?.target) {
    event.target.value = ''
  }
  if (!file) return

  try {
    const text = await file.text()
    jsonText.value = text
    await importTasksFromJson(text)
  } catch (error) {
    console.error('Import json file error:', error)
    jsonStatus.value = t('json_import_fail')
  }
}

function syncMapTopologyFromPayload(payload, nextValidCells = validCells.value) {
  currentMapTopology.value = normalizeMapTopology(
    payload?.topology,
    gridColsValue(),
    gridRowsValue(),
    nextValidCells
  )
}

function createMapResizePreviewSnapshot(cols, rows, canApply = true) {
  return {
    current_grid_cols: cols,
    current_grid_rows: rows,
    requested_grid_cols: cols,
    requested_grid_rows: rows,
    can_apply: canApply,
    blockers: [],
    active_task_count: 0,
    busy_agv_count: 0,
    agv_overflow_count: 0,
    point_overflow_count: 0,
    template_overflow_count: 0,
    blocked_overflow_count: 0,
  }
}

function sanitizeDraftStateForCurrentGrid() {
  let adjusted = false

  const nextTaskForm = {
    ...taskForm.value,
    start_x: clampXToCurrentGrid(taskForm.value.start_x),
    start_y: clampYToCurrentGrid(taskForm.value.start_y),
    end_x: clampXToCurrentGrid(taskForm.value.end_x),
    end_y: clampYToCurrentGrid(taskForm.value.end_y),
  }
  if (
    nextTaskForm.start_x !== taskForm.value.start_x ||
    nextTaskForm.start_y !== taskForm.value.start_y ||
    nextTaskForm.end_x !== taskForm.value.end_x ||
    nextTaskForm.end_y !== taskForm.value.end_y
  ) {
    taskForm.value = nextTaskForm
    adjusted = true
  }

  const nextChainStages = taskChainStages.value.map(stage => {
    const nextStage = {
      ...stage,
      start_x: clampXToCurrentGrid(stage.start_x),
      start_y: clampYToCurrentGrid(stage.start_y),
      end_x: clampXToCurrentGrid(stage.end_x),
      end_y: clampYToCurrentGrid(stage.end_y),
    }
    if (
      nextStage.start_x !== stage.start_x ||
      nextStage.start_y !== stage.start_y ||
      nextStage.end_x !== stage.end_x ||
      nextStage.end_y !== stage.end_y
    ) {
      adjusted = true
    }
    return nextStage
  })
  taskChainStages.value = nextChainStages

  const nextCustomPointForm = {
    ...customPointForm.value,
    x: clampXToCurrentGrid(customPointForm.value.x),
    y: clampYToCurrentGrid(customPointForm.value.y),
  }
  if (
    nextCustomPointForm.x !== customPointForm.value.x ||
    nextCustomPointForm.y !== customPointForm.value.y
  ) {
    customPointForm.value = nextCustomPointForm
    adjusted = true
  }

  const nextPickPoints = taskChainMapPickPoints.value.filter(isWithinCurrentGrid)
  if (nextPickPoints.length !== taskChainMapPickPoints.value.length) {
    taskChainMapPickPoints.value = nextPickPoints
    adjusted = true
  }

  if (taskBuilderMode.value === 'chain' && taskChainMapPickActive.value) {
    startPoint.value = taskChainMapPickPoints.value[0] ?? null
    endPoint.value = taskChainMapPickPoints.value.at(-1) ?? null
  } else {
    if (startPoint.value && !isWithinCurrentGrid(startPoint.value)) {
      startPoint.value = {
        x: clampXToCurrentGrid(startPoint.value.x),
        y: clampYToCurrentGrid(startPoint.value.y),
      }
      adjusted = true
    }
    if (endPoint.value && !isWithinCurrentGrid(endPoint.value)) {
      endPoint.value = {
        x: clampXToCurrentGrid(endPoint.value.x),
        y: clampYToCurrentGrid(endPoint.value.y),
      }
      adjusted = true
    }
  }

  return adjusted
}

function obstaclePresetName(preset) {
  if (!preset?.name) return preset?.key ?? ''
  if (typeof preset.name === 'string') return preset.name
  return preset.name[locale.value] ?? preset.name.zh ?? preset.name.en ?? preset.key
}

function obstaclePresetDescription(preset) {
  if (!preset?.description) return ''
  if (typeof preset.description === 'string') return preset.description
  return (
    preset.description[locale.value] ??
    preset.description.zh ??
    preset.description.en ??
    ''
  )
}

function localizedMapProfileField(value) {
  if (!value) return ''
  if (typeof value === 'string') return value
  return value[locale.value] ?? value.zh ?? value.en ?? ''
}

function isCurrentMapProfile(profile) {
  return Boolean(profile?.key && currentMapProfile.value?.key && profile.key === currentMapProfile.value.key)
}

function isMapProfileApplying(profile) {
  return Boolean(profile?.key && mapProfileApplyingKey.value === profile.key)
}

function isMapProfileDeleting(profile) {
  return Boolean(profile?.key && mapProfileDeletingKey.value === profile.key)
}

function isMapProfileExporting(profile) {
  return Boolean(profile?.key && mapProfileExportingKey.value === profile.key)
}

function isMapProfilePreviewing(profile) {
  return Boolean(profile?.key && mapProfilePreviewingKey.value === profile.key && mapResizePreviewLoading.value)
}

function isMapProfilePreviewed(profile) {
  return Boolean(profile?.key && mapProfilePreviewingKey.value === profile.key && mapResizePreviewMatchesInput.value)
}

function mapProfilePreviewStatus(profile) {
  if (isCurrentMapProfile(profile)) return 'current'
  if (!isMapProfilePreviewed(profile)) return ''
  return mapResizePreview.value?.can_apply ? 'ready' : 'blocked'
}

function mapProfilePreviewStatusText(profile) {
  const status = mapProfilePreviewStatus(profile)
  if (status === 'current') return settingsLocale.value.mapProfileCurrent
  if (status === 'ready') return settingsLocale.value.mapProfilePreviewReady
  if (status === 'blocked') return settingsLocale.value.mapProfilePreviewBlocked
  return ''
}

function mapProfilePreviewReasonItems(profile) {
  if (!isMapProfilePreviewed(profile)) return []
  if (mapProfilePreviewStatus(profile) !== 'blocked') return []
  return mapResizePreviewReasonItems.value.slice(0, 3)
}

function focusMapResizeReasonKey(reasonKey) {
  const reason = buildMapResizeReasonItem(reasonKey)
  if (!reason?.key) return
  focusMapResizeReasonItem(reason)
}

function mapProfileActionSummaryTitle() {
  if (!mapProfileActionSummary.value) return ''
  if (mapProfileActionSummary.value.type === 'blocked') {
    return settingsLocale.value.mapProfileSummaryBlockedTitle
  }
  if (mapProfileActionSummary.value.type === 'forced') {
    return settingsLocale.value.mapProfileSummaryForcedTitle
  }
  return ''
}

function exportMapProfileActionSummary() {
  const summary = mapProfileActionSummary.value
  if (!summary || summary.type !== 'forced') return false
  try {
    const payload = {
      version: 1,
      exported_at: new Date().toISOString(),
      type: summary.type,
      previous_profile_name: summary.previousProfileName || null,
      applied_profile_name: summary.profileName || null,
      previous_size: summary.previousSizeLabel || null,
      applied_size: summary.nextSizeLabel || null,
      previous_blocked_count: Number(summary.previousBlockedCount ?? 0),
      applied_blocked_count: Number(summary.nextBlockedCount ?? 0),
      relocated_agv_count: Number(summary.relocatedAgvs?.length ?? 0),
      trimmed_blocked_cells_count: Number(summary.trimmedBlockedCount ?? 0),
      relocated_agvs: Array.isArray(summary.relocatedAgvs) ? summary.relocatedAgvs : [],
      trimmed_blocked_cells: Array.isArray(summary.trimmedBlockedCells) ? summary.trimmedBlockedCells : [],
    }
    downloadJsonFile(buildTaskExportFilename('agv-map-profile-force-diff'), JSON.stringify(payload, null, 2))
    showFloatingToast(settingsLocale.value.mapProfileSummaryExportSuccess, 'success')
    return true
  } catch (error) {
    console.error('Export map profile summary error:', error)
    showFloatingToast(settingsLocale.value.mapProfileSummaryExportFailed, 'error')
    return false
  }
}

function canForceApplyPreviewResult() {
  if (!mapResizePreview.value || mapResizePreview.value.can_apply) return false
  return Boolean(mapResizePreview.value.force_apply_allowed)
}

function canForceApplyMapProfile(profile) {
  return Boolean(authCanForceApplyMap.value && isMapProfilePreviewed(profile) && canForceApplyPreviewResult())
}

function mapResizeSectionDomId(sectionKey = 'reasons') {
  return `map-resize-preview-section-${sectionKey || 'reasons'}`
}

function highlightMapResizeSection(sectionKey) {
  mapResizeHighlightedSection.value = sectionKey
  if (mapResizeSectionHighlightTimer) {
    clearTimeout(mapResizeSectionHighlightTimer)
  }
  mapResizeSectionHighlightTimer = setTimeout(() => {
    mapResizeHighlightedSection.value = ''
    mapResizeSectionHighlightTimer = null
  }, 1800)
}

function highlightMapResizeItems(itemKeys = []) {
  mapResizeHighlightedItemKeys.value = [...new Set((Array.isArray(itemKeys) ? itemKeys : [itemKeys]).filter(Boolean))]
  if (mapResizeItemHighlightTimer) {
    clearTimeout(mapResizeItemHighlightTimer)
  }
  if (mapResizeHighlightedItemKeys.value.length === 0) {
    mapResizeItemHighlightTimer = null
    return
  }
  mapResizeItemHighlightTimer = setTimeout(() => {
    mapResizeHighlightedItemKeys.value = []
    mapResizeItemHighlightTimer = null
  }, 1800)
}

function collectSectionFocusCells(section) {
  if (!section?.items) return []
  return section.items
    .map(item => item.focus)
    .filter(cell => cell && Number.isFinite(Number(cell.x)) && Number.isFinite(Number(cell.y)))
}

function focusMapResizeReasonItem(reason) {
  if (!reason) return
  const targetSectionKey = reason.targetSectionKey || 'reasons'
  highlightMapResizeSection(targetSectionKey)

  if (reason.targetSectionKey) {
    const targetSection = mapResizePreviewDetailSections.value.find(section => section.key === reason.targetSectionKey)
    const itemKeys = targetSection?.items?.map(item => item.key) ?? []
    highlightMapResizeItems(itemKeys)
    if (targetSection?.title) {
      showFloatingToast(`${settingsLocale.value.resizePreviewDetailTitle}: ${targetSection.title}`, 'info')
    } else {
      showFloatingToast(reason.text, 'info')
    }
    const focusCells = collectSectionFocusCells(targetSection)
    if (focusCells.length > 0) {
      focusMapPreviewCells(focusCells)
    }
  } else {
    highlightMapResizeItems([])
    showFloatingToast(reason.text, 'info')
  }

  const targetElement =
    typeof document !== 'undefined'
      ? document.getElementById(mapResizeSectionDomId(targetSectionKey))
      : null
  if (!targetElement) return

  const panelElement = mapSettingsPanelRef.value
  if (panelElement && typeof panelElement.scrollTo === 'function') {
    const panelRect = panelElement.getBoundingClientRect()
    const targetRect = targetElement.getBoundingClientRect()
    const nextScrollTop = panelElement.scrollTop + (targetRect.top - panelRect.top) - 12
    panelElement.scrollTop = Math.max(0, nextScrollTop)
  } else {
    targetElement.scrollIntoView({
      behavior: 'auto',
      block: 'start',
    })
  }
}

function normalizeMapResizePreviewInputs() {
  mapResizePreviewDirty.value = true
  return setMapResizePreviewDraft(mapResizePreviewColsInput.value, mapResizePreviewRowsInput.value)
}

function markMapResizePreviewDirty() {
  mapResizePreviewDirty.value = true
}

function focusMapPreviewCells(cells) {
  const normalizedCells = [...new Map(
    (Array.isArray(cells) ? cells : [cells])
      .filter(cell => cell && Number.isFinite(Number(cell.x)) && Number.isFinite(Number(cell.y)))
      .map(cell => {
        const x = Number(cell.x)
        const y = Number(cell.y)
        return [`${x},${y}`, { x, y }]
      })
  ).values()]
  if (normalizedCells.length === 0) return

  const minX = Math.min(...normalizedCells.map(cell => cell.x))
  const maxX = Math.max(...normalizedCells.map(cell => cell.x))
  const minY = Math.min(...normalizedCells.map(cell => cell.y))
  const maxY = Math.max(...normalizedCells.map(cell => cell.y))

  focusMapAtWorld(((minX + maxX + 1) / 2) * CELL_SIZE, ((minY + maxY + 1) / 2) * CELL_SIZE)
  mapPreviewFocusCells.value = normalizedCells.map(cell => ({
    ...cell,
    key: `focus-${++mapPreviewFocusSequence}-${cell.x}-${cell.y}`,
  }))

  if (mapPreviewFocusTimer) {
    clearTimeout(mapPreviewFocusTimer)
  }
  mapPreviewFocusTimer = setTimeout(() => {
    mapPreviewFocusCells.value = []
    mapPreviewFocusTimer = null
  }, 1800)
}

function focusMapPreviewCell(cell) {
  focusMapPreviewCells(cell ? [cell] : [])
}

async function saveCurrentMapProfile() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  const defaultName =
    (typeof currentMapProfile.value?.name === 'string'
      ? currentMapProfile.value.name
      : currentMapProfileLabel.value) || `${gridColsValue()}x${gridRowsValue()}`
  const profileNameInput = window.prompt(
    `${settingsLocale.value.mapProfileSaveConfirm}\n\n${settingsLocale.value.mapProfileSave}`,
    defaultName
  )
  if (profileNameInput === null) {
    return false
  }

  const profileName = profileNameInput.trim()
  if (!profileName) {
    setObstacleLayoutStatus('error', settingsLocale.value.mapProfileNameRequired)
    return false
  }

  mapProfileSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map/profile`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        name: profileName,
        blocked_cells: blockedCells.value,
        valid_cells: validCells.value,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue(),
        topology: currentMapTopology.value,
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, settingsLocale.value.mapProfileSaveFailed)
    }
    await fetchMapProfiles()
    const successMessage = data?.name_adjusted
      ? formatMapProfileAdjustedMessage(data?.requested_name, data?.resolved_name)
      : settingsLocale.value.mapProfileSaveSuccess
    setObstacleLayoutStatus('success', successMessage)
    showFloatingToast(successMessage, 'success')
    return true
  } catch (error) {
    console.error('Save map profile error:', error)
    setObstacleLayoutStatus('error', error?.message || settingsLocale.value.mapProfileSaveFailed)
    return false
  } finally {
    mapProfileSaving.value = false
  }
}

async function exportMapProfile(profile) {
  if (!profile?.key) return false
  mapProfileExportingKey.value = profile.key
  try {
    const res = await fetch(`${API_BASE}/status/map/profile/${encodeURIComponent(profile.key)}`)
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, settingsLocale.value.mapProfileExportFailed)
    }

    const payload = {
      version: 1,
      exported_at: new Date().toISOString(),
      profile: {
        key: data.key,
        name: localizedMapProfileField(data.name) || data.key,
        description: localizedMapProfileField(data.description),
        grid_cols: Number(data.grid_cols),
        grid_rows: Number(data.grid_rows),
        custom: Boolean(data.custom),
        blocked_count: Number(data.blocked_count ?? 0),
        blocked_cells: Array.isArray(data.blocked_cells) ? data.blocked_cells : [],
        valid_count: Number(data.valid_count ?? 0),
        valid_cells: Array.isArray(data.valid_cells) ? data.valid_cells : [],
        topology: data?.topology ?? createEmptyMapTopology()
      }
    }
    downloadJsonFile(`agv-map-profile-${data.key}.json`, JSON.stringify(payload, null, 2))
    showFloatingToast(settingsLocale.value.mapProfileExportSuccess, 'success')
    return true
  } catch (error) {
    console.error('Export map profile error:', error)
    showFloatingToast(error?.message || settingsLocale.value.mapProfileExportFailed, 'error')
    return false
  } finally {
    mapProfileExportingKey.value = ''
  }
}

function triggerMapProfileImport() {
  mapProfileFileInputRef.value?.click()
}

function normalizeImportedMapProfilePayload(payload) {
  const profile = payload?.profile ?? payload ?? {}
  const name = String(profile.name ?? '').trim()
  if (!name) return null

  const gridCols = sanitizeGridDimensionInput(profile.grid_cols, gridColsValue())
  const gridRows = sanitizeGridDimensionInput(profile.grid_rows, gridRowsValue())
  const rawCells = Array.isArray(profile.blocked_cells) ? profile.blocked_cells : []
  const rawValidCells = Array.isArray(profile.valid_cells) ? profile.valid_cells : null
  const blockedCells = normalizeBlockedCellList(
    rawCells
      .filter(cell => Number.isFinite(Number(cell?.x)) && Number.isFinite(Number(cell?.y)))
      .map(cell => ({
        x: Math.round(Number(cell.x)),
        y: Math.round(Number(cell.y))
      }))
  )
  const validCells = normalizeValidCellList(
    rawValidCells?.map(cell => ({
      x: Math.round(Number(cell?.x)),
      y: Math.round(Number(cell?.y))
    })),
    gridCols,
    gridRows
  )
  const topology = normalizeMapTopology(profile.topology, gridCols, gridRows, validCells)

  return {
    name,
    description: String(profile.description ?? '').trim() || null,
    grid_cols: gridCols,
    grid_rows: gridRows,
    blocked_cells: filterBlockedCellsAgainstValid(blockedCells, validCells),
    valid_cells: validCells,
    topology
  }
}

function formatMapProfileAdjustedMessage(requestedName, resolvedName) {
  return settingsLocale.value.mapProfileNameAdjusted
    .replace('{requested}', requestedName || resolvedName || '')
    .replace('{resolved}', resolvedName || requestedName || '')
}

async function onMapProfileFileChange(event) {
  const input = event?.target
  const file = input?.files?.[0]
  if (!file) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) {
    if (input) input.value = ''
    return
  }

  mapProfileImporting.value = true
  try {
    const rawText = await file.text()
    const parsed = JSON.parse(rawText)
    const normalized = normalizeImportedMapProfilePayload(parsed)
    if (!normalized) {
      throw new Error(settingsLocale.value.mapProfileImportInvalid)
    }

    const res = await fetch(`${API_BASE}/status/map/profile`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        ...normalized,
        import_source: 'json'
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, settingsLocale.value.mapProfileImportFailed)
    }

    await fetchMapProfiles()
    const successMessage = data?.name_adjusted
      ? formatMapProfileAdjustedMessage(data?.requested_name, data?.resolved_name)
      : settingsLocale.value.mapProfileImportSuccess
    setObstacleLayoutStatus('success', successMessage)
    showFloatingToast(successMessage, 'success')
  } catch (error) {
    console.error('Import map profile error:', error)
    setObstacleLayoutStatus('error', error?.message || settingsLocale.value.mapProfileImportFailed)
    showFloatingToast(error?.message || settingsLocale.value.mapProfileImportFailed, 'error')
  } finally {
    mapProfileImporting.value = false
    if (input) {
      input.value = ''
    }
  }
}

async function deleteMapProfile(profile) {
  if (!profile?.key || !profile?.deletable) {
    return false
  }
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (!window.confirm(settingsLocale.value.mapProfileDeleteConfirm)) {
    return false
  }

  mapProfileDeletingKey.value = profile.key
  try {
    const res = await fetch(`${API_BASE}/status/map/profile/${encodeURIComponent(profile.key)}`, {
      method: 'DELETE',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, settingsLocale.value.mapProfileDeleteFailed)
    }
    if (mapProfilePreviewingKey.value === profile.key) {
      mapProfilePreviewingKey.value = ''
    }
    await fetchMapProfiles()
    setObstacleLayoutStatus('success', settingsLocale.value.mapProfileDeleteSuccess)
    showFloatingToast(settingsLocale.value.mapProfileDeleteSuccess, 'success')
    return true
  } catch (error) {
    console.error('Delete map profile error:', error)
    setObstacleLayoutStatus('error', error?.message || settingsLocale.value.mapProfileDeleteFailed)
    return false
  } finally {
    mapProfileDeletingKey.value = ''
  }
}

async function applyMapProfile(profile) {
  if (!profile?.key) return false
  if (obstacleLayoutDirty.value) {
    setObstacleLayoutStatus('error', obstacleSaveRequiredText())
    return false
  }
  if (isCurrentMapProfile(profile)) {
    showFloatingToast(settingsLocale.value.mapProfileApplyCurrent, 'info')
    return false
  }

  const profileName = localizedMapProfileField(profile.name) || profile.key
  const forceApply = canForceApplyMapProfile(profile)
  if (
    !ensureAuthenticatedOperation(
      t('auth_action_requires_login'),
      forceApply ? 'map.force_apply' : 'map.write',
      forceApply ? t('auth_map_force_apply_denied') : buildCapabilityDeniedMessage('map')
    )
  ) {
    return false
  }
  const confirmMessage = forceApply
    ? settingsLocale.value.mapProfileForceApplyConfirm
    : settingsLocale.value.mapProfileApplyConfirm
  if (!window.confirm(`${confirmMessage}\n${profileName}`)) {
    return false
  }

  const requestedCols = Math.max(1, Number(profile.grid_cols || 0))
  const requestedRows = Math.max(1, Number(profile.grid_rows || 0))
  const previousSizeLabel = `${gridColsValue()} x ${gridRowsValue()}`
  const previousBlockedCount = blockedCells.value.length
  const previousProfileName = currentMapProfileLabel.value
  mapProfileApplyingKey.value = profile.key
  mapProfilePreviewingKey.value = profile.key
  mapProfileActionSummary.value = null
  mapResizePreviewDirty.value = true
  setMapResizePreviewDraft(requestedCols, requestedRows)

  try {
    const query = forceApply ? '?force=true' : ''
    const res = await fetch(`${API_BASE}/status/map/profile/${encodeURIComponent(profile.key)}${query}`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      if (Array.isArray(data?.detail?.blockers)) {
        mapResizePreview.value = {
          ...(mapResizePreview.value ?? createMapResizePreviewSnapshot(gridColsValue(), gridRowsValue(), false)),
          ...data.detail,
          can_apply: false,
          requested_grid_cols: requestedCols,
          requested_grid_rows: requestedRows,
        }
        mapProfileActionSummary.value = {
          type: 'blocked',
          profileName,
          blockers: data.detail.blockers,
          forceApplyAllowed: Boolean(data.detail.force_apply_allowed),
        }
        await nextTick()
        if (data.detail.blockers.length > 0) {
          focusMapResizeReasonKey(data.detail.blockers[0])
        }
      }
      throw createApiError(data, settingsLocale.value.mapProfileApplyFailed)
    }

    applyGridSizeFromPayload(data)
    mapResizePreviewDirty.value = false
    const normalized = normalizeBlockedCellList(data?.blocked_cells ?? blockedCells.value)
    const normalizedValidCells = normalizeValidCellList(data?.valid_cells, requestedCols, requestedRows)
    blockedCells.value = normalized
    validCells.value = normalizedValidCells
    syncedBlockedCells.value = normalized
    syncedValidCells.value = normalizedValidCells
    syncMapTopologyFromPayload(data, normalizedValidCells)
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized, normalizedValidCells)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    mapResizePreview.value = createMapResizePreviewSnapshot(requestedCols, requestedRows, true)
    await Promise.all([fetchMapProfiles(), fetchMapPresets()])
    await nextTick()
    updateMapViewportMetrics(true)
    clearPreview()
    cancelSelection()

    let successMessage = mergeObstacleStatusMessage(
      forceApply ? settingsLocale.value.mapProfileForceApplySuccess : settingsLocale.value.mapProfileApplySuccess,
      Number(data?.skipped_occupied_count ?? 0)
    )
    if (forceApply) {
      successMessage = successMessage
        .replace('{agvs}', String(Number(data?.relocated_agv_count ?? 0)))
        .replace('{blocked}', String(Number(data?.trimmed_blocked_cells_count ?? 0)))
      mapProfileActionSummary.value = {
        type: 'forced',
        profileName,
        previousProfileName,
        previousSizeLabel,
        nextSizeLabel: `${requestedCols} x ${requestedRows}`,
        previousBlockedCount,
        nextBlockedCount: normalized.length,
        relocatedAgvs: Array.isArray(data?.relocated_agvs) ? data.relocated_agvs : [],
        trimmedBlockedCount: Number(data?.trimmed_blocked_cells_count ?? 0),
        trimmedBlockedCells: Array.isArray(data?.trimmed_blocked_cells) ? data.trimmed_blocked_cells : [],
      }
      const focusCells = [
        ...(Array.isArray(data?.relocated_agvs) ? data.relocated_agvs.map(item => item?.to).filter(Boolean) : []),
      ]
      if (focusCells.length > 0) {
        focusMapPreviewCells(focusCells)
      }
    } else {
      mapProfileActionSummary.value = null
    }
    setObstacleLayoutStatus('success', successMessage)
    showFloatingToast(successMessage, 'success')
    return true
  } catch (error) {
    console.error('Apply map profile error:', error)
    setObstacleLayoutStatus('error', error?.message || settingsLocale.value.mapProfileApplyFailed)
    return false
  } finally {
    mapProfileApplyingKey.value = ''
  }
}

async function runMapResizePrecheck(nextCols = null, nextRows = null, previewProfileKey = '') {
  if (obstacleLayoutDirty.value) {
    setObstacleLayoutStatus('error', obstacleSaveRequiredText())
    return
  }
  const requestedCols = sanitizeGridDimensionInput(
    isPrimitiveGridOverride(nextCols) ? nextCols : mapResizePreviewColsInput.value,
    gridColsValue()
  )
  const requestedRows = sanitizeGridDimensionInput(
    isPrimitiveGridOverride(nextRows) ? nextRows : mapResizePreviewRowsInput.value,
    gridRowsValue()
  )
  mapResizePreviewDirty.value = true
  setMapResizePreviewDraft(requestedCols, requestedRows)
  mapProfilePreviewingKey.value = previewProfileKey || ''
  mapResizePreviewLoading.value = true
  try {
    const params = new URLSearchParams({
      grid_cols: String(requestedCols),
      grid_rows: String(requestedRows),
    })
    const res = await fetch(`${API_BASE}/status/map/resize-precheck?${params.toString()}`)
    if (!res.ok) {
      throw new Error(`Map resize precheck failed: ${res.status}`)
    }
    mapResizePreview.value = await res.json()
  } catch (error) {
    console.error('Map resize precheck error:', error)
    if (previewProfileKey) {
      mapProfilePreviewingKey.value = ''
    }
    showFloatingToast(error?.message || settingsLocale.value.resizePreviewRequestFailed, 'error')
  } finally {
    mapResizePreviewLoading.value = false
  }
}

async function previewMapProfile(profile) {
  if (!profile?.key) return
  if (obstacleLayoutDirty.value) {
    setObstacleLayoutStatus('error', obstacleSaveRequiredText())
    return
  }
  mapResizePreviewDirty.value = true
  await runMapResizePrecheck(profile.grid_cols, profile.grid_rows, profile.key)
}

async function applyMapResize() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (obstacleLayoutDirty.value) {
    setObstacleLayoutStatus('error', obstacleSaveRequiredText())
    return false
  }
  const { requestedCols, requestedRows } = normalizeMapResizePreviewInputs()
  mapProfilePreviewingKey.value = ''

  if (requestedCols === gridColsValue() && requestedRows === gridRowsValue()) {
    showFloatingToast(settingsLocale.value.resizeApplyNoChange, 'info')
    return false
  }
  if (!mapResizePreviewMatchesInput.value) {
    showFloatingToast(settingsLocale.value.resizePreviewStale, 'error')
    return false
  }
  if (!mapResizePreview.value?.can_apply) {
    showFloatingToast(settingsLocale.value.resizeApplyBlocked, 'error')
    return false
  }
  if (!window.confirm(settingsLocale.value.resizeApplyConfirm)) {
    return false
  }

  mapResizePreviewLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map/resize`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        grid_cols: requestedCols,
        grid_rows: requestedRows,
      })
    })
    const data = await res.json()
    if (!res.ok) {
      if (Array.isArray(data?.detail?.blockers)) {
        mapResizePreview.value = {
          ...(mapResizePreview.value ?? createMapResizePreviewSnapshot(gridColsValue(), gridRowsValue(), false)),
          ...data.detail,
          can_apply: false,
          requested_grid_cols: requestedCols,
          requested_grid_rows: requestedRows,
        }
      }
      throw createApiError(data, settingsLocale.value.resizeApplyFailed)
    }

    applyGridSizeFromPayload(data)
    mapResizePreviewDirty.value = false
    const normalized = normalizeBlockedCellList(data?.blocked_cells ?? blockedCells.value)
    const normalizedValidCells = normalizeValidCellList(data?.valid_cells, requestedCols, requestedRows)
    blockedCells.value = normalized
    validCells.value = normalizedValidCells
    syncedBlockedCells.value = normalized
    syncedValidCells.value = normalizedValidCells
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized, normalizedValidCells)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    mapResizePreview.value = createMapResizePreviewSnapshot(requestedCols, requestedRows, true)
    await Promise.all([fetchMapProfiles(), fetchMapPresets()])
    await nextTick()
    updateMapViewportMetrics(true)
    clearPreview()
    cancelSelection()
    setObstacleLayoutStatus('success', settingsLocale.value.resizeApplySuccess)
    showFloatingToast(settingsLocale.value.resizeApplySuccess, 'success')
    return true
  } catch (error) {
    console.error('Apply map resize error:', error)
    setObstacleLayoutStatus('error', error?.message || settingsLocale.value.resizeApplyFailed)
    return false
  } finally {
    mapResizePreviewLoading.value = false
  }
}

function detectObstacleSceneKey(cells, nextValidCells = validCells.value) {
  const normalizedCells = normalizeBlockedCellList(cells)
  const currentKeys = normalizedCells.map(cell => blockedCellKey(cell.x, cell.y))
  const currentValidKeys = normalizeValidCellList(nextValidCells).map(cell => blockedCellKey(cell.x, cell.y))

  for (const preset of obstaclePresets.value) {
    const presetCells = normalizeBlockedCellList(preset.blocked_cells ?? [])
    const presetKeys = presetCells.map(cell => blockedCellKey(cell.x, cell.y))
    const presetValidKeys = normalizeValidCellList(
      preset.valid_cells,
      Number(preset.grid_cols || gridColsValue()),
      Number(preset.grid_rows || gridRowsValue())
    ).map(cell => blockedCellKey(cell.x, cell.y))
    if (presetKeys.length !== currentKeys.length) continue
    if (presetValidKeys.length !== currentValidKeys.length) continue
    if (presetKeys.every((key, index) => key === currentKeys[index])) {
      if (presetValidKeys.every((key, index) => key === currentValidKeys[index])) {
        return preset.key
      }
    }
  }

  return 'custom'
}

function normalizeBlockedCellList(cells) {
  return Array.from(new Set(
    cells
      .filter(cell => Number.isInteger(cell.x) && Number.isInteger(cell.y))
      .map(cell => `${cell.x},${cell.y}`)
  ))
    .map(key => {
      const [x, y] = key.split(',').map(Number)
      return { x, y }
    })
    .sort((a, b) => a.x - b.x || a.y - b.y)
}

function filterBlockedCellsAgainstValid(cells, nextValidCells = validCells.value) {
  const validKeySet = new Set(
    normalizeValidCellList(nextValidCells).map(cell => blockedCellKey(cell.x, cell.y))
  )
  return normalizeBlockedCellList(cells).filter(cell => validKeySet.has(blockedCellKey(cell.x, cell.y)))
}

function filterBlockedCellsAgainstOccupied(cells) {
  const normalized = normalizeBlockedCellList(cells)
  const filtered = []
  const skipped = []

  for (const cell of normalized) {
    if (occupiedCellSet.value.has(blockedCellKey(cell.x, cell.y))) {
      skipped.push(cell)
      continue
    }
    filtered.push(cell)
  }

  return { filtered, skipped }
}

function hasObstacleMutationLock() {
  return obstacleMutationLocked.value
}

function ensureObstacleMutationAllowed() {
  if (!hasObstacleMutationLock()) return true
  const message = obstacleMutationLockedText()
  setObstacleLayoutStatus('error', message)
  return false
}

function toggleObstacleEditMode() {
  if (!obstacleEditMode.value && !ensureObstacleMutationAllowed()) {
    return
  }
  obstacleEditMode.value = !obstacleEditMode.value
  if (obstacleEditMode.value) {
    cancelSelection()
    clearPreview()
    cancelTaskChainMapPick(false)
  }
}

function toggleBlockedCellAt(x, y) {
  if (isCellOccupied(x, y) || !isValidMapCell(x, y)) return
  const key = blockedCellKey(x, y)
  if (blockedCellSet.value.has(key)) {
    blockedCells.value = blockedCells.value.filter(cell => blockedCellKey(cell.x, cell.y) !== key)
    return
  }
  blockedCells.value = normalizeBlockedCellList([...blockedCells.value, { x, y }])
}

function applyObstaclePaintAt(x, y, mode) {
  if (isCellOccupied(x, y) || !isValidMapCell(x, y)) return

  const key = blockedCellKey(x, y)
  if (obstaclePaintLastKey === key) return
  obstaclePaintLastKey = key

  if (mode === 'remove') {
    if (!blockedCellSet.value.has(key)) return
    blockedCells.value = blockedCells.value.filter(cell => blockedCellKey(cell.x, cell.y) !== key)
    return
  }

  if (blockedCellSet.value.has(key)) return
  blockedCells.value = normalizeBlockedCellList([...blockedCells.value, { x, y }])
}

function stopObstaclePaint() {
  obstaclePaintActive = false
  obstaclePaintLastKey = ''
}

async function saveBlockedCells(
  nextBlockedCells = blockedCells.value,
  nextValidCells = validCells.value,
  nextGridCols = gridColsValue(),
  nextGridRows = gridRowsValue(),
  nextTopology = currentMapTopology.value
) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (!ensureObstacleMutationAllowed()) {
    return false
  }
  obstacleMapSaving.value = true
  try {
    const targetGridCols = sanitizeGridDimensionInput(nextGridCols, gridColsValue())
    const targetGridRows = sanitizeGridDimensionInput(nextGridRows, gridRowsValue())
    const normalizedValidCells = normalizeValidCellList(nextValidCells, targetGridCols, targetGridRows)
    const normalizedTopology = normalizeMapTopology(nextTopology, targetGridCols, targetGridRows, normalizedValidCells)
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(
      filterBlockedCellsAgainstValid(nextBlockedCells, normalizedValidCells)
    )
    const res = await fetch(`${API_BASE}/status/map`, {
      method: 'PUT',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        blocked_cells: filtered,
        valid_cells: normalizedValidCells,
        grid_cols: targetGridCols,
        grid_rows: targetGridRows,
        topology: normalizedTopology
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Save blocked cells failed')
    }
    applyGridSizeFromPayload(data)
    const appliedCols = Number(data?.grid_cols || targetGridCols)
    const appliedRows = Number(data?.grid_rows || targetGridRows)
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? filtered)
      .filter(cell => cell.x < appliedCols && cell.y < appliedRows)
    const syncedValid = normalizeValidCellList(data?.valid_cells, appliedCols, appliedRows)
    blockedCells.value = normalized
    validCells.value = syncedValid
    syncedBlockedCells.value = normalized
    syncedValidCells.value = syncedValid
    syncMapTopologyFromPayload(data, syncedValid)
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized, syncedValid)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    clearPreview()
    cancelSelection()
    const skippedCount = Number(data?.skipped_occupied_count ?? skipped.length ?? 0)
    setObstacleLayoutStatus('success', mergeObstacleStatusMessage(settingsLocale.value.obstacleSaved, skippedCount))
    await scheduleAutoIfReady()
    return true
  } catch (error) {
    console.error('Save blocked cells error:', error)
    setObstacleLayoutStatus('error', error?.message || 'Save blocked cells failed')
    return false
  } finally {
    obstacleMapSaving.value = false
  }
}

async function saveCurrentObstaclePreset(defaultName = '') {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  const presetNameInput = window.prompt(obstaclePresetNamePromptText(), defaultName)
  if (presetNameInput === null) {
    return false
  }

  const presetName = presetNameInput.trim()
  if (!presetName) {
    setObstacleLayoutStatus('error', obstaclePresetNameRequiredText())
    return false
  }

  obstacleMapSaving.value = true
  try {
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(blockedCells.value)
    const res = await fetch(`${API_BASE}/status/map/preset`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        name: presetName,
        blocked_cells: filtered,
        valid_cells: validCells.value,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Save obstacle preset failed')
    }

    applyGridSizeFromPayload(data)
    await fetchMapPresets()
    const newPresetKey = data?.preset?.key
    if (newPresetKey && obstaclePresets.value.some(preset => preset.key === newPresetKey)) {
      selectedObstaclePreset.value = newPresetKey
    }
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value, validCells.value)
    setObstacleLayoutStatus(
      'success',
      mergeObstacleStatusMessage(
        settingsLocale.value.obstaclePresetSavedCustom,
        Number(data?.skipped_occupied_count ?? skipped.length ?? 0)
      )
    )
    clearImportedObstacleLayoutPreset()
    return true
  } catch (error) {
    console.error('Save obstacle preset error:', error)
    setObstacleLayoutStatus('error', error?.message || 'Save obstacle preset failed')
    return false
  } finally {
    obstacleMapSaving.value = false
  }
}

async function saveImportedObstacleAsPreset() {
  return saveCurrentObstaclePreset(importedObstaclePresetSuggestedName.value || defaultImportedObstaclePresetName())
}

async function deleteSelectedObstaclePreset() {
  if (!selectedObstaclePresetDeletable.value) {
    setObstacleLayoutStatus('error', settingsLocale.value.obstaclePresetDeleteOnlyCustom)
    return false
  }
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (!window.confirm(obstaclePresetDeleteConfirmText())) {
    return false
  }

  obstacleMapSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map/preset/${selectedObstaclePreset.value}`, {
      method: 'DELETE',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Delete obstacle preset failed')
    }

    await fetchMapPresets()
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value, validCells.value)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    setObstacleLayoutStatus('success', settingsLocale.value.obstaclePresetDeleted)
    return true
  } catch (error) {
    console.error('Delete obstacle preset error:', error)
    setObstacleLayoutStatus('error', error?.message || 'Delete obstacle preset failed')
    return false
  } finally {
    obstacleMapSaving.value = false
  }
}

async function resetBlockedCellsToDefault() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (!ensureObstacleMutationAllowed()) {
    return false
  }
  if (obstacleLayoutDirty.value && !window.confirm(confirmDiscardObstacleChangesText())) {
    return false
  }
  obstacleMapSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map/reset`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Reset blocked cells failed')
    }
    applyGridSizeFromPayload(data)
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? [])
    const normalizedValidCells = normalizeValidCellList(data?.valid_cells, gridColsValue(), gridRowsValue())
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    validCells.value = normalizedValidCells
    syncedBlockedCells.value = filtered
    syncedValidCells.value = normalizedValidCells
    syncMapTopologyFromPayload(data, normalizedValidCells)
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered, normalizedValidCells)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    clearPreview()
    cancelSelection()
    setObstacleLayoutStatus(
      'success',
      mergeObstacleStatusMessage(
        settingsLocale.value.obstacleResetDone,
        Number(data?.skipped_occupied_count ?? 0) + skipped.length
      )
    )
    await scheduleAutoIfReady()
    return true
  } catch (error) {
    console.error('Reset blocked cells error:', error)
    setObstacleLayoutStatus('error', error?.message || 'Reset blocked cells failed')
    return false
  } finally {
    obstacleMapSaving.value = false
  }
}

async function ensureBlockedCellsSynced() {
  if (!obstacleLayoutDirty.value) return true
  setObstacleLayoutStatus('error', obstacleSaveRequiredText())
  return false
}

async function fetchMapPresets() {
  try {
    const res = await fetch(`${API_BASE}/status/map/presets`)
    if (!res.ok) {
      throw new Error(`Map preset request failed: ${res.status}`)
    }
    const data = await res.json()
    applyGridSizeFromPayload(data)
    obstaclePresets.value = Array.isArray(data?.presets) ? data.presets : []
    if (
      obstaclePresets.value.length > 0 &&
      !obstaclePresets.value.some(preset => preset.key === selectedObstaclePreset.value)
    ) {
      selectedObstaclePreset.value = obstaclePresets.value[0].key
    }
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value, validCells.value)
  } catch (error) {
    console.error('Fetch map presets error:', error)
    obstaclePresets.value = []
  }
}

async function fetchMapProfiles() {
  try {
    const res = await fetch(`${API_BASE}/status/map/profiles`)
    if (!res.ok) {
      throw new Error(`Map profile request failed: ${res.status}`)
    }
    const data = await res.json()
    mapProfiles.value = Array.isArray(data?.profiles) ? data.profiles : []
    currentMapProfile.value = data?.current_profile ?? null
    syncMapSizeResizeState()
  } catch (error) {
    console.error('Fetch map profiles error:', error)
    mapProfiles.value = []
    currentMapProfile.value = null
    syncMapSizeResizeState()
  }
}

function syncMapSizeResizeState() {
  const hasActiveTasks = tasks.value.some(task =>
    ['pending', 'assigned', 'running', 'blocked'].includes(task.status)
  )
  const hasBusyAgvs = agvs.value.some(agv => !['idle', 'maintenance'].includes(agv.status))
  mapSizeResizeReady.value = !hasActiveTasks && !hasBusyAgvs
  if (hasActiveTasks && hasBusyAgvs) {
    mapSizeResizeLockReason.value = 'active_tasks_and_busy_agvs'
    return
  }
  if (hasActiveTasks) {
    mapSizeResizeLockReason.value = 'active_tasks_present'
    return
  }
  if (hasBusyAgvs) {
    mapSizeResizeLockReason.value = 'agvs_not_idle'
    return
  }
  mapSizeResizeLockReason.value = 'ready'
}

async function fetchMapLayout() {
  try {
    const res = await fetch(`${API_BASE}/status/map`)
    if (!res.ok) {
      throw new Error(`Map layout request failed: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data?.blocked_cells)) {
      applyGridSizeFromPayload(data)
      blockedCells.value = [...DEFAULT_BLOCKED_CELLS]
      validCells.value = buildFullValidCellList(gridColsValue(), gridRowsValue())
      syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
      syncedValidCells.value = buildFullValidCellList(gridColsValue(), gridRowsValue())
      currentMapTopology.value = createEmptyMapTopology()
      appliedObstacleSceneKey.value = 'default_shelves'
      selectedObstaclePreset.value = 'default_shelves'
      clearImportedObstacleLayoutPreset()
      return
    }

    applyGridSizeFromPayload(data)
    const normalized = normalizeBlockedCellList(
      data.blocked_cells.map(cell => ({
        x: Number(cell.x),
        y: Number(cell.y)
      }))
    )
    const normalizedValidCells = normalizeValidCellList(data?.valid_cells, gridColsValue(), gridRowsValue())
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    validCells.value = normalizedValidCells
    syncedBlockedCells.value = filtered
    syncedValidCells.value = normalizedValidCells
    syncMapTopologyFromPayload(data, normalizedValidCells)
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered, normalizedValidCells)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    if (skipped.length > 0) {
      setObstacleLayoutStatus('info', obstacleSkippedOccupiedText(skipped.length))
    }
  } catch (error) {
    console.error('Fetch map layout error:', error)
    blockedCells.value = [...DEFAULT_BLOCKED_CELLS]
    validCells.value = buildFullValidCellList(gridColsValue(), gridRowsValue())
    syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
    syncedValidCells.value = buildFullValidCellList(gridColsValue(), gridRowsValue())
    currentMapTopology.value = createEmptyMapTopology()
    appliedObstacleSceneKey.value = 'default_shelves'
    selectedObstaclePreset.value = 'default_shelves'
    clearImportedObstacleLayoutPreset()
  }
}

async function applyObstaclePreset() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (!ensureObstacleMutationAllowed()) {
    return false
  }
  if (!selectedObstaclePreset.value) {
    setObstacleLayoutStatus('error', settingsLocale.value.obstaclePresetNone)
    return false
  }
  if (obstacleLayoutDirty.value && !window.confirm(confirmDiscardObstacleChangesText())) {
    return false
  }

  obstacleMapSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map/preset/${selectedObstaclePreset.value}`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Apply obstacle preset failed')
    }
    applyGridSizeFromPayload(data)
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? [])
    const normalizedValidCells = normalizeValidCellList(data?.valid_cells, gridColsValue(), gridRowsValue())
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    validCells.value = normalizedValidCells
    syncedBlockedCells.value = filtered
    syncedValidCells.value = normalizedValidCells
    syncMapTopologyFromPayload(data, normalizedValidCells)
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered, normalizedValidCells)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    clearImportedObstacleLayoutPreset()
    clearPreview()
    cancelSelection()
    setObstacleLayoutStatus(
      'success',
      mergeObstacleStatusMessage(
        settingsLocale.value.obstacleApplied,
        Number(data?.skipped_occupied_count ?? 0) + skipped.length
      )
    )
    await scheduleAutoIfReady()
    return true
  } catch (error) {
    console.error('Apply obstacle preset error:', error)
    setObstacleLayoutStatus('error', error?.message || 'Apply obstacle preset failed')
    return false
  } finally {
    obstacleMapSaving.value = false
  }
}

function downloadObstacleLayout() {
  const payload = {
    grid_cols: gridColsValue(),
    grid_rows: gridRowsValue(),
    blocked_cells: normalizeBlockedCellList(blockedCells.value),
    valid_cells: normalizeValidCellList(validCells.value),
    topology: currentMapTopology.value
  }
  downloadJsonFile('agv-obstacle-layout.json', JSON.stringify(payload, null, 2))
}

function triggerObstacleLayoutImport() {
  if (!ensureObstacleMutationAllowed()) {
    return
  }
  obstacleLayoutFileInputRef.value?.click()
}

async function importObstacleLayout(rawText, sourceName = '') {
  try {
    if (!ensureObstacleMutationAllowed()) {
      return
    }
    if (obstacleLayoutDirty.value && !window.confirm(confirmDiscardObstacleChangesText())) {
      return
    }
    const parsed = JSON.parse(rawText)
    const rawCells = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed?.blocked_cells)
        ? parsed.blocked_cells
        : null
    const rawValidCells = Array.isArray(parsed?.valid_cells) ? parsed.valid_cells : null
    if (!rawCells) {
      throw new Error(invalidObstacleLayoutText())
    }

    const normalized = normalizeBlockedCellList(
      rawCells.map(cell => ({
        x: Number(cell?.x),
        y: Number(cell?.y)
      }))
    )
    const normalizedValidCells = normalizeValidCellList(rawValidCells, gridColsValue(), gridRowsValue())
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(
      filterBlockedCellsAgainstValid(normalized, normalizedValidCells)
    )
    blockedCells.value = filtered
    validCells.value = normalizedValidCells
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered, normalizedValidCells)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    rememberImportedObstacleLayoutPreset(sourceName)
    setObstacleLayoutStatus('info', mergeObstacleStatusMessage(obstacleImportedPendingSaveText(), skipped.length))
  } catch (error) {
    console.error('Import obstacle layout error:', error)
    setObstacleLayoutStatus('error', error?.message || 'Import obstacle layout failed')
  }
}

async function onObstacleLayoutFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const text = await file.text()
  await importObstacleLayout(text, file.name)
}

function stopEnterpriseAgvMotionPolling() {
  if (!enterpriseAgvMotionPollTimer) return
  clearInterval(enterpriseAgvMotionPollTimer)
  enterpriseAgvMotionPollTimer = null
}

function ensureEnterpriseAgvMotionPolling() {
  if (enterpriseAgvMotionPollTimer || typeof window === 'undefined') return
  enterpriseAgvMotionPollTimer = setInterval(() => {
    if (!dashboardUnlocked.value || !uiTreatAsEnterpriseRole.value || isPlatformAdminGovernanceMode.value) return
    void fetchAgvs()
  }, ENTERPRISE_AGV_MOTION_POLL_INTERVAL_MS)
}

function stopAgvAnimationLoop() {
  if (!agvAnimationFrameHandle || typeof window === 'undefined') return
  window.cancelAnimationFrame(agvAnimationFrameHandle)
  agvAnimationFrameHandle = null
}

function runAgvAnimationLoop() {
  agvAnimationNow.value = Date.now()
  if (!enterpriseAgvMotionActive.value || typeof window === 'undefined') {
    agvAnimationFrameHandle = null
    return
  }
  agvAnimationFrameHandle = window.requestAnimationFrame(runAgvAnimationLoop)
}

function ensureAgvAnimationLoop() {
  if (agvAnimationFrameHandle || typeof window === 'undefined') return
  agvAnimationFrameHandle = window.requestAnimationFrame(runAgvAnimationLoop)
}

async function fetchAgvs() {
  const res = await fetch(`${API_BASE}/agv/list`)
  agvs.value = await res.json()
  agvAnimationNow.value = Date.now()
}

async function fetchTasks() {
  const res = await fetch(`${API_BASE}/task/list`)
  tasks.value = await res.json()
}

async function fetchFaultEvents() {
  const query = faultEventFilter.value === 'all' ? '' : `?status=${faultEventFilter.value}`
  const res = await fetch(`${API_BASE}/fault/list${query}`)
  if (!res.ok) {
    throw new Error(`Fault event request failed: ${res.status}`)
  }
  faultEvents.value = await res.json()
}

async function refreshCoreState() {
  await Promise.all([fetchAgvs(), fetchTasks(), fetchFaultEvents()])
  if (authCanAiRender.value && panelSections.value.ai) {
    const lastFetchedMs = comfyRenderLastFetchedAt.value ? Date.parse(comfyRenderLastFetchedAt.value) : 0
    if (!Number.isFinite(lastFetchedMs) || Date.now() - lastFetchedMs >= 5000) {
      void fetchComfyRenderJobs()
    }
  }
  if (authCanViewAudit.value && panelSections.value.operations) {
    const lastFetchedMs = operationAuditLastFetchedAt.value ? Date.parse(operationAuditLastFetchedAt.value) : 0
    if (!Number.isFinite(lastFetchedMs) || Date.now() - lastFetchedMs >= 3000) {
      requestOperationAuditRefresh()
    }
  }
  syncDisplayedPathsFromTasks()
}

function setFaultPanelStatus(message, type = 'info') {
  faultPanelStatus.value = message
  faultPanelStatusType.value = type
}

function resetFaultReportForm() {
  faultReportForm.value = {
    fault_type: 'path_blocked',
    severity: 'medium',
    message: ''
  }
}

async function refreshState() {
  if (polling) return
  polling = true
  try {
    await refreshCoreState()
    await tryManualBoundSchedule()
    if (dispatchMode.value === 'auto' && !hasActiveTask()) {
      clearAutoPaths()
    }
    await tryAutoSchedule()
  } finally {
    polling = false
  }
}

async function emergencyStopSelectedAgv() {
  if (!selectedBackendAgv.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'fault.write', buildCapabilityDeniedMessage('fault'))) return
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/agv/${selectedBackendAgv.value.id}/emergency-stop`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({ reported_by: 'ui' })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, faultLocale.value.emergencyStop)
    }
    setFaultPanelStatus(faultLocale.value.stopSuccess, 'success')
    await refreshCoreState()
  } catch (error) {
    console.error('Emergency stop error:', error)
    setFaultPanelStatus(error?.message || faultLocale.value.emergencyStop, 'error')
  } finally {
    agvActionLoadingId.value = null
  }
}

async function resumeSelectedAgv() {
  if (!selectedBackendAgv.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'fault.write', buildCapabilityDeniedMessage('fault'))) return
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/agv/${selectedBackendAgv.value.id}/resume`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, faultLocale.value.resume)
    }
    setFaultPanelStatus(faultLocale.value.resumeSuccess, 'success')
    await refreshCoreState()
    await scheduleAutoIfReady()
  } catch (error) {
    console.error('Resume AGV error:', error)
    setFaultPanelStatus(error?.message || faultLocale.value.resume, 'error')
  } finally {
    agvActionLoadingId.value = null
  }
}

async function moveSelectedAgvToMaintenance() {
  if (!selectedBackendAgv.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'fault.write', buildCapabilityDeniedMessage('fault'))) return
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/agv/${selectedBackendAgv.value.id}/to-maintenance`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, moveToMaintenanceText())
    }
    if (locale.value === 'ja') {
      setFaultPanelStatus(`AGV #${selectedBackendAgv.value.id} を整備リストへ移動しました。`, 'success')
    } else if (locale.value === 'zh') {
      setFaultPanelStatus(`AGV #${selectedBackendAgv.value.id} 已移入维护列表。`, 'success')
    } else {
      setFaultPanelStatus(`AGV #${selectedBackendAgv.value.id} moved to maintenance list.`, 'success')
    }
    cancelSelection()
    await refreshCoreState()
  } catch (error) {
    console.error('Move AGV to maintenance error:', error)
    setFaultPanelStatus(error?.message || moveToMaintenanceText(), 'error')
  } finally {
    agvActionLoadingId.value = null
  }
}

async function returnAgvToService(agvId) {
  if (!agvId) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'fault.write', buildCapabilityDeniedMessage('fault'))) return
  agvActionLoadingId.value = agvId
  try {
    const res = await fetch(`${API_BASE}/agv/${agvId}/return-to-service`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, returnToServiceText())
    }
    if (locale.value === 'ja') {
      setFaultPanelStatus(`AGV #${agvId} を再び待機に戻しました。`, 'success')
    } else if (locale.value === 'zh') {
      setFaultPanelStatus(`AGV #${agvId} 已恢复上岗。`, 'success')
    } else {
      setFaultPanelStatus(`AGV #${agvId} returned to service.`, 'success')
    }
    await refreshCoreState()
    await scheduleAutoIfReady()
  } catch (error) {
    console.error('Return AGV to service error:', error)
    setFaultPanelStatus(error?.message || returnToServiceText(), 'error')
  } finally {
    agvActionLoadingId.value = null
  }
}

async function submitFaultReport() {
  if (!selectedBackendAgv.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'fault.write', buildCapabilityDeniedMessage('fault'))) return
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/fault/report`, {
      method: 'POST',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        agv_id: selectedBackendAgv.value.id,
        fault_type: faultReportForm.value.fault_type,
        severity: faultReportForm.value.severity,
        message: faultReportForm.value.message || null,
        reported_by: 'ui'
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, faultLocale.value.reportFault)
    }
    showFaultReportForm.value = false
    resetFaultReportForm()
    setFaultPanelStatus(faultLocale.value.faultReported, 'success')
    await refreshCoreState()
  } catch (error) {
    console.error('Report fault error:', error)
    setFaultPanelStatus(error?.message || faultLocale.value.reportFault, 'error')
  } finally {
    agvActionLoadingId.value = null
  }
}

async function resolveFaultEventItem(eventItem) {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'fault.write', buildCapabilityDeniedMessage('fault'))) return
  resolvingFaultId.value = eventItem.id
  try {
    const res = await fetch(`${API_BASE}/fault/${eventItem.id}/resolve`, {
      method: 'POST',
      headers: buildAuthorizedHeaders()
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, faultLocale.value.resolve)
    }
    setFaultPanelStatus(faultLocale.value.faultResolved, 'success')
    await refreshCoreState()
    await scheduleAutoIfReady()
  } catch (error) {
    console.error('Resolve fault event error:', error)
    setFaultPanelStatus(error?.message || faultLocale.value.resolve, 'error')
  } finally {
    resolvingFaultId.value = null
  }
}

function onKeyDown(event) {
  const target = event.target
  const isTypingTarget =
    target instanceof HTMLElement &&
    (target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.tagName === 'SELECT' ||
      target.isContentEditable)
  if (isTypingTarget) return

  const normalizedKey = normalizeShortcutKeyValue(event.key)

  if (enterpriseShortcutPlannerDialogOpen.value && shortcutEditorCaptureActionKey.value) {
    if (!normalizedKey || ['Shift', 'Control', 'Alt', 'Meta'].includes(normalizedKey)) return
    event.preventDefault()
    applyCapturedShortcutKey(shortcutEditorCaptureActionKey.value, normalizedKey)
    return
  }

  if (enterpriseShortcutPlannerDialogOpen.value) return

  if (normalizedKey === 'H') {
    event.preventDefault()
    openGuideCenter()
    return
  }

  if (normalizedKey && normalizedKey === normalizeShortcutKeyValue(activeShortcutBindings.value.selection_cancel)) {
    event.preventDefault()
    cancelSelection()
    return
  }

  if (normalizedKey && normalizedKey === normalizeShortcutKeyValue(activeShortcutBindings.value.algorithm_toggle)) {
    event.preventDefault()
    toggleAlgorithmMode()
    return
  }

  if (normalizedKey && normalizedKey === normalizeShortcutKeyValue(activeShortcutBindings.value.context_cancel)) {
    event.preventDefault()
    clearPreview()
    cancelTaskChainMapPick(false)
    return
  }

  if (normalizedKey === 'P') {
    if (showEnterpriseWorkspaceBanner.value) {
      event.preventDefault()
      reopenEnterpriseWorkspacePopup()
    }
  }
}

function onMapContextMenu(event) {
  event.preventDefault()
  cancelSelection()
}

watch(dispatchMode, mode => {
  cancelSelection()
  clearPreview()
  if (mode !== 'auto') {
    cancelTaskChainMapPick(false)
  }
  if (mode === 'manual') {
    clearAutoPaths()
    clearAutoMarkers()
  }
  saveMapDisplaySettings()
})

watch(obstacleEditMode, enabled => {
  stopObstaclePaint()
  if (!enabled) return
  cancelSelection()
  clearPreview()
  cancelTaskChainMapPick(false)
})

watch(obstacleMutationLocked, locked => {
  if (locked) {
    if (obstacleEditMode.value) {
      obstacleEditMode.value = false
    }
    setObstacleLayoutStatus('error', obstacleMutationLockedText())
    return
  }
  if (obstacleLayoutDirty.value) {
    setObstacleLayoutStatus('info', settingsLocale.value.obstacleDirty)
    return
  }
  setObstacleLayoutStatus('success', settingsLocale.value.obstacleSaved)
})

watch(taskBuilderMode, mode => {
  if (shouldAutoRefreshFloatingCompare()) {
    requestFloatingCompareRefresh()
  } else {
    clearPathCompare()
  }
  if (mode !== 'chain') {
    cancelTaskChainMapPick(false)
  }
})

watch(taskChainMapPickStageCount, stageCount => {
  const requiredPoints = stageCount + 1
  if (taskChainMapPickPoints.value.length > requiredPoints) {
    taskChainMapPickPoints.value = taskChainMapPickPoints.value.slice(0, requiredPoints)
  }
  if (!taskChainMapPickActive.value) return
  startPoint.value = taskChainMapPickPoints.value[0] ?? null
  endPoint.value = taskChainMapPickPoints.value.at(-1) ?? null
})

watch(
  [taskForm, taskChainStages],
  () => {
    if (shouldAutoRefreshFloatingCompare()) {
      requestFloatingCompareRefresh()
      return
    }
    clearPathCompare()
  },
  { deep: true }
)

watch(
  blockedCells,
  () => {
    if (shouldAutoRefreshFloatingCompare()) {
      requestFloatingCompareRefresh()
      return
    }
    clearPathCompare()
  },
  { deep: true }
)

watch(
  [tasks, agvs],
  () => {
    syncMapSizeResizeState()
  },
  { deep: true }
)

watch(
  shortcutPreferenceScopeKey,
  scopeKey => {
    const nextBindings = loadShortcutBindingsForScope(scopeKey)
    activeShortcutBindings.value = { ...nextBindings }
    if (!enterpriseShortcutPlannerDialogOpen.value) {
      shortcutEditorDraft.value = { ...nextBindings }
      shortcutEditorCaptureActionKey.value = ''
      resetShortcutEditorDraftStatus('', 'info')
    }
  },
  { immediate: true }
)

function onWindowBeforeUnload(event) {
  if (!enterpriseShortcutPlannerDialogOpen.value || !shortcutEditorHasUnsavedChanges.value || !shortcutEditorCanEdit.value) return
  event.preventDefault()
  event.returnValue = ''
}

onMounted(() => {
  loadCustomPoints()
  loadTaskTemplates()
  loadComfyWorkflowTemplates()
  void hydratePointTemplateBackend()
  loadExperimentRecords()
  loadMapDisplaySettings()
  loadPanelSections()
  void fetchUiSettings()
  void fetchAuthMe().then(state => {
    authGuestAccepted.value = Boolean(state?.authenticated)
    if (state?.authenticated && Array.isArray(state?.capabilities) && state.capabilities.includes('audit.view')) {
      void fetchOperationAudits({ force: true })
    }
  })
  loadPanelSummaryMode()
  loadTaskQueueView()
  syncPanelWidth()
  compareFloatingX.value = Math.max((windowWidth.value || 1280) - 440, 520)
  updateMapViewportMetrics(true)
  if (typeof ResizeObserver !== 'undefined') {
    mapResizeObserver = new ResizeObserver(() => {
      updateMapViewportMetrics()
    })
    if (mapViewportRef.value) {
      mapResizeObserver.observe(mapViewportRef.value)
    }
  }
  syncMapSizeResizeState()
  void fetchMapProfiles()
  void fetchMapPresets()
  void fetchMapLayout()
  void refreshState()
  timer = setInterval(() => {
    void refreshState()
  }, 1000)
  authGovernanceSyncTimer = setInterval(() => {
    void syncAuthGovernanceState()
  }, 45000)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('beforeunload', onWindowBeforeUnload)
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('mousemove', onGlobalMouseMove)
  window.addEventListener('mouseup', onGlobalMouseUp)
  showGuideCenter.value = showGuideCenterOnLoad.value
})

watch(
  [uiTreatAsEnterpriseRole, isPlatformAdminGovernanceMode, dashboardUnlocked],
  ([isEnterpriseSurface, isGovernanceMode, unlocked]) => {
    if (isEnterpriseSurface && unlocked && !isGovernanceMode) {
      ensureEnterpriseAgvMotionPolling()
      return
    }
    stopEnterpriseAgvMotionPolling()
  },
  { immediate: true }
)

watch(
  enterpriseAgvMotionActive,
  active => {
    if (active) {
      ensureAgvAnimationLoop()
      return
    }
    stopAgvAnimationLoop()
    agvAnimationNow.value = Date.now()
  },
  { immediate: true }
)

watch(
  customPoints,
  () => {
    saveCustomPoints()
  },
  { deep: true }
)

watch(
  customTaskTemplates,
  () => {
    saveTaskTemplates()
  },
  { deep: true }
)

watch(
  experimentRecords,
  () => {
    saveExperimentRecords()
  },
  { deep: true }
)

watch(
  panelSections,
  () => {
    savePanelSections()
    if (authCanAiRender.value && panelSections.value.ai) {
      void fetchComfyCheckpoints()
      void fetchComfyRenderJobs({ force: true })
      void fetchComfySharedTemplates({ force: true })
    }
    if (authCanViewAudit.value && panelSections.value.operations) {
      requestOperationAuditRefresh({ force: true })
    }
  },
  { deep: true }
)

watch([authAuthenticated, authCanAiRender], ([authenticated, canRender]) => {
  if (!authenticated || !canRender) {
    comfyRenderJobs.value = []
    comfyRenderLastFetchedAt.value = ''
    comfyRenderAvailableCheckpoints.value = []
    comfyRenderCheckpointName.value = ''
    comfyRenderSharedTemplates.value = []
    comfyRenderSelectedSharedTemplateId.value = ''
    return
  }
  void fetchComfyCheckpoints({ force: true })
  void fetchComfyRenderJobs({ force: true })
  void fetchComfySharedTemplates({ force: true })
})

watch(authCurrentRole, authRole => {
  if (authRole === 'platform_admin') {
    platformAdminSurfaceMode.value = 'governance'
  } else {
    platformAdminEnterprisePreviewRole.value = 'enterprise_admin'
  }
})

watch([enterpriseUiRole, canUseEnterpriseUi], ([role, isEnterprise]) => {
  if (!isEnterprise && !isPlatformAdminEnterprisePreviewMode.value) {
    enterpriseSettingsDialogOpen.value = false
    enterpriseSettingsActiveTab.value = 'overview'
    return
  }
  if (!enterpriseSettingsTabKeys.value.includes(enterpriseSettingsActiveTab.value)) {
    enterpriseSettingsActiveTab.value = loadEnterpriseSettingsTabPreference(role) || preferredEnterpriseSettingsTab(role)
  }
})

watch([enterpriseSettingsActiveTab, enterpriseUiRole, canUseEnterpriseUi], ([tab, role, isEnterprise]) => {
  if (!isEnterprise) return
  saveEnterpriseSettingsTabPreference(role, tab)
})

watch([authAuthenticated, authCanViewAudit], ([authenticated, canViewAudit]) => {
  if (!authenticated || !canViewAudit) {
    operationAudits.value = []
    operationAuditLastFetchedAt.value = ''
    return
  }
  requestOperationAuditRefresh({ force: true })
})

watch([authAuthenticated, authCanEnterpriseApprove], ([authenticated, canApprove]) => {
  if (authenticated && canApprove) {
    fetchEnterpriseApplications({ forceSelectFirst: false })
    return
  }
  enterpriseApprovalDialogOpen.value = false
  enterpriseApplications.value = []
  enterpriseApprovalSummary.value = { all: 0, pending: 0, approved: 0, rejected: 0 }
  selectedEnterpriseApplicationId.value = null
  enterpriseApprovalReviewNote.value = ''
})

watch([authAuthenticated, authCanSystemManage], ([authenticated, canManage]) => {
  if (authenticated && canManage) {
    fetchManagedUserAccounts({ forceSelectFirst: false })
    return
  }
  accountGovernanceDialogOpen.value = false
  managedUserAccounts.value = []
  selectedManagedUserId.value = ''
  accountGovernanceLastFetchedAt.value = ''
  accountGovernanceSummary.value = {
    all: 0,
    personal: 0,
    enterprise: 0,
    platform_admin: 0,
    approved: 0,
    pending: 0,
    rejected: 0,
    suspended: 0,
    deactivated: 0
  }
})

watch([authAuthenticated, authCanEnterpriseRequestSubmit], ([authenticated, canSubmit]) => {
  if (authenticated && canSubmit) return
  enterpriseRequestDialogOpen.value = false
  enterpriseRequestItems.value = []
  enterpriseRequestRecipients.value = []
  selectedEnterpriseRequestId.value = ''
  enterpriseRequestSummary.value = { all: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 }
  enterpriseRequestLastFetchedAt.value = ''
  resetEnterpriseRequestDraft()
})

watch([authAuthenticated, authCanPlatformBugSubmit, authCanPlatformBugManage], ([authenticated, canSubmit, canManage]) => {
  if (authenticated && (canSubmit || canManage)) {
    if (canManage) {
      fetchPlatformBugFeedback({ forceSelectFirst: false })
    }
    return
  }
  platformBugFeedbackDialogOpen.value = false
  platformBugFeedbackItems.value = []
  selectedPlatformBugFeedbackId.value = ''
  platformBugFeedbackSummary.value = { all: 0, open: 0, in_progress: 0, resolved: 0, closed: 0 }
  platformBugFeedbackLastFetchedAt.value = ''
  platformBugFeedbackManagementMode.value = false
})

watch([isPlatformAdminGovernanceMode, authCanPlatformBugManage], ([isGovernance, canManage]) => {
  if (!isGovernance || !canManage) return
  fetchPlatformBugFeedback({ forceSelectFirst: false })
})

watch(enterpriseApprovalStatusFilter, () => {
  if (!enterpriseApprovalDialogOpen.value || !authCanEnterpriseApprove.value) return
  fetchEnterpriseApplications({ forceSelectFirst: true })
})

watch([accountGovernanceRoleFilter, accountGovernanceStatusFilter], () => {
  if (!accountGovernanceDialogOpen.value || !authCanSystemManage.value) return
  fetchManagedUserAccounts({ forceSelectFirst: true })
})

watch(accountGovernanceSearch, () => {
  if (!accountGovernanceDialogOpen.value || !authCanSystemManage.value) return
  if (accountGovernanceSearchTimer) clearTimeout(accountGovernanceSearchTimer)
  accountGovernanceSearchTimer = setTimeout(() => {
    fetchManagedUserAccounts({ forceSelectFirst: true })
  }, 220)
})

watch([enterpriseRequestStatusFilter, enterpriseRequestCategoryFilter], () => {
  if (!enterpriseRequestDialogOpen.value || !authCanEnterpriseRequestSubmit.value) return
  fetchEnterpriseRequests({ forceSelectFirst: true })
})

watch(enterpriseRequestSearch, () => {
  if (!enterpriseRequestDialogOpen.value || !authCanEnterpriseRequestSubmit.value) return
  fetchEnterpriseRequests({ forceSelectFirst: true })
})

watch([platformBugFeedbackStatusFilter, platformBugFeedbackCategoryFilter], () => {
  if (!platformBugFeedbackDialogOpen.value || (!authCanPlatformBugSubmit.value && !authCanPlatformBugManage.value)) return
  fetchPlatformBugFeedback({ forceSelectFirst: true })
})

watch(platformBugFeedbackSearch, () => {
  if (!platformBugFeedbackDialogOpen.value || (!authCanPlatformBugSubmit.value && !authCanPlatformBugManage.value)) return
  fetchPlatformBugFeedback({ forceSelectFirst: true })
})

watch([managedUserAccounts, accountGovernanceDialogOpen], () => {
  if (!accountGovernanceDialogOpen.value) return
  selectedManagedUserIds.value = selectedManagedUserIds.value.filter(id =>
    managedUserAccounts.value.some(item => String(item.id || '') === String(id || ''))
  )
  if (!managedUserAccounts.value.some(item => String(item.id || '') === String(selectedManagedUserId.value || ''))) {
    selectedManagedUserId.value = String(managedUserAccounts.value[0]?.id || '')
  }
})

watch(selectedManagedUserId, () => {
  resetAccountGovernanceActionDraft()
})

watch([enterpriseRequestItems, enterpriseRequestDialogOpen], () => {
  if (!enterpriseRequestDialogOpen.value) return
  if (!enterpriseRequestItems.value.some(item => String(item.id || '') === String(selectedEnterpriseRequestId.value || ''))) {
    selectedEnterpriseRequestId.value = String(enterpriseRequestItems.value[0]?.id || '')
  }
})

watch(selectedEnterpriseRequestId, () => {
  enterpriseRequestResponseNote.value = String(selectedEnterpriseRequest.value?.response_note || '')
})

watch([platformBugFeedbackItems, platformBugFeedbackDialogOpen], () => {
  if (!platformBugFeedbackDialogOpen.value) return
  if (!platformBugFeedbackItems.value.some(item => String(item.id || '') === String(selectedPlatformBugFeedbackId.value || ''))) {
    selectedPlatformBugFeedbackId.value = String(platformBugFeedbackItems.value[0]?.id || '')
  }
})

watch(selectedPlatformBugFeedbackId, () => {
  platformBugFeedbackResponseNote.value = String(selectedPlatformBugFeedback.value?.response_note || '')
})

watch([enterpriseApprovalSearch, filteredEnterpriseApplications], () => {
  if (!enterpriseApprovalDialogOpen.value) return
  if (!filteredEnterpriseApplications.value.some(item => Number(item.id) === Number(selectedEnterpriseApplicationId.value))) {
    selectedEnterpriseApplicationId.value = filteredEnterpriseApplications.value[0]?.id ?? null
  }
})

watch(
  [enterpriseApprovalStatusFilter, enterpriseApprovalSearch, enterpriseApprovalDraftOnly, selectedEnterpriseApplicationId, enterpriseApprovalNoteDrafts],
  () => {
    saveEnterpriseApprovalUiState()
  },
  { deep: true }
)

watch(selectedEnterpriseApplicationId, nextId => {
  const normalizedId = Number(nextId || 0)
  if (!normalizedId) {
    enterpriseApprovalReviewNote.value = ''
    return
  }
  const savedDraft = enterpriseApprovalNoteDrafts.value[String(normalizedId)]
  enterpriseApprovalReviewNote.value = String(savedDraft?.text || '')
})

watch(enterpriseApprovalReviewNote, nextValue => {
  const applicationId = Number(selectedEnterpriseApplicationId.value || 0)
  if (!applicationId) return
  const normalizedKey = String(applicationId)
  const trimmed = String(nextValue || '').trim()
  const nextDrafts = { ...enterpriseApprovalNoteDrafts.value }
  if (!trimmed) {
    delete nextDrafts[normalizedKey]
    enterpriseApprovalNoteDrafts.value = nextDrafts
    return
  }
  nextDrafts[normalizedKey] = {
    text: String(nextValue || ''),
    updated_at: new Date().toISOString()
  }
  enterpriseApprovalNoteDrafts.value = nextDrafts
})

watch(panelSummaryMode, () => {
  summaryZoomArmed.value = false
  savePanelSummaryMode()
})

watch(compareDisplayMode, mode => {
  if (mode === 'panel') {
    stopFloatingCompareRefresh()
    showFloatingCompare.value = false
  } else {
    comparePanelExpanded.value = false
  }
})

watch(showFloatingCompare, visible => {
  if (visible) {
    requestFloatingCompareRefresh()
    return
  }
  stopFloatingCompareRefresh()
})

watch([showAutoPath, showMarkerIcons, showPathArrows, showStatusLegend, statusLegendLayout, statusLegendOpacity, showMinimap, showGuideCenterOnLoad, compareDisplayMode, compareFloatingOpacity], () => {
  saveMapDisplaySettings()
})

watch([currentGridCols, currentGridRows], async ([nextCols, nextRows], [prevCols, prevRows]) => {
  const changed = Number(nextCols) !== Number(prevCols) || Number(nextRows) !== Number(prevRows)
  if (changed) {
    const adjusted = sanitizeDraftStateForCurrentGrid()
    if (adjusted) {
      showFloatingToast(settingsLocale.value.resizeDraftAdjusted, 'info')
    }
  }
  await nextTick()
  updateMapViewportMetrics(true)
})

watch(
  [queueGroupsCollapsed, taskCardCollapsed],
  () => {
    saveTaskQueueView()
  },
  { deep: true }
)

watch(faultEventFilter, () => {
  void fetchFaultEvents()
})

watch(selectedBackendAgv, agv => {
  if (dispatchMode.value === 'manual' && agv && isSchedulableIdleAgvStatus(agv.status) && !trackedManualTaskId.value) {
    syncManualDispatchBuilderState()
    return
  }
  if (agv) return
  showFaultReportForm.value = false
  resetFaultReportForm()
})

watch(
  [dispatchMode, selectedAgvId, taskBuilderMode],
  () => {
    if (dispatchMode.value !== 'manual') return
    syncManualDispatchBuilderState()
  }
)

watch(
  [tasks, agvs, trackedManualTaskId, selectedBackendAgv, dispatchMode, manualDispatchStep],
  () => {
    if (dispatchMode.value !== 'manual') return
    if (!trackedManualTaskId.value) {
      if (manualDispatchStep.value !== 'idle') {
        return
      }
      if (isSchedulableIdleAgvStatus(selectedBackendAgv.value?.status) && !taskChainMapPickActive.value) {
        clearManualDispatchPreview()
      }
      return
    }
    if (!selectedBackendAgv.value) {
      // Keep preview on transient poll mismatch; only clear when user has really deselected AGV.
      if (!selectedAgvId.value) {
        clearManualDispatchPreview()
      }
      return
    }

    const trackedTask = tasks.value.find(task => task.id === trackedManualTaskId.value)
    if (!trackedTask) {
      return
    }

    if (['finished', 'blocked', 'failed'].includes(trackedTask.status)) {
      if (trackedTask.status === 'blocked' && isRecoveryRequiredTask(trackedTask)) {
        // Keep AGV selected after emergency stop so operator context does not vanish.
        trackedManualTaskId.value = null
        manualDispatchStep.value = 'idle'
        clearManualDestination()
        return
      }
      const remainingMs = manualPreviewMinVisibleUntil.value - Date.now()
      if (remainingMs > 0) {
        if (manualPreviewHoldTimer) {
          clearTimeout(manualPreviewHoldTimer)
        }
        manualPreviewHoldTimer = setTimeout(() => {
          manualPreviewHoldTimer = null
          cancelSelection()
        }, remainingMs + 20)
        return
      }
      cancelSelection()
      return
    }

    if (trackedTask.agv_id !== selectedBackendAgv.value.id) {
      // Avoid auto-cancel flicker during polling. Only clear tracked preview if user switched to another idle AGV.
      if (isSchedulableIdleAgvStatus(selectedBackendAgv.value.status)) {
        trackedManualTaskId.value = null
        manualDispatchStep.value = 'idle'
        clearManualDestination()
        return
      }
      return
    }

    if (
      !['assigned', 'running'].includes(trackedTask.status) &&
      isSchedulableIdleAgvStatus(selectedBackendAgv.value.status)
    ) {
      cancelSelection()
    }
  },
  { deep: true }
)

watch(
  tasks,
  () => {
    pruneTaskCardCollapsedState()
  },
  { deep: true }
)

watch(
  [algorithm, blockedCells, tasks, previewTaskId],
  () => {
    if (!previewTaskId.value) return
    const previewTask = tasks.value.find(task => task.id === previewTaskId.value)
    if (!previewTask || !canPreviewTask(previewTask)) {
      clearPreview()
      return
    }
    refreshTaskPreview(previewTask)
  },
  { deep: true }
)




const authDialogBindings = {
  t,
  showAuthGate,
  dashboardUnlocked,
  authPanelOpen,
  authModalTitle,
  authPanelModeText,
  authRoleBadgeClass,
  authAuthenticated,
  authCurrentDisplayName,
  authModeText,
  authEntryHintText,
  authCurrentUser,
  authAccountStatusLabel,
  authCurrentOrganizationName,
  authCurrentEnterpriseApplication,
  authIsEnterpriseRole,
  showEnterpriseWorkspaceBanner,
  authEnterpriseStatusFollowup,
  authEnterpriseStatusFollowupVisible,
  authEnterpriseStatusFollowupTitle,
  authEnterpriseStatusFollowupHint,
  authEnterpriseStatusFollowupNextStepText,
  authEnterpriseStatusFollowupUpdatedText,
  authEnterpriseStatusFollowupProgressItems,
  authEnterpriseApplicationProgressItems,
  enterpriseApplicationNextStepText,
  authAccountStatusLastCheckedText,
  authEnterpriseQuickActionItems,
  authEnterpriseQuickActionHint,
  enterpriseRoleFocus,
  enterpriseRoleScopeText,
  enterpriseWorkspaceSectionLabels,
  enterpriseRoleWorkspaceActionItems,
  authStatusNotice,
  authLoginRestrictionNotice,
  authPersonalRegisterValidation,
  authPersonalRegisterStatusText,
  authEnterpriseRegisterValidation,
  authEnterpriseRegisterStatusText,
  authEnterpriseRegisterDraftHasContent,
  authEnterpriseRegisterDraftUpdatedText,
  authEnterpriseRegisterDraftDiffText,
  authEnterpriseRegisterExistingHint,
  authEnterpriseRegisterExistingPrimaryActionLabel,
  authEnterpriseRegisterSnapshotActionItems,
  authEnterpriseRegisterFollowupProgressItems,
  authEnterpriseRegisterFollowupUpdatedText,
  authEnterpriseRegisterFollowup,
  authLoading,
  authCapabilityCards,
  authPrimaryAccounts,
  authDialogView,
  authUsername,
  authPassword,
  authDemoAccounts,
  authPersonalRegisterForm,
  authEnterpriseRegisterForm,
  authEnterpriseRegisterLoading,
  buildAuthCapabilityStateText,
  authCanEnterpriseApprove,
  recentPendingEnterpriseApplications,
  recentReviewedEnterpriseApplications,
  recentEnterpriseApprovalDraftApplications,
  enterpriseApprovalReviewFollowup,
  enterpriseApprovalReviewFollowupVisible,
  enterpriseApprovalReviewFollowupMetaText,
  enterpriseApprovalReviewFollowupUpdatedText,
  enterpriseApprovalReviewFollowupProgressItems,
  enterpriseApprovalReviewFollowupNextStepText,
  enterpriseApprovalDraftCount,
  enterpriseApprovalDraftSummaryText,
  enterpriseApprovalLastFetchedText,
  enterGuestMode,
  handleAuthLogout,
  handleAuthQuickLogin,
  switchAuthDialogView,
  handleAuthLogin,
  handlePersonalRegister,
  authDemoAccountLabel,
  handleAuthDemoFill,
  handleEnterpriseRegister,
  signInEnterpriseRegisterFollowup,
  continueEnterpriseRegisterFollowupEditing,
  dismissEnterpriseRegisterFollowup,
  clearEnterpriseRegisterDraft,
  useCurrentEnterpriseApplicationForRegisterDraft,
  runAuthEnterpriseRegisterExistingPrimaryAction,
  refreshEnterpriseAccountStatus,
  refreshEnterpriseApprovalSnapshot,
  resumeEnterpriseRegistrationFromApplication,
  copyEnterpriseApplicationCompanyName,
  copyEnterpriseApplicationContactName,
  copyEnterpriseApplicationSummary,
  copyEnterpriseApplicationReviewNote,
  copyEnterpriseApplicationUsername,
  copyEnterpriseApplicationContactEmail,
  formatInlineMessage,
  openEnterpriseApprovalDialog,
  openEnterpriseApprovalDraftWorkspace,
  openEnterpriseSettingsDialog,
  openEnterpriseApprovalDialogForItem,
  applyCurrentEnterpriseWorkspacePreset,
  applyEnterpriseWorkspaceFromAuth,
  runAuthEnterpriseQuickAction,
  runAuthEnterpriseRegisterExistingAction,
  runEnterpriseStatusFollowupAction,
  runEnterpriseApprovalFollowupAction,
  runEnterpriseWorkspaceAction,
  runAuthStatusNoticeAction
}

const operationsAuditPanelBindings = {
  t,
  authCanViewAudit,
  operationAuditResourceFilter,
  operationAuditActionFilter,
  operationAuditResourceOptions,
  operationAuditActionOptions,
  operationAuditLastFetchedAt,
  operationAuditLoading,
  deletingOperationAuditId,
  operationAuditBulkDeleting,
  operationAudits,
  filteredOperationAudits,
  matchedOperationAuditIds,
  isOperationAuditSelected,
  toggleOperationAuditSelection,
  clearSelectedOperationAudits,
  areAllVisibleOperationAuditsSelected,
  selectedVisibleOperationAuditCount,
  toggleSelectVisibleOperationAudits,
  buildOperationsHintText,
  formatInlineMessage,
  fetchOperationAudits,
  resetOperationAuditFilters,
  exportFilteredOperationAuditsJsonWithAuth,
  exportFilteredOperationAuditsCsvWithAuth,
  deleteSelectedOperationAuditsWithAuth,
  deleteOperationAuditWithAuth,
  formatOperationAuditTitle,
  formatOperationAuditResourceRef,
  operationActionLabel,
  formatOperationAuditOperator,
  formatOperationAuditMetadata,
  openAuthDialog,
  buildOperationsEntryActionText
}

const algorithmCompareWorkspaceBindings = {
  currentCompareHint,
  pathCompareError,
  pathCompareResult,
  compareResultEntries,
  algorithm,
  recommendedCompareAlgorithm,
  algorithmText,
  compareResultBadgeText,
  applyComparedAlgorithm,
  formatCompareResultStatus,
  algorithmCompareLocale,
  formatCompareStageLengths,
  authCanExperimentWrite,
  buildCapabilityLockedTitle,
  saveCurrentExperimentRecordWithAuth,
  exportCurrentCompareResultJsonWithAuth,
  exportCurrentCompareResultCsvWithAuth,
  experimentLocale
}

const experimentRecordsPanelBindings = {
  t,
  experimentLocale,
  authCanExperimentWrite,
  experimentRecordCount,
  experimentStatus,
  experimentStatusType,
  experimentRecords,
  matchedExperimentRecordIds,
  taskChainLocale,
  taskBuilderLocale,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  buildCapabilityLockedTitle,
  saveCurrentExperimentRecordWithAuth,
  exportCurrentCompareResultJsonWithAuth,
  exportCurrentCompareResultCsvWithAuth,
  exportAllExperimentRecordsJsonWithAuth,
  exportAllExperimentRecordsCsvWithAuth,
  clearExperimentRecordsWithAuth,
  formatExperimentCardTitle,
  algorithmText,
  formatExperimentAlgorithms,
  formatExperimentSavedAt,
  exportExperimentRecord,
  deleteExperimentRecordWithAuth
}

const taskTemplatesPanelBindings = {
  t,
  authCanTemplateWrite,
  authCanDispatchWrite,
  taskTemplateForm,
  taskTemplateStatus,
  taskTemplateStatusType,
  taskChainLocale,
  templateJsonText,
  templateJsonStatus,
  templateJsonStatusType,
  templateJsonLocale,
  taskTemplates,
  matchedTemplateIds,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  buildCapabilityLockedTitle,
  saveCurrentTaskTemplateWithAuth,
  saveCurrentTaskChainTemplateWithAuth,
  handleTemplateFileChange,
  importTaskTemplatesFromJsonWithAuth,
  exportTaskTemplatesToJsonWithAuth,
  downloadTemplateJsonFileWithAuth,
  clearTemplateJsonTextWithAuth,
  taskTemplateName,
  taskTemplateTypeText,
  formatTemplateMeta,
  formatTemplateStageCount,
  onTemplateApplyClick,
  onTemplateApplyDoubleClick,
  createTaskFromTemplateWithAuth,
  deleteTaskTemplateWithAuth
}

const pointLibraryPanelBindings = {
  t,
  authCanPointWrite,
  customPointForm,
  currentGridCols,
  currentGridRows,
  pointFormStatus,
  pointFormStatusType,
  pointSearch,
  filteredPoints,
  matchedPointIds,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  buildCapabilityLockedTitle,
  addCustomPointWithAuth,
  pointName,
  pointZone,
  pointTypeText,
  applyPointToTaskForm,
  deleteCustomPointWithAuth
}

const jsonToolsPanelBindings = {
  t,
  authCanJsonWrite,
  taskJsonLocale,
  taskJsonExampleFileLocale,
  jsonText,
  jsonStatus,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  fillTaskJsonExample,
  downloadTaskJsonExample,
  buildCapabilityLockedTitle,
  importTasksFromJson,
  importTasksFromJsonFile,
  exportTasksToJsonWithAuth,
  clearJsonTextWithAuth
}

const taskQueuePanelBindings = {
  t,
  authCanDispatchWrite,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  taskQueueViewFilter,
  orphanedTaskCount,
  deleteOrphanedTasks,
  tasks,
  taskGroups,
  toggleQueueGroup,
  panelLocale,
  isQueueGroupCollapsed,
  countRetryableBlockedTasks,
  buildCapabilityLockedTitle,
  retryAllBlockedTasksWithAStar,
  areGroupTaskCardsCollapsed,
  setQueueGroupTaskCardsCollapsed,
  areGroupTaskCardsExpanded,
  queueViewLocale,
  exportFinishedTasksToJson,
  deleteFinishedTasks,
  previewTaskId,
  isTaskCardFolded,
  matchedTaskIds,
  onTaskHover,
  onTaskLeave,
  toggleTaskCard,
  taskStatusText,
  formatTaskCompactSummary,
  formatTaskMeta,
  formatTaskStageProgress,
  formatTaskCurrentStage,
  formatTaskAlgorithm,
  formatTaskInitialPoint,
  formatTaskAgv,
  formatTaskCreatedBy,
  isTaskOrphaned,
  formatTaskPathStats,
  isTaskReasonAlert,
  formatDispatchReason,
  taskLastActionLabel,
  formatTaskLastAction,
  formatTaskLastOperator,
  formatTaskTime,
  isTaskDeletable,
  deleteTask,
  isRecoveryRequiredTask,
  isCellOccupiedTimeoutTask,
  isTaskRecoveryBusy,
  retryBlockedTaskFromCurrent,
  retryFromCurrentButtonText,
  retryBlockedTaskWithAStar,
  recoverBlockedTask,
  recoveryActionText
}

const faultOperationsPanelBindings = {
  faultLocale,
  faultEventFilter,
  authCanFaultWrite,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  selectedBackendAgv,
  faultSelectedAgvCardRef,
  faultSelectedAgvPulse,
  agvActionLoadingId,
  statusText,
  cancelSelection,
  selectedAgvTask,
  buildCapabilityLockedTitle,
  emergencyStopSelectedAgv,
  resumeSelectedAgv,
  showFaultReportForm,
  moveSelectedAgvToMaintenance,
  moveToMaintenanceText,
  faultReportForm,
  faultTypeText,
  faultSeverityText,
  submitFaultReport,
  maintenanceBackendAgvs,
  maintenanceListTitleText,
  returnAgvToService,
  returnToServiceText,
  faultPanelStatus,
  faultPanelStatusType,
  filteredFaultEvents,
  faultEventStatusText,
  faultEventTypeText,
  formatFaultReportedBy,
  formatFaultResolvedBy,
  resolvingFaultId,
  resolveFaultEventItem
}

const taskBuilderPanelBindings = {
  t,
  taskBuilderRootRef: taskBuilderRef,
  taskBuilderTitleText,
  toggleTaskBuilderMode,
  taskBuilderLocale,
  currentTaskBuilderModeCompactLabel,
  currentTaskBuilderHint,
  authCanDispatchWrite,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  manualDispatchOriginText,
  taskBuilderMode,
  taskChainLocale,
  taskForm,
  currentGridCols,
  currentGridRows,
  singleTaskStartLabelX,
  singleTaskStartLabelY,
  singleTaskEndLabelX,
  singleTaskEndLabelY,
  manualDispatchReady,
  buildCapabilityLockedTitle,
  addTaskFromForm,
  singleTaskSubmitText,
  algorithm,
  dispatchMode,
  taskChainMapPickActive,
  toggleTaskChainMapPick,
  taskChainMapPickButtonText,
  taskChainMapPickUiLocale,
  taskChainMapPickStageCount,
  setTaskChainMapPickStageCount,
  taskChainMapPickStageCountInput,
  taskChainMapPickStatusText,
  taskChainStages,
  removeTaskChainStage,
  addTaskChainStage,
  resetTaskChainStages,
  addTaskChainFromForm,
  chainTaskSubmitText
}

const dispatchControlSummaryPanelBindings = {
  t,
  panelLocale,
  currentDispatchModeLabel,
  toggleDispatchModeFromSummary,
  toggleAlgorithmMode,
  algorithmText,
  algorithm,
  algorithmHintText,
  compareDisplayMode,
  comparePanelRootRef: comparePanelRef,
  algorithmCompareLocale,
  taskBuilderMode,
  taskChainLocale,
  currentTaskBuilderModeCompactLabel,
  toggleComparePanelExpanded,
  comparePanelExpanded,
  pathCompareLoading,
  compareCurrentRoute,
  pathCompareResult,
  pathCompareError,
  clearPathCompare,
  algorithmCompareWorkspaceBindings
}

const floatingComparePanelBindings = {
  compareDisplayMode,
  showFloatingCompare,
  compareFloatingStyle,
  algorithmCompareLocale,
  taskBuilderMode,
  taskChainLocale,
  currentTaskBuilderModeCompactLabel,
  closeFloatingCompare,
  startFloatingCompareDrag,
  pathCompareLoading,
  compareCurrentRoute,
  algorithmCompareWorkspaceBindings
}

const mapSettingsPanelBindings = {
  showMapSettings,
  mapSettingsPanelRootRef: mapSettingsPanelRef,
  settingsLocale,
  guideCenterLocale,
  openGuideCenter,
  showAutoPath,
  showMarkerIcons,
  showPathArrows,
  showMinimap,
  showGuideCenterOnLoad,
  authCanMapWrite,
  buildCapabilityReadonlyHint,
  buildEnterprisePanelReadonlyHint,
  openAuthDialog,
  buildOperationsEntryActionText,
  obstacleEditMode,
  obstacleMutationLocked,
  buildCapabilityLockedTitle,
  toggleObstacleEditModeWithAuth,
  obstacleMutationLockedText,
  selectedObstaclePreset,
  obstaclePresets,
  obstaclePresetName,
  selectedObstaclePresetInfo,
  obstaclePresetDescription,
  obstacleLayoutDirty,
  obstacleLayoutStatus,
  obstacleLayoutStatusType,
  obstacleMapSaving,
  applyObstaclePreset,
  saveCurrentObstaclePreset,
  selectedObstaclePresetDeletable,
  deleteSelectedObstaclePreset,
  saveBlockedCells,
  downloadObstacleLayout,
  triggerObstacleLayoutImportWithAuth,
  resetBlockedCellsToDefault,
  importedObstacleLayoutPendingPreset,
  saveImportedObstacleAsPreset,
  obstacleImportSaveAsPresetText,
  obstacleLayoutFileInputRef,
  onObstacleLayoutFileChange,
  mapSizeLabel,
  currentObstaclePresetLabel,
  blockedCellCount,
  uiSettingsBackendMode,
  currentMapProfileLabel,
  mapSizeResizeStatusLabel,
  currentMapProfileDescription,
  previewedMapProfile,
  localizedMapProfileField,
  mapProfileActionSummary,
  mapProfileActionSummaryTitle,
  focusMapResizeReasonKey,
  buildMapResizeReasonItem,
  exportMapProfileActionSummary,
  focusMapPreviewCell,
  mapProfileSaving,
  mapProfileImporting,
  saveCurrentMapProfile,
  triggerMapProfileImport,
  mapProfileFileInputRef,
  onMapProfileFileChange,
  mapProfiles,
  isCurrentMapProfile,
  formatMapProfileCreatedBy,
  formatMapProfileLastOperator,
  mapProfilePreviewStatusText,
  mapProfilePreviewStatus,
  mapProfilePreviewReasonItems,
  focusMapResizeReasonItem,
  canForceApplyMapProfile,
  mapProfileApplyingKey,
  mapProfileDeletingKey,
  mapProfileExportingKey,
  canApplyMapProfileWithCapability,
  buildMapProfileApplyTitle,
  applyMapProfile,
  isMapProfileApplying,
  isMapProfilePreviewing,
  previewMapProfile,
  exportMapProfile,
  isMapProfileExporting,
  isMapProfileDeleting,
  deleteMapProfile,
  mapResizePreviewColsInput,
  markMapResizePreviewDirty,
  normalizeMapResizePreviewInputs,
  mapResizePreviewRowsInput,
  mapResizePreviewLoading,
  runMapResizePrecheck,
  canApplyMapResize,
  applyMapResize,
  currentGridCols,
  currentGridRows,
  mapResizeRequestedSizeLabel,
  mapResizePreviewStatusLabel,
  mapResizePreview,
  mapResizePreviewReasonItems,
  mapResizeSectionDomId,
  mapResizeHighlightedSection,
  mapResizePreviewDetailSections,
  mapResizeHighlightedItemKeys,
  highlightMapResizeItems,
  compareDisplayMode,
  compareFloatingOpacity,
  showStatusLegend,
  statusLegendLayout,
  statusLegendOpacity,
  resetMapView
}

const guideCenterDialogBindings = {
  showGuideCenter,
  closeGuideCenter,
  guideCenterLocale,
  shortcutGuideEntries,
  panelLocale
}

const enterpriseApprovalDialogBindings = {
  t,
  formatInlineMessage,
  enterpriseApprovalSummary,
  enterpriseApprovalStatusFilter,
  enterpriseApprovalSearch,
  enterpriseApprovalDraftOnly,
  enterpriseApprovalLoading,
  filteredEnterpriseApplications,
  recentReviewedEnterpriseApplications,
  enterpriseApprovalFilterSummaryText,
  enterpriseApprovalDraftCount,
  enterpriseApprovalDraftSummaryText,
  enterpriseApprovalEmptyStateHint,
  enterpriseApprovalEmptyStateActions,
  enterpriseApprovalLastFetchedText,
  enterpriseApprovalReviewFollowup,
  enterpriseApprovalReviewFollowupVisible,
  enterpriseApprovalReviewFollowupMetaText,
  enterpriseApprovalReviewFollowupUpdatedText,
  enterpriseApprovalReviewFollowupProgressItems,
  enterpriseApprovalReviewFollowupNextStepText,
  selectedEnterpriseApplicationId,
  selectedEnterpriseApplication,
  selectedEnterpriseApplicationPositionText,
  selectedEnterpriseApplicationProgressItems,
  selectedEnterpriseApplicationNextStepText,
  selectedEnterpriseApplicationActionItems,
  enterpriseApprovalReviewNoteTemplates,
  enterpriseApprovalReviewNote,
  enterpriseApprovalReviewNoteLength,
  enterpriseApprovalReviewDraftUpdatedText,
  enterpriseApprovalCanReject,
  enterpriseApprovalReviewLoading,
  hasEnterpriseApprovalDraft,
  canSelectPreviousEnterpriseApplication,
  canSelectNextEnterpriseApplication,
  hasNextEnterpriseApprovalDraft,
  closeEnterpriseApprovalDialog,
  resetEnterpriseApprovalFilters,
  setEnterpriseApprovalStatusFilter,
  toggleEnterpriseApprovalDraftOnly,
  refreshEnterpriseApprovalSnapshot,
  exportEnterpriseApplicationsJson,
  exportEnterpriseApplicationsCsv,
  fetchEnterpriseApplications,
  runEnterpriseApprovalEmptyStateAction,
  selectPreviousEnterpriseApplication,
  selectNextEnterpriseApplication,
  selectNextEnterpriseApprovalDraft,
  applyEnterpriseApprovalReviewNoteTemplate,
  clearEnterpriseApprovalReviewNote,
  clearEnterpriseApprovalCurrentDraft,
  clearAllEnterpriseApprovalDrafts,
  copyEnterpriseApplicationUsername,
  copyEnterpriseApplicationContactEmail,
  runEnterpriseApprovalFollowupAction,
  runEnterpriseApprovalAction,
  openEnterpriseApprovalDialogForItem,
  reviewEnterpriseApplication
}

const platformAccountGovernanceDialogBindings = {
  t,
  formatInlineMessage,
  accountGovernanceSummary,
  accountGovernanceRoleFilter,
  accountGovernanceStatusFilter,
  accountGovernanceSearch,
  accountGovernanceLoading,
  accountGovernanceActionLoading,
  managedUserAccounts,
  selectedManagedUserId,
  selectedManagedUserIdSet,
  selectedManagedUser,
  accountGovernanceSelectedCount,
  accountGovernanceSelectionSummaryText,
  accountGovernanceBulkSuspendableUsers,
  accountGovernanceBulkUnsuspendableUsers,
  accountGovernanceBulkDeactivatableUsers,
  accountGovernanceFilterSummaryText,
  accountGovernanceEmptyHint,
  accountGovernanceLastFetchedText,
  accountGovernanceSelectedTemplateKey,
  accountGovernanceActionTemplateItems,
  accountGovernanceSuspendReason,
  accountGovernanceSuspendNote,
  accountGovernanceSuspendDurationPreset,
  applyAccountGovernanceActionTemplate,
  closeAccountGovernanceDialog,
  resetAccountGovernanceFilters,
  toggleManagedUserSelection,
  selectAllManagedUsers,
  clearSelectedManagedUsers,
  fetchManagedUserAccounts,
  exportManagedUserAccounts,
  suspendManagedUserAccount,
  unsuspendManagedUserAccount,
  deactivateManagedUserAccount,
  runManagedUserBulkAction
}

const enterpriseRequestDialogBindings = {
  t,
  formatInlineMessage,
  enterpriseRequestSummary,
  enterpriseRequestStatusFilter,
  enterpriseRequestCategoryFilter,
  enterpriseRequestSearch,
  enterpriseRequestLoading,
  enterpriseRequestActionLoading,
  enterpriseRequestItems,
  enterpriseRequestRecipients,
  selectedEnterpriseRequestId,
  selectedEnterpriseRequest,
  enterpriseRequestDraft,
  enterpriseRequestResponseNote,
  enterpriseRequestLastFetchedText,
  enterpriseRequestFilterSummaryText,
  enterpriseRequestEmptyHint,
  enterpriseRequestCanManageSelected,
  closeEnterpriseRequestDialog,
  fetchEnterpriseRequests,
  resetEnterpriseRequestFilters,
  submitEnterpriseRequest,
  updateSelectedEnterpriseRequestStatus
}

const platformBugFeedbackDialogBindings = {
  t,
  formatInlineMessage,
  platformBugFeedbackSummary,
  platformBugFeedbackStatusFilter,
  platformBugFeedbackCategoryFilter,
  platformBugFeedbackSearch,
  platformBugFeedbackLoading,
  platformBugFeedbackActionLoading,
  platformBugFeedbackItems,
  selectedPlatformBugFeedbackId,
  selectedPlatformBugFeedback,
  platformBugFeedbackDraft,
  platformBugFeedbackResponseNote,
  platformBugFeedbackLastFetchedText,
  platformBugFeedbackFilterSummaryText,
  platformBugFeedbackEmptyHint,
  platformBugFeedbackManagementMode,
  platformBugFeedbackCanManageSelected,
  closePlatformBugFeedbackDialog,
  fetchPlatformBugFeedback,
  resetPlatformBugFeedbackFilters,
  submitPlatformBugFeedback,
  updateSelectedPlatformBugFeedbackStatus
}

const platformAdminGovernanceHubBindings = {
  t,
  formatInlineMessage,
  enterpriseApprovalSummary,
  enterpriseApprovalLastFetchedText,
  accountGovernanceSummary,
  accountGovernanceLastFetchedText,
  platformBugFeedbackSummary,
  platformBugFeedbackLastFetchedText,
  operationAuditLastFetchedAt,
  platformRecentAuditEntries,
  formatOperationAuditTitle,
  formatOperationAuditOperator,
  formatOperationAuditResourceRef,
  formatOperationAuditMetadata,
  openEnterpriseApprovalDialog,
  openAccountGovernanceDialog,
  openPlatformBugFeedbackDialog,
  requestOperationAuditRefresh,
  enterPlatformAdminPersonalPreviewMode,
  enterPlatformAdminEnterprisePreviewMode
}

const enterpriseSettingsDialogBindings = {
  t,
  authRoleLabel: enterpriseUiRoleLabel,
  authAccountStatusLabel,
  authCurrentAccountStatus,
  authCurrentOrganizationName,
  authCurrentEnterpriseApplication,
  authCanDispatchWrite,
  authCanTemplateWrite,
  authCanPointWrite,
  authCanExperimentWrite,
  enterpriseSettingsTabDefinitions,
  enterpriseSettingsActiveTab,
  enterpriseSettingsTabLabel,
  enterpriseSettingsSidebarCollapsed,
  enterprisePageSettingsDialogOpen,
  enterpriseShortcutPlannerDialogOpen,
  enterpriseMapEditorDialogOpen,
  enterpriseMapEditorSaving,
  enterpriseTopologyEditorDialogOpen,
  enterpriseActiveTabModeLabel,
  enterpriseActiveTabAccessLabel,
  enterpriseActiveTabAccessHint,
  enterpriseActiveTabModeHint,
  enterpriseRoleFocus,
  enterpriseRoleScopeText,
  enterpriseWorkspaceSectionLabels,
  enterpriseRoleWorkspaceActionItems,
  enterpriseOverviewQuickTabs,
  enterpriseEnabledCapabilityCards,
  enterpriseReadonlyCapabilityCards,
  enterpriseOverviewCards,
  authAccountStatusLastCheckedText,
  authEnterpriseRegisterDraftHasContent,
  authEnterpriseRegisterDraftUpdatedText,
  authEnterpriseRegisterDraftDiffText,
  enterpriseApplicationNextStepText,
  authEnterpriseStatusFollowup,
  authEnterpriseStatusFollowupVisible,
  authEnterpriseStatusFollowupTitle,
  authEnterpriseStatusFollowupHint,
  authEnterpriseStatusFollowupNextStepText,
  authEnterpriseStatusFollowupUpdatedText,
  authEnterpriseStatusFollowupProgressItems,
  enterpriseApplicationActionItems,
  authEnterpriseApplicationProgressItems,
  copyEnterpriseApplicationCompanyName,
  copyEnterpriseApplicationContactName,
  copyEnterpriseApplicationSummary,
  copyEnterpriseApplicationReviewNote,
  copyEnterpriseApplicationUsername,
  copyEnterpriseApplicationContactEmail,
  useCurrentEnterpriseApplicationForRegisterDraft,
  resumeEnterpriseRegistrationFromApplication,
  currentMapProfileLabel,
  currentDispatchModeLabel,
  dispatchModeAutoLabel,
  dispatchModeManualLabel,
  compareDisplayTitleLabel,
  compareDisplayPanelLabel,
  compareDisplayFloatingLabel,
  guideCenterLocale,
  shortcutGuideEntries,
  shortcutEditorRows,
  shortcutEditorCanEdit,
  shortcutEditorCaptureActionKey,
  shortcutEditorStatus,
  shortcutEditorStatusType,
  shortcutEditorHasConflicts,
  shortcutEditorHasUnsavedChanges,
  openGuideCenter,
  showAutoPath,
  showMarkerIcons,
  showPathArrows,
  showMinimap,
  compareFloatingOpacity,
  resetMapView,
  enterpriseActiveTasks,
  enterpriseOpenFaults,
  enterpriseBusyAgvs,
  enterpriseRecentTasks,
  enterpriseRecentFaults,
  enterpriseRecentAuditEntries,
  enterprisePointTemplateActionScope,
  enterprisePointTemplateFocus,
  enterpriseMapWorkspaceCards,
  enterpriseMapWorkspaceMetaText,
  enterpriseRouteTopologyCards,
  enterpriseRouteTopologyMetaText,
  enterprisePointTemplateWorkspaceCards,
  enterpriseRuntimeWorkspaceCards,
  enterpriseAiWorkspaceCards,
  enterpriseAuditWorkspaceCards,
  enterpriseRecentCustomPoints,
  enterpriseRecentCustomTemplates,
  enterpriseRuntimeActionScope,
  enterpriseRuntimeFocus,
  enterpriseAiActionScope,
  mapSizeLabel,
  blockedCellCount,
  currentMapTopologySummary,
  enterpriseMapEditorRows,
  enterpriseMapEditorCols,
  enterpriseMapEditorDraftCols,
  enterpriseMapEditorDraftRows,
  enterpriseMapEditorValidCount,
  enterpriseMapEditorBlockedCount,
  enterpriseMapEditorIsIrregular,
  enterpriseMapEditorZoomPercent,
  enterpriseMapEditorFootprintLabel,
  enterpriseMapEditorSizeLabel,
  enterpriseMapEditorGridStyle,
  enterpriseTopologyEditorDraft,
  enterpriseTopologyDraftSummary,
  enterpriseTopologyNodesByCell,
  enterpriseTopologySelectedNode,
  enterpriseTopologySelectedEdge,
  enterpriseTopologyLinkSourceNode,
  enterpriseTopologyNodeTypeOptions,
  enterpriseTopologyEdgeDirectionOptions,
  enterpriseTopologyLaneTypeOptions,
  enterpriseTopologyGridStyle,
  enterpriseTopologyEdgeSvgStyle,
  enterpriseTopologySvgEdges,
  mapProfiles,
  mapProfileActionSummary,
  pointLibrary,
  customPoints,
  currentGridCols,
  currentGridRows,
  customPointForm,
  pointFormStatus,
  pointFormStatusType,
  addCustomPointWithAuth,
  applyPointToTaskForm,
  deleteCustomPointWithAuth,
  taskTemplates,
  customTaskTemplates,
  taskTemplateForm,
  taskTemplateStatus,
  taskTemplateStatusType,
  taskChainLocale,
  experimentLocale,
  algorithmCompareLocale,
  dispatchMode,
  saveCurrentTaskTemplateWithAuth,
  saveCurrentTaskChainTemplateWithAuth,
  createTaskFromTemplateWithAuth,
  deleteTaskTemplateWithAuth,
  onTemplateApplyClick,
  compareDisplayMode,
  algorithm,
  taskPriority,
  comfyRenderJobs,
  comfyRenderAvailableCheckpoints,
  comfyRenderBuiltinTemplateKey,
  comfyRenderSourceType,
  comfyRenderSourceRef,
  comfyRenderCheckpointName,
  comfyRenderWorkflowPreset,
  comfyRenderPromptStyle,
  comfyRenderTemplateName,
  comfyRenderSelectedTemplateId,
  comfyRenderPromptText,
  comfyRenderInputJsonText,
  comfyRenderWorkflowJsonText,
  comfyRenderSelectedSharedTemplateId,
  comfyRenderStatus,
  comfyRenderStatusType,
  comfyRenderBuiltinTemplates,
  comfyRenderSelectedBuiltinTemplate,
  comfyRenderSelectedBuiltinTemplateMatchesRecommendation,
  comfyRenderRecommendedBuiltinTemplate,
  comfyRenderRecommendedBuiltinReasonText,
  comfyRenderSourceOptions,
  comfyRenderWorkflowPresetOptions,
  comfyRenderPromptStyleOptions,
  comfyRenderSavedTemplates,
  comfyRenderHasCustomTemplates,
  comfyRenderSharedTemplates,
  comfyRenderSelectedSharedTemplate,
  comfyRenderHasSharedTemplates,
  comfyRenderSelectedSharedTemplateMetaText,
  comfyRenderWorkflowPresetSummary,
  comfyRenderPromptStyleSummary,
  comfyRenderRecommendedCheckpointSummary,
  comfyRenderLastFetchedText,
  comfyRenderSubmitting,
  comfyRenderLoading,
  comfyRenderSharedTemplateSaving,
  comfyRenderSharedTemplatesLoading,
  enterpriseRecentAiJobs,
  deletingComfyJobId,
  operationAudits,
  operationAuditLastFetchedAt,
  operationAuditResourceFilter,
  operationAuditActionFilter,
  operationAuditResourceOptions,
  operationAuditActionOptions,
  operationAuditResourceFilterLabel,
  operationAuditActionFilterLabel,
  operationAuditLoading,
  deletingOperationAuditId,
  operationAuditBulkDeleting,
  enterpriseFilteredAuditEntries,
  matchedOperationAuditIds,
  settingsLocale,
  authCanViewAudit,
  authCanAiRender,
  showGuideCenterOnLoad,
  authCanMapWrite,
  mapProfileApplyingKey,
  mapProfileDeletingKey,
  mapProfileExportingKey,
  mapProfileImporting,
  closeEnterpriseSettingsDialog,
  openEnterprisePageSettingsDialog,
  closeEnterprisePageSettingsDialog,
  openEnterpriseShortcutPlannerDialog,
  closeEnterpriseShortcutPlannerDialog,
  startShortcutCapture,
  stopShortcutCapture,
  restoreShortcutEditorActionDefault,
  clearShortcutEditorActionBinding,
  restoreShortcutEditorDefaults,
  saveShortcutEditorDraft,
  openEnterpriseMapEditorDialog,
  closeEnterpriseMapEditorDialog,
  resetEnterpriseMapEditorDraft,
  openEnterpriseTopologyEditorDialog,
  closeEnterpriseTopologyEditorDialog,
  resetEnterpriseTopologyEditorDraft,
  switchEnterpriseSettingsTab,
  toggleEnterpriseSettingsSidebar,
  enterpriseTabAccessLabel,
  taskStatusText,
  formatTaskCompactSummary,
  formatTaskTime,
  formatDateTimeInline,
  faultTypeText,
  faultSeverityText,
  formatOperationAuditTitle,
  formatOperationAuditOperator,
  formatOperationAuditResourceRef,
  formatOperationAuditMetadata,
  resetOperationAuditFilters,
  exportFilteredOperationAuditsJsonWithAuth,
  exportFilteredOperationAuditsCsvWithAuth,
  isOperationAuditSelected,
  toggleOperationAuditSelection,
  clearSelectedOperationAudits,
  areAllVisibleOperationAuditsSelected,
  selectedVisibleOperationAuditCount,
  toggleSelectVisibleOperationAudits,
  deleteSelectedOperationAuditsWithAuth,
  deleteOperationAuditWithAuth,
  refreshEnterpriseAccountStatus,
  runEnterpriseStatusFollowupAction,
  runEnterpriseApplicationAction,
  applyEnterprisePanelPreset,
  applyCurrentEnterpriseWorkspacePreset,
  openPageSettingsFromEnterpriseSettings,
  jumpFromEnterpriseSettings,
  runEnterpriseWorkspaceAction,
  mapProfileActionSummaryTitle,
  buildMapResizeReasonItem,
  focusMapResizeReasonKey,
  exportMapProfileActionSummary,
  isCurrentMapProfile,
  localizedMapProfileField,
  formatMapProfileCreatedBy,
  formatMapProfileLastOperator,
  mapProfilePreviewStatusText,
  mapProfilePreviewStatus,
  mapProfilePreviewReasonItems,
  focusMapResizeReasonItem,
  canForceApplyMapProfile,
  isMapProfileApplying,
  canApplyMapProfileWithCapability,
  buildMapProfileApplyTitle,
  isEnterpriseMapEditorCellValid,
  isEnterpriseTopologyCellValid,
  isEnterpriseMapEditorCellBlocked,
  isEnterpriseMapEditorCellLocked,
  canResizeEnterpriseMapEditorTo,
  resizeEnterpriseMapEditorDraft,
  adjustEnterpriseMapEditorZoom,
  resetEnterpriseMapEditorZoom,
  handleEnterpriseMapEditorWheel,
  applyEnterpriseMapEditorCell,
  saveEnterpriseMapEditorDraft,
  applyEnterpriseTopologyCell,
  selectEnterpriseTopologyNode,
  selectEnterpriseTopologyEdge,
  updateEnterpriseTopologyNode,
  updateEnterpriseTopologyEdge,
  toggleEnterpriseTopologyLinkSource,
  removeSelectedEnterpriseTopologyNode,
  removeSelectedEnterpriseTopologyEdge,
  saveEnterpriseTopologyEditorDraft,
  formatEnterpriseTopologyNodeBadge,
  formatMapProfileTopologySummary,
  isCellOccupied,
  applyMapProfile,
  isMapProfilePreviewing,
  previewMapProfile,
  isMapProfileExporting,
  exportMapProfile,
  isMapProfileDeleting,
  deleteMapProfile,
  buildCapabilityLockedTitle,
  formatInlineMessage,
  algorithmText,
  compareCurrentRoute,
  setDispatchModeFromEnterprise,
  setRuntimeAlgorithmFromEnterprise,
  setCompareDisplayModeFromEnterprise,
  algorithmCompareWorkspaceBindings,
  buildAiRenderSharedTemplatesHintText,
  openComfyBuiltinTemplateOverview,
  applySelectedBuiltinComfyTemplate,
  fetchComfyCheckpoints,
  loadComfySourcePayload,
  loadDefaultComfyWorkflow,
  submitComfyRenderJob,
  fetchComfyRenderJobs,
  saveCurrentComfyTemplate,
  applySelectedComfyTemplate,
  exportSelectedComfyTemplate,
  onComfyTemplateFileChange,
  deleteSelectedComfyTemplate,
  saveCurrentComfySharedTemplate,
  applySelectedSharedTemplate,
  fetchComfySharedTemplates,
  deleteSelectedSharedTemplate,
  openComfyRenderAssetPreview,
  deleteComfyRenderJob,
  openAuthDialog,
  formatComfyRenderSource,
  formatComfyRenderStatus,
  formatComfyRenderAssetActionLabel,
  formatEnterpriseComfyRenderJobMeta,
  buildAiRenderHintText,
  buildOperationsEntryActionText,
  operationActionLabel,
  fetchOperationAudits,
  buildOperationsHintText
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  stopEnterpriseAgvMotionPolling()
  stopAgvAnimationLoop()
  if (authGovernanceSyncTimer) {
    clearInterval(authGovernanceSyncTimer)
    authGovernanceSyncTimer = null
  }
  if (clickTimer) clearTimeout(clickTimer)
  clearPreview()
  if (manualPreviewHoldTimer) clearTimeout(manualPreviewHoldTimer)
  if (mapPreviewFocusTimer) clearTimeout(mapPreviewFocusTimer)
  if (mapResizeSectionHighlightTimer) clearTimeout(mapResizeSectionHighlightTimer)
  if (mapResizeItemHighlightTimer) clearTimeout(mapResizeItemHighlightTimer)
  if (accountGovernanceSearchTimer) clearTimeout(accountGovernanceSearchTimer)
  if (taskBuilderJumpTimer) clearTimeout(taskBuilderJumpTimer)
  if (agvRecoveryJumpTimer) clearTimeout(agvRecoveryJumpTimer)
  if (faultSelectedAgvPulseTimer) clearTimeout(faultSelectedAgvPulseTimer)
  hideFloatingToast()
  disposePanelCompareUi()
  if (mapResizeObserver) mapResizeObserver.disconnect()
  stopObstaclePaint()
  document.body.style.cursor = ''
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('beforeunload', onWindowBeforeUnload)
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('mousemove', onGlobalMouseMove)
  window.removeEventListener('mouseup', onGlobalMouseUp)
})
</script>

<template>
  <div class="page-shell">
    <AuthDialog v-if="showAuthDialog" :ui="authDialogBindings" />

    <EnterpriseApprovalDialog v-if="enterpriseApprovalDialogOpen" :ui="enterpriseApprovalDialogBindings" />

    <PlatformAccountGovernanceDialog
      v-if="accountGovernanceDialogOpen"
      :ui="platformAccountGovernanceDialogBindings"
    />

    <EnterpriseRequestDialog
      v-if="enterpriseRequestDialogOpen"
      :ui="enterpriseRequestDialogBindings"
    />

    <PlatformBugFeedbackDialog
      v-if="platformBugFeedbackDialogOpen"
      :ui="platformBugFeedbackDialogBindings"
    />

    <EnterpriseSettingsDialog v-if="enterpriseSettingsDialogOpen" :ui="enterpriseSettingsDialogBindings" />

    <div v-if="isPlatformAdminGovernanceMode" class="page-top page-top-governance">
      <div class="page-top-main">
        <button class="page-title-auth" type="button" :title="authTitleButtonTitle" @click="openAuthDialog">
          <span class="page-title-auth-main">{{ t('title') }}</span>
          <span class="page-title-auth-divider">·</span>
          <span class="page-title-auth-mode">{{ authModeText }}</span>
        </button>

        <div class="toolbar">
          <label class="field">
            {{ t('language') }}
            <select v-model="locale">
              <option value="zh">中文</option>
              <option value="ja">日本語</option>
              <option value="en">English</option>
            </select>
          </label>

          <button
            v-if="authCanEnterpriseApprove"
            class="toolbar-compare-entry toolbar-admin-entry"
            type="button"
            @click="openEnterpriseApprovalDialog"
          >
            <span>{{ t('enterprise_approval_entry') }}</span>
            <span v-if="platformApprovalPendingCount > 0" class="toolbar-entry-badge">
              {{ formatInlineMessage(t('enterprise_approval_pending_badge'), { count: platformApprovalPendingCount }) }}
            </span>
          </button>
          <button
            v-if="authCanSystemManage"
            class="toolbar-compare-entry toolbar-admin-entry"
            type="button"
            @click="openAccountGovernanceDialog()"
          >
            <span>{{ t('account_governance_entry') }}</span>
          </button>
          <button
            v-if="authCanPlatformBugManage"
            class="toolbar-compare-entry toolbar-admin-entry"
            type="button"
            @click="openPlatformBugFeedbackDialog({ status: 'open' })"
          >
            <span>{{ t('platform_bug_feedback_entry') }}</span>
            <span v-if="platformBugFeedbackOpenCount > 0" class="toolbar-entry-badge">
              {{ formatInlineMessage(t('platform_bug_feedback_open_badge'), { count: platformBugFeedbackOpenCount }) }}
            </span>
          </button>
        </div>

        <p class="toolbar-hint">{{ t('platform_admin_governance_hint') }}</p>
        <p class="toolbar-hint toolbar-hint-secondary">{{ t('platform_admin_governance_subhint') }}</p>
      </div>
    </div>

    <div v-else class="page-top" :style="pageTopStyle">
      <div class="page-top-main">
        <button class="page-title-auth" type="button" :title="authTitleButtonTitle" @click="openAuthDialog">
          <span class="page-title-auth-main">{{ t('title') }}</span>
          <span class="page-title-auth-divider">·</span>
          <span class="page-title-auth-mode">{{ authModeText }}</span>
        </button>

        <div class="toolbar">
          <label class="field">
            {{ t('language') }}
            <select v-model="locale">
              <option value="zh">中文</option>
              <option value="ja">日本語</option>
              <option value="en">English</option>
            </select>
          </label>

          <div class="field">
            <span class="field-label">{{ t('dispatch') }}</span>
            <select v-model="dispatchMode">
              <option value="auto">{{ t('dispatch_auto') }}</option>
              <option value="manual">{{ t('dispatch_manual') }}</option>
            </select>
          </div>

          <label class="field">
            {{ t('algorithm') }}
            <select v-model="algorithm">
              <option value="simple">{{ t('algo_simple') }}</option>
              <option value="astar">{{ t('algo_astar') }}</option>
            </select>
          </label>

          <label class="field">
            {{ t('priority') }}
            <select v-model.number="taskPriority">
              <option :value="5">5</option>
              <option :value="4">4</option>
              <option :value="3">3</option>
              <option :value="2">2</option>
              <option :value="1">1</option>
            </select>
          </label>

          <div class="status-pill" :class="{ empty: !selectedAgv }" :title="toolbarSelectedAgvTitle">
            <span class="status-pill-dot" :style="{ backgroundColor: selectedAgv ? statusColor(selectedAgv.status) : '#9e9e9e' }"></span>
            <span class="status-pill-text">{{ toolbarSelectedAgvText }}</span>
          </div>

          <button ref="compareEntryButtonRef" class="toolbar-compare-entry" type="button" @click="handleCompareEntryClick">
            {{ compareEntryText }}
          </button>
          <button
            v-if="showEnterpriseSettingsToolbarEntry"
            class="toolbar-compare-entry toolbar-admin-entry"
            type="button"
            @click="openEnterpriseSettingsDialog()"
          >
            <span>{{ t('enterprise_settings_entry') }}</span>
            <span
              v-if="enterpriseToolbarStatusBadgeText"
              class="toolbar-entry-badge"
              :class="[`tone-${authCurrentAccountStatus}`]"
            >
              {{ enterpriseToolbarStatusBadgeText }}
            </span>
          </button>
          <button
            v-if="authCanEnterpriseApprove && showPlatformAdminManagementEntries"
            class="toolbar-compare-entry toolbar-admin-entry"
            type="button"
            @click="openEnterpriseApprovalDialog"
          >
            <span>{{ t('enterprise_approval_entry') }}</span>
            <span v-if="platformApprovalPendingCount > 0" class="toolbar-entry-badge">
              {{ formatInlineMessage(t('enterprise_approval_pending_badge'), { count: platformApprovalPendingCount }) }}
            </span>
          </button>
          <button
            v-if="authCanSystemManage && showPlatformAdminManagementEntries"
            class="toolbar-compare-entry toolbar-admin-entry"
            type="button"
            @click="openAccountGovernanceDialog()"
          >
            <span>{{ t('account_governance_entry') }}</span>
          </button>
        </div>
        <p class="toolbar-hint">{{ t('hint') }}</p>
        <p v-if="toolbarGuideHintText" class="toolbar-hint toolbar-hint-secondary">{{ toolbarGuideHintText }}</p>
      </div>

      <div class="page-top-spacer"></div>

      <aside class="page-top-summary">
        <div class="panel-topbar">
          <div class="panel-summary-header">
            <strong class="panel-summary-title">{{ panelSummaryLocale.title }}</strong>
            <div class="panel-summary-mode-switch">
              <button
                v-for="mode in panelSummaryModes"
                :key="mode.key"
                class="panel-summary-mode-button"
                :class="{ active: panelSummaryMode === mode.key }"
                type="button"
                @click="panelSummaryMode = mode.key"
              >
                {{ mode.label }}
              </button>
            </div>
          </div>

          <div
            v-if="showPanelSummary"
            class="panel-summary-shell"
            :class="{ compact: panelSummaryMode === 'compact', full: panelSummaryMode === 'full' }"
          >
            <div v-if="panelSummaryMode === 'compact'" class="panel-summary-compact">
              <button
                v-for="item in panelSummaryCompactItems"
                :key="item.key"
                class="panel-summary-tower"
                :class="[`summary-${item.key}`, { armed: item.key === 'zoom' && summaryZoomArmed }]"
                type="button"
                @click="handlePanelSummaryItemClick(item)"
                @wheel="handlePanelSummaryItemWheel($event, item, 'compact')"
                @mouseleave="handlePanelSummaryItemMouseLeave(item)"
                @dblclick="handlePanelSummaryItemDoubleClick($event, item)"
              >
                <strong class="panel-summary-tower-value">{{ item.value }}</strong>
              </button>
            </div>

            <div v-else class="panel-summary-grid">
              <button
                v-for="item in panelSummaryItems"
                :key="item.key"
                class="panel-summary-card"
                :class="{ armed: item.key === 'zoom' && summaryZoomArmed }"
                type="button"
                @click="handlePanelSummaryItemClick(item)"
                @wheel="handlePanelSummaryItemWheel($event, item, 'full')"
                @mouseleave="handlePanelSummaryItemMouseLeave(item)"
                @dblclick="handlePanelSummaryItemDoubleClick($event, item)"
              >
                <span class="panel-summary-label">{{ item.label }}</span>
                <strong class="panel-summary-value">{{ item.value }}</strong>
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="isPlatformAdminPreviewMode" class="platform-admin-preview-bar">
      <div class="platform-admin-preview-copy">
        <strong>{{ platformAdminPreviewTitle }}</strong>
        <span>{{ platformAdminPreviewHint }}</span>
      </div>
      <div class="platform-admin-preview-actions">
        <div v-if="isPlatformAdminEnterprisePreviewMode" class="platform-admin-preview-role-switch">
          <span>{{ t('platform_admin_preview_role_switch') }}</span>
          <div class="platform-admin-preview-role-buttons">
            <button
              v-for="item in platformAdminPreviewRoleItems"
              :key="`platform-admin-preview-role-${item.key}`"
              class="btn-ghost"
              :class="{ active: platformAdminEnterprisePreviewRole === item.key }"
              type="button"
              @click="enterPlatformAdminEnterprisePreviewMode(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <button class="btn-secondary" type="button" @click="enterPlatformAdminGovernanceMode">
          {{ t('platform_admin_preview_exit') }}
        </button>
      </div>
    </div>

    <PlatformAdminGovernanceHub
      v-if="isPlatformAdminGovernanceMode"
      :ui="platformAdminGovernanceHubBindings"
    />

    <div v-else ref="layoutRef" class="layout" :style="layoutStyle">
      <div ref="mapPaneRef" class="map-pane">
        <div
          v-if="showEnterpriseWorkspacePopup"
          ref="enterpriseWorkspacePopupRef"
          class="enterprise-workspace-popup"
          :style="enterpriseWorkspacePopupStyle"
        >
          <div class="enterprise-workspace-popup-head" @mousedown="startEnterpriseWorkspacePopupDrag">
            <div class="enterprise-workspace-popup-copy">
              <div class="enterprise-workspace-popup-title-row">
                <strong>{{ enterpriseRoleFocus.title }}</strong>
                <span class="point-badge enterprise-settings-chip">{{ enterpriseUiRoleLabel }}</span>
              </div>
              <p>{{ enterpriseRoleScopeText }}</p>
            </div>
            <button
              class="enterprise-workspace-popup-close"
              type="button"
              :title="t('auth_close')"
              @click="dismissEnterpriseWorkspacePopup"
            >
              ×
            </button>
          </div>
          <div class="enterprise-settings-chip-list">
            <span
              v-for="label in enterpriseWorkspaceSectionLabels"
              :key="`enterprise-workspace-popup-${label}`"
              class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
            >
              {{ label }}
            </span>
          </div>
          <div
            class="enterprise-workspace-popup-actions"
            :style="{ gridTemplateColumns: `repeat(${enterpriseWorkspacePopupActionItems.length || 1}, minmax(0, 1fr))` }"
          >
            <button
              v-for="action in enterpriseWorkspacePopupActionItems"
              :key="`enterprise-workspace-popup-action-${action.key}`"
              :class="['enterprise-workspace-popup-action', action.tone === 'ghost' ? 'btn-ghost' : 'btn-secondary']"
              type="button"
              @click="action.handler()"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
        <section
          ref="mapViewportRef"
          class="map"
          :class="{ panning: isMapPanning, editing: obstacleEditMode }"
          @mousedown="onMapMouseDown"
          @click="onMapClick"
          @dblclick="onMapDoubleClick"
          @wheel.prevent="onMapWheel"
          @contextmenu="onMapContextMenu"
        >
          <div
            v-if="showStatusLegend"
            class="map-status-overlay"
            :class="{
              'is-horizontal': statusLegendLayout === 'horizontal',
              'is-vertical': statusLegendLayout === 'vertical'
            }"
            :style="{ '--status-legend-opacity': statusLegendOpacity }"
            @mousedown.stop
            @click.stop
            @dblclick.stop
            @wheel.stop
          >
            <div class="legend-title">{{ t('agv_status') }}</div>
              <div class="legend-row">
                <div class="legend-item">
                  <span class="legend-dot idle"></span>{{ t('status_idle') }}
                </div>
                <div class="legend-item">
                  <span class="legend-dot returning"></span>{{ t('status_idle_returning') }}
                </div>
                <div class="legend-item">
                  <span class="legend-dot charging"></span>{{ t('status_waiting_for_charge') }}
                </div>
                <div class="legend-item">
                  <span class="legend-dot relocating"></span>{{ t('status_relocating') }}
                  <span class="info-icon" :title="t('status_relocating_desc')">i</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot running"></span>{{ t('status_running') }}
              </div>
              <div class="legend-item">
                <span class="legend-dot fault"></span>{{ t('status_fault') }}
              </div>
              <div class="legend-item">
                <span class="legend-dot emergency-stop"></span>{{ faultLocale.emergencyStopped }}
              </div>
            </div>
          </div>

          <div class="map-stage" :class="{ 'is-irregular': mapIsIrregular }" :style="mapStageStyle">
            <div
              v-for="cell in mapValidCells"
              :key="`valid-${cell.x}-${cell.y}`"
              class="map-valid-cell"
              :style="{
                left: `${cell.x * CELL_SIZE}px`,
                top: `${cell.y * CELL_SIZE}px`,
                width: `${CELL_SIZE}px`,
                height: `${CELL_SIZE}px`
              }"
            ></div>
            <div
              v-for="cell in mapVoidCells"
              :key="`void-${cell.x}-${cell.y}`"
              class="void-cell"
              :style="{
                left: `${cell.x * CELL_SIZE}px`,
                top: `${cell.y * CELL_SIZE}px`,
                width: `${CELL_SIZE}px`,
                height: `${CELL_SIZE}px`
              }"
            ></div>
            <div
              v-for="cell in blockedCells"
              :key="`blocked-${cell.x}-${cell.y}`"
              class="blocked-cell"
              :style="{
                left: `${cell.x * CELL_SIZE}px`,
                top: `${cell.y * CELL_SIZE}px`,
                width: `${CELL_SIZE}px`,
                height: `${CELL_SIZE}px`
              }"
            ></div>

            <div
              v-for="focusCell in mapPreviewFocusCells"
              :key="focusCell.key"
              class="map-preview-focus-cell"
              :style="{
                left: `${focusCell.x * CELL_SIZE}px`,
                top: `${focusCell.y * CELL_SIZE}px`,
                width: `${CELL_SIZE}px`,
                height: `${CELL_SIZE}px`
              }"
            ></div>

            <svg class="path-layer" :width="mapWidth" :height="mapHeight">
              <defs>
                <marker id="path-arrow-start" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" class="arrow-head start"></path>
                </marker>
                <marker id="path-arrow-end" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" class="arrow-head end"></path>
                </marker>
                <marker id="path-arrow-auto-start" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" class="arrow-head auto-start"></path>
                </marker>
                <marker id="path-arrow-auto-end" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" class="arrow-head auto-end"></path>
                </marker>
                <marker id="path-arrow-preview" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 z" class="arrow-head preview"></path>
                </marker>
              </defs>
              <polyline
                class="path-to-start"
                :points="manualPathToStartPoints"
                fill="none"
                stroke-width="3"
                stroke-dasharray="6 4"
              />
              <polyline
                class="path-to-end"
                :points="manualPathToEndPoints"
                fill="none"
                stroke-width="3"
              />
              <polyline
                v-if="showAutoRuntimeVisuals"
                class="path-auto-start"
                :points="autoPathToStartPoints"
                fill="none"
                stroke-width="2"
                stroke-dasharray="4 4"
              />
              <polyline
                v-if="showAutoRuntimeVisuals"
                class="path-auto-end"
                :points="autoPathToEndPoints"
                fill="none"
                stroke-width="2"
              />
              <polyline
                v-if="manualChainRoutePoints"
                class="path-chain-route path-chain-manual"
                :points="manualChainRoutePoints"
                fill="none"
                stroke-width="2"
                stroke-dasharray="3 4"
              />
              <polyline
                v-if="autoChainRoutePoints"
                class="path-chain-route path-chain-auto"
                :points="autoChainRoutePoints"
                fill="none"
                stroke-width="2"
                stroke-dasharray="3 4"
              />
              <polyline
                v-if="previewTaskId"
                class="path-preview"
                :points="previewPathPoints"
                fill="none"
                stroke-width="2"
                stroke-dasharray="2 4"
              />
              <line
                v-for="segment in showPathArrows ? manualPathToStartArrows : []"
                :key="`manual-start-${segment.id}`"
                class="path-arrow path-arrow-start"
                :x1="segment.x1"
                :y1="segment.y1"
                :x2="segment.x2"
                :y2="segment.y2"
                marker-end="url(#path-arrow-start)"
              />
              <line
                v-for="segment in showPathArrows ? manualPathToEndArrows : []"
                :key="`manual-end-${segment.id}`"
                class="path-arrow path-arrow-end"
                :x1="segment.x1"
                :y1="segment.y1"
                :x2="segment.x2"
                :y2="segment.y2"
                marker-end="url(#path-arrow-end)"
              />
              <line
                v-for="segment in showPathArrows && showAutoRuntimeVisuals ? autoPathToStartArrows : []"
                :key="`auto-start-${segment.id}`"
                class="path-arrow path-arrow-auto-start"
                :x1="segment.x1"
                :y1="segment.y1"
                :x2="segment.x2"
                :y2="segment.y2"
                marker-end="url(#path-arrow-auto-start)"
              />
              <line
                v-for="segment in showPathArrows && showAutoRuntimeVisuals ? autoPathToEndArrows : []"
                :key="`auto-end-${segment.id}`"
                class="path-arrow path-arrow-auto-end"
                :x1="segment.x1"
                :y1="segment.y1"
                :x2="segment.x2"
                :y2="segment.y2"
                marker-end="url(#path-arrow-auto-end)"
              />
              <line
                v-for="segment in showPathArrows ? previewPathArrows : []"
                :key="`preview-${segment.id}`"
                class="path-arrow path-arrow-preview"
                :x1="segment.x1"
                :y1="segment.y1"
                :x2="segment.x2"
                :y2="segment.y2"
                marker-end="url(#path-arrow-preview)"
              />
            </svg>

            <div
              v-if="activeDisplayStartMarker"
              :class="
                showMarkerIcons
                  ? [
                      'point-icon',
                      'point-icon-start',
                      activeDisplayMarkerVariant === 'auto' ? 'point-icon-auto' : 'point-icon-manual'
                    ]
                  : 'marker start'
              "
              :style="pointStyle(activeDisplayStartMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>

            <div
              v-if="activeDisplayEndMarker"
              :class="
                showMarkerIcons
                  ? [
                      'point-icon',
                      'point-icon-end',
                      activeDisplayMarkerVariant === 'auto' ? 'point-icon-auto' : 'point-icon-manual'
                    ]
                  : 'marker end'
              "
              :style="pointStyle(activeDisplayEndMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
            >
              <span v-if="showMarkerIcons">E</span>
            </div>

            <div
              v-for="(point, index) in chainMidMarkers"
              :key="`chain-mid-${index}`"
              class="transfer-marker"
              :style="pointStyle(point, CELL_SIZE, 22)"
            >
              <span>{{ point.order }}</span>
            </div>

            <div
              v-if="previewStart"
              class="marker preview-start"
              :style="pointStyle(previewStart, CELL_SIZE, 10)"
            />

            <div
              v-if="previewEnd"
              class="marker preview-end"
              :style="pointStyle(previewEnd, CELL_SIZE, 10)"
            />

            <div
              v-for="agv in displayAgvs"
              :key="agv.id"
              class="agv"
              :class="{
                selected: agv.id === selectedAgvId,
                'is-enterprise-motion': uiTreatAsEnterpriseRole && agv.source === 'backend',
                'is-waiting': uiTreatAsEnterpriseRole && agv.source === 'backend' && agv.motionState === 'waiting',
                'is-yielding': uiTreatAsEnterpriseRole && agv.source === 'backend' && agv.motionState === 'yielding',
                'is-returning': uiTreatAsEnterpriseRole && agv.source === 'backend' && agv.motionState === 'idle_returning',
                'is-charging': uiTreatAsEnterpriseRole && agv.source === 'backend' && ['waiting_for_charge', 'charging'].includes(agv.motionState)
              }"
              :style="{
                left: `${agv.displayX * CELL_SIZE + (CELL_SIZE - AGV_SIZE) / 2}px`,
                top: `${agv.displayY * CELL_SIZE + (CELL_SIZE - AGV_SIZE) / 2}px`,
                backgroundColor: statusColor(agv.status)
              }"
              :title="formatEnterpriseAgvRuntimeHint(agv)"
              @click="onAgvClick(agv, $event)"
              @contextmenu.prevent="cancelSelection"
            >
              {{ agv.id }}
            </div>
          </div>

          <div
            class="map-controls"
            @mousedown.stop
            @click.stop
            @dblclick.stop
            @wheel.stop
          >
            <div class="map-zoom-pill">{{ mapZoomLabel }}</div>
            <button
              v-if="!uiTreatAsEnterpriseRole"
              class="map-control-button map-control-button-page-settings"
              type="button"
              :title="t('enterprise_settings_page_settings_entry')"
              :aria-label="t('enterprise_settings_page_settings_entry')"
              @click="toggleMapSettings"
            >
              <span aria-hidden="true">⚙</span>
              <span class="visually-hidden">{{ t('enterprise_settings_page_settings_entry') }}</span>
            </button>
            <MapSettingsPanel :ui="mapSettingsPanelBindings" />
          </div>

          <div
            v-if="showMinimap"
            ref="minimapRef"
            class="minimap"
            :style="{ width: `${MINIMAP_WIDTH}px`, height: `${minimapHeight}px` }"
            @click.stop
            @dblclick.stop
            @wheel.stop
            @mousedown="onMinimapMouseDown"
          >
            <div
              class="minimap-grid"
              :class="{ 'is-irregular': mapIsIrregular }"
              :style="{
                backgroundSize: `${CELL_SIZE * minimapScale}px ${CELL_SIZE * minimapScale}px`
              }"
            ></div>
            <div
              v-for="cell in mapValidCells"
              :key="`mini-valid-${cell.x}-${cell.y}`"
              class="minimap-valid-cell"
              :style="{
                left: `${cell.x * CELL_SIZE * minimapScale}px`,
                top: `${cell.y * CELL_SIZE * minimapScale}px`,
                width: `${CELL_SIZE * minimapScale}px`,
                height: `${CELL_SIZE * minimapScale}px`
              }"
            ></div>
            <div
              v-for="cell in mapVoidCells"
              :key="`mini-void-${cell.x}-${cell.y}`"
              class="minimap-void-cell"
              :style="{
                left: `${cell.x * CELL_SIZE * minimapScale}px`,
                top: `${cell.y * CELL_SIZE * minimapScale}px`,
                width: `${CELL_SIZE * minimapScale}px`,
                height: `${CELL_SIZE * minimapScale}px`
              }"
            ></div>
            <div
              v-for="cell in blockedCells"
              :key="`mini-blocked-${cell.x}-${cell.y}`"
              class="minimap-blocked-cell"
              :style="{
                left: `${cell.x * CELL_SIZE * minimapScale}px`,
                top: `${cell.y * CELL_SIZE * minimapScale}px`,
                width: `${CELL_SIZE * minimapScale}px`,
                height: `${CELL_SIZE * minimapScale}px`
              }"
            ></div>
            <svg class="minimap-path-layer" :width="MINIMAP_WIDTH" :height="minimapHeight">
              <polyline
                class="path-to-start minimap-path"
                :points="minimapManualPathToStartPoints"
                fill="none"
                stroke-width="1.8"
              />
              <polyline
                class="path-to-end minimap-path"
                :points="minimapManualPathToEndPoints"
                fill="none"
                stroke-width="1.8"
              />
              <polyline
                v-if="showAutoRuntimeVisuals"
                class="path-auto-start minimap-path"
                :points="minimapAutoPathToStartPoints"
                fill="none"
                stroke-width="1.4"
              />
              <polyline
                v-if="showAutoRuntimeVisuals"
                class="path-auto-end minimap-path"
                :points="minimapAutoPathToEndPoints"
                fill="none"
                stroke-width="1.4"
              />
              <polyline
                v-if="minimapManualChainRoutePoints"
                class="path-chain-route path-chain-manual minimap-path"
                :points="minimapManualChainRoutePoints"
                fill="none"
                stroke-width="1.2"
                stroke-dasharray="2 3"
              />
              <polyline
                v-if="minimapAutoChainRoutePoints"
                class="path-chain-route path-chain-auto minimap-path"
                :points="minimapAutoChainRoutePoints"
                fill="none"
                stroke-width="1.2"
                stroke-dasharray="2 3"
              />
              <polyline
                v-if="previewTaskId"
                class="path-preview minimap-path"
                :points="minimapPreviewPathPoints"
                fill="none"
                stroke-width="1.2"
              />
            </svg>
            <div class="minimap-label">{{ t('map_overview') }}</div>
            <div
              v-for="agv in displayAgvs"
              :key="`mini-${agv.id}`"
              class="minimap-agv"
              :class="{
                'is-waiting': uiTreatAsEnterpriseRole && agv.source === 'backend' && agv.motionState === 'waiting',
                'is-yielding': uiTreatAsEnterpriseRole && agv.source === 'backend' && agv.motionState === 'yielding',
                'is-returning': uiTreatAsEnterpriseRole && agv.source === 'backend' && agv.motionState === 'idle_returning',
                'is-charging': uiTreatAsEnterpriseRole && agv.source === 'backend' && ['waiting_for_charge', 'charging'].includes(agv.motionState)
              }"
              :style="{
                left: `${agv.displayX * CELL_SIZE * minimapScale + (CELL_SIZE * minimapScale) / 2 - 4}px`,
                top: `${agv.displayY * CELL_SIZE * minimapScale + (CELL_SIZE * minimapScale) / 2 - 4}px`,
                backgroundColor: statusColor(agv.status)
              }"
            ></div>
            <div
              v-if="minimapDisplayStartMarker"
              :class="
                showMarkerIcons
                  ? [
                      'minimap-point-icon',
                      'minimap-point-start',
                      activeDisplayMarkerVariant === 'auto' ? 'minimap-point-auto' : 'minimap-point-manual'
                    ]
                  : 'marker start minimap-marker-dot'
              "
              :style="pointStyle(minimapDisplayStartMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>
            <div
              v-if="minimapDisplayEndMarker"
              :class="
                showMarkerIcons
                  ? [
                      'minimap-point-icon',
                      'minimap-point-end',
                      activeDisplayMarkerVariant === 'auto' ? 'minimap-point-auto' : 'minimap-point-manual'
                    ]
                  : 'marker end minimap-marker-dot'
              "
              :style="pointStyle(minimapDisplayEndMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
            >
              <span v-if="showMarkerIcons">E</span>
            </div>
            <div
              v-for="(point, index) in chainMidMarkers"
              :key="`mini-chain-mid-${index}`"
              class="transfer-marker minimap-transfer-marker"
              :style="pointStyle(point, minimapCellSize, 8)"
            >
              <span>{{ point.order }}</span>
            </div>
            <div class="minimap-viewport" :style="minimapViewportStyle"></div>
          </div>
          <div
            v-if="showFeedbackBell"
            class="feedback-fab"
            @mousedown.stop
            @click.stop
            @dblclick.stop
            @wheel.stop
          >
            <div v-if="feedbackBellMenuOpen" class="feedback-fab-menu">
              <button
                v-if="showEnterpriseRequestToolbarEntry"
                class="feedback-fab-menu-item"
                type="button"
                @click="openEnterpriseRequestDialogFromBell"
              >
                <strong>{{ t('enterprise_request_entry') }}</strong>
                <span>{{ t('feedback_bell_enterprise_request_hint') }}</span>
              </button>
              <button
                v-if="showPlatformBugFeedbackToolbarEntry"
                class="feedback-fab-menu-item"
                type="button"
                @click="openPlatformBugFeedbackDialogFromBell"
              >
                <strong>{{ t('platform_bug_feedback_entry') }}</strong>
                <span>{{ t('feedback_bell_platform_bug_hint') }}</span>
              </button>
            </div>
            <button
              class="feedback-fab-button"
              :class="{ 'is-open': feedbackBellMenuOpen }"
              type="button"
              :title="t('feedback_bell_entry')"
              @click.stop="toggleFeedbackBellMenu"
            >
              <svg class="feedback-fab-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M8.5 18h7m-8-1.5v-4.2a4.5 4.5 0 1 1 9 0v4.2l1.4 1.7a.7.7 0 0 1-.54 1.14H6.64a.7.7 0 0 1-.54-1.14l1.4-1.7Z"
                />
                <path d="M10.2 18.6a1.8 1.8 0 0 0 3.6 0" />
              </svg>
            </button>
          </div>
        </section>
      </div>

      <div class="panel-resizer" @mousedown="startPanelResize"></div>

      <aside class="panel-shell">
        <div ref="panelRef" class="panel" @scroll="onPanelScroll">
          <div v-if="hasVisiblePanelSections" class="panel-search">
            <div class="panel-search-row">
              <input
                v-model.trim="panelSearch"
                class="panel-search-input"
                type="text"
                :placeholder="panelSearchLocale.placeholder"
              />
              <button class="btn-ghost" type="button" @click="clearPanelSearch">
                {{ panelSearchLocale.clear }}
              </button>
            </div>
            <div v-if="panelSearch" class="panel-search-results">
              <button
                v-for="result in panelSearchResults"
                :key="result.key"
                class="panel-search-chip"
                type="button"
                @click="jumpToPanelSearchResult(result.key)"
              >
                {{ result.text }}
              </button>
              <div v-if="panelSearchResults.length === 0" class="panel-search-empty">
                {{ panelSearchLocale.empty }}
              </div>
            </div>
          </div>

          <div v-if="hasVisiblePanelSections" class="panel-section-actions">
            <button
              class="btn-ghost"
              type="button"
              :disabled="areAllPanelSectionsExpanded"
              @click="setAllPanelSections(true)"
            >
              {{ panelLocale.expandAll }}
            </button>
            <button
              class="btn-ghost"
              type="button"
              :disabled="areAllPanelSectionsCollapsed"
              @click="setAllPanelSections(false)"
            >
              {{ panelLocale.collapseAll }}
            </button>
          </div>

          <div v-if="!hasVisiblePanelSections" class="panel-empty-state">
            <strong>{{ t('enterprise_workspace_empty_title') }}</strong>
            <span>{{ t('enterprise_workspace_empty_hint') }}</span>
            <div class="approval-actions">
              <button
                v-if="showEnterpriseSettingsToolbarEntry"
                class="btn-secondary"
                type="button"
                @click="openEnterpriseSettingsDialog()"
              >
                {{ t('enterprise_settings_entry') }}
              </button>
            </div>
          </div>

          <section
            v-if="visiblePanelSectionKeySet.has('control')"
            ref="controlSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.control,
              'search-hit': matchedPanelSectionKeys.includes('control'),
              focused: focusedPanelSection === 'control'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.control"
              @click="togglePanelSection('control')"
            >
              <span>{{ panelLocale.sections.control }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.control ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.control" class="panel-section-body">
              <DispatchControlSummaryPanel :ui="dispatchControlSummaryPanelBindings" />

              <FaultOperationsPanel :ui="faultOperationsPanelBindings" />

              <TaskBuilderPanel :ui="taskBuilderPanelBindings" />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('queue')"
            ref="queueSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.queue,
              'search-hit': matchedPanelSectionKeys.includes('queue'),
              focused: focusedPanelSection === 'queue'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.queue"
              @click="togglePanelSection('queue')"
            >
              <span>{{ panelLocale.sections.queue }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.queue ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.queue" class="panel-section-body">
              <TaskQueuePanel :ui="taskQueuePanelBindings" />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('templates')"
            ref="templatesSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.templates,
              'search-hit': matchedPanelSectionKeys.includes('templates'),
              focused: focusedPanelSection === 'templates'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.templates"
              @click="togglePanelSection('templates')"
            >
              <span>{{ panelLocale.sections.templates }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.templates ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.templates" class="panel-section-body">
              <TaskTemplatesPanel :ui="taskTemplatesPanelBindings" />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('points')"
            ref="pointsSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.points,
              'search-hit': matchedPanelSectionKeys.includes('points'),
              focused: focusedPanelSection === 'points'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.points"
              @click="togglePanelSection('points')"
            >
              <span>{{ panelLocale.sections.points }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.points ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.points" class="panel-section-body">
              <PointLibraryPanel :ui="pointLibraryPanelBindings" />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('json')"
            ref="jsonSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.json,
              'search-hit': matchedPanelSectionKeys.includes('json'),
              focused: focusedPanelSection === 'json'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.json"
              @click="togglePanelSection('json')"
            >
              <span>{{ panelLocale.sections.json }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.json ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.json" class="panel-section-body">
              <JsonToolsPanel :ui="jsonToolsPanelBindings" />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('experiments')"
            ref="experimentsSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.experiments,
              'search-hit': matchedPanelSectionKeys.includes('experiments'),
              focused: focusedPanelSection === 'experiments'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.experiments"
              @click="togglePanelSection('experiments')"
            >
              <span>{{ panelLocale.sections.experiments }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.experiments ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.experiments" class="panel-section-body">
              <ExperimentRecordsPanel :ui="experimentRecordsPanelBindings" />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('ai')"
            ref="aiSectionRef"
            class="panel-section ai-panel-section"
            :class="{
              collapsed: !panelSections.ai,
              'search-hit': matchedPanelSectionKeys.includes('ai'),
              focused: focusedPanelSection === 'ai'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.ai"
              @click="togglePanelSection('ai')"
            >
              <span>{{ panelLocale.sections.ai }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.ai ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.ai" class="panel-section-body ai-panel-section-body">
              <ComfyAiWorkspace
                v-model:builtin-template-key="comfyRenderBuiltinTemplateKey"
                v-model:source-type="comfyRenderSourceType"
                v-model:source-ref="comfyRenderSourceRef"
                v-model:checkpoint-name="comfyRenderCheckpointName"
                v-model:workflow-preset="comfyRenderWorkflowPreset"
                v-model:prompt-style="comfyRenderPromptStyle"
                v-model:template-name="comfyRenderTemplateName"
                v-model:selected-template-id="comfyRenderSelectedTemplateId"
                v-model:prompt-text="comfyRenderPromptText"
                v-model:input-json-text="comfyRenderInputJsonText"
                v-model:workflow-json-text="comfyRenderWorkflowJsonText"
                v-model:selected-shared-template-id="comfyRenderSelectedSharedTemplateId"
                :t="t"
                :format-inline-message="formatInlineMessage"
                :can-render="authCanAiRender"
                :heading="t('ai_render_title')"
                :hint-text="buildAiRenderHintText()"
                :status-text="comfyRenderStatus"
                :status-type="comfyRenderStatusType"
                :builtin-templates="comfyRenderBuiltinTemplates"
                :selected-builtin-template="comfyRenderSelectedBuiltinTemplate"
                :selected-builtin-template-matches-recommendation="comfyRenderSelectedBuiltinTemplateMatchesRecommendation"
                :recommended-builtin-template="comfyRenderRecommendedBuiltinTemplate"
                :recommended-builtin-reason-text="comfyRenderRecommendedBuiltinReasonText"
                :source-options="comfyRenderSourceOptions"
                :workflow-preset-options="comfyRenderWorkflowPresetOptions"
                :prompt-style-options="comfyRenderPromptStyleOptions"
                :saved-templates="comfyRenderSavedTemplates"
                :has-custom-templates="comfyRenderHasCustomTemplates"
                :shared-templates="comfyRenderSharedTemplates"
                :selected-shared-template="comfyRenderSelectedSharedTemplate"
                :has-shared-templates="comfyRenderHasSharedTemplates"
                :shared-templates-hint-text="buildAiRenderSharedTemplatesHintText()"
                :shared-template-meta-text="comfyRenderSelectedSharedTemplateMetaText"
                checkpoint-list-id="comfy-checkpoint-options"
                :available-checkpoints="comfyRenderAvailableCheckpoints"
                :workflow-preset-summary="comfyRenderWorkflowPresetSummary"
                :prompt-style-summary="comfyRenderPromptStyleSummary"
                :recommended-checkpoint-summary="comfyRenderRecommendedCheckpointSummary"
                :submitting="comfyRenderSubmitting"
                :loading-jobs="comfyRenderLoading"
                :shared-template-saving="comfyRenderSharedTemplateSaving"
                :shared-templates-loading="comfyRenderSharedTemplatesLoading"
                :jobs="comfyRenderJobs"
                :jobs-title="''"
                :jobs-empty-text="t('ai_render_empty')"
                :matched-job-ids="matchedComfyJobIds"
                :deleting-job-id="deletingComfyJobId"
                :last-fetched-text="comfyRenderLastFetchedText"
                :no-access-action-text="buildOperationsEntryActionText()"
                :on-open-builtin-overview="openComfyBuiltinTemplateOverview"
                :on-apply-builtin="applySelectedBuiltinComfyTemplate"
                :on-load-source="loadComfySourcePayload"
                :on-fill-default-workflow="loadDefaultComfyWorkflow"
                :on-submit="submitComfyRenderJob"
                :on-refresh-jobs="() => fetchComfyRenderJobs({ force: true })"
                :on-save-template="saveCurrentComfyTemplate"
                :on-apply-template="applySelectedComfyTemplate"
                :on-export-template="exportSelectedComfyTemplate"
                :on-import-template="onComfyTemplateFileChange"
                :on-delete-template="deleteSelectedComfyTemplate"
                :on-save-shared-template="saveCurrentComfySharedTemplate"
                :on-apply-shared-template="applySelectedSharedTemplate"
                :on-refresh-shared-templates="() => fetchComfySharedTemplates({ force: true })"
                :on-delete-shared-template="deleteSelectedSharedTemplate"
                :on-preview-asset="openComfyRenderAssetPreview"
                :on-delete-job="deleteComfyRenderJob"
                :on-entry-action="openAuthDialog"
                :format-source="formatComfyRenderSource"
                :format-status="formatComfyRenderStatus"
                :format-asset-action-label="formatComfyRenderAssetActionLabel"
                :job-meta-text="formatPanelComfyRenderJobMeta"
              />
            </div>
          </section>

          <section
            v-if="visiblePanelSectionKeySet.has('operations')"
            ref="operationsSectionRef"
            class="panel-section"
            :class="{
              collapsed: !panelSections.operations,
              'search-hit': matchedPanelSectionKeys.includes('operations'),
              focused: focusedPanelSection === 'operations'
            }"
          >
            <button
              class="panel-section-toggle"
              type="button"
              :aria-expanded="panelSections.operations"
              @click="togglePanelSection('operations')"
            >
              <span>{{ panelLocale.sections.operations }}</span>
              <span class="panel-section-toggle-text">
                {{ panelSections.operations ? panelLocale.collapse : panelLocale.expand }}
              </span>
            </button>
            <div v-show="panelSections.operations" class="panel-section-body">
              <OperationsAuditPanel :ui="operationsAuditPanelBindings" />
            </div>
          </section>
        </div>
        <button
          v-if="taskTemplateJumpReady"
          class="task-builder-jump-button"
          type="button"
          @click="focusTaskBuilder(taskBuilderMode)"
        >
          {{ taskBuilderLocale.jumpAction }}
        </button>
        <button
          v-if="agvRecoveryJumpReady && agvRecoveryJumpTargetAgvId"
          class="agv-recovery-jump-button"
          type="button"
          @click="jumpToRecoveryAgvCard"
        >
          {{ agvRecoveryJumpButtonText() }}
        </button>
        <button
          v-if="showPanelBackToTop"
          class="back-to-top"
          type="button"
          :title="t('panel_back_to_top')"
          @click="scrollPanelToTop"
        >
          ↑
        </button>
      </aside>
    </div>
    <div v-if="comfyRenderBuiltinTemplatesOverviewVisible" class="asset-preview-mask" @click.self="closeComfyBuiltinTemplateOverview">
      <section class="asset-preview-modal ai-template-overview-modal" role="dialog" aria-modal="true">
        <header class="asset-preview-header">
          <div>
            <div class="auth-dialog-kicker">{{ t('ai_render_builtin_templates') }}</div>
            <h2 class="auth-dialog-title">{{ t('ai_render_show_builtin_overview') }}</h2>
          </div>
          <div class="asset-preview-actions">
            <button class="btn-ghost" type="button" @click="closeComfyBuiltinTemplateOverview">
              {{ t('auth_close') }}
            </button>
          </div>
        </header>
        <div class="asset-preview-body ai-template-overview-body">
          <div class="ai-template-grid ai-template-grid-modal">
            <article
              v-for="item in comfyRenderBuiltinTemplates"
              :key="`builtin-overview-dialog-${item.key}`"
              class="ai-template-card builtin"
              :class="{
                featured: item.key === comfyRenderRecommendedBuiltinTemplate?.key,
                'is-selected': item.key === comfyRenderSelectedBuiltinTemplate?.key
              }"
            >
              <div class="ai-template-card-head">
                <div class="ai-template-card-copy">
                  <strong>{{ item.label }}</strong>
                  <div class="task-line">{{ item.hint }}</div>
                </div>
                <span class="point-badge enterprise-settings-chip">{{ item.workflowPreset }}</span>
              </div>
              <div class="ai-template-chip-row">
                <span
                  v-if="item.key === comfyRenderRecommendedBuiltinTemplate?.key"
                  class="point-badge enterprise-settings-chip"
                >
                  {{ t('ai_render_recommended_template_title') }}
                </span>
                <span
                  v-if="item.key === comfyRenderSelectedBuiltinTemplate?.key"
                  class="point-badge enterprise-settings-chip enterprise-settings-chip-muted"
                >
                  {{ t('ai_render_builtin_current_template') }}
                </span>
                <span class="point-badge enterprise-settings-chip enterprise-settings-chip-muted">
                  {{ item.promptStyleLabel }}
                </span>
              </div>
              <div v-if="item.recommendedSources.length" class="task-line">
                {{ t('ai_render_builtin_recommended_for') }}{{ item.recommendedSources.join(' / ') }}
              </div>
              <button class="btn-secondary full-width" type="button" :disabled="comfyRenderSubmitting" @click="applyBuiltinComfyTemplate(item.key)">
                {{ t('ai_render_apply_builtin') }}
              </button>
            </article>
          </div>
        </div>
      </section>
    </div>

    <div v-if="comfyRenderPreviewVisible" class="asset-preview-mask" @click.self="closeComfyRenderAssetPreview">
      <section class="asset-preview-modal" role="dialog" aria-modal="true">
        <header class="asset-preview-header">
          <div>
            <div class="auth-dialog-kicker">{{ t('ai_render_title') }}</div>
            <h2 class="auth-dialog-title">{{ comfyRenderPreviewTitle }}</h2>
          </div>
          <div class="asset-preview-actions">
            <a
              class="btn-secondary"
              :href="comfyRenderPreviewUrl"
              target="_blank"
              rel="noreferrer"
            >
              {{ t('ai_render_result_open_external') }}
            </a>
            <button class="btn-ghost" type="button" @click="closeComfyRenderAssetPreview">
              {{ t('auth_close') }}
            </button>
          </div>
        </header>
        <div class="asset-preview-body">
          <img :src="comfyRenderPreviewUrl" :alt="comfyRenderPreviewTitle" class="asset-preview-image" />
        </div>
      </section>
    </div>

    <GuideCenterDialog :ui="guideCenterDialogBindings" />

    <FloatingComparePanel :ui="floatingComparePanelBindings" />
    <div
      v-if="floatingToastVisible && floatingToastMessage"
      class="floating-toast"
      :class="`floating-toast-${floatingToastType}`"
      role="status"
      aria-live="polite"
    >
      {{ floatingToastMessage }}
    </div>
  </div>
</template>




