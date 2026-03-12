<script setup>
import './assets/agv-map.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LOCALE_TEXTS } from './locales'
import { DEFAULT_POINT_LIBRARY, DEFAULT_TASK_TEMPLATES } from './config/defaultData'
import { useDispatchScheduler } from './composables/useDispatchScheduler'
import { useLocalPersistence } from './composables/useLocalPersistence'
import { useTemplatePointActions } from './composables/useTemplatePointActions'
import { usePanelCompareUi } from './composables/usePanelCompareUi'
import { useDataExportActions } from './composables/useDataExportActions'
import { useMapViewport } from './composables/useMapViewport'
import { useTaskBuilderState } from './composables/useTaskBuilderState'
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
import { buildAStarPath, buildSimplePath } from './utils/pathPreview'
import { rowsToCsv } from './utils/csv'
import { downloadJsonFile } from './utils/fileDownload'
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

const GRID_COLS = 10
const GRID_ROWS = 8
const CELL_SIZE = 50
const AGV_SIZE = 30
const API_BASE = 'http://127.0.0.1:8000'
const CUSTOM_POINTS_STORAGE_KEY = 'agv_custom_points'
const MAP_DISPLAY_STORAGE_KEY = 'agv_map_display_settings'
const TASK_TEMPLATE_STORAGE_KEY = 'agv_task_templates'
const PANEL_SECTION_STORAGE_KEY = 'agv_panel_sections'
const PANEL_SUMMARY_MODE_STORAGE_KEY = 'agv_panel_summary_mode'
const TASK_QUEUE_VIEW_STORAGE_KEY = 'agv_task_queue_view'
const EXPERIMENT_RECORDS_STORAGE_KEY = 'agv_experiment_records'
const MAP_WIDTH = GRID_COLS * CELL_SIZE
const MAP_HEIGHT = GRID_ROWS * CELL_SIZE
const MINIMAP_WIDTH = 168
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

const agvs = ref([])
const localAgvs = ref([])
const tasks = ref([])
const blockedCells = ref([...DEFAULT_BLOCKED_CELLS])

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
const customPoints = ref([])
const customTaskTemplates = ref([])
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
const templateFileInputRef = ref(null)
const panelSearch = ref('')
const focusedPanelSection = ref('')
const panelSummaryMode = ref('compact')
const panelSections = ref({
  control: true,
  queue: true,
  templates: false,
  points: false,
  json: false,
  experiments: false
})
const queueGroupsCollapsed = ref(buildDefaultQueueGroupState())
const taskCardCollapsed = ref({})
const summaryZoomArmed = ref(false)

const selectedAgvId = ref(null)
const trackedManualTaskId = ref(null)
const manualDispatchStep = ref('idle')
const manualPreviewMinVisibleUntil = ref(0)
const startPoint = ref(null)
const endPoint = ref(null)
const showGuideCenter = ref(false)

const manualPathToStart = ref([])
const manualPathToEnd = ref([])
const autoPathToStart = ref([])
const autoPathToEnd = ref([])

const previewTaskId = ref(null)
const previewStart = ref(null)
const previewEnd = ref(null)
const previewPath = ref([])
const layoutRef = ref(null)
const mapViewportRef = ref(null)
const minimapRef = ref(null)
const panelRef = ref(null)
const compareEntryButtonRef = ref(null)
const controlSectionRef = ref(null)
const taskBuilderRef = ref(null)
const comparePanelRef = ref(null)
const queueSectionRef = ref(null)
const templatesSectionRef = ref(null)
const pointsSectionRef = ref(null)
const jsonSectionRef = ref(null)
const experimentsSectionRef = ref(null)
const panelWidth = ref(380)
const showPanelBackToTop = ref(false)
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
const mapZoom = ref(1)
const mapOffsetX = ref(0)
const mapOffsetY = ref(0)
const mapViewportWidth = ref(MAP_WIDTH)
const mapViewportHeight = ref(MAP_HEIGHT)
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
const obstaclePresets = ref([])
const selectedObstaclePreset = ref('default_shelves')
const appliedObstacleSceneKey = ref('default_shelves')
const obstacleLayoutStatus = ref('')
const obstacleLayoutStatusType = ref('info')
const obstacleLayoutFileInputRef = ref(null)
const compareDisplayMode = ref('panel')
const comparePanelExpanded = ref(false)
const showFloatingCompare = ref(false)
const compareFloatingOpacity = ref(0.92)
const compareFloatingX = ref(0)
const compareFloatingY = ref(140)

let timer = null
let clickTimer = null
let previewTimer = null
let taskBuilderJumpTimer = null
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

const messages = {
  zh: LOCALE_TEXTS.zh.messages,
  ja: LOCALE_TEXTS.ja.messages,
  en: LOCALE_TEXTS.en.messages
}

const t = key => messages[locale.value]?.[key] ?? messages.en[key] ?? key

const localeTexts = computed(() => LOCALE_TEXTS[locale.value] ?? LOCALE_TEXTS.en)

function fillTemplate(template, variables = {}) {
  return String(template ?? '').replace(/\{(\w+)\}/g, (_, key) => String(variables[key] ?? ''))
}

function apiPointText(pointType) {
  return (
    localeTexts.value.apiPointText?.[pointType] ??
    LOCALE_TEXTS.en.apiPointText?.[pointType] ??
    String(pointType ?? '')
  )
}

function apiAlgorithmText(algorithmName) {
  return (
    localeTexts.value.apiAlgorithmText?.[algorithmName] ??
    LOCALE_TEXTS.en.apiAlgorithmText?.[algorithmName] ??
    String(algorithmName ?? '')
  )
}

function localizeApiErrorDetail(detail, fallbackMessage = '') {
  const fallback = fallbackMessage || ''

  if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.error_code) {
    const template =
      localeTexts.value.apiErrorText?.[detail.error_code] ??
      LOCALE_TEXTS.en.apiErrorText?.[detail.error_code] ??
      fallback

    return fillTemplate(template, {
      stage: detail.stage_index ?? '',
      point: apiPointText(detail.point_type),
      algorithm: apiAlgorithmText(detail.algorithm)
    })
  }

  if (typeof detail === 'string') {
    const sentinel = localizeDispatchReason(detail)
    if (sentinel) return sentinel

    const legacyMatches = [
      [/^Task coordinates are required$/i, 'task_coordinates_required'],
      [/^Task not found$/i, 'task_not_found'],
      [/^Task is not blocked$/i, 'task_not_blocked'],
      [/^Blocked task retry only supports A\*$/i, 'blocked_retry_requires_astar'],
      [/^No idle AGV$/i, 'no_idle_agv'],
      [/^No pending tasks$/i, 'no_pending_tasks'],
      [/^No reachable tasks$/i, 'no_reachable_tasks'],
      [/^Task route unreachable with current algorithm$/i, 'task_route_unreachable'],
      [/^Preset not found$/i, 'preset_not_found']
    ]

    for (const [pattern, errorCode] of legacyMatches) {
      if (pattern.test(detail)) {
        return (
          localeTexts.value.apiErrorText?.[errorCode] ??
          LOCALE_TEXTS.en.apiErrorText?.[errorCode] ??
          fallback
        )
      }
    }

    const startUnreachableMatch = detail.match(
      /^No idle AGV can reach the task start with algorithm (simple|astar)$/i
    )
    if (startUnreachableMatch) {
      const algorithmName = startUnreachableMatch[1].toLowerCase()
      return fillTemplate(
        localeTexts.value.apiErrorText?.task_start_unreachable ??
          LOCALE_TEXTS.en.apiErrorText.task_start_unreachable,
        { algorithm: apiAlgorithmText(algorithmName) }
      )
    }

    return detail
  }

  return fallback
}

function localizeDispatchReason(reason) {
  if (!reason || typeof reason !== 'string') return ''

  if (
    /自动调度队列已暂停/.test(reason) ||
    /Auto dispatch queue is paused while manual dispatch mode is active/i.test(reason) ||
    /手動モード.*自動調度キュー/.test(reason)
  ) {
    if (locale.value === 'ja') return 'タスクは自動調度キューで割当待ちです（手動モードでも継続）。'
    if (locale.value === 'zh') return '任务正在自动调度队列中等待分配（手动模式不会暂停自动调度）。'
    return 'The task is waiting in the auto dispatch queue (manual mode does not pause auto scheduling).'
  }

  if (reason === 'cell_occupied_waiting') {
    if (locale.value === 'ja') return '前方セルがほかの AGV に占有されているため、その場で待機しています。'
    if (locale.value === 'zh') return '前方格子正被其他 AGV 占用，当前任务正在原地等待通行。'
    return 'The next cell is occupied by another AGV. Waiting in place for the path to clear.'
  }

  const directReason =
    localeTexts.value.dispatchReasonText?.[reason] ??
    LOCALE_TEXTS.en.dispatchReasonText?.[reason] ??
    ''
  if (directReason) return directReason

  const [errorCode, rawAlgorithm] = reason.split(':')
  if (!rawAlgorithm) return ''

  if (!['task_start_unreachable', 'task_route_unreachable', 'retry_waiting_for_idle_agv', 'retry_waiting_for_bound_agv'].includes(errorCode)) {
    return ''
  }

  const template =
    localeTexts.value.apiErrorText?.[errorCode] ??
    LOCALE_TEXTS.en.apiErrorText?.[errorCode] ??
    ''

  return fillTemplate(template, {
    algorithm: apiAlgorithmText(rawAlgorithm.toLowerCase())
  })
}

function createApiError(payload, fallbackMessage = '') {
  return new Error(localizeApiErrorDetail(payload?.detail, fallbackMessage))
}

const selectedAgv = computed(() => {
  if (!selectedAgvId.value) return null
  return displayAgvs.value.find(agv => agv.id === selectedAgvId.value) ?? null
})
const selectedBackendAgv = computed(() => {
  if (!selectedAgv.value || selectedAgv.value.source !== 'backend') return null
  return selectedAgv.value
})

const displayAgvs = computed(() => {
  const backendAgvs = agvs.value.map(agv => ({ ...agv, source: 'backend' }))
  return [...backendAgvs, ...localAgvs.value]
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
  return Boolean(selectedBackendAgv.value && selectedBackendAgv.value.status === 'idle')
})
const filteredFaultEvents = computed(() => {
  if (faultEventFilter.value === 'all') return faultEvents.value
  return faultEvents.value.filter(event => event.status === faultEventFilter.value)
})

const toSvgPoints = (points, cellSize = CELL_SIZE) =>
  points
    .map(point => {
      const cx = point.x * cellSize + cellSize / 2
      const cy = point.y * cellSize + cellSize / 2
      return `${cx},${cy}`
    })
    .join(' ')

const toArrowSegments = (points, cellSize = CELL_SIZE) => {
  if (points.length < 2) return []

  const segments = []
  let segmentStartIndex = 0
  let direction = {
    dx: points[1].x - points[0].x,
    dy: points[1].y - points[0].y
  }

  for (let index = 2; index < points.length; index += 1) {
    const nextDirection = {
      dx: points[index].x - points[index - 1].x,
      dy: points[index].y - points[index - 1].y
    }

    if (nextDirection.dx !== direction.dx || nextDirection.dy !== direction.dy) {
      segments.push({
        start: points[segmentStartIndex],
        end: points[index - 1],
        direction
      })
      segmentStartIndex = index - 1
      direction = nextDirection
    }
  }

  segments.push({
    start: points[segmentStartIndex],
    end: points.at(-1),
    direction
  })

  return segments
    .map((segment, index) => {
      const startX = segment.start.x * cellSize + cellSize / 2
      const startY = segment.start.y * cellSize + cellSize / 2
      const endX = segment.end.x * cellSize + cellSize / 2
      const endY = segment.end.y * cellSize + cellSize / 2
      const distance = Math.hypot(endX - startX, endY - startY)

      if (distance === 0) return null

      const unitX = (endX - startX) / distance
      const unitY = (endY - startY) / distance
      const centerX = (startX + endX) / 2
      const centerY = (startY + endY) / 2
      const arrowLength = Math.min(distance, cellSize * 1.15)

      return {
        id: `${index}-${segment.start.x}-${segment.start.y}-${segment.end.x}-${segment.end.y}`,
        x1: centerX - unitX * (arrowLength / 2),
        y1: centerY - unitY * (arrowLength / 2),
        x2: centerX + unitX * (arrowLength / 2),
        y2: centerY + unitY * (arrowLength / 2)
      }
    })
    .filter(Boolean)
}

const manualPathToStartPoints = computed(() => toSvgPoints(manualPathToStart.value))
const manualPathToEndPoints = computed(() => toSvgPoints(manualPathToEnd.value))
const autoPathToStartPoints = computed(() => toSvgPoints(autoPathToStart.value))
const autoPathToEndPoints = computed(() => toSvgPoints(autoPathToEnd.value))
const previewPathPoints = computed(() => toSvgPoints(previewPath.value))
const manualPathToStartArrows = computed(() => toArrowSegments(manualPathToStart.value))
const manualPathToEndArrows = computed(() => toArrowSegments(manualPathToEnd.value))
const autoPathToStartArrows = computed(() => toArrowSegments(autoPathToStart.value))
const autoPathToEndArrows = computed(() => toArrowSegments(autoPathToEnd.value))
const previewPathArrows = computed(() => toArrowSegments(previewPath.value))
const isCompactLayout = computed(() => windowWidth.value <= 960)
const shouldShowAutoPath = computed(() => dispatchMode.value === 'auto' && showAutoPath.value)
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
        gridTemplateColumns: `minmax(0, 1fr) 10px ${panelWidth.value}px`
      }
)
const mapStageStyle = computed(() => ({
  width: `${MAP_WIDTH}px`,
  height: `${MAP_HEIGHT}px`,
  transform: `translate(${mapOffsetX.value}px, ${mapOffsetY.value}px) scale(${mapZoom.value})`
}))
const mapZoomLabel = computed(() => `${Math.round(mapZoom.value * 100)}%`)
const minimapScale = computed(() => MINIMAP_WIDTH / MAP_WIDTH)
const minimapHeight = computed(() => MAP_HEIGHT * minimapScale.value)
const minimapCellSize = computed(() => CELL_SIZE * minimapScale.value)
const blockedCellSet = computed(
  () => new Set(blockedCells.value.map(cell => `${cell.x},${cell.y}`))
)
const occupiedCellSet = computed(() => {
  const keys = new Set()
  for (const agv of [...agvs.value, ...localAgvs.value]) {
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
const selectedObstaclePresetInfo = computed(
  () => obstaclePresets.value.find(preset => preset.key === selectedObstaclePreset.value) ?? null
)
const appliedObstaclePresetInfo = computed(
  () => obstaclePresets.value.find(preset => preset.key === appliedObstacleSceneKey.value) ?? null
)
const syncedBlockedCellSet = computed(
  () => new Set(syncedBlockedCells.value.map(cell => `${cell.x},${cell.y}`))
)
const obstacleLayoutDirty = computed(() => {
  if (blockedCellCount.value !== syncedBlockedCells.value.length) return true
  for (const key of blockedCellSet.value) {
    if (!syncedBlockedCellSet.value.has(key)) return true
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
const minimapPreviewPathPoints = computed(() => toSvgPoints(previewPath.value, minimapCellSize.value))
function isFinitePoint(point) {
  return Number.isFinite(Number(point?.x)) && Number.isFinite(Number(point?.y))
}

function taskStageWaypoints(task) {
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

function taskCurrentStageIndex(task) {
  const stages = Array.isArray(task?.stages) ? task.stages : []
  if (stages.length === 0) return 0
  const idx = Number(task?.current_stage_index ?? 0)
  if (!Number.isFinite(idx)) return 0
  return clampValue(Math.floor(idx), 0, stages.length - 1)
}

function taskRemainingWaypoints(task) {
  const stages = Array.isArray(task?.stages) ? task.stages : []
  if (stages.length === 0) return []

  const stageIndex = taskCurrentStageIndex(task)
  const currentStage = stages[stageIndex]
  const points = []

  if (isFinitePoint({ x: currentStage?.start_x, y: currentStage?.start_y })) {
    points.push({ x: Number(currentStage.start_x), y: Number(currentStage.start_y) })
  }

  for (let index = stageIndex; index < stages.length; index += 1) {
    const stage = stages[index]
    if (isFinitePoint({ x: stage?.end_x, y: stage?.end_y })) {
      points.push({ x: Number(stage.end_x), y: Number(stage.end_y) })
    }
  }

  return points
}

function taskChainMidPoints(task) {
  const waypoints = taskRemainingWaypoints(task)
  if (waypoints.length <= 2) return []
  return waypoints.slice(1, -1).map((point, index) => ({
    ...point,
    order: index + 1
  }))
}

function resolveTaskOverallEndMarker(task) {
  const waypoints = taskStageWaypoints(task)
  if (waypoints.length > 0) return waypoints.at(-1)
  if (
    Number.isFinite(Number(task?.overall_end_x)) &&
    Number.isFinite(Number(task?.overall_end_y))
  ) {
    return {
      x: Number(task.overall_end_x),
      y: Number(task.overall_end_y)
    }
  }
  return resolveTaskEndMarker(task)
}

const manualChainRoutePoints = computed(() => {
  const task = manualDisplayTask.value
  if (!task || Number(task.total_stages ?? 1) <= 1) return ''
  return toSvgPoints(taskRemainingWaypoints(task))
})

const autoChainRoutePoints = computed(() => {
  if (!shouldShowAutoPath.value) return ''
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
  if (!shouldShowAutoPath.value) return ''
  const task = autoDisplayTask.value
  if (!task || Number(task.total_stages ?? 1) <= 1) return ''
  return toSvgPoints(taskRemainingWaypoints(task), minimapCellSize.value)
})
const minimapViewportStyle = computed(() => {
  const scale = minimapScale.value
  const visibleWidth = Math.min(MAP_WIDTH, mapViewportWidth.value / mapZoom.value)
  const visibleHeight = Math.min(MAP_HEIGHT, mapViewportHeight.value / mapZoom.value)
  const visibleX = clampValue(-mapOffsetX.value / mapZoom.value, 0, MAP_WIDTH - visibleWidth)
  const visibleY = clampValue(-mapOffsetY.value / mapZoom.value, 0, MAP_HEIGHT - visibleHeight)

  return {
    left: `${visibleX * scale}px`,
    top: `${visibleY * scale}px`,
    width: `${visibleWidth * scale}px`,
    height: `${visibleHeight * scale}px`
  }
})
function resolveTaskStartMarker(task) {
  if (!task) return null
  const stage = currentTaskStage(task)
  return stage?.path_to_start?.at(-1) ?? stage?.path_to_end?.[0] ?? { x: stage?.start_x ?? task.start_x, y: stage?.start_y ?? task.start_y }
}

function resolveTaskEndMarker(task) {
  if (!task) return null
  const stage = currentTaskStage(task)
  return stage?.path_to_end?.at(-1) ?? { x: stage?.end_x ?? task.end_x, y: stage?.end_y ?? task.end_y }
}

function taskDispatchOrigin(task) {
  if (task?.dispatch_origin_x !== null && task?.dispatch_origin_x !== undefined && task?.dispatch_origin_y !== null && task?.dispatch_origin_y !== undefined) {
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

const autoDisplayTask = computed(() => findLatestActiveTask('auto'))
const manualDisplayTask = computed(() => {
  if (trackedManualTaskId.value) {
    const trackedTask = tasks.value.find(task => task.id === trackedManualTaskId.value)
    if (trackedTask) return trackedTask
  }
  return findLatestActiveTask('manual')
})

const manualDisplayStartMarker = computed(() => {
  if (trackedManualTaskId.value && manualDisplayTask.value) {
    const task = manualDisplayTask.value
    if (Number(task.total_stages ?? 1) > 1) {
      return resolveTaskStartMarker(task)
    }
    return resolveTaskStartMarker(task)
  }
  return startPoint.value ?? manualPathToStart.value.at(-1) ?? manualPathToEnd.value[0] ?? null
})
const manualDisplayEndMarker = computed(() => {
  if (trackedManualTaskId.value && manualDisplayTask.value) {
    const task = manualDisplayTask.value
    if (Number(task.total_stages ?? 1) > 1) {
      return resolveTaskOverallEndMarker(task)
    }
    return resolveTaskEndMarker(task)
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
  if (!shouldShowAutoPath.value) return null
  const task = autoDisplayTask.value
  if (task && Number(task.total_stages ?? 1) > 1) {
    return resolveTaskStartMarker(task)
  }
  return resolveTaskStartMarker(task) ?? autoPathToStart.value.at(-1) ?? autoPathToEnd.value[0] ?? null
})
const autoDisplayEndMarker = computed(() => {
  if (!shouldShowAutoPath.value) return null
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
  const points =
    dispatchMode.value === 'manual'
      ? incomplete
        ? picked
        : picked.slice(0, -1)
      : incomplete
        ? picked.slice(1)
        : picked.slice(1, -1)
  return points.map((point, index) => ({
    ...point,
    order: index + 1
  }))
})
const minimapManualStartMarker = computed(() => manualDisplayStartMarker.value)
const minimapManualEndMarker = computed(() => manualDisplayEndMarker.value)
const minimapAutoStartMarker = computed(() => autoDisplayStartMarker.value)
const minimapAutoEndMarker = computed(() => autoDisplayEndMarker.value)
const pointLibrary = computed(() => [...DEFAULT_POINT_LIBRARY, ...customPoints.value])
const taskTemplates = computed(() => [...DEFAULT_TASK_TEMPLATES, ...customTaskTemplates.value])
const templateJsonLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: 'テンプレート JSON',
      hint: 'カスタムテンプレートを JSON で保存したり、一括で取り込めます。',
      placeholder:
        '{ "templates": [{ "name": "入庫口 A から組立 1", "start_x": 0, "start_y": 0, "end_x": 6, "end_y": 2, "priority": 3 }] }',
      import: 'テンプレート取込',
      export: 'カスタムを出力',
      importFile: 'ファイル取込',
      downloadFile: 'JSON 保存',
      clear: 'JSON クリア',
      exportEmpty: '書き出すカスタムテンプレートがありません',
      exportOk: '書き出し件数',
      importOk: '取込件数',
      importFail: 'テンプレート JSON が不正か、取込に失敗しました',
      skipped: 'スキップ'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '模板 JSON',
      hint: '可导出自定义模板，也可从 JSON 批量导入。',
      placeholder:
        '{ "templates": [{ "name": "入库口 A 到装配台 1", "start_x": 0, "start_y": 0, "end_x": 6, "end_y": 2, "priority": 3 }] }',
      import: '导入模板',
      export: '导出自定义模板',
      importFile: '导入文件',
      downloadFile: '下载 JSON',
      clear: '清空模板 JSON',
      exportEmpty: '当前没有可导出的自定义模板',
      exportOk: '已导出数量',
      importOk: '已导入数量',
      importFail: '模板 JSON 格式无效或导入失败',
      skipped: '已跳过'
    }
  }

  return {
    title: 'Template JSON',
    hint: 'Export custom templates or import them in batches from JSON.',
    placeholder:
      '{ "templates": [{ "name": "Inbound A to Assembly 1", "start_x": 0, "start_y": 0, "end_x": 6, "end_y": 2, "priority": 3 }] }',
    import: 'Import Templates',
    export: 'Export Custom Templates',
    importFile: 'Import File',
    downloadFile: 'Download JSON',
    clear: 'Clear Template JSON',
    exportEmpty: 'There are no custom templates to export',
    exportOk: 'Exported',
    importOk: 'Imported',
    importFail: 'Template JSON is invalid or import failed',
    skipped: 'Skipped'
  }
})
const panelLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      sections: {
        control: '配車操作',
        queue: 'タスクキュー',
        templates: 'タスクテンプレート',
        points: '共通ポイント',
        json: 'JSON ツール',
        experiments: '実験記録'
      },
      expandAll: 'すべて展開',
      collapseAll: 'すべて折りたたむ',
      collapse: '折りたたむ',
      expand: '展開',
      currentMode: '現在モード',
      modeAuto: '自動配車',
      modeManual: '手動配車',
      modeAutoHint: '始点と終点を指定すると、システムが空き AGV を選んで実行します。',
      modeManualHint: '先に AGV を選び、その後に目的地を指定してその車両だけを移動させます。'
    }
  }

  if (locale.value === 'zh') {
    return {
      sections: {
        control: '调度控制',
        queue: '任务队列',
        templates: '任务模板',
        points: '常用点位',
        json: 'JSON 工具',
        experiments: '实验记录'
      },
      expandAll: '全部展开',
      collapseAll: '全部收起',
      collapse: '收起',
      expand: '展开',
      currentMode: '当前模式',
      modeAuto: '自动调度',
      modeManual: '手动调车',
      modeAutoHint: '设置起点和终点后，系统会自动选择空闲 AGV 执行任务。',
      modeManualHint: '先选择 AGV，再指定目标位置，只调度这台车。'
    }
  }

  return {
    sections: {
      control: 'Dispatch Control',
      queue: 'Task Queue',
      templates: 'Task Templates',
      points: 'Common Points',
      json: 'JSON Tools',
      experiments: 'Experiment Records'
    },
    expandAll: 'Expand All',
    collapseAll: 'Collapse All',
    collapse: 'Collapse',
    expand: 'Expand',
    currentMode: 'Current Mode',
    modeAuto: 'Auto Dispatch',
    modeManual: 'Manual Relocation',
    modeAutoHint: 'After you set start and end points, the system selects an idle AGV automatically.',
    modeManualHint: 'Select an AGV first, then choose a target point to move only that vehicle.'
  }
})
const currentDispatchModeLabel = computed(() =>
  dispatchMode.value === 'auto' ? panelLocale.value.modeAuto : panelLocale.value.modeManual
)
const currentDispatchModeHint = computed(() =>
  dispatchMode.value === 'auto' ? panelLocale.value.modeAutoHint : panelLocale.value.modeManualHint
)
const faultLocale = computed(() => localeTexts.value.fault ?? LOCALE_TEXTS.en.fault)
const panelSearchLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      placeholder: 'パネル名・タスク・テンプレート・ポイントを検索',
      clear: '検索クリア',
      empty: '一致するセクションや項目はありません',
      hits: '件一致'
    }
  }

  if (locale.value === 'zh') {
    return {
      placeholder: '搜索面板、任务、模板或点位',
      clear: '清空搜索',
      empty: '没有匹配的面板或条目',
      hits: '项匹配'
    }
  }

  return {
    placeholder: 'Search panels, tasks, templates, or points',
    clear: 'Clear Search',
    empty: 'No matching sections or items',
    hits: 'matches'
  }
})
const panelSummaryLocale = computed(() => localeTexts.value.panelSummary ?? LOCALE_TEXTS.en.panelSummary)
const settingsLocale = computed(() => localeTexts.value.settings ?? LOCALE_TEXTS.en.settings)
const guideCenterLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      open: '使い方',
      title: '操作ガイド',
      close: '閉じる',
      modeTitle: 'モード説明',
      modeAutoTitle: '自動配車',
      modeManualTitle: '手動配車',
      shortcutsTitle: 'ショートカット',
      shortcutCancel: '地図で右クリック / F: AGV 選択を解除',
      shortcutAlgorithm: 'R: simple / A* を切替',
      shortcutContext: '地図で右クリック: 段階選点のキャンセル',
      workflowTitle: '基本フロー',
      workflowAuto: t('dispatch_help_auto'),
      workflowManual: t('dispatch_help_manual'),
      workflowForm: t('dispatch_help_form')
    }
  }

  if (locale.value === 'zh') {
    return {
      open: '使用说明',
      title: '操作说明中心',
      close: '关闭',
      modeTitle: '模式说明',
      modeAutoTitle: '自动调度',
      modeManualTitle: '手动调车',
      shortcutsTitle: '快捷键',
      shortcutCancel: '地图右键 / F：取消 AGV 选中',
      shortcutAlgorithm: 'R：切换 simple / A*',
      shortcutContext: '地图右键：多段选点时可取消当前选点流程',
      workflowTitle: '基础流程',
      workflowAuto: t('dispatch_help_auto'),
      workflowManual: t('dispatch_help_manual'),
      workflowForm: t('dispatch_help_form')
    }
  }

  return {
    open: 'Guide',
    title: 'Operation Guide',
    close: 'Close',
    modeTitle: 'Mode Guide',
    modeAutoTitle: 'Auto Dispatch',
    modeManualTitle: 'Manual Dispatch',
    shortcutsTitle: 'Shortcuts',
    shortcutCancel: 'Right click on map / F: Clear AGV selection',
    shortcutAlgorithm: 'R: Toggle simple / A*',
    shortcutContext: 'Right click on map: cancel stage point-picking',
    workflowTitle: 'Basic Workflow',
    workflowAuto: t('dispatch_help_auto'),
    workflowManual: t('dispatch_help_manual'),
    workflowForm: t('dispatch_help_form')
  }
})
const toolbarGuideHintText = computed(() => {
  if (locale.value === 'ja') return '操作説明は「使い方」をご確認ください。'
  if (locale.value === 'zh') return '操作说明请见“说明中心”。'
  return 'See "Guide" for operation instructions.'
})
const taskChainLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: '段階タスク',
      hint: 'A -> B -> C のような連続工程を 1 件のタスクとして順番に実行します。',
      stage: '段階',
      stageLabel: '段階名',
      stageLabelPlaceholder: '例：組立工程',
      addStage: '段階追加',
      removeStage: '削除',
      resetStages: '段階を初期化',
      createTask: '段階タスクを作成',
      progress: '進行',
      currentRoute: '現在段階',
      overallRoute: '全体経路',
      priorityHint: '優先度は上の共通設定を使用します。',
      saveTemplate: '現在の段階タスクをテンプレート保存',
      stageCount: '段階数',
      loadedHint: '段階テンプレートを読み込みました。下の段階タスク作成ボタンを使ってください。'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '阶段任务',
      hint: '用于 A -> B -> C 这类连续流程，同一任务会按阶段顺序连续执行。',
      stage: '阶段',
      stageLabel: '阶段名',
      stageLabelPlaceholder: '例如：装配工序',
      addStage: '新增阶段',
      removeStage: '删除',
      resetStages: '重置阶段',
      createTask: '创建阶段任务',
      progress: '进度',
      currentRoute: '当前阶段',
      overallRoute: '总路线',
      priorityHint: '优先级使用上方公共设置。',
      saveTemplate: '保存当前阶段任务为模板',
      stageCount: '阶段数',
      loadedHint: '已载入阶段模板，请使用下方阶段任务按钮创建。'
    }
  }

  return {
    title: 'Stage Task',
    hint: 'Use one task to execute linked stages such as A -> B -> C in order.',
    stage: 'Stage',
    stageLabel: 'Stage Name',
    stageLabelPlaceholder: 'e.g. Assembly',
    addStage: 'Add Stage',
    removeStage: 'Remove',
    resetStages: 'Reset Stages',
    createTask: 'Create Stage Task',
    progress: 'Progress',
    currentRoute: 'Current Stage',
    overallRoute: 'Overall Route',
    priorityHint: 'Priority uses the shared control above.',
    saveTemplate: 'Save Stage Task as Template',
    stageCount: 'Stages',
    loadedHint: 'Stage template loaded. Use the stage task button below to create it.'
  }
})
const taskBuilderLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: 'タスク作成',
      single: '単一タスク',
      chain: '段階タスク',
      singleCompact: '単段',
      chainCompact: '多段',
      switchLabel: '切替',
      singleHint: 'A -> B の単一搬送タスクを作成します。',
      jumpAction: '作成欄へ移動',
      jumpHint: '読み込み後、右下の黄色ボタンから移動できます。ダブルクリックなら直接移動します。',
      loadedSingle: '単一タスクのフォームに読み込みました。',
      loadedChain: '段階タスクのフォームに読み込みました。'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '任务创建',
      single: '单段任务',
      chain: '阶段任务',
      singleCompact: '单段',
      chainCompact: '多段',
      switchLabel: '切换',
      singleHint: '用于创建 A -> B 的单段搬运任务。',
      jumpAction: '跳转到任务创建',
      jumpHint: '载入后可点击右下角黄色按钮跳转，双击可直接跳转。',
      loadedSingle: '已载入到单段任务表单。',
      loadedChain: '已载入到阶段任务表单。'
    }
  }

  return {
    title: 'Task Builder',
    single: 'Single',
    chain: 'Stages',
    singleCompact: 'Single',
    chainCompact: 'Multi',
    switchLabel: 'Mode',
    singleHint: 'Create a single A -> B transport task.',
    jumpAction: 'Jump to Builder',
    jumpHint: 'Use the yellow button at the lower-right after loading, or double-click to jump directly.',
    loadedSingle: 'Loaded into the single-task form.',
    loadedChain: 'Loaded into the stage-task form.'
  }
})
const taskJsonLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      singleExample: '単一サンプル',
      chainExample: '段階サンプル',
      singleLoaded: '単一タスク JSON サンプルを入力しました。',
      chainLoaded: '段階タスク JSON サンプルを入力しました。'
    }
  }

  if (locale.value === 'zh') {
    return {
      singleExample: '填入单段示例',
      chainExample: '填入阶段示例',
      singleLoaded: '已填入单段任务 JSON 示例。',
      chainLoaded: '已填入阶段任务 JSON 示例。'
    }
  }

  return {
    singleExample: 'Single Example',
    chainExample: 'Stage Example',
    singleLoaded: 'Loaded a single-task JSON example.',
    chainLoaded: 'Loaded a stage-task JSON example.'
  }
})
const taskJsonExampleFileLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      singleDownload: '単一サンプルを保存',
      chainDownload: '段階サンプルを保存',
      singleDownloaded: '単一タスク JSON サンプルを保存しました。',
      chainDownloaded: '段階タスク JSON サンプルを保存しました。'
    }
  }

  if (locale.value === 'zh') {
    return {
      singleDownload: '下载单段示例',
      chainDownload: '下载阶段示例',
      singleDownloaded: '已下载单段任务 JSON 示例。',
      chainDownloaded: '已下载阶段任务 JSON 示例。'
    }
  }

  return {
    singleDownload: 'Download Single Sample',
    chainDownload: 'Download Stage Sample',
    singleDownloaded: 'Downloaded a single-task JSON sample.',
    chainDownloaded: 'Downloaded a stage-task JSON sample.'
  }
})
const taskChainMapPickUiLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      start: '選点',
      cancel: '取消',
      stageCount: '予定',
      idle: (required, stages) => `予定 ${stages} 段 / 必要 ${required} 点。先に「選点」を押してから地図をクリックしてください。`,
      status: (picked, required, stages) =>
        picked >= required
          ? `${required} 点を選択済みです。確認後に ${stages} 段タスクを作成します。`
          : `${picked}/${required} 点を選択済みです。続けて選点してください。`
    }
  }

  if (locale.value === 'zh') {
    return {
      start: '选点',
      cancel: '取消',
      stageCount: '预选',
      idle: (required, stages) => `预选 ${stages} 段 / 需 ${required} 点，先点击“选点”，再到地图上选点。`,
      status: (picked, required, stages) =>
        picked >= required
          ? `已选满 ${required} 点，确认后创建 ${stages} 段任务。`
          : `已选 ${picked}/${required} 点，请继续选点。`
    }
  }

  return {
    start: 'Pick',
    cancel: 'Cancel',
    stageCount: 'Plan',
    idle: (required, stages) => `Plan ${stages} stages / ${required} points. Click "Pick" first, then select points on the map.`,
    status: (picked, required, stages) =>
      picked >= required
        ? `${required} points selected. Confirm to create ${stages} stages.`
        : `${picked}/${required} points selected. Keep picking.`
  }
})
const queueViewLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      collapseCards: 'カードを折りたたむ',
      expandCards: 'カードを展開'
    }
  }

  if (locale.value === 'zh') {
    return {
      collapseCards: '折叠卡片',
      expandCards: '展开卡片'
    }
  }

  return {
    collapseCards: 'Fold Cards',
    expandCards: 'Expand Cards'
  }
})
const experimentLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: '実験記録',
      hint: '現在の比較結果を保存し、JSON / CSV として書き出せます。',
      saveCurrent: '現在結果を保存',
      exportCurrentJson: '現在結果 JSON',
      exportCurrentCsv: '現在結果 CSV',
      exportAllJson: '全記録 JSON',
      exportAllCsv: '全記録 CSV',
      clearAll: '全削除',
      empty: '保存済みの実験記録はありません',
      noCompare: '先にアルゴリズム比較を実行してください。',
      savedOk: '実験記録を保存しました。',
      deletedOk: '実験記録を削除しました。',
      clearedOk: '実験記録をすべて削除しました。',
      exportEmpty: '書き出す実験記録がありません。',
      exportCurrentJsonOk: '現在結果の JSON を書き出しました。',
      exportCurrentCsvOk: '現在結果の CSV を書き出しました。',
      exportAllJsonOk: '全実験記録の JSON を書き出しました。',
      exportAllCsvOk: '全実験記録の CSV を書き出しました。',
      route: '経路',
      scene: 'シーン',
      obstacles: '障害セル',
      savedAt: '保存時刻',
      currentAlgorithm: '現在アルゴリズム',
      recommendedAlgorithm: '推奨アルゴリズム',
      delete: '削除',
      recordPrefix: '記録'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '实验记录',
      hint: '可保存当前算法对比结果，并导出为 JSON / CSV。',
      saveCurrent: '保存当前结果',
      exportCurrentJson: '导出当前 JSON',
      exportCurrentCsv: '导出当前 CSV',
      exportAllJson: '导出全部 JSON',
      exportAllCsv: '导出全部 CSV',
      clearAll: '清空记录',
      empty: '当前没有已保存的实验记录',
      noCompare: '请先执行算法对比。',
      savedOk: '实验记录已保存。',
      deletedOk: '实验记录已删除。',
      clearedOk: '实验记录已清空。',
      exportEmpty: '当前没有可导出的实验记录。',
      exportCurrentJsonOk: '已导出当前结果 JSON。',
      exportCurrentCsvOk: '已导出当前结果 CSV。',
      exportAllJsonOk: '已导出全部实验记录 JSON。',
      exportAllCsvOk: '已导出全部实验记录 CSV。',
      route: '路线',
      scene: '场景',
      obstacles: '障碍格',
      savedAt: '保存时间',
      currentAlgorithm: '当前算法',
      recommendedAlgorithm: '推荐算法',
      delete: '删除',
      recordPrefix: '记录'
    }
  }

  return {
    title: 'Experiment Records',
    hint: 'Save the current compare result and export it as JSON / CSV.',
    saveCurrent: 'Save Current Result',
    exportCurrentJson: 'Export Current JSON',
    exportCurrentCsv: 'Export Current CSV',
    exportAllJson: 'Export All JSON',
    exportAllCsv: 'Export All CSV',
    clearAll: 'Clear Records',
    empty: 'There are no saved experiment records.',
    noCompare: 'Run an algorithm comparison first.',
    savedOk: 'Experiment record saved.',
    deletedOk: 'Experiment record deleted.',
    clearedOk: 'Experiment records cleared.',
    exportEmpty: 'There are no experiment records to export.',
    exportCurrentJsonOk: 'Exported the current result JSON.',
    exportCurrentCsvOk: 'Exported the current result CSV.',
    exportAllJsonOk: 'Exported all experiment records as JSON.',
    exportAllCsvOk: 'Exported all experiment records as CSV.',
    route: 'Route',
    scene: 'Scene',
    obstacles: 'Blocked Cells',
    savedAt: 'Saved At',
    currentAlgorithm: 'Current Algorithm',
    recommendedAlgorithm: 'Recommended Algorithm',
    delete: 'Delete',
    recordPrefix: 'Record'
  }
})
const currentTaskBuilderModeCompactLabel = computed(() =>
  taskBuilderMode.value === 'chain' ? taskBuilderLocale.value.chainCompact : taskBuilderLocale.value.singleCompact
)
const taskChainStageCount = computed(() => Math.max(taskChainStages.value.length, 2))
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

async function handleManualScheduleFailure(createdTaskId, scheduleData) {
  await fetchTasks()
  const latestTask = tasks.value.find(task => task.id === createdTaskId)

  if (latestTask?.status === 'blocked') {
    window.alert(blockedTaskAlertText(latestTask))
    trackedManualTaskId.value = null
    manualDispatchStep.value = 'idle'
    clearManualDestination()
    return false
  }

  if (latestTask && ['assigned', 'running'].includes(latestTask.status)) {
    manualPathToStart.value = latestTask.path_to_start ?? []
    manualPathToEnd.value = latestTask.path_to_end ?? []
    trackedManualTaskId.value = latestTask.id
    startPoint.value = resolveTaskStartMarker(latestTask)
    endPoint.value = resolveTaskEndMarker(latestTask)
    manualDispatchStep.value = 'running'
    bumpManualPreviewMinVisible()
    await fetchAgvs()
    return true
  }

  if (latestTask?.status === 'pending') {
    trackedManualTaskId.value = latestTask.id
    startPoint.value = resolveTaskStartMarker(latestTask)
    endPoint.value = resolveTaskEndMarker(latestTask)
    manualDispatchStep.value = 'running'
    bumpManualPreviewMinVisible()
    window.alert(manualTaskQueuedText(latestTask))
    return true
  }

  window.alert(localizeApiErrorDetail(scheduleData?.detail, t('task_manual_unreachable')))
  trackedManualTaskId.value = null
  manualDispatchStep.value = 'idle'
  clearManualDestination()
  return false
}
const taskChainMapPickButtonText = computed(() =>
  taskChainMapPickActive.value ? taskChainMapPickUiLocale.value.cancel : taskChainMapPickUiLocale.value.start
)
const algorithmCompareLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: 'アルゴリズム比較',
      hintSingle: '現在の単一路線を simple と A* で比較します。',
      hintChain: '現在の段階タスクを simple と A* で比較します。',
      run: '現在の経路を比較',
      clear: '結果を消去',
      invalid: '比較するための有効な座標が必要です。',
      reachable: '到達可能',
      unreachable: '到達不可',
      total: '総距離',
      stages: '段階距離',
      failedStage: '失敗段階',
      recommended: '推奨',
      current: '現在',
      apply: '使用中',
      switchTo: '切替'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '算法对比',
      hintSingle: '对当前单段路线进行 simple 与 A* 对比。',
      hintChain: '对当前阶段任务进行 simple 与 A* 对比。',
      run: '对比当前路线',
      clear: '清空结果',
      invalid: '当前表单坐标无效，无法进行算法对比。',
      reachable: '可达',
      unreachable: '不可达',
      total: '总长度',
      stages: '阶段长度',
      failedStage: '失败阶段',
      recommended: '推荐',
      current: '当前',
      apply: '使用中',
      switchTo: '切换'
    }
  }

  return {
    title: 'Algorithm Compare',
    hintSingle: 'Compare the current single route with simple and A*.',
    hintChain: 'Compare the current staged task with simple and A*.',
    run: 'Compare Current Route',
    clear: 'Clear',
    invalid: 'Current form coordinates are invalid for comparison.',
    reachable: 'Reachable',
    unreachable: 'Blocked',
    total: 'Total Length',
    stages: 'Stage Lengths',
    failedStage: 'Failed Stage',
    recommended: 'Recommended',
    current: 'Current',
    apply: 'Using',
    switchTo: 'Switch'
  }
})
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
const areAllPanelSectionsExpanded = computed(() => Object.values(panelSections.value).every(Boolean))
const areAllPanelSectionsCollapsed = computed(() => Object.values(panelSections.value).every(value => !value))
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
    }
  ]

  for (const section of sections) {
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
    tasks: sortTasks(tasks.value.filter(task => task.status === group.key), group.key)
  }))
})

function buildDefaultQueueGroupState() {
  return {
    pending: false,
    blocked: false,
    assigned: false,
    running: false,
    finished: true
  }
}

function clampValue(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function pointStyle(point, cellSize = CELL_SIZE, size = 12) {
  return {
    left: `${point.x * cellSize + cellSize / 2 - size / 2}px`,
    top: `${point.y * cellSize + cellSize / 2 - size / 2}px`
  }
}

function blockedCellKey(x, y) {
  return `${x},${y}`
}

function isBlockedCell(x, y) {
  return blockedCellSet.value.has(blockedCellKey(x, y))
}

function sortTasks(list, status) {
  const copy = [...list]
  if (status === 'pending' || status === 'blocked') {
    return copy.sort((a, b) => b.priority - a.priority || a.id - b.id)
  }
  if (status === 'finished') {
    return copy.sort((a, b) => compareTime(b.finished_at, a.finished_at) || b.id - a.id)
  }
  return copy.sort((a, b) => compareTime(b.assigned_at, a.assigned_at) || b.priority - a.priority || a.id - b.id)
}

function compareTime(a, b) {
  const aTime = a ? Date.parse(a) : 0
  const bTime = b ? Date.parse(b) : 0
  return aTime - bTime
}

function statusColor(status) {
  const map = {
    idle: '#7f8c8d',
    running: '#2e7d32',
    fault: '#c62828',
    relocating: '#ef6c00',
    emergency_stop: '#7b1f2f'
  }
  return map[status] ?? '#333'
}

function statusText(status) {
  const localized = {
    zh: {
      emergency_stop: faultLocale.value.emergencyStopped
    },
    ja: {
      emergency_stop: faultLocale.value.emergencyStopped
    },
    en: {
      emergency_stop: faultLocale.value.emergencyStopped
    }
  }
  return localized[locale.value]?.[status] ?? t(`status_${status}`) ?? status
}

function compactStatusText(status) {
  const map = {
    zh: {
      idle: '空闲',
      running: '运行',
      fault: '故障',
      relocating: '就位',
      emergency_stop: '急停'
    },
    ja: {
      idle: '待機',
      running: '運行',
      fault: '故障',
      relocating: '移動',
      emergency_stop: '急停'
    },
    en: {
      idle: 'IDLE',
      running: 'RUN',
      fault: 'FAULT',
      relocating: 'MOVE',
      emergency_stop: 'STOP'
    }
  }

  return map[locale.value]?.[status] ?? statusText(status)
}

function taskStatusText(status) {
  return t(`task_${status}`) ?? status
}

function algorithmText(value) {
  return value === 'astar' ? t('algo_astar') : t('algo_simple')
}

function faultTypeText(value) {
  return faultLocale.value.faultTypes[value] ?? value
}

function faultSeverityText(value) {
  return faultLocale.value.severities[value] ?? value
}

function faultEventTypeText(value) {
  if (value === 'emergency_stop') return faultLocale.value.eventEmergency
  return faultLocale.value.eventFault
}

function faultEventStatusText(value) {
  return value === 'resolved' ? faultLocale.value.statusResolved : faultLocale.value.statusOpen
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

function dispatchModeText(value) {
  return value === 'manual' ? t('reason_manual') : t('reason_auto')
}

function formatTaskMeta(task) {
  if (isTaskChain(task)) {
    const start = overallTaskStart(task)
    const end = overallTaskEnd(task)
    return `${taskChainLocale.value.overallRoute}: (${start.x}, ${start.y}) -> (${end.x}, ${end.y})`
  }
  return `${t('task_start')} (${task.start_x}, ${task.start_y}) -> ${t('task_end')} (${task.end_x}, ${task.end_y})`
}

function formatTaskAgv(task) {
  return `${t('task_agv')}: ${task.agv_id ?? t('selected_none')}`
}

function formatTaskStageProgress(task) {
  if (!isTaskChain(task)) return ''
  return `${taskChainLocale.value.progress}: ${Number(task.current_stage_index ?? 0) + 1}/${task.total_stages ?? normalizeTaskStages(task).length}`
}

function formatTaskCurrentStage(task) {
  if (!isTaskChain(task)) return ''
  const stage = currentTaskStage(task)
  const label = stage.label ? ` ${stage.label}` : ''
  return `${taskChainLocale.value.currentRoute}${label}: (${stage.start_x}, ${stage.start_y}) -> (${stage.end_x}, ${stage.end_y})`
}

function formatTaskTime(task) {
  const values = [
    { label: t('time_created'), value: task.created_at },
    { label: t('time_assigned'), value: task.assigned_at },
    { label: t('time_started'), value: task.started_at },
    { label: t('time_finished'), value: task.finished_at }
  ].filter(item => item.value)

  if (values.length === 0) return ''
  return values.map(item => `${item.label}: ${item.value}`).join(' | ')
}

function formatTaskCompactSummary(task) {
  const start = isTaskChain(task) ? overallTaskStart(task) : { x: task.start_x, y: task.start_y }
  const end = isTaskChain(task) ? overallTaskEnd(task) : { x: task.end_x, y: task.end_y }
  const parts = [
    `(${start.x}, ${start.y}) -> (${end.x}, ${end.y})`,
    `${t('task_priority')} ${task.priority}`,
    taskStatusText(task.status)
  ]

  if (task.agv_id !== null && task.agv_id !== undefined) {
    parts.push(`AGV #${task.agv_id}`)
  }
  if (isTaskChain(task)) {
    parts.push(`${Number(task.current_stage_index ?? 0) + 1}/${task.total_stages ?? normalizeTaskStages(task).length}`)
  }

  return parts.join(' | ')
}

function formatDispatchReason(task) {
  if (task.status === 'pending' && task.dispatch_reason) {
    const localizedReason = localizeDispatchReason(task.dispatch_reason)
    if (localizedReason) return localizedReason
  }
  if (task.status === 'pending') {
    if (task.dispatch_mode === 'manual' && task.preferred_agv_id) {
      if (task.dispatch_algorithm && task.dispatch_reason?.startsWith('retry_waiting_for_bound_agv')) {
        if (locale.value === 'ja') return `指定 AGV #${task.preferred_agv_id} の空きを待っています。${algorithmText(task.dispatch_algorithm)} で再試行します。`
        if (locale.value === 'zh') return `任务已绑定 AGV #${task.preferred_agv_id}，当前正在等待该车辆空闲后按 ${algorithmText(task.dispatch_algorithm)} 重试。`
        return `Waiting for bound AGV #${task.preferred_agv_id} to become idle before retrying with ${algorithmText(task.dispatch_algorithm)}.`
      }
      if (locale.value === 'ja') return `手動派車タスクは指定 AGV #${task.preferred_agv_id} を待機中です。`
      if (locale.value === 'zh') return `该手动派车任务正在等待指定 AGV #${task.preferred_agv_id} 执行。`
      return `This manual dispatch task is waiting for bound AGV #${task.preferred_agv_id}.`
    }
    if (task.dispatch_mode === 'manual') {
      if (locale.value === 'ja') return '手動派車タスクは指定 AGV への割当を待機中です。'
      if (locale.value === 'zh') return '该手动派车任务正在等待指定车辆执行。'
      return 'This manual dispatch task is waiting for its assigned AGV.'
    }
    if (obstacleEditMode.value) {
      if (locale.value === 'ja') return '障害編集モード中のため、自動調度を一時停止しています。'
      if (locale.value === 'zh') return '当前处于障碍编辑模式，自动调度已暂停。'
      return 'Auto dispatch is paused while obstacle editing is active.'
    }
    if (obstacleLayoutDirty.value) {
      return obstacleSaveRequiredText()
    }
    if (task.dispatch_algorithm && !hasIdleAgv()) {
      if (locale.value === 'ja') return `${algorithmText(task.dispatch_algorithm)} で再調度待機中です。空き AGV を待っています。`
      if (locale.value === 'zh') return `任务将按 ${algorithmText(task.dispatch_algorithm)} 重试，当前正在等待空闲 AGV。`
      return `Waiting for an idle AGV to retry this task with ${algorithmText(task.dispatch_algorithm)}.`
    }
    if (!hasIdleAgv()) {
      if (agvs.value.some(agv => ['fault', 'emergency_stop'].includes(agv.status))) {
        if (locale.value === 'ja') return '使用可能な AGV がなく、故障または急停からの復帰を待っています。'
        if (locale.value === 'zh') return '当前没有可用 AGV，系统正在等待故障或急停中的车辆恢复。'
        return 'No AGV is currently available. Waiting for faulted or emergency-stopped AGVs to recover.'
      }
      return t('dispatch_waiting')
    }
    if (!task.dispatch_mode) {
      if (locale.value === 'ja') return '自動調度キューで待機中です（手動モードでも継続）。'
      if (locale.value === 'zh') return '任务正在自动调度队列中等待分配（手动模式不会暂停自动调度）。'
      return 'Waiting in the auto dispatch queue (manual mode does not pause auto scheduling).'
    }
  }
  if (task.status === 'blocked' && task.dispatch_reason) {
    return localizeDispatchReason(task.dispatch_reason) || task.dispatch_reason
  }
  if (task.status === 'blocked') {
    return t('dispatch_blocked')
  }

  const parts = []
  if (task.dispatch_mode) {
    parts.push(`${t('reason_mode')}: ${dispatchModeText(task.dispatch_mode)}`)
  }
  if (task.dispatch_distance !== null && task.dispatch_distance !== undefined) {
    parts.push(`${t('reason_distance')}: ${task.dispatch_distance}`)
  }
  if (task.dispatch_algorithm) {
    parts.push(`${t('reason_algorithm')}: ${algorithmText(task.dispatch_algorithm)}`)
  }
  if (task.agv_id !== null && task.agv_id !== undefined) {
    parts.push(`AGV #${task.agv_id}`)
  }
  if (isTaskChain(task)) {
    parts.push(`${Number(task.current_stage_index ?? 0) + 1}/${task.total_stages ?? normalizeTaskStages(task).length}`)
  }

  return parts.join(' | ')
}

function formatTaskAlgorithm(task) {
  if (!task?.dispatch_algorithm) return ''
  return `${t('algorithm')}: ${algorithmText(task.dispatch_algorithm)}`
}

function formatTaskPathStats(task) {
  const parts = []
  if (task.path_length_to_start !== null && task.path_length_to_start !== undefined) {
    if (locale.value === 'ja') {
      parts.push(`始点まで ${task.path_length_to_start}`)
    } else if (locale.value === 'zh') {
      parts.push(`到起点 ${task.path_length_to_start}`)
    } else {
      parts.push(`to start ${task.path_length_to_start}`)
    }
  }
  if (task.path_length_to_end !== null && task.path_length_to_end !== undefined) {
    if (locale.value === 'ja') {
      parts.push(`実行区間 ${task.path_length_to_end}`)
    } else if (locale.value === 'zh') {
      parts.push(`执行段 ${task.path_length_to_end}`)
    } else {
      parts.push(`run ${task.path_length_to_end}`)
    }
  }
  return parts.join(' | ')
}

function formatTaskInitialPoint(task) {
  if (task?.dispatch_mode !== 'manual') return ''
  const origin = taskDispatchOrigin(task)
  if (!origin) return ''
  if (locale.value === 'ja') {
    return `初期位置 (${origin.x},${origin.y})`
  }
  if (locale.value === 'zh') {
    return `初始点 (${origin.x},${origin.y})`
  }
  return `Initial (${origin.x},${origin.y})`
}

function blockedTaskAlertText(task) {
  return localizeDispatchReason(task?.dispatch_reason) || task?.dispatch_reason || t('task_blocked_alert')
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
    gridCols: GRID_COLS,
    gridRows: GRID_ROWS
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
  compareDisplayMode,
  compareFloatingOpacity,
  clampValue,
  normalizeCustomPoints: parsed =>
    normalizeStoredCustomPoints(parsed, {
      gridCols: GRID_COLS,
      gridRows: GRID_ROWS,
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

function toggleDispatchModeFromSummary() {
  dispatchMode.value = dispatchMode.value === 'auto' ? 'manual' : 'auto'
}

function buildTemplateExportPayload() {
  return buildTemplateExportPayloadRaw(customTaskTemplates.value, {
    normalizeStages: normalizeTemplateStages
  })
}

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
  importTaskTemplatesFromRaw,
  importTaskTemplatesFromJson,
  downloadTemplateJsonFile,
  triggerTemplateFileImport,
  handleTemplateFileChange
} = useTemplatePointActions({
  t,
  GRID_COLS,
  GRID_ROWS,
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
  templateFileInputRef,
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
  panelSections.value = {
    control: expanded,
    queue: expanded,
    templates: expanded,
    points: expanded,
    json: expanded
  }
}

function hasIdleAgv() {
  return agvs.value.some(agv => agv.status === 'idle')
}

function hasPendingTask() {
  return tasks.value.some(task => task.status === 'pending' || task.status === 'blocked')
}

function hasActiveTask() {
  return tasks.value.some(task => task.status === 'assigned' || task.status === 'running')
}

const { tryAutoSchedule, tryManualBoundSchedule, scheduleAutoIfReady } = useDispatchScheduler({
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
  hasIdleAgv,
  hasPendingTask,
  resolveTaskStartMarker,
  resolveTaskEndMarker,
  bumpManualPreviewMinVisible
})

function clearAutoPaths() {
  autoPathToStart.value = []
  autoPathToEnd.value = []
}

function clearAutoMarkers() {
  if (dispatchMode.value === 'auto') {
    startPoint.value = null
    endPoint.value = null
  }
}

function clearPreview() {
  if (previewTimer) {
    clearTimeout(previewTimer)
    previewTimer = null
  }
  previewTaskId.value = null
  previewStart.value = null
  previewEnd.value = null
  previewPath.value = []
}

function clearManualDestination() {
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
  if (selectedBackendAgv.value.status !== 'idle') {
    if (alertOnFailure) {
      if (locale.value === 'ja') {
        window.alert('手動派車では空き AGV のみ指定できます。')
      } else if (locale.value === 'zh') {
        window.alert('手动派车只能指定空闲 AGV。')
      } else {
        window.alert('Manual dispatch can only target idle AGVs.')
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
  setTaskChainStageCount,
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
  buildDefaultTaskChainStages,
  createTaskChainStage,
  getSelectedManualDispatchAgv,
  clearAutoMarkers
})

function syncManualDispatchBuilderState() {
  const agv = getSelectedManualDispatchAgv(false)
  if (!agv || trackedManualTaskId.value) return
}

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
    if (!shouldHoldManualPreview) {
      clearManualPaths()
    }
  }
}

function isCellOccupied(x, y) {
  return displayAgvs.value.some(agv => agv.x === x && agv.y === y)
}

const {
  syncPanelWidth,
  resetMapView,
  changeMapZoom,
  clampMapTransform,
  updateMapViewportMetrics,
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
    MAP_WIDTH,
    MAP_HEIGHT,
    MINIMAP_WIDTH,
    MIN_ZOOM,
    MAX_ZOOM,
    CELL_SIZE,
    GRID_COLS,
    GRID_ROWS
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

function buildPreviewPathByAlgorithm(sx, sy, ex, ey) {
  return algorithm.value === 'astar'
    ? buildAStarPath(sx, sy, ex, ey, GRID_COLS, GRID_ROWS, isBlockedCell)
    : buildSimplePath(sx, sy, ex, ey, isBlockedCell)
}

function blockedCellAlertText() {
  if (locale.value === 'ja') return '障害セルは始点・終点・中継点に設定できません。'
  if (locale.value === 'zh') return '障碍格不能作为起点、终点或中转点。'
  return 'Blocked cells cannot be used as start, end, or transfer points.'
}

function onAgvClick(agv, event) {
  event.stopPropagation()
  if (agv.source !== 'backend') return
  selectedAgvId.value = agv.id
  if (dispatchMode.value !== 'manual') return
  if (agv.status !== 'idle') return
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
    obstaclePaintMode = isBlockedCell(cell.x, cell.y) ? 'remove' : 'add'
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
    return
  }
  if (clickTimer) return
  const cell = getCellFromEvent(event)
  if (!cell) return
  const { x, y } = cell
  clickTimer = setTimeout(() => {
    clickTimer = null
    handleSingleClick(x, y)
  }, 220)
}

function toggleMapSettings() {
  showMapSettings.value = !showMapSettings.value
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
  if (obstacleEditMode.value) {
    toggleBlockedCellAt(x, y)
    return
  }

  if (isBlockedCell(x, y)) {
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
    startPoint.value = { x: agv.x, y: agv.y }
    endPoint.value = null
    manualPathToStart.value = []
    manualPathToEnd.value = []
    void confirmAndSchedule(x, y, agv.id)
    return
  }

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
  if (!ok) return
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
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }

  const isAutoMode = dispatchMode.value === 'auto'
  try {
    autoScheduleGuard.value = true
    const createRes = await fetch(`${API_BASE}/task/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_x: startPoint.value.x,
        start_y: startPoint.value.y,
        end_x: endPoint.value.x,
        end_y: endPoint.value.y,
        priority: taskPriority.value,
        ...(dispatchMode.value === 'manual' ? buildManualTaskCreateMeta(getSelectedManualDispatchAgv(false)) : {})
      })
    })
    const createData = await createRes.json()
    if (!createRes.ok) {
      throw createApiError(createData, 'Task create failed')
    }

    if (isAutoMode) {
      const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: createData.task.id,
          agv_id: null,
          algorithm: algorithm.value,
          grid_cols: GRID_COLS,
          grid_rows: GRID_ROWS
        })
      })
      const scheduleData = await scheduleRes.json()
      if (!scheduleRes.ok) {
        await fetchTasks()
        const latestTask = tasks.value.find(task => task.id === createData.task.id)
        if (latestTask?.status === 'blocked') {
          window.alert(blockedTaskAlertText(latestTask))
        } else {
          window.alert(localizeApiErrorDetail(scheduleData?.detail, t('task_manual_unreachable')))
        }
        clearAutoMarkers()
        return
      }

      autoPathToStart.value = scheduleData.path_to_start ?? []
      autoPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
      clearAutoMarkers()
      await Promise.all([fetchAgvs(), fetchTasks()])
      return
    }

    const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: createData.task.id,
        agv_id: agvId,
        algorithm: algorithm.value,
        grid_cols: GRID_COLS,
        grid_rows: GRID_ROWS
      })
    })
    const scheduleData = await scheduleRes.json()
    if (!scheduleRes.ok) {
      await handleManualScheduleFailure(createData.task.id, scheduleData)
      return
    }

    startPoint.value = resolveTaskStartMarker(scheduleData.task)
    endPoint.value = resolveTaskEndMarker(scheduleData.task)
    manualPathToStart.value = scheduleData.path_to_start ?? []
    manualPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []
    trackedManualTaskId.value = scheduleData.task.id
    bumpManualPreviewMinVisible()

    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Schedule error:', error)
    if (!isAutoMode) {
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
}

function onPanelScroll() {
  showPanelBackToTop.value = (panelRef.value?.scrollTop ?? 0) > 140
}

function scrollPanelToTop() {
  panelRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function onGlobalMouseMove(event) {
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
    }
    mapPanCandidate = false
    mapPanMoved = false
    isMapPanning.value = false
  }
}

async function deleteTask(task) {
  if (!['pending', 'blocked'].includes(task.status)) return
  const ok = window.confirm(t('confirm_delete_task'))
  if (!ok) return

  try {
    const res = await fetch(`${API_BASE}/task/${task.id}`, {
      method: 'DELETE'
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Delete failed')
    }
    if (previewTaskId.value === task.id) {
      clearPreview()
    }
    await fetchTasks()
  } catch (error) {
    console.error('Delete task error:', error)
  }
}

async function retryBlockedTaskWithAStar(task) {
  if (task.status !== 'blocked') return
  if (!(await ensureBlockedCellsSynced())) {
    window.alert(obstacleSaveRequiredText())
    return
  }

  try {
    const res = await fetch(`${API_BASE}/schedule/retry_blocked/${task.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        algorithm: 'astar',
        grid_cols: GRID_COLS,
        grid_rows: GRID_ROWS
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
        }
      } else {
        clearAutoPaths()
      }
      window.alert(t('task_retry_astar_queued'))
    } else if (isManualRetry) {
      if (data?.task?.agv_id ?? task.preferred_agv_id) {
        selectedAgvId.value = data?.task?.agv_id ?? task.preferred_agv_id
      }
      manualPathToStart.value = data.path_to_start ?? []
      manualPathToEnd.value = data.path_to_end ?? data.path ?? []
      trackedManualTaskId.value = data?.task?.id ?? task.id
      startPoint.value = resolveTaskStartMarker(data?.task ?? task)
      endPoint.value = resolveTaskEndMarker(data?.task ?? task)
    } else {
      autoPathToStart.value = data.path_to_start ?? []
      autoPathToEnd.value = data.path_to_end ?? data.path ?? []
    }
    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Retry blocked task error:', error)
    window.alert(error instanceof Error ? error.message : String(error))
    await fetchTasks()
  }
}

async function retryAllBlockedTasksWithAStar(taskGroup) {
  const blockedTasks = (taskGroup?.tasks ?? []).filter(task => task.status === 'blocked')
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
      const res = await fetch(`${API_BASE}/schedule/retry_blocked/${task.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          algorithm: 'astar',
          grid_cols: GRID_COLS,
          grid_rows: GRID_ROWS
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
          isValidGridCoordinate(stage.start_x, GRID_COLS) &&
          isValidGridCoordinate(stage.start_y, GRID_ROWS) &&
          isValidGridCoordinate(stage.end_x, GRID_COLS) &&
          isValidGridCoordinate(stage.end_y, GRID_ROWS)
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
    !isValidGridCoordinate(Number(payload.start_x), GRID_COLS) ||
    !isValidGridCoordinate(Number(payload.start_y), GRID_ROWS) ||
    !isValidGridCoordinate(Number(payload.end_x), GRID_COLS) ||
    !isValidGridCoordinate(Number(payload.end_y), GRID_ROWS)
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: data.task.id,
          agv_id: manualAgv.id,
          algorithm: algorithm.value,
          grid_cols: GRID_COLS,
          grid_rows: GRID_ROWS
        })
      })
      const scheduleData = await scheduleRes.json()
      if (!scheduleRes.ok) {
        return await handleManualScheduleFailure(data.task.id, scheduleData)
      }

      startPoint.value = resolveTaskStartMarker(scheduleData.task)
      endPoint.value = resolveTaskEndMarker(scheduleData.task)
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
    grid_cols: GRID_COLS,
    grid_rows: GRID_ROWS,
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
    const stages = taskChainStages.value.map((stage, index) => ({
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
          !isValidGridCoordinate(stage.start_x, GRID_COLS) ||
          !isValidGridCoordinate(stage.start_y, GRID_ROWS) ||
          !isValidGridCoordinate(stage.end_x, GRID_COLS) ||
          !isValidGridCoordinate(stage.end_y, GRID_ROWS)
      )
    ) {
      return null
    }

    return {
      stages,
      grid_cols: GRID_COLS,
      grid_rows: GRID_ROWS
    }
  }

  const payload = {
    start_x: Number(taskForm.value.start_x),
    start_y: Number(taskForm.value.start_y),
    end_x: Number(taskForm.value.end_x),
    end_y: Number(taskForm.value.end_y),
    grid_cols: GRID_COLS,
    grid_rows: GRID_ROWS
  }

  if (
    !isValidGridCoordinate(payload.start_x, GRID_COLS) ||
    !isValidGridCoordinate(payload.start_y, GRID_ROWS) ||
    !isValidGridCoordinate(payload.end_x, GRID_COLS) ||
    !isValidGridCoordinate(payload.end_y, GRID_ROWS)
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

const {
  jumpToPanelSearchResult,
  scrollToComparePanel,
  shouldAutoRefreshFloatingCompare,
  stopFloatingCompareRefresh,
  requestFloatingCompareRefresh,
  positionFloatingCompareBelowEntry,
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

async function importTasksFromJson() {
  if (!jsonText.value) return
  jsonStatus.value = ''

  let parsed
  try {
    parsed = JSON.parse(jsonText.value)
  } catch {
    jsonStatus.value = t('json_import_fail')
    return
  }

  const taskItems = Array.isArray(parsed) ? parsed : parsed?.tasks
  if (!Array.isArray(taskItems)) {
    jsonStatus.value = t('json_import_fail')
    return
  }

  try {
    const res = await fetch(`${API_BASE}/task/import_json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tasks: taskItems })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Import failed')
    }
    jsonStatus.value = t('json_import_ok')
    await fetchTasks()
    await tryAutoSchedule()
  } catch (error) {
    console.error('Import json error:', error)
    jsonStatus.value = t('json_import_fail')
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

function canPreviewTask(task) {
  return ['pending', 'blocked', 'assigned', 'running'].includes(task?.status)
}

function refreshTaskPreview(task) {
  if (!task) return
  const stage = currentTaskStage(task)
  const startX = Number(stage?.start_x ?? task.start_x)
  const startY = Number(stage?.start_y ?? task.start_y)
  const endX = Number(stage?.end_x ?? task.end_x)
  const endY = Number(stage?.end_y ?? task.end_y)
  if (![startX, startY, endX, endY].every(Number.isFinite)) return

  previewTaskId.value = task.id
  previewStart.value = { x: startX, y: startY }
  previewEnd.value = { x: endX, y: endY }
  previewPath.value = buildPreviewPathByAlgorithm(startX, startY, endX, endY)
}

function onTaskHover(task) {
  if (!canPreviewTask(task)) return
  if (previewTimer) clearTimeout(previewTimer)
  refreshTaskPreview(task)
}

function onTaskLeave() {
  clearPreview()
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
  if (locale.value === 'ja') return '障害レイアウトを読み込みました。保存後に比較や調度へ反映されます。'
  if (locale.value === 'zh') return '已导入障碍布局，请点击“保存障碍”后再用于算法对比和调度。'
  return 'Obstacle layout imported. Save it before using it for comparison or dispatch.'
}

function obstacleMutationLockedText() {
  if (locale.value === 'ja') return '実行中または到着待ちの AGV があるため、障害レイアウトは変更できません。タスク完了後に再試行してください。'
  if (locale.value === 'zh') return '当前存在运行中或就位中的 AGV，禁止修改障碍布局。请等待任务完成后再操作。'
  return 'Obstacle layout changes are blocked while AGVs are running or relocating. Wait until active tasks finish.'
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

function detectObstacleSceneKey(cells) {
  const normalizedCells = normalizeBlockedCellList(cells)
  const currentKeys = normalizedCells.map(cell => blockedCellKey(cell.x, cell.y))

  for (const preset of obstaclePresets.value) {
    const presetCells = normalizeBlockedCellList(preset.blocked_cells ?? [])
    const presetKeys = presetCells.map(cell => blockedCellKey(cell.x, cell.y))
    if (presetKeys.length !== currentKeys.length) continue
    if (presetKeys.every((key, index) => key === currentKeys[index])) {
      return preset.key
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
  if (isCellOccupied(x, y)) return
  const key = blockedCellKey(x, y)
  if (blockedCellSet.value.has(key)) {
    blockedCells.value = blockedCells.value.filter(cell => blockedCellKey(cell.x, cell.y) !== key)
    return
  }
  blockedCells.value = normalizeBlockedCellList([...blockedCells.value, { x, y }])
}

function applyObstaclePaintAt(x, y, mode) {
  if (isCellOccupied(x, y)) return

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

async function saveBlockedCells() {
  if (!ensureObstacleMutationAllowed()) {
    return false
  }
  obstacleMapSaving.value = true
  try {
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(blockedCells.value)
    const res = await fetch(`${API_BASE}/status/map`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        blocked_cells: filtered,
        grid_cols: GRID_COLS,
        grid_rows: GRID_ROWS
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Save blocked cells failed')
    }
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? filtered)
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
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

async function resetBlockedCellsToDefault() {
  if (!ensureObstacleMutationAllowed()) {
    return false
  }
  if (obstacleLayoutDirty.value && !window.confirm(confirmDiscardObstacleChangesText())) {
    return false
  }
  obstacleMapSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map/reset`, {
      method: 'POST'
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Reset blocked cells failed')
    }
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? [])
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    syncedBlockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
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
    obstaclePresets.value = Array.isArray(data?.presets) ? data.presets : []
    if (
      obstaclePresets.value.length > 0 &&
      !obstaclePresets.value.some(preset => preset.key === selectedObstaclePreset.value)
    ) {
      selectedObstaclePreset.value = obstaclePresets.value[0].key
    }
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value)
  } catch (error) {
    console.error('Fetch map presets error:', error)
    obstaclePresets.value = []
  }
}

async function fetchMapLayout() {
  try {
    const res = await fetch(`${API_BASE}/status/map`)
    if (!res.ok) {
      throw new Error(`Map layout request failed: ${res.status}`)
    }

    const data = await res.json()
    if (!Array.isArray(data?.blocked_cells)) {
      blockedCells.value = [...DEFAULT_BLOCKED_CELLS]
      syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
      appliedObstacleSceneKey.value = 'default_shelves'
      selectedObstaclePreset.value = 'default_shelves'
      return
    }

    const normalized = normalizeBlockedCellList(
      data.blocked_cells.map(cell => ({
        x: Number(cell.x),
        y: Number(cell.y)
      }))
    )
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    syncedBlockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
    if (skipped.length > 0) {
      setObstacleLayoutStatus('info', obstacleSkippedOccupiedText(skipped.length))
    }
  } catch (error) {
    console.error('Fetch map layout error:', error)
    blockedCells.value = [...DEFAULT_BLOCKED_CELLS]
    syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
    appliedObstacleSceneKey.value = 'default_shelves'
    selectedObstaclePreset.value = 'default_shelves'
  }
}

async function applyObstaclePreset() {
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
      method: 'POST'
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Apply obstacle preset failed')
    }
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? [])
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    syncedBlockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
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
    grid_cols: GRID_COLS,
    grid_rows: GRID_ROWS,
    blocked_cells: normalizeBlockedCellList(blockedCells.value)
  }
  downloadJsonFile('agv-obstacle-layout.json', JSON.stringify(payload, null, 2))
}

function triggerObstacleLayoutImport() {
  if (!ensureObstacleMutationAllowed()) {
    return
  }
  obstacleLayoutFileInputRef.value?.click()
}

async function importObstacleLayout(rawText) {
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
    if (!rawCells) {
      throw new Error('Invalid obstacle layout')
    }

    const normalized = normalizeBlockedCellList(
      rawCells.map(cell => ({
        x: Number(cell?.x),
        y: Number(cell?.y)
      }))
    )
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
    if (appliedObstacleSceneKey.value !== 'custom') {
      selectedObstaclePreset.value = appliedObstacleSceneKey.value
    }
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
  await importObstacleLayout(text)
}

async function fetchAgvs() {
  const res = await fetch(`${API_BASE}/agv/list`)
  agvs.value = await res.json()
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
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/agv/${selectedBackendAgv.value.id}/emergency-stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/agv/${selectedBackendAgv.value.id}/resume`, {
      method: 'POST'
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

async function submitFaultReport() {
  if (!selectedBackendAgv.value) return
  agvActionLoadingId.value = selectedBackendAgv.value.id
  try {
    const res = await fetch(`${API_BASE}/fault/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
  resolvingFaultId.value = eventItem.id
  try {
    const res = await fetch(`${API_BASE}/fault/${eventItem.id}/resolve`, {
      method: 'POST'
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

  if (event.key === 'f' || event.key === 'F') {
    cancelSelection()
    return
  }

  if (event.key === 'r' || event.key === 'R') {
    event.preventDefault()
    algorithm.value = algorithm.value === 'simple' ? 'astar' : 'simple'
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

onMounted(() => {
  loadCustomPoints()
  loadTaskTemplates()
  loadExperimentRecords()
  loadMapDisplaySettings()
  loadPanelSections()
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
  void fetchMapPresets()
  void fetchMapLayout()
  void refreshState()
  timer = setInterval(() => {
    void refreshState()
  }, 1000)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('mousemove', onGlobalMouseMove)
  window.addEventListener('mouseup', onGlobalMouseUp)
  showGuideCenter.value = true
})

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
  },
  { deep: true }
)

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

watch([showAutoPath, showMarkerIcons, showPathArrows, showStatusLegend, statusLegendLayout, statusLegendOpacity, showMinimap, compareDisplayMode, compareFloatingOpacity], () => {
  saveMapDisplaySettings()
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
  if (dispatchMode.value === 'manual' && agv && agv.status === 'idle' && !trackedManualTaskId.value) {
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
      if (selectedBackendAgv.value?.status === 'idle' && !taskChainMapPickActive.value) {
        clearManualDispatchPreview()
      }
      return
    }
    if (!selectedBackendAgv.value) {
      clearManualDispatchPreview()
      return
    }

    const trackedTask = tasks.value.find(task => task.id === trackedManualTaskId.value)
    if (!trackedTask || ['finished', 'blocked', 'failed'].includes(trackedTask.status)) {
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
      if (selectedBackendAgv.value.status === 'idle') {
        cancelSelection()
        return
      }
      clearManualDispatchPreview()
      return
    }

    if (
      !['assigned', 'running'].includes(trackedTask.status) &&
      selectedBackendAgv.value.status === 'idle'
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

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (clickTimer) clearTimeout(clickTimer)
  if (previewTimer) clearTimeout(previewTimer)
  if (manualPreviewHoldTimer) clearTimeout(manualPreviewHoldTimer)
  if (taskBuilderJumpTimer) clearTimeout(taskBuilderJumpTimer)
  disposePanelCompareUi()
  if (mapResizeObserver) mapResizeObserver.disconnect()
  stopObstaclePaint()
  document.body.style.cursor = ''
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('mousemove', onGlobalMouseMove)
  window.removeEventListener('mouseup', onGlobalMouseUp)
})
</script>

<template>
  <div class="page-shell">
    <div class="page-top" :style="pageTopStyle">
      <div class="page-top-main">
    <h1>{{ t('title') }}</h1>

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

      <button class="toolbar-guide-entry" type="button" @click="openGuideCenter">
        {{ guideCenterLocale.open }}
      </button>

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
    </div>

    <p class="toolbar-hint">{{ t('hint') }}</p>
    <p class="toolbar-hint toolbar-hint-secondary">{{ toolbarGuideHintText }}</p>
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

    <div ref="layoutRef" class="layout" :style="layoutStyle">
      <div class="map-pane">
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

          <div class="map-stage" :style="mapStageStyle">
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

            <svg class="path-layer" :width="MAP_WIDTH" :height="MAP_HEIGHT">
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
                v-if="shouldShowAutoPath"
                class="path-auto-start"
                :points="autoPathToStartPoints"
                fill="none"
                stroke-width="2"
                stroke-dasharray="4 4"
              />
              <polyline
                v-if="shouldShowAutoPath"
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
                v-for="segment in showPathArrows && shouldShowAutoPath ? autoPathToStartArrows : []"
                :key="`auto-start-${segment.id}`"
                class="path-arrow path-arrow-auto-start"
                :x1="segment.x1"
                :y1="segment.y1"
                :x2="segment.x2"
                :y2="segment.y2"
                marker-end="url(#path-arrow-auto-start)"
              />
              <line
                v-for="segment in showPathArrows && shouldShowAutoPath ? autoPathToEndArrows : []"
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
              v-if="autoDisplayStartMarker"
              :class="showMarkerIcons ? 'point-icon point-icon-start point-icon-auto' : 'marker start'"
              :style="pointStyle(autoDisplayStartMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>

            <div
              v-if="autoDisplayEndMarker"
              :class="showMarkerIcons ? 'point-icon point-icon-end point-icon-auto' : 'marker end'"
              :style="pointStyle(autoDisplayEndMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
            >
              <span v-if="showMarkerIcons">E</span>
            </div>

            <div
              v-if="manualDisplayStartMarker"
              :class="showMarkerIcons ? 'point-icon point-icon-start point-icon-manual' : 'marker start'"
              :style="pointStyle(manualDisplayStartMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>

            <div
              v-if="manualDisplayEndMarker"
              :class="showMarkerIcons ? 'point-icon point-icon-end point-icon-manual' : 'marker end'"
              :style="pointStyle(manualDisplayEndMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
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
              :class="{ selected: agv.id === selectedAgvId }"
              :style="{
                left: `${agv.x * CELL_SIZE + (CELL_SIZE - AGV_SIZE) / 2}px`,
                top: `${agv.y * CELL_SIZE + (CELL_SIZE - AGV_SIZE) / 2}px`,
                backgroundColor: statusColor(agv.status)
              }"
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
            <button class="map-control-button" type="button" @click="toggleMapSettings">
              {{ settingsLocale.title }}
            </button>
            <div v-if="showMapSettings" class="map-settings-panel">
              <div class="map-settings-title">{{ settingsLocale.title }}</div>
              <button class="map-settings-guide-button" type="button" @click="openGuideCenter">
                {{ guideCenterLocale.open }}
              </button>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.mapGroup }}</div>
                <label class="map-setting-row">
                  <input v-model="showAutoPath" type="checkbox" />
                  <span>{{ settingsLocale.showAutoPath }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showMarkerIcons" type="checkbox" />
                  <span>{{ settingsLocale.showMarkerIcons }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showPathArrows" type="checkbox" />
                  <span>{{ settingsLocale.showPathArrows }}</span>
                </label>
                <label class="map-setting-row">
                  <input v-model="showMinimap" type="checkbox" />
                  <span>{{ settingsLocale.showMinimap }}</span>
                </label>
              </div>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.obstacleGroup }}</div>
                <label class="map-setting-row">
                  <input
                    :checked="obstacleEditMode"
                    type="checkbox"
                    :disabled="obstacleMutationLocked"
                    @change="toggleObstacleEditMode"
                  />
                  <span>{{ settingsLocale.obstacleEdit }}</span>
                </label>
                <p class="panel-hint map-settings-hint">{{ settingsLocale.obstacleHint }}</p>
                <p v-if="obstacleMutationLocked" class="panel-hint map-settings-hint">
                  {{ obstacleMutationLockedText() }}
                </p>
                <div class="map-settings-select-group">
                  <label class="map-settings-select-label" for="obstacle-preset-select">
                    {{ settingsLocale.obstaclePreset }}
                  </label>
                  <select
                    id="obstacle-preset-select"
                    v-model="selectedObstaclePreset"
                    class="map-settings-select"
                  >
                    <option
                      v-for="preset in obstaclePresets"
                      :key="preset.key"
                      :value="preset.key"
                    >
                      {{ obstaclePresetName(preset) }}
                    </option>
                  </select>
                </div>
                <p v-if="selectedObstaclePresetInfo" class="panel-hint map-settings-hint">
                  {{ obstaclePresetDescription(selectedObstaclePresetInfo) }}
                </p>
                <div class="map-settings-status">
                  {{ obstacleLayoutDirty ? settingsLocale.obstacleDirty : settingsLocale.obstacleSaved }}
                </div>
                <div
                  v-if="obstacleLayoutStatus"
                  class="map-settings-status"
                  :class="`status-${obstacleLayoutStatusType}`"
                >
                  {{ obstacleLayoutStatus }}
                </div>
                <div class="map-settings-actions">
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="obstacleMapSaving || obstacleMutationLocked || obstaclePresets.length === 0"
                    @click="applyObstaclePreset"
                  >
                    {{ settingsLocale.obstaclePresetApply }}
                  </button>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="obstacleMapSaving || obstacleMutationLocked || !obstacleLayoutDirty"
                    @click="saveBlockedCells"
                  >
                    {{ settingsLocale.obstacleSave }}
                  </button>
                  <button class="btn-ghost" type="button" @click="downloadObstacleLayout">
                    {{ settingsLocale.obstacleExport }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="obstacleMutationLocked"
                    @click="triggerObstacleLayoutImport"
                  >
                    {{ settingsLocale.obstacleImport }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="obstacleMapSaving || obstacleMutationLocked"
                    @click="resetBlockedCellsToDefault"
                  >
                    {{ settingsLocale.obstacleReset }}
                  </button>
                </div>
                <input
                  ref="obstacleLayoutFileInputRef"
                  type="file"
                  accept="application/json,.json"
                  class="hidden-file-input"
                  @change="onObstacleLayoutFileChange"
                />
              </div>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.compareGroup }}</div>
                <div class="map-settings-select-group">
                  <label class="map-settings-select-label" for="compare-display-mode">
                    {{ settingsLocale.compareDisplay }}
                  </label>
                  <select
                    id="compare-display-mode"
                    v-model="compareDisplayMode"
                    class="map-settings-select"
                  >
                    <option value="panel">{{ settingsLocale.compareDisplayPanel }}</option>
                    <option value="floating">{{ settingsLocale.compareDisplayFloating }}</option>
                  </select>
                </div>
                <div v-if="compareDisplayMode === 'floating'" class="map-settings-select-group">
                  <label class="map-settings-select-label" for="compare-opacity-range">
                    {{ settingsLocale.compareOpacity }}
                  </label>
                  <input
                    id="compare-opacity-range"
                    v-model.number="compareFloatingOpacity"
                    type="range"
                    min="0.45"
                    max="1"
                    step="0.05"
                  />
                </div>
              </div>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.promptGroup }}</div>
                <label class="map-setting-row">
                  <input v-model="showStatusLegend" type="checkbox" />
                  <span>{{ settingsLocale.showAgvStatus }}</span>
                </label>
                <div v-if="showStatusLegend" class="map-settings-select-group">
                  <label class="map-settings-select-label" for="status-legend-layout">
                    {{ settingsLocale.agvLegendLayout }}
                  </label>
                  <select
                    id="status-legend-layout"
                    v-model="statusLegendLayout"
                    class="map-settings-select"
                  >
                    <option value="horizontal">{{ settingsLocale.agvLegendLayoutHorizontal }}</option>
                    <option value="vertical">{{ settingsLocale.agvLegendLayoutVertical }}</option>
                  </select>
                </div>
                <div v-if="showStatusLegend" class="map-settings-select-group">
                  <label class="map-settings-select-label" for="status-legend-opacity">
                    {{ settingsLocale.agvLegendOpacity }}
                  </label>
                  <input
                    id="status-legend-opacity"
                    v-model.number="statusLegendOpacity"
                    type="range"
                    min="0.2"
                    max="0.9"
                    step="0.05"
                  />
                </div>
              </div>
              <button class="map-settings-action" type="button" @click="resetMapView">
                {{ settingsLocale.resetView }}
              </button>
            </div>
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
              :style="{
                backgroundSize: `${CELL_SIZE * minimapScale}px ${CELL_SIZE * minimapScale}px`
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
                v-if="shouldShowAutoPath"
                class="path-auto-start minimap-path"
                :points="minimapAutoPathToStartPoints"
                fill="none"
                stroke-width="1.4"
              />
              <polyline
                v-if="shouldShowAutoPath"
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
              :style="{
                left: `${agv.x * CELL_SIZE * minimapScale + (CELL_SIZE * minimapScale) / 2 - 4}px`,
                top: `${agv.y * CELL_SIZE * minimapScale + (CELL_SIZE * minimapScale) / 2 - 4}px`,
                backgroundColor: statusColor(agv.status)
              }"
            ></div>
            <div
              v-if="minimapAutoStartMarker"
              :class="showMarkerIcons ? 'minimap-point-icon minimap-point-start minimap-point-auto' : 'marker start minimap-marker-dot'"
              :style="pointStyle(minimapAutoStartMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>
            <div
              v-if="minimapAutoEndMarker"
              :class="showMarkerIcons ? 'minimap-point-icon minimap-point-end minimap-point-auto' : 'marker end minimap-marker-dot'"
              :style="pointStyle(minimapAutoEndMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
            >
              <span v-if="showMarkerIcons">E</span>
            </div>
            <div
              v-if="minimapManualStartMarker"
              :class="showMarkerIcons ? 'minimap-point-icon minimap-point-start minimap-point-manual' : 'marker start minimap-marker-dot'"
              :style="pointStyle(minimapManualStartMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>
            <div
              v-if="minimapManualEndMarker"
              :class="showMarkerIcons ? 'minimap-point-icon minimap-point-end minimap-point-manual' : 'marker end minimap-marker-dot'"
              :style="pointStyle(minimapManualEndMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
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
        </section>
      </div>

      <div class="panel-resizer" @mousedown="startPanelResize"></div>

      <aside class="panel-shell">
        <div ref="panelRef" class="panel" @scroll="onPanelScroll">
          <div class="panel-search">
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

          <div class="panel-section-actions">
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

          <section
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
              <button class="dispatch-summary dispatch-summary-button" type="button" @click="toggleDispatchModeFromSummary">
                <span class="dispatch-summary-label">{{ panelLocale.currentMode }}</span>
                <strong>{{ currentDispatchModeLabel }}</strong>
              </button>
              <div class="dispatch-summary dispatch-algorithm-note">
                <span class="dispatch-summary-label">{{ t('algorithm') }}</span>
                <strong>{{ algorithmText(algorithm) }}</strong>
                <p>{{ algorithmHintText }}</p>
              </div>

              <div
                v-if="compareDisplayMode === 'panel'"
                ref="comparePanelRef"
                class="dispatch-summary algorithm-compare-panel"
              >
                <div class="algorithm-compare-header">
                  <div>
                    <span class="dispatch-summary-label">{{ algorithmCompareLocale.title }}</span>
                    <strong>{{ taskBuilderMode === 'chain' ? taskChainLocale.title : currentTaskBuilderModeCompactLabel }}</strong>
                  </div>
                  <div class="algorithm-compare-actions">
                    <button class="btn-ghost" type="button" @click="toggleComparePanelExpanded">
                      {{ comparePanelExpanded ? panelLocale.collapse : panelLocale.expand }}
                    </button>
                    <button class="btn-secondary" type="button" :disabled="pathCompareLoading" @click="compareCurrentRoute">
                      {{ pathCompareLoading ? '...' : algorithmCompareLocale.run }}
                    </button>
                    <button
                      v-if="pathCompareResult || pathCompareError"
                      class="btn-ghost"
                      type="button"
                      @click="clearPathCompare"
                    >
                      {{ algorithmCompareLocale.clear }}
                    </button>
                  </div>
                </div>
                <template v-if="comparePanelExpanded">
                  <p class="panel-hint">{{ currentCompareHint }}</p>
                  <div v-if="pathCompareError" class="template-status error">{{ pathCompareError }}</div>
                  <div v-else-if="pathCompareResult" class="algorithm-compare-grid">
                    <article
                      v-for="entry in compareResultEntries"
                      :key="entry[0]"
                      class="algorithm-compare-card"
                      :class="{
                        active: algorithm === entry[0],
                        recommended: recommendedCompareAlgorithm === entry[0]
                      }"
                    >
                      <div class="algorithm-compare-card-head">
                        <strong>{{ algorithmText(entry[0]) }}</strong>
                        <button class="btn-ghost" type="button" @click="applyComparedAlgorithm(entry[0])">
                          {{ compareResultBadgeText(entry[0]) }}
                        </button>
                      </div>
                      <div class="task-line">
                        {{ formatCompareResultStatus(entry[1]) }}
                      </div>
                      <div class="task-line">
                        {{ algorithmCompareLocale.total }}:
                        {{ entry[1].total_length ?? '--' }}
                      </div>
                      <div class="task-line">
                        {{ algorithmCompareLocale.stages }}:
                        {{ formatCompareStageLengths(entry[1]) || '--' }}
                      </div>
                      <div v-if="entry[1].failed_stage_index !== null" class="task-line task-reason">
                        {{ algorithmCompareLocale.failedStage }}: {{ Number(entry[1].failed_stage_index) + 1 }}
                      </div>
                    </article>
                  </div>
                  <div v-if="pathCompareResult" class="json-actions">
                    <button class="btn-primary" type="button" @click="saveCurrentExperimentRecord">
                      {{ experimentLocale.saveCurrent }}
                    </button>
                    <button class="btn-secondary" type="button" @click="exportCurrentCompareResultJson">
                      {{ experimentLocale.exportCurrentJson }}
                    </button>
                    <button class="btn-secondary" type="button" @click="exportCurrentCompareResultCsv">
                      {{ experimentLocale.exportCurrentCsv }}
                    </button>
                  </div>
                </template>
              </div>

              <div class="dispatch-summary fault-panel">
                <div class="fault-panel-header">
                  <div>
                    <span class="dispatch-summary-label">{{ faultLocale.title }}</span>
                    <strong>{{ faultLocale.selectedAgv }}</strong>
                  </div>
                  <div class="fault-filter-group">
                    <button
                      class="btn-ghost fault-filter-button"
                      :class="{ active: faultEventFilter === 'open' }"
                      type="button"
                      @click="faultEventFilter = 'open'"
                    >
                      {{ faultLocale.filterOpen }}
                    </button>
                    <button
                      class="btn-ghost fault-filter-button"
                      :class="{ active: faultEventFilter === 'resolved' }"
                      type="button"
                      @click="faultEventFilter = 'resolved'"
                    >
                      {{ faultLocale.filterResolved }}
                    </button>
                    <button
                      class="btn-ghost fault-filter-button"
                      :class="{ active: faultEventFilter === 'all' }"
                      type="button"
                      @click="faultEventFilter = 'all'"
                    >
                      {{ faultLocale.filterAll }}
                    </button>
                  </div>
                </div>

                <template v-if="selectedBackendAgv">
                  <div class="fault-selected-agv">
                    <div class="fault-selected-line">
                      <strong>AGV #{{ selectedBackendAgv.id }}</strong>
                      <div class="fault-selected-head-actions">
                        <span class="status-badge" :class="selectedBackendAgv.status">{{ statusText(selectedBackendAgv.status) }}</span>
                        <button
                          class="btn-ghost fault-selected-clear-button"
                          type="button"
                          :disabled="agvActionLoadingId === selectedBackendAgv.id"
                          @click="cancelSelection"
                        >
                          {{ faultLocale.clearSelection }}
                        </button>
                      </div>
                    </div>
                    <div class="task-line">
                      {{ faultLocale.currentTask }}:
                      {{ selectedAgvTask ? `#${selectedAgvTask.id}` : faultLocale.currentTaskNone }}
                    </div>
                    <div class="fault-action-row">
                      <button
                        v-if="selectedBackendAgv.status !== 'emergency_stop'"
                        class="btn-danger fault-action-button"
                        type="button"
                        :disabled="agvActionLoadingId === selectedBackendAgv.id || selectedBackendAgv.status === 'fault'"
                        @click="emergencyStopSelectedAgv"
                      >
                        {{ faultLocale.emergencyStop }}
                      </button>
                      <button
                        v-else
                        class="btn-secondary fault-action-button"
                        type="button"
                        :disabled="agvActionLoadingId === selectedBackendAgv.id"
                        @click="resumeSelectedAgv"
                      >
                        {{ faultLocale.resume }}
                      </button>
                      <button
                        class="btn-secondary fault-action-button"
                        type="button"
                        :disabled="agvActionLoadingId === selectedBackendAgv.id"
                        @click="showFaultReportForm = !showFaultReportForm"
                      >
                        {{ faultLocale.reportFault }}
                      </button>
                    </div>
                    <div v-if="showFaultReportForm" class="fault-report-form">
                      <label>
                        {{ faultLocale.faultType }}
                        <select v-model="faultReportForm.fault_type">
                          <option value="path_blocked">{{ faultTypeText('path_blocked') }}</option>
                          <option value="battery">{{ faultTypeText('battery') }}</option>
                          <option value="motor">{{ faultTypeText('motor') }}</option>
                          <option value="communication">{{ faultTypeText('communication') }}</option>
                          <option value="manual">{{ faultTypeText('manual') }}</option>
                          <option value="other">{{ faultTypeText('other') }}</option>
                        </select>
                      </label>
                      <label>
                        {{ faultLocale.severity }}
                        <select v-model="faultReportForm.severity">
                          <option value="low">{{ faultSeverityText('low') }}</option>
                          <option value="medium">{{ faultSeverityText('medium') }}</option>
                          <option value="high">{{ faultSeverityText('high') }}</option>
                          <option value="critical">{{ faultSeverityText('critical') }}</option>
                        </select>
                      </label>
                      <label>
                        {{ faultLocale.message }}
                        <textarea v-model.trim="faultReportForm.message" rows="2"></textarea>
                      </label>
                      <div class="fault-action-row">
                        <button
                          class="btn-primary fault-action-button"
                          type="button"
                          :disabled="agvActionLoadingId === selectedBackendAgv.id"
                          @click="submitFaultReport"
                        >
                          {{ faultLocale.reportFaultSubmit }}
                        </button>
                        <button
                          class="btn-ghost fault-action-button"
                          type="button"
                          @click="showFaultReportForm = false"
                        >
                          {{ faultLocale.reportFaultCancel }}
                        </button>
                      </div>
                    </div>
                  </div>
                </template>
                <p v-else class="panel-hint">{{ faultLocale.noSelectedAgv }}</p>

                <div v-if="faultPanelStatus" class="template-status" :class="faultPanelStatusType">
                  {{ faultPanelStatus }}
                </div>

                <div class="fault-event-list">
                  <article v-for="eventItem in filteredFaultEvents" :key="eventItem.id" class="fault-event-card">
                    <div class="fault-event-head">
                      <strong>#{{ eventItem.id }} · AGV #{{ eventItem.agv_id }}</strong>
                      <span class="status-badge" :class="eventItem.status === 'resolved' ? 'finished' : 'blocked'">
                        {{ faultEventStatusText(eventItem.status) }}
                      </span>
                    </div>
                    <div class="task-line">
                      {{ faultLocale.eventType }}: {{ faultEventTypeText(eventItem.event_type) }}
                    </div>
                    <div class="task-line">
                      {{ faultLocale.faultType }}: {{ faultTypeText(eventItem.fault_type) }}
                    </div>
                    <div class="task-line">
                      {{ faultLocale.severity }}: {{ faultSeverityText(eventItem.severity) }}
                    </div>
                    <div v-if="eventItem.message" class="task-line task-reason">
                      {{ faultLocale.message }}: {{ eventItem.message }}
                    </div>
                    <div class="task-line task-time">
                      {{ faultLocale.reportedAt }}: {{ eventItem.reported_at }}
                    </div>
                    <div v-if="eventItem.resolved_at" class="task-line task-time">
                      {{ faultLocale.resolvedAt }}: {{ eventItem.resolved_at }}
                    </div>
                    <div class="task-actions">
                      <button
                        v-if="eventItem.status !== 'resolved'"
                        class="btn-secondary task-action-button"
                        type="button"
                        :disabled="resolvingFaultId === eventItem.id"
                        @click="resolveFaultEventItem(eventItem)"
                      >
                        {{ faultLocale.resolve }}
                      </button>
                    </div>
                  </article>
                  <div v-if="filteredFaultEvents.length === 0" class="empty-note">
                    {{ faultLocale.empty }}
                  </div>
                </div>
              </div>

              <div ref="taskBuilderRef" class="task-form task-builder">
                <div class="task-builder-header">
                  <h2>{{ taskBuilderTitleText }}</h2>
                  <button class="task-builder-mode-toggle" type="button" @click="toggleTaskBuilderMode">
                    <span class="task-builder-mode-toggle-label">{{ taskBuilderLocale.switchLabel }}</span>
                    <strong>{{ currentTaskBuilderModeCompactLabel }}</strong>
                  </button>
                </div>
                <p class="panel-hint">{{ currentTaskBuilderHint }}</p>
                <p v-if="manualDispatchOriginText" class="panel-hint">{{ manualDispatchOriginText }}</p>
                <p v-if="taskBuilderMode === 'chain'" class="panel-hint">{{ taskChainLocale.priorityHint }}</p>
                <div class="task-builder-meta">
                  <div class="task-builder-meta-group">
                    <label>{{ t('task_priority') }}</label>
                    <select v-model.number="taskForm.priority">
                      <option :value="5">5</option>
                      <option :value="4">4</option>
                      <option :value="3">3</option>
                      <option :value="2">2</option>
                      <option :value="1">1</option>
                    </select>
                  </div>
                  <div class="task-builder-meta-group">
                    <label>{{ t('algorithm') }}</label>
                    <div class="task-builder-algorithm-switch">
                      <button
                        class="task-builder-algorithm-button"
                        :class="{ active: algorithm === 'simple' }"
                        type="button"
                        @click="algorithm = 'simple'"
                      >
                        {{ t('algo_simple') }}
                      </button>
                      <button
                        class="task-builder-algorithm-button"
                        :class="{ active: algorithm === 'astar' }"
                        type="button"
                        @click="algorithm = 'astar'"
                      >
                        {{ t('algo_astar') }}
                      </button>
                    </div>
                  </div>
                </div>

                <template v-if="taskBuilderMode === 'single'">
                  <div class="form-grid">
                    <label>{{ singleTaskStartLabelX }}</label>
                    <input v-model.number="taskForm.start_x" type="number" min="0" :max="GRID_COLS - 1" />
                    <label>{{ singleTaskStartLabelY }}</label>
                    <input v-model.number="taskForm.start_y" type="number" min="0" :max="GRID_ROWS - 1" />
                    <label>{{ singleTaskEndLabelX }}</label>
                    <input v-model.number="taskForm.end_x" type="number" min="0" :max="GRID_COLS - 1" />
                    <label>{{ singleTaskEndLabelY }}</label>
                    <input v-model.number="taskForm.end_y" type="number" min="0" :max="GRID_ROWS - 1" />
                  </div>
                  <button class="btn-primary full-width" type="button" :disabled="!manualDispatchReady" @click="addTaskFromForm">
                    {{ singleTaskSubmitText }}
                  </button>
                </template>

                <template v-else>
                  <div class="task-chain-map-actions">
                    <div class="task-chain-map-toolbar">
                      <button
                        class="btn-secondary"
                        type="button"
                        :class="{ active: taskChainMapPickActive }"
                        :disabled="dispatchMode === 'manual' && !manualDispatchReady"
                        @click="toggleTaskChainMapPick"
                      >
                        {{ taskChainMapPickButtonText }}
                      </button>
                      <label class="task-chain-count-control">
                        <span class="task-chain-count-label">{{ taskChainMapPickUiLocale.stageCount }}</span>
                        <button
                          class="btn-ghost task-chain-count-button"
                          type="button"
                          :disabled="taskChainMapPickStageCount <= 2"
                          @click="setTaskChainMapPickStageCount(taskChainMapPickStageCount - 1)"
                        >
                          -
                        </button>
                        <input
                          v-model.number="taskChainMapPickStageCountInput"
                          class="task-chain-count-input"
                          type="number"
                          min="2"
                        />
                        <button
                          class="btn-ghost task-chain-count-button"
                          type="button"
                          @click="setTaskChainMapPickStageCount(taskChainMapPickStageCount + 1)"
                        >
                          +
                        </button>
                      </label>
                    </div>
                    <span class="task-chain-map-status">{{ taskChainMapPickStatusText }}</span>
                  </div>
                  <div
                    v-for="(stage, index) in taskChainStages"
                    :key="`chain-stage-${index}`"
                    class="task-chain-stage"
                  >
                    <div class="task-chain-stage-head">
                      <strong>{{ taskChainLocale.stage }} {{ index + 1 }}</strong>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="taskChainStages.length <= 2"
                        @click="removeTaskChainStage(index)"
                      >
                        {{ taskChainLocale.removeStage }}
                      </button>
                    </div>
                    <div class="form-grid chain-form-grid">
                      <label>{{ taskChainLocale.stageLabel }}</label>
                      <input v-model.trim="stage.label" type="text" :placeholder="taskChainLocale.stageLabelPlaceholder" />
                      <label>{{ t('form_start_x') }}</label>
                      <input v-model.number="stage.start_x" type="number" min="0" :max="GRID_COLS - 1" />
                      <label>{{ t('form_start_y') }}</label>
                      <input v-model.number="stage.start_y" type="number" min="0" :max="GRID_ROWS - 1" />
                      <label>{{ t('form_end_x') }}</label>
                      <input v-model.number="stage.end_x" type="number" min="0" :max="GRID_COLS - 1" />
                      <label>{{ t('form_end_y') }}</label>
                      <input v-model.number="stage.end_y" type="number" min="0" :max="GRID_ROWS - 1" />
                    </div>
                  </div>
                  <div class="task-chain-actions">
                    <button class="btn-secondary" type="button" @click="addTaskChainStage">
                      {{ taskChainLocale.addStage }}
                    </button>
                    <button class="btn-ghost" type="button" @click="resetTaskChainStages">
                      {{ taskChainLocale.resetStages }}
                    </button>
                  </div>
                  <button
                    class="btn-primary full-width"
                    type="button"
                    :disabled="taskChainStages.length < 2 || !manualDispatchReady"
                    @click="addTaskChainFromForm"
                  >
                    {{ chainTaskSubmitText }}
                  </button>
                </template>
              </div>
            </div>
          </section>

          <section
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
              <div class="queue-panel">
                <h2>{{ t('tasks') }}</h2>
                <div v-if="tasks.length === 0" class="empty">{{ t('tasks_empty') }}</div>

                <section v-for="group in taskGroups" :key="group.key" class="queue-group">
                  <div class="queue-header" :class="{ prominent: group.key === 'finished' }">
                    <button class="queue-header-main" type="button" @click="toggleQueueGroup(group.key)">
                      <span>{{ group.title }}</span>
                      <span class="queue-header-meta">
                        <span class="queue-count">{{ group.tasks.length }}</span>
                        <span class="queue-toggle-text">
                          {{ isQueueGroupCollapsed(group.key) ? panelLocale.expand : panelLocale.collapse }}
                        </span>
                      </span>
                    </button>
                  </div>

                  <template v-if="!isQueueGroupCollapsed(group.key)">
                    <div v-if="group.tasks.length > 0" class="queue-bulk-actions" :class="{ prominent: group.key === 'finished' }">
                      <button
                        v-if="group.key === 'blocked'"
                        class="queue-bulk-button"
                        type="button"
                        @click="retryAllBlockedTasksWithAStar(group)"
                      >
                        {{ t('queue_retry_all_astar') }}
                      </button>
                      <button
                        class="queue-bulk-button"
                        type="button"
                        :disabled="areGroupTaskCardsCollapsed(group)"
                        @click="setQueueGroupTaskCardsCollapsed(group, true)"
                      >
                        {{ queueViewLocale.collapseCards }}
                      </button>
                      <button
                        class="queue-bulk-button"
                        type="button"
                        :disabled="areGroupTaskCardsExpanded(group)"
                        @click="setQueueGroupTaskCardsCollapsed(group, false)"
                      >
                        {{ queueViewLocale.expandCards }}
                      </button>
                    </div>

                    <div v-else class="queue-empty">
                      {{ t('queue_empty') }}
                    </div>

                    <article
                      v-for="task in group.tasks"
                      :key="task.id"
                      class="task-card"
                      :class="{
                        previewing: previewTaskId === task.id,
                        collapsed: isTaskCardFolded(task.id),
                        'search-hit': matchedTaskIds.includes(task.id)
                      }"
                      @mouseenter="onTaskHover(task)"
                      @mouseleave="onTaskLeave"
                    >
                      <button class="task-head task-card-toggle" type="button" @click="toggleTaskCard(task.id)">
                        <strong>#{{ task.id }}</strong>
                        <span class="task-head-side">
                          <span class="status-badge" :class="task.status">{{ taskStatusText(task.status) }}</span>
                          <span class="task-card-toggle-text">
                            {{ isTaskCardFolded(task.id) ? panelLocale.expand : panelLocale.collapse }}
                          </span>
                        </span>
                      </button>

                      <div v-if="isTaskCardFolded(task.id)" class="task-line task-line-compact">
                        {{ formatTaskCompactSummary(task) }}
                      </div>

                      <template v-else>
                        <div class="task-line">{{ formatTaskMeta(task) }}</div>
                        <div v-if="formatTaskStageProgress(task)" class="task-line">{{ formatTaskStageProgress(task) }}</div>
                        <div v-if="formatTaskCurrentStage(task)" class="task-line">{{ formatTaskCurrentStage(task) }}</div>
                        <div class="task-line">{{ t('task_priority') }}: {{ task.priority }}</div>
                        <div v-if="formatTaskAlgorithm(task)" class="task-line">{{ formatTaskAlgorithm(task) }}</div>
                        <div v-if="formatTaskInitialPoint(task)" class="task-line">{{ formatTaskInitialPoint(task) }}</div>
                        <div class="task-line">{{ formatTaskAgv(task) }}</div>
                        <div v-if="formatTaskPathStats(task)" class="task-line">{{ formatTaskPathStats(task) }}</div>
                        <div class="task-line task-reason">
                          {{ t('dispatch_reason') }}: {{ formatDispatchReason(task) }}
                        </div>
                        <div v-if="formatTaskTime(task)" class="task-line task-time">
                          {{ formatTaskTime(task) }}
                        </div>
                        <div class="task-actions">
                          <button
                            v-if="['pending', 'blocked'].includes(task.status)"
                            class="btn-delete task-action-button"
                            type="button"
                            @click="deleteTask(task)"
                          >
                            {{ t('delete_task') }}
                          </button>
                          <button
                            v-if="task.status === 'blocked'"
                            class="btn-secondary task-action-button"
                            type="button"
                            @click="retryBlockedTaskWithAStar(task)"
                          >
                            {{ t('task_retry_astar') }}
                          </button>
                        </div>
                      </template>
                    </article>
                  </template>
                </section>
              </div>
            </div>
          </section>

          <section
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
              <div class="task-templates">
                <h2>{{ t('template_library') }}</h2>
                <p class="panel-hint">{{ t('template_hint') }}</p>

                <div class="template-manage">
                  <h3>{{ t('template_manage') }}</h3>
                  <div class="form-grid template-manage-grid">
                    <label>{{ t('template_name') }}</label>
                    <input
                      v-model.trim="taskTemplateForm.name"
                      type="text"
                      :placeholder="t('template_name_placeholder')"
                    />
                  </div>
                  <div class="template-save-actions">
                    <button class="btn-primary full-width" type="button" @click="saveCurrentTaskAsTemplate">
                      {{ t('template_save_current') }}
                    </button>
                    <button class="btn-secondary full-width" type="button" @click="saveCurrentTaskChainAsTemplate">
                      {{ taskChainLocale.saveTemplate }}
                    </button>
                  </div>
                  <div v-if="taskTemplateStatus" class="template-status" :class="taskTemplateStatusType">
                    {{ taskTemplateStatus }}
                  </div>
                </div>

                <div class="template-manage template-json-tools">
                  <h3>{{ templateJsonLocale.title }}</h3>
                  <p class="panel-hint">{{ templateJsonLocale.hint }}</p>
                  <input
                    ref="templateFileInputRef"
                    class="visually-hidden"
                    type="file"
                    accept=".json,application/json"
                    @change="handleTemplateFileChange"
                  />
                  <textarea
                    v-model="templateJsonText"
                    class="json-area"
                    rows="6"
                    :placeholder="templateJsonLocale.placeholder"
                  ></textarea>
                  <div class="json-actions">
                    <button class="btn-secondary" type="button" @click="importTaskTemplatesFromJson">
                      {{ templateJsonLocale.import }}
                    </button>
                    <button class="btn-secondary" type="button" @click="triggerTemplateFileImport">
                      {{ templateJsonLocale.importFile }}
                    </button>
                    <button class="btn-secondary" type="button" @click="exportTaskTemplatesToJson">
                      {{ templateJsonLocale.export }}
                    </button>
                    <button class="btn-secondary" type="button" @click="downloadTemplateJsonFile">
                      {{ templateJsonLocale.downloadFile }}
                    </button>
                    <button class="btn-ghost" type="button" @click="clearTemplateJsonText">
                      {{ templateJsonLocale.clear }}
                    </button>
                  </div>
                  <div v-if="templateJsonStatus" class="template-status" :class="templateJsonStatusType">
                    {{ templateJsonStatus }}
                  </div>
                </div>

                <div class="template-list">
                  <article
                    v-for="template in taskTemplates"
                    :key="template.id"
                    class="template-card"
                    :class="{ 'search-hit': matchedTemplateIds.includes(template.id) }"
                  >
                    <div class="template-head">
                      <strong>{{ taskTemplateName(template) }}</strong>
                      <span class="point-badge" :class="{ custom: template.custom }">
                        {{ taskTemplateTypeText(template) }}
                      </span>
                    </div>
                    <div class="template-meta">
                      {{ formatTemplateMeta(template) }}
                    </div>
                    <div v-if="formatTemplateStageCount(template)" class="template-meta">
                      {{ formatTemplateStageCount(template) }}
                    </div>
                    <div class="template-meta">{{ t('task_priority') }}: {{ template.priority }}</div>
                    <div class="template-actions">
                      <button
                        class="btn-secondary"
                        type="button"
                        @click="onTemplateApplyClick(template)"
                        @dblclick.stop="onTemplateApplyDoubleClick(template)"
                      >
                        {{ t('template_apply') }}
                      </button>
                      <button class="btn-ghost" type="button" @click="createTaskFromTemplate(template)">
                        {{ t('template_run') }}
                      </button>
                      <button
                        v-if="template.custom"
                        class="btn-delete"
                        type="button"
                        @click="deleteTaskTemplate(template)"
                      >
                        {{ t('template_delete') }}
                      </button>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </section>

          <section
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
              <div class="point-library">
                <h2>{{ t('point_library') }}</h2>
                <p class="panel-hint">{{ t('point_fill_hint') }}</p>

                <div class="point-manage">
                  <h3>{{ t('point_manage') }}</h3>
                  <p class="panel-hint">{{ t('point_manage_hint') }}</p>
                  <div class="form-grid">
                    <label>{{ t('point_form_name') }}</label>
                    <input
                      v-model.trim="customPointForm.name"
                      type="text"
                      :placeholder="t('point_form_name_placeholder')"
                    />
                    <label>{{ t('point_form_zone') }}</label>
                    <input
                      v-model.trim="customPointForm.zone"
                      type="text"
                      :placeholder="t('point_form_zone_placeholder')"
                    />
                    <label>{{ t('form_start_x') }}</label>
                    <input v-model.number="customPointForm.x" type="number" min="0" :max="GRID_COLS - 1" />
                    <label>{{ t('form_start_y') }}</label>
                    <input v-model.number="customPointForm.y" type="number" min="0" :max="GRID_ROWS - 1" />
                  </div>
                  <button class="btn-primary full-width" type="button" @click="addCustomPoint">
                    {{ t('point_add') }}
                  </button>
                  <div v-if="pointFormStatus" class="point-status" :class="pointFormStatusType">
                    {{ pointFormStatus }}
                  </div>
                </div>

                <input
                  v-model.trim="pointSearch"
                  class="point-search"
                  type="text"
                  :placeholder="t('point_search_placeholder')"
                />

                <div v-if="filteredPoints.length === 0" class="point-empty">
                  {{ t('point_search_empty') }}
                </div>

                <div v-else class="point-list">
                  <article
                    v-for="point in filteredPoints"
                    :key="point.id"
                    class="point-card"
                    :class="{ 'search-hit': matchedPointIds.includes(point.id) }"
                  >
                    <div class="point-head">
                      <strong>{{ pointName(point) }}</strong>
                      <div class="point-tags">
                        <span class="point-zone">{{ pointZone(point) }}</span>
                        <span class="point-badge" :class="{ custom: point.custom }">
                          {{ pointTypeText(point) }}
                        </span>
                      </div>
                    </div>
                    <div class="point-meta">
                      {{ t('point_coords') }}: ({{ point.x }}, {{ point.y }})
                    </div>
                    <div class="point-actions">
                      <button
                        class="btn-secondary"
                        type="button"
                        @click="applyPointToTaskForm('start', point)"
                      >
                        {{ t('point_apply_start') }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        @click="applyPointToTaskForm('end', point)"
                      >
                        {{ t('point_apply_end') }}
                      </button>
                      <button
                        v-if="point.custom"
                        class="btn-delete"
                        type="button"
                        @click="deleteCustomPoint(point)"
                      >
                        {{ t('point_delete') }}
                      </button>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </section>

          <section
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
              <div class="json-tools">
                <h2>{{ t('json_tools') }}</h2>
                <div class="json-example-actions">
                  <button class="btn-secondary" type="button" @click="fillTaskJsonExample('single')">
                    {{ taskJsonLocale.singleExample }}
                  </button>
                  <button class="btn-ghost" type="button" @click="downloadTaskJsonExample('single')">
                    {{ taskJsonExampleFileLocale.singleDownload }}
                  </button>
                  <button class="btn-secondary" type="button" @click="fillTaskJsonExample('chain')">
                    {{ taskJsonLocale.chainExample }}
                  </button>
                  <button class="btn-ghost" type="button" @click="downloadTaskJsonExample('chain')">
                    {{ taskJsonExampleFileLocale.chainDownload }}
                  </button>
                </div>
                <textarea
                  v-model="jsonText"
                  class="json-area"
                  rows="8"
                  :placeholder="t('json_placeholder')"
                ></textarea>
                <div class="json-actions">
                  <button class="btn-secondary" type="button" @click="importTasksFromJson">
                    {{ t('import_json') }}
                  </button>
                  <button class="btn-secondary" type="button" @click="exportTasksToJson">
                    {{ t('export_json') }}
                  </button>
                  <button class="btn-ghost" type="button" @click="clearJsonText">
                    {{ t('clear_json') }}
                  </button>
                </div>
                <div v-if="jsonStatus" class="json-status">{{ jsonStatus }}</div>
              </div>
            </div>
          </section>

          <section
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
              <div class="experiment-panel">
                <h2>{{ experimentLocale.title }}</h2>
                <p class="panel-hint">{{ experimentLocale.hint }}</p>

                <div class="json-actions">
                  <button class="btn-primary" type="button" @click="saveCurrentExperimentRecord">
                    {{ experimentLocale.saveCurrent }}
                  </button>
                  <button class="btn-secondary" type="button" @click="exportCurrentCompareResultJson">
                    {{ experimentLocale.exportCurrentJson }}
                  </button>
                  <button class="btn-secondary" type="button" @click="exportCurrentCompareResultCsv">
                    {{ experimentLocale.exportCurrentCsv }}
                  </button>
                </div>

                <div class="json-actions">
                  <button class="btn-secondary" type="button" @click="exportAllExperimentRecordsJson">
                    {{ experimentLocale.exportAllJson }}
                  </button>
                  <button class="btn-secondary" type="button" @click="exportAllExperimentRecordsCsv">
                    {{ experimentLocale.exportAllCsv }}
                  </button>
                  <button class="btn-ghost" type="button" :disabled="experimentRecordCount === 0" @click="clearExperimentRecords">
                    {{ experimentLocale.clearAll }}
                  </button>
                </div>

                <div v-if="experimentStatus" class="template-status" :class="experimentStatusType">
                  {{ experimentStatus }}
                </div>

                <div v-if="experimentRecordCount === 0" class="empty-note">
                  {{ experimentLocale.empty }}
                </div>

                <div v-else class="experiment-record-list">
                  <article
                    v-for="record in experimentRecords"
                    :key="record.id"
                    class="experiment-record-card"
                    :class="{ 'search-hit': matchedExperimentRecordIds.includes(record.id) }"
                  >
                    <div class="experiment-record-head">
                      <strong>{{ experimentLocale.recordPrefix }} #{{ record.id }}</strong>
                      <span class="point-badge">{{ record.task_mode === 'chain' ? taskChainLocale.title : taskBuilderLocale.single }}</span>
                    </div>
                    <div class="task-line">
                      {{ experimentLocale.scene }}: {{ record.scene_name }}
                    </div>
                    <div class="task-line">
                      {{ t('task_stages') }}: {{ record.stage_count }} | {{ experimentLocale.obstacles }}: {{ record.obstacle_count }} | {{ record.grid_cols }}x{{ record.grid_rows }}
                    </div>
                    <div class="task-line">
                      {{ experimentLocale.route }}: {{ record.route_summary }}
                    </div>
                    <div class="task-line">
                      {{ experimentLocale.currentAlgorithm }}: {{ algorithmText(record.current_algorithm) }}
                    </div>
                    <div v-if="record.recommended_algorithm" class="task-line">
                      {{ experimentLocale.recommendedAlgorithm }}: {{ algorithmText(record.recommended_algorithm) }}
                    </div>
                    <div class="task-line">
                      {{ formatExperimentAlgorithms(record) }}
                    </div>
                    <div class="task-line task-time">
                      {{ experimentLocale.savedAt }}: {{ formatExperimentSavedAt(record.saved_at) }}
                    </div>
                    <div class="task-actions">
                      <button class="btn-secondary task-action-button" type="button" @click="exportExperimentRecord(record, 'json')">
                        JSON
                      </button>
                      <button class="btn-secondary task-action-button" type="button" @click="exportExperimentRecord(record, 'csv')">
                        CSV
                      </button>
                      <button class="btn-delete task-action-button" type="button" @click="deleteExperimentRecord(record.id)">
                        {{ experimentLocale.delete }}
                      </button>
                    </div>
                  </article>
                </div>
              </div>
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

    <div v-if="showGuideCenter" class="guide-modal-mask" @click.self="closeGuideCenter">
      <section class="guide-modal" role="dialog" aria-modal="true">
        <header class="guide-modal-header">
          <strong>{{ guideCenterLocale.title }}</strong>
          <button class="btn-ghost" type="button" @click="closeGuideCenter">
            {{ guideCenterLocale.close }}
          </button>
        </header>
        <div class="guide-modal-body">
          <div class="guide-section">
            <div class="guide-section-title">{{ guideCenterLocale.modeTitle }}</div>
            <div class="guide-line">
              {{ guideCenterLocale.modeAutoTitle }}：{{ panelLocale.modeAutoHint }}
            </div>
            <div class="guide-line">
              {{ guideCenterLocale.modeManualTitle }}：{{ panelLocale.modeManualHint }}
            </div>
          </div>
          <div class="guide-section">
            <div class="guide-section-title">{{ guideCenterLocale.shortcutsTitle }}</div>
            <div class="guide-line">{{ guideCenterLocale.shortcutCancel }}</div>
            <div class="guide-line">{{ guideCenterLocale.shortcutAlgorithm }}</div>
            <div class="guide-line">{{ guideCenterLocale.shortcutContext }}</div>
          </div>
          <div class="guide-section">
            <div class="guide-section-title">{{ guideCenterLocale.workflowTitle }}</div>
            <div class="guide-line">{{ guideCenterLocale.workflowAuto }}</div>
            <div class="guide-line">{{ guideCenterLocale.workflowManual }}</div>
            <div class="guide-line">{{ guideCenterLocale.workflowForm }}</div>
          </div>
        </div>
      </section>
    </div>

    <div
      v-if="compareDisplayMode === 'floating' && showFloatingCompare"
      class="floating-compare-panel"
      :style="compareFloatingStyle"
    >
      <div class="floating-compare-head" @mousedown="startFloatingCompareDrag">
        <div>
          <span class="dispatch-summary-label">{{ algorithmCompareLocale.title }}</span>
          <strong>{{ taskBuilderMode === 'chain' ? taskChainLocale.title : currentTaskBuilderModeCompactLabel }}</strong>
        </div>
        <button class="btn-ghost" type="button" @mousedown.stop @click="closeFloatingCompare">×</button>
      </div>
      <p class="panel-hint">{{ currentCompareHint }}</p>
      <div class="algorithm-compare-actions">
        <button class="btn-secondary" type="button" :disabled="pathCompareLoading" @click="compareCurrentRoute">
          {{ pathCompareLoading ? '...' : algorithmCompareLocale.run }}
        </button>
      </div>
      <div v-if="pathCompareError" class="template-status error">{{ pathCompareError }}</div>
      <div v-else-if="pathCompareResult" class="algorithm-compare-grid">
        <article
          v-for="entry in compareResultEntries"
          :key="entry[0]"
          class="algorithm-compare-card"
          :class="{
            active: algorithm === entry[0],
            recommended: recommendedCompareAlgorithm === entry[0]
          }"
        >
          <div class="algorithm-compare-card-head">
            <strong>{{ algorithmText(entry[0]) }}</strong>
            <button class="btn-ghost" type="button" @click="applyComparedAlgorithm(entry[0])">
              {{ compareResultBadgeText(entry[0]) }}
            </button>
          </div>
          <div class="task-line">
            {{ formatCompareResultStatus(entry[1]) }}
          </div>
          <div class="task-line">
            {{ algorithmCompareLocale.total }}:
            {{ entry[1].total_length ?? '--' }}
          </div>
          <div class="task-line">
            {{ algorithmCompareLocale.stages }}:
            {{ formatCompareStageLengths(entry[1]) || '--' }}
          </div>
          <div v-if="entry[1].failed_stage_index !== null" class="task-line task-reason">
            {{ algorithmCompareLocale.failedStage }}: {{ Number(entry[1].failed_stage_index) + 1 }}
          </div>
        </article>
      </div>
      <div v-if="pathCompareResult" class="json-actions">
        <button class="btn-primary" type="button" @click="saveCurrentExperimentRecord">
          {{ experimentLocale.saveCurrent }}
        </button>
        <button class="btn-secondary" type="button" @click="exportCurrentCompareResultJson">
          {{ experimentLocale.exportCurrentJson }}
        </button>
        <button class="btn-secondary" type="button" @click="exportCurrentCompareResultCsv">
          {{ experimentLocale.exportCurrentCsv }}
        </button>
      </div>
    </div>
  </div>
</template>

