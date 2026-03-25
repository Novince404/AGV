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
import { downloadJsonFile } from './utils/fileDownload'
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
const AuthDialog = defineAsyncComponent(() => import('./components/AuthDialog.vue'))
const OperationsAuditPanel = defineAsyncComponent(() => import('./components/OperationsAuditPanel.vue'))
const AlgorithmCompareWorkspace = defineAsyncComponent(() => import('./components/AlgorithmCompareWorkspace.vue'))
const ExperimentRecordsPanel = defineAsyncComponent(() => import('./components/ExperimentRecordsPanel.vue'))

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
const ENTERPRISE_SETTINGS_TAB_STORAGE_KEY = 'agv_enterprise_settings_tabs'
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

const manualPathToStart = ref([])
const manualPathToEnd = ref([])
const autoPathToStart = ref([])
const autoPathToEnd = ref([])
const layoutRef = ref(null)
const mapSettingsPanelRef = ref(null)
const mapViewportRef = ref(null)
const minimapRef = ref(null)
const panelRef = ref(null)
const compareEntryButtonRef = ref(null)
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

const {
  authPanelOpen,
  authLoading,
  authInitialized,
  authUsername,
  authPassword,
  demoAccounts: authDemoAccounts,
  isAuthenticated: authAuthenticated,
  currentUser: authCurrentUser,
  currentRole: authCurrentRole,
  currentDisplayName: authCurrentDisplayName,
  currentAccountStatus: authCurrentAccountStatus,
  currentOrganizationName: authCurrentOrganizationName,
  currentCapabilities: authCurrentCapabilities,
  currentCapabilityGroups: authCurrentCapabilityGroups,
  buildAuthHeaders,
  fetchAuthMe,
  login: loginWithAuthSession,
  logout: logoutFromAuthSession,
  fillDemoAccount
} = useAuthSession({
  API_BASE,
  createApiError
})

const authGuestAccepted = ref(false)
const authDialogView = ref('login')
const authEnterpriseRegisterLoading = ref(false)
const authEnterpriseRegisterForm = ref({
  company_name: '',
  contact_name: '',
  contact_email: '',
  username: '',
  password: ''
})
const enterpriseApprovalDialogOpen = ref(false)
const enterpriseApprovalLoading = ref(false)
const enterpriseApprovalReviewLoading = ref(false)
const enterpriseApprovalStatusFilter = ref('pending')
const enterpriseApprovalSummary = ref({ all: 0, pending: 0, approved: 0, rejected: 0 })
const enterpriseApplications = ref([])
const selectedEnterpriseApplicationId = ref(null)
const enterpriseApprovalReviewNote = ref('')
const enterpriseSettingsDialogOpen = ref(false)
const enterpriseSettingsActiveTab = ref('overview')
const authRoleLabel = computed(() => t(`auth_role_${authCurrentRole.value}`))
const authRoleBadgeClass = computed(() => `role-${authCurrentRole.value}`)
const dashboardUnlocked = computed(() => authAuthenticated.value || authGuestAccepted.value)
const authModeText = computed(() =>
  authAuthenticated.value ? t(`auth_mode_${authCurrentRole.value}`) : t('auth_mode_guest')
)
const authEntryHintText = computed(() => {
  if (!authAuthenticated.value) return t('auth_entry_hint_guest')
  return t(`auth_entry_hint_${authCurrentRole.value}`)
})
const authAccountStatusLabel = computed(() => t(`auth_account_status_${authCurrentAccountStatus.value}`))
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
const authIsEnterpriseRole = computed(() =>
  ['enterprise_operator', 'enterprise_logistics', 'enterprise_admin'].includes(authCurrentRole.value)
)
const selectedEnterpriseApplication = computed(() =>
  enterpriseApplications.value.find(item => Number(item.id) === Number(selectedEnterpriseApplicationId.value)) || null
)
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
  const buildTab = (key, primary) => {
    const accessMode = enterpriseTabAccessMode(key)
    return {
      key,
      label: tabLabel(key),
      primary,
      accessMode,
      hint: enterpriseTabAccessHint(key, accessMode)
    }
  }
  if (authCurrentRole.value === 'enterprise_operator') {
    return [
      buildTab('overview', true),
      buildTab('runtime', true),
      buildTab('ai', false)
    ]
  }
  if (authCurrentRole.value === 'enterprise_logistics') {
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
    value: authRoleLabel.value
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
const enterpriseRoleFocus = computed(() => {
  if (authCurrentRole.value === 'enterprise_operator') {
    return {
      title: t('enterprise_settings_focus_operator_title'),
      hint: t('enterprise_settings_focus_operator_hint')
    }
  }
  if (authCurrentRole.value === 'enterprise_logistics') {
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
function enterpriseRoleWorkspaceSectionKeys(role = authCurrentRole.value) {
  if (role === 'enterprise_operator') return ['control', 'queue']
  if (role === 'enterprise_logistics') return ['templates', 'points', 'experiments']
  if (role === 'enterprise_admin') return ['operations', 'ai', 'control', 'queue']
  return ['control', 'queue']
}

function enterprisePanelPreset(role = authCurrentRole.value) {
  if (role === 'enterprise_operator') {
    return {
      control: true,
      queue: true,
      templates: false,
      points: false,
      json: false,
      experiments: false,
      ai: false,
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
      ai: false,
      operations: false
    }
  }
  if (role === 'enterprise_admin') {
    return {
      control: true,
      queue: true,
      templates: true,
      points: true,
      json: false,
      experiments: true,
      ai: true,
      operations: true
    }
  }
  return null
}

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
  if (authCurrentRole.value === 'enterprise_operator') return t('enterprise_settings_scope_operator')
  if (authCurrentRole.value === 'enterprise_logistics') return t('enterprise_settings_scope_logistics')
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
  if (authCurrentRole.value === 'enterprise_operator') {
    return {
      title: t('enterprise_settings_point_templates_focus_operator_title'),
      hint: t('enterprise_settings_point_templates_focus_operator_hint'),
      actions: [
        { key: 'queue', label: t('enterprise_settings_open_queue') },
        { key: 'templates', label: t('enterprise_settings_open_templates') }
      ]
    }
  }
  if (authCurrentRole.value === 'enterprise_logistics') {
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
  if (authCurrentRole.value === 'enterprise_operator') {
    return {
      title: t('enterprise_settings_runtime_focus_operator_title'),
      hint: t('enterprise_settings_runtime_focus_operator_hint'),
      actions: [
        { key: 'control', label: t('enterprise_settings_open_dispatch') },
        { key: 'queue', label: t('enterprise_settings_open_queue') }
      ]
    }
  }
  if (authCurrentRole.value === 'enterprise_logistics') {
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
    default:
      return String(action || '')
  }
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
  const resourceType = operationResourceLabel(entry?.resource_type)
  const resourceId = entry?.resource_id ? `#${entry.resource_id}` : ''
  return resourceId ? `${resourceType} ${resourceId}` : resourceType
}

function formatOperationAuditMetadata(entry) {
  const metadata = entry?.metadata
  if (!metadata || typeof metadata !== 'object') return ''

  const parts = []
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
  { value: 'agv', label: t('operations_resource_agv') }
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
  { value: 'render', label: t('operations_action_render') }
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

const displayAgvs = computed(() => {
  const backendAgvs = agvs.value
    .filter(agv => agv.status !== 'maintenance')
    .map(agv => ({ ...agv, source: 'backend' }))
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
        gridTemplateColumns: `minmax(0, 1fr) 10px ${panelWidth.value}px`
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
const blockedCellSet = computed(
  () => new Set(blockedCells.value.map(cell => `${cell.x},${cell.y}`))
)
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
const mapSizeLabel = computed(() => `${currentGridCols.value} x ${currentGridRows.value}`)
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
const faultLocale = computed(() => localeTexts.value.fault ?? LOCALE_TEXTS.en.fault)
const panelSummaryLocale = computed(() => localeTexts.value.panelSummary ?? LOCALE_TEXTS.en.panelSummary)
const settingsLocale = computed(() => localeTexts.value.settings ?? LOCALE_TEXTS.en.settings)
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
  return blockedCellSet.value.has(blockedCellKey(x, y))
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
    const nextRole = String(state?.user?.role || state?.role || '').trim()
    authGuestAccepted.value = Boolean(state?.authenticated)
    authPanelOpen.value = false
    authDialogView.value = 'login'
    if (nextRole.startsWith('enterprise_')) {
      applyEnterprisePanelPreset(nextRole, { silent: true })
    }
    await fetchOperationAudits({ force: true })
    showFloatingToast(buildAuthLoginSuccessMessage(state), 'success')
  } catch (error) {
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

function resetEnterpriseRegisterForm() {
  authEnterpriseRegisterForm.value = {
    company_name: '',
    contact_name: '',
    contact_email: '',
    username: '',
    password: ''
  }
}

function switchAuthDialogView(view) {
  authDialogView.value = view === 'enterprise-register' ? 'enterprise-register' : 'login'
}

async function handleEnterpriseRegister() {
  const payload = {
    company_name: String(authEnterpriseRegisterForm.value.company_name || '').trim(),
    contact_name: String(authEnterpriseRegisterForm.value.contact_name || '').trim(),
    contact_email: String(authEnterpriseRegisterForm.value.contact_email || '').trim(),
    username: String(authEnterpriseRegisterForm.value.username || '').trim(),
    password: String(authEnterpriseRegisterForm.value.password || '')
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

async function fetchEnterpriseApplications({ forceSelectFirst = false } = {}) {
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
    if (forceSelectFirst || !selectedEnterpriseApplication.value) {
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

async function openEnterpriseApprovalDialog() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'enterprise.approve', buildCapabilityDeniedMessage('platform'))) return
  enterpriseApprovalDialogOpen.value = true
  enterpriseApprovalReviewNote.value = ''
  await fetchEnterpriseApplications({ forceSelectFirst: true })
}

function closeEnterpriseApprovalDialog() {
  enterpriseApprovalDialogOpen.value = false
  enterpriseApprovalReviewNote.value = ''
}

function preferredEnterpriseSettingsTab(role = authCurrentRole.value) {
  if (role === 'enterprise_operator') return 'runtime'
  if (role === 'enterprise_logistics') return 'map_profiles'
  if (role === 'enterprise_admin') return 'audit'
  return 'overview'
}

function loadEnterpriseSettingsTabPreference(role = authCurrentRole.value) {
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

function saveEnterpriseSettingsTabPreference(role = authCurrentRole.value, tab = enterpriseSettingsActiveTab.value) {
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

function applyEnterprisePanelPreset(role = authCurrentRole.value, { silent = false } = {}) {
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
  if (!authIsEnterpriseRole.value) {
    showFloatingToast(t('enterprise_settings_requires_enterprise'), 'error')
    return
  }
  const availableKeys = enterpriseSettingsTabKeys.value
  const rememberedTab = loadEnterpriseSettingsTabPreference()
  const preferredTab = String(targetTab || '').trim() || rememberedTab || preferredEnterpriseSettingsTab()
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
  enterpriseSettingsDialogOpen.value = false
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

async function reviewEnterpriseApplication(decision) {
  const applicationId = Number(selectedEnterpriseApplicationId.value || 0)
  if (!applicationId) return
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
          review_note: String(enterpriseApprovalReviewNote.value || '').trim() || null
        })
      }
    )
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw createApiError(data, 'Enterprise application review failed')
    }
    enterpriseApprovalReviewNote.value = ''
    await fetchEnterpriseApplications({ forceSelectFirst: false })
    showFloatingToast(
      decision === 'reject' ? t('enterprise_approval_reject_success') : t('enterprise_approval_approve_success'),
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

function triggerTemplateFileImportWithAuth() {
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'template.write', buildCapabilityDeniedMessage('data'))) return
  triggerTemplateFileImport()
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
  triggerTemplateFileImport,
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
  panelSections.value = {
    control: expanded,
    queue: expanded,
    templates: expanded,
    points: expanded,
    json: expanded,
    experiments: expanded,
    ai: expanded,
    operations: expanded
  }
}

function hasIdleAgv() {
  return agvs.value.some(agv => agv.status === 'idle')
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
  if (locale.value === 'ja') return '障害セルは始点・終点・中継点に設定できません。'
  if (locale.value === 'zh') return '障碍格不能作为起点、终点或中转点。'
  return 'Blocked cells cannot be used as start, end, or transfer points.'
}

function onAgvClick(agv, event) {
  event.stopPropagation()
  if (agv.source !== 'backend') return
  mapDraftPrimedMode.value = null
  selectedAgvId.value = agv.id
  if (dispatchMode.value !== 'manual') return
  if (agv.status !== 'idle') return
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

  if (taskBuilderMode.value === 'single') {
    if (dispatchMode.value === 'auto') {
      preferredRuntimeDisplayMode.value = 'auto'
      mapDraftPrimedMode.value = 'auto'
      if (!autoDraftPicking.value && !startPoint.value) {
        endPoint.value = null
      }
    } else if (dispatchMode.value === 'manual' && selectedBackendAgv.value?.status === 'idle') {
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

async function importTasksFromJson() {
  if (!jsonText.value) return
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'json.write', buildCapabilityDeniedMessage('data'))) return
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
      headers: buildAuthorizedJsonHeaders(),
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
  if (!mapResizePreview.value && !mapResizePreviewDirty.value) {
    setMapResizePreviewDraft(currentGridCols.value, currentGridRows.value)
  }
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
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue(),
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
        blocked_cells: Array.isArray(data.blocked_cells) ? data.blocked_cells : []
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
  const blockedCells = normalizeBlockedCellList(
    rawCells
      .filter(cell => Number.isFinite(Number(cell?.x)) && Number.isFinite(Number(cell?.y)))
      .map(cell => ({
        x: Math.round(Number(cell.x)),
        y: Math.round(Number(cell.y))
      }))
  )

  return {
    name,
    description: String(profile.description ?? '').trim() || null,
    grid_cols: gridCols,
    grid_rows: gridRows,
    blocked_cells: blockedCells
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
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized)
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
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized)
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
  if (!ensureAuthenticatedOperation(t('auth_action_requires_login'), 'map.write', buildCapabilityDeniedMessage('map'))) return false
  if (!ensureObstacleMutationAllowed()) {
    return false
  }
  obstacleMapSaving.value = true
  try {
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(blockedCells.value)
    const res = await fetch(`${API_BASE}/status/map`, {
      method: 'PUT',
      headers: buildAuthorizedJsonHeaders(),
      body: JSON.stringify({
        blocked_cells: filtered,
        grid_cols: gridColsValue(),
        grid_rows: gridRowsValue()
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Save blocked cells failed')
    }
    applyGridSizeFromPayload(data)
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? filtered)
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    appliedObstacleSceneKey.value = detectObstacleSceneKey(normalized)
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
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value)
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
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value)
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
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    syncedBlockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
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
    appliedObstacleSceneKey.value = detectObstacleSceneKey(blockedCells.value)
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
      syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
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
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    syncedBlockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
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
    syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
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
    const { filtered, skipped } = filterBlockedCellsAgainstOccupied(normalized)
    blockedCells.value = filtered
    syncedBlockedCells.value = filtered
    appliedObstacleSceneKey.value = detectObstacleSceneKey(filtered)
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
    if (!rawCells) {
      throw new Error(invalidObstacleLayoutText())
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

  if (event.key === 'f' || event.key === 'F') {
    cancelSelection()
    return
  }

  if (event.key === 'r' || event.key === 'R') {
    event.preventDefault()
    toggleAlgorithmMode()
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

watch([authCurrentRole, authIsEnterpriseRole], ([role, isEnterprise]) => {
  if (!isEnterprise) {
    enterpriseSettingsDialogOpen.value = false
    enterpriseSettingsActiveTab.value = 'overview'
    return
  }
  if (!enterpriseSettingsTabKeys.value.includes(enterpriseSettingsActiveTab.value)) {
    enterpriseSettingsActiveTab.value = loadEnterpriseSettingsTabPreference(role) || preferredEnterpriseSettingsTab(role)
  }
})

watch([enterpriseSettingsActiveTab, authCurrentRole, authIsEnterpriseRole], ([tab, role, isEnterprise]) => {
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
  if (authenticated && canApprove) return
  enterpriseApprovalDialogOpen.value = false
  enterpriseApplications.value = []
  selectedEnterpriseApplicationId.value = null
  enterpriseApprovalReviewNote.value = ''
})

watch(enterpriseApprovalStatusFilter, () => {
  if (!enterpriseApprovalDialogOpen.value || !authCanEnterpriseApprove.value) return
  fetchEnterpriseApplications({ forceSelectFirst: true })
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

watch([showAutoPath, showMarkerIcons, showPathArrows, showStatusLegend, statusLegendLayout, statusLegendOpacity, showMinimap, compareDisplayMode, compareFloatingOpacity], () => {
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
      if (selectedBackendAgv.value.status === 'idle') {
        trackedManualTaskId.value = null
        manualDispatchStep.value = 'idle'
        clearManualDestination()
        return
      }
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
  authLoading,
  authCapabilityCards,
  authPrimaryAccounts,
  authDialogView,
  authUsername,
  authPassword,
  authDemoAccounts,
  authEnterpriseRegisterForm,
  authEnterpriseRegisterLoading,
  buildAuthCapabilityStateText,
  enterGuestMode,
  handleAuthLogout,
  handleAuthQuickLogin,
  switchAuthDialogView,
  handleAuthLogin,
  authDemoAccountLabel,
  handleAuthDemoFill,
  handleEnterpriseRegister
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
  operationAudits,
  filteredOperationAudits,
  matchedOperationAuditIds,
  buildOperationsHintText,
  formatInlineMessage,
  fetchOperationAudits,
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

const enterpriseApprovalDialogBindings = {
  t,
  enterpriseApprovalSummary,
  enterpriseApprovalStatusFilter,
  enterpriseApprovalLoading,
  enterpriseApplications,
  selectedEnterpriseApplicationId,
  selectedEnterpriseApplication,
  enterpriseApprovalReviewNote,
  enterpriseApprovalReviewLoading,
  closeEnterpriseApprovalDialog,
  fetchEnterpriseApplications,
  reviewEnterpriseApplication
}

const enterpriseSettingsDialogBindings = {
  t,
  authRoleLabel,
  enterpriseSettingsTabDefinitions,
  enterpriseSettingsActiveTab,
  enterpriseSettingsTabLabel,
  enterpriseActiveTabModeLabel,
  enterpriseActiveTabAccessLabel,
  enterpriseActiveTabAccessHint,
  enterpriseActiveTabModeHint,
  enterpriseRoleFocus,
  enterpriseRoleScopeText,
  enterpriseWorkspaceSectionLabels,
  enterpriseEnabledCapabilityCards,
  enterpriseReadonlyCapabilityCards,
  enterpriseOverviewCards,
  currentMapProfileLabel,
  currentDispatchModeLabel,
  enterpriseActiveTasks,
  enterpriseOpenFaults,
  enterpriseBusyAgvs,
  enterpriseRecentTasks,
  enterpriseRecentFaults,
  enterpriseRecentAuditEntries,
  enterprisePointTemplateActionScope,
  enterprisePointTemplateFocus,
  enterpriseRecentCustomPoints,
  enterpriseRecentCustomTemplates,
  enterpriseRuntimeActionScope,
  enterpriseRuntimeFocus,
  enterpriseAiActionScope,
  mapSizeLabel,
  blockedCellCount,
  mapProfiles,
  mapProfileActionSummary,
  pointLibrary,
  customPoints,
  taskTemplates,
  customTaskTemplates,
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
  operationAuditLoading,
  enterpriseFilteredAuditEntries,
  matchedOperationAuditIds,
  settingsLocale,
  authCanViewAudit,
  authCanAiRender,
  authCanMapWrite,
  mapProfileApplyingKey,
  mapProfileDeletingKey,
  mapProfileExportingKey,
  mapProfileImporting,
  closeEnterpriseSettingsDialog,
  switchEnterpriseSettingsTab,
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
  applyEnterprisePanelPreset,
  jumpFromEnterpriseSettings,
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
  buildAiRenderSharedTemplatesHintText,
  openComfyBuiltinTemplateOverview,
  applySelectedBuiltinComfyTemplate,
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
  if (clickTimer) clearTimeout(clickTimer)
  clearPreview()
  if (manualPreviewHoldTimer) clearTimeout(manualPreviewHoldTimer)
  if (mapPreviewFocusTimer) clearTimeout(mapPreviewFocusTimer)
  if (mapResizeSectionHighlightTimer) clearTimeout(mapResizeSectionHighlightTimer)
  if (mapResizeItemHighlightTimer) clearTimeout(mapResizeItemHighlightTimer)
  if (taskBuilderJumpTimer) clearTimeout(taskBuilderJumpTimer)
  if (agvRecoveryJumpTimer) clearTimeout(agvRecoveryJumpTimer)
  if (faultSelectedAgvPulseTimer) clearTimeout(faultSelectedAgvPulseTimer)
  hideFloatingToast()
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
    <AuthDialog v-if="showAuthDialog" :ui="authDialogBindings" />

    <EnterpriseApprovalDialog v-if="enterpriseApprovalDialogOpen" :ui="enterpriseApprovalDialogBindings" />

    <EnterpriseSettingsDialog v-if="enterpriseSettingsDialogOpen" :ui="enterpriseSettingsDialogBindings" />

    <div class="page-top" :style="pageTopStyle">
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
        v-if="authIsEnterpriseRole"
        class="toolbar-compare-entry toolbar-admin-entry"
        type="button"
        @click="openEnterpriseSettingsDialog()"
      >
        {{ t('enterprise_settings_entry') }}
      </button>
      <button
        v-if="authCanEnterpriseApprove"
        class="toolbar-compare-entry toolbar-admin-entry"
        type="button"
        @click="openEnterpriseApprovalDialog"
      >
        {{ t('enterprise_approval_entry') }}
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
            <div v-if="showMapSettings" ref="mapSettingsPanelRef" class="map-settings-panel">
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
              <div v-if="!authCanMapWrite" class="permission-gate-card compact">
                <div class="empty-note">
                  {{ buildCapabilityReadonlyHint('map') }}
                </div>
                <div v-if="buildEnterprisePanelReadonlyHint('map')" class="task-line permission-gate-extra">
                  {{ buildEnterprisePanelReadonlyHint('map') }}
                </div>
                <button class="btn-primary" type="button" @click="openAuthDialog">
                  {{ buildOperationsEntryActionText() }}
                </button>
              </div>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.obstacleGroup }}</div>
                <label class="map-setting-row">
                  <input
                    :checked="obstacleEditMode"
                    type="checkbox"
                    :disabled="!authCanMapWrite || obstacleMutationLocked"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @change="toggleObstacleEditModeWithAuth"
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
                    :disabled="!authCanMapWrite || obstacleMapSaving || obstacleMutationLocked || obstaclePresets.length === 0"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="applyObstaclePreset"
                  >
                    {{ settingsLocale.obstaclePresetApply }}
                  </button>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanMapWrite || obstacleMapSaving"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="saveCurrentObstaclePreset"
                  >
                    {{ settingsLocale.obstaclePresetSaveCustom }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="!authCanMapWrite || obstacleMapSaving || !selectedObstaclePresetDeletable"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="deleteSelectedObstaclePreset"
                  >
                    {{ settingsLocale.obstaclePresetDelete }}
                  </button>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanMapWrite || obstacleMapSaving || obstacleMutationLocked || !obstacleLayoutDirty"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
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
                    :disabled="!authCanMapWrite || obstacleMutationLocked"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="triggerObstacleLayoutImportWithAuth"
                  >
                    {{ settingsLocale.obstacleImport }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="!authCanMapWrite || obstacleMapSaving || obstacleMutationLocked"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="resetBlockedCellsToDefault"
                  >
                    {{ settingsLocale.obstacleReset }}
                  </button>
                  <button
                    v-if="importedObstacleLayoutPendingPreset"
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanMapWrite || obstacleMapSaving"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="saveImportedObstacleAsPreset"
                  >
                    {{ obstacleImportSaveAsPresetText() }}
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
                <div class="map-settings-subtitle">{{ settingsLocale.infoGroup }}</div>
                <div class="map-settings-info-grid">
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoSize }}</div>
                    <div class="map-settings-info-value">{{ mapSizeLabel }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoPreset }}</div>
                    <div class="map-settings-info-value">{{ currentObstaclePresetLabel }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoBlocked }}</div>
                    <div class="map-settings-info-value">{{ blockedCellCount }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoBackend }}</div>
                    <div class="map-settings-info-value">{{ uiSettingsBackendMode }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoProfile }}</div>
                    <div class="map-settings-info-value">{{ currentMapProfileLabel }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.mapInfoResizeCheck }}</div>
                    <div class="map-settings-info-value">{{ mapSizeResizeStatusLabel }}</div>
                  </div>
                </div>
                <p v-if="currentMapProfileDescription" class="panel-hint map-settings-hint">
                  {{ currentMapProfileDescription }}
                </p>
              </div>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.profileGroup }}</div>
                <p class="panel-hint map-settings-hint">{{ settingsLocale.profileGroupHint }}</p>
                <p v-if="previewedMapProfile" class="panel-hint map-settings-hint">
                  {{
                    settingsLocale.mapProfilePreviewTarget
                      .replace('{name}', localizedMapProfileField(previewedMapProfile.name) || previewedMapProfile.key)
                      .replace('{size}', `${previewedMapProfile.grid_cols} x ${previewedMapProfile.grid_rows}`)
                  }}
                </p>
                <div
                  v-if="mapProfileActionSummary"
                  class="map-profile-summary-card"
                  :class="{
                    'is-blocked': mapProfileActionSummary.type === 'blocked',
                    'is-forced': mapProfileActionSummary.type === 'forced'
                  }"
                >
                  <div class="map-profile-summary-title">{{ mapProfileActionSummaryTitle() }}</div>
                  <div class="map-profile-summary-text">
                    {{ mapProfileActionSummary.profileName }}
                  </div>
                  <div
                    v-if="mapProfileActionSummary.type === 'blocked' && mapProfileActionSummary.forceApplyAllowed"
                    class="map-profile-summary-text"
                  >
                    {{ settingsLocale.mapProfileSummaryForceHint }}
                  </div>
                  <ul
                    v-if="mapProfileActionSummary.type === 'blocked' && Array.isArray(mapProfileActionSummary.blockers)"
                    class="map-size-preview-list compact"
                  >
                    <li
                      v-for="reasonKey in mapProfileActionSummary.blockers"
                      :key="`summary-${reasonKey}`"
                    >
                      <button
                        type="button"
                        class="map-size-preview-reason-action"
                        @click.stop="focusMapResizeReasonKey(reasonKey)"
                      >
                        {{ buildMapResizeReasonItem(reasonKey).text }}
                      </button>
                    </li>
                  </ul>
                  <div
                    v-if="mapProfileActionSummary.type === 'forced'"
                    class="map-profile-summary-metrics"
                  >
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummaryPreviousProfile
                          .replace('{name}', mapProfileActionSummary.previousProfileName || '—')
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummaryNextProfile
                          .replace('{name}', mapProfileActionSummary.profileName || '—')
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummarySizeBefore
                          .replace('{size}', mapProfileActionSummary.previousSizeLabel || '—')
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummarySizeAfter
                          .replace('{size}', mapProfileActionSummary.nextSizeLabel || '—')
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummaryBlockedBefore
                          .replace('{count}', String(mapProfileActionSummary.previousBlockedCount ?? 0))
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummaryBlockedAfter
                          .replace('{count}', String(mapProfileActionSummary.nextBlockedCount ?? 0))
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummaryRelocated
                          .replace('{count}', String(mapProfileActionSummary.relocatedAgvs?.length ?? 0))
                      }}
                    </div>
                    <div class="map-profile-summary-metric">
                      {{
                        settingsLocale.mapProfileSummaryTrimmed
                          .replace('{count}', String(mapProfileActionSummary.trimmedBlockedCount ?? 0))
                      }}
                    </div>
                  </div>
                  <div
                    v-if="mapProfileActionSummary.type === 'forced'"
                    class="map-profile-summary-actions"
                  >
                    <button
                      type="button"
                      class="btn-ghost"
                      @click="exportMapProfileActionSummary"
                    >
                      {{ settingsLocale.mapProfileSummaryExport }}
                    </button>
                  </div>
                  <div
                    v-if="mapProfileActionSummary.type === 'forced' && mapProfileActionSummary.trimmedBlockedCells?.length"
                    class="map-profile-summary-text"
                  >
                    {{ settingsLocale.mapProfileSummaryTrimmedList }}
                  </div>
                  <ul
                    v-if="mapProfileActionSummary.type === 'forced' && mapProfileActionSummary.trimmedBlockedCells?.length"
                    class="map-size-preview-list compact"
                  >
                    <li
                      v-for="cell in mapProfileActionSummary.trimmedBlockedCells"
                      :key="`trimmed-${cell.x}-${cell.y}`"
                    >
                      <span>
                        ({{ cell.x }}, {{ cell.y }})
                      </span>
                    </li>
                  </ul>
                  <ul
                    v-if="mapProfileActionSummary.type === 'forced' && mapProfileActionSummary.relocatedAgvs?.length"
                    class="map-size-preview-list compact"
                  >
                    <li
                      v-for="item in mapProfileActionSummary.relocatedAgvs"
                      :key="`relocated-${item.id}`"
                    >
                      <button
                        type="button"
                        class="map-size-preview-detail-action"
                        @click.stop="focusMapPreviewCell(item.to)"
                      >
                        AGV #{{ item.id }} · ({{ item.from.x }}, {{ item.from.y }}) → ({{ item.to.x }}, {{ item.to.y }})
                      </button>
                    </li>
                  </ul>
                </div>
                <div class="map-settings-actions">
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanMapWrite || mapProfileSaving || mapProfileImporting"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="saveCurrentMapProfile"
                  >
                    {{ mapProfileSaving ? settingsLocale.mapProfileApplying : settingsLocale.mapProfileSave }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="!authCanMapWrite || mapProfileSaving || mapProfileImporting"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="triggerMapProfileImport"
                  >
                    {{ mapProfileImporting ? settingsLocale.mapProfileImporting : settingsLocale.mapProfileImport }}
                  </button>
                </div>
                <input
                  ref="mapProfileFileInputRef"
                  type="file"
                  accept="application/json,.json"
                  class="hidden-file-input"
                  @change="onMapProfileFileChange"
                />
                <div class="map-profile-grid">
                  <div
                    v-for="profile in mapProfiles"
                    :key="profile.key"
                    class="map-profile-card"
                    :class="{ 'is-current': isCurrentMapProfile(profile) }"
                  >
                    <div class="map-profile-head">
                      <div class="map-profile-name">{{ localizedMapProfileField(profile.name) }}</div>
                      <span v-if="isCurrentMapProfile(profile)" class="map-profile-badge">
                        {{ settingsLocale.mapProfileCurrent }}
                      </span>
                    </div>
                    <div class="map-profile-meta">
                      {{ profile.grid_cols }} x {{ profile.grid_rows }}
                    </div>
                    <div class="map-profile-desc">
                      {{ localizedMapProfileField(profile.description) }}
                    </div>
                    <div v-if="formatMapProfileCreatedBy(profile)" class="map-profile-operator">
                      {{ formatMapProfileCreatedBy(profile) }}
                    </div>
                    <div v-if="formatMapProfileLastOperator(profile)" class="map-profile-operator">
                      {{ formatMapProfileLastOperator(profile) }}
                    </div>
                    <div
                      v-if="mapProfilePreviewStatusText(profile)"
                      class="map-profile-preview-status"
                      :class="{
                        'is-ready': mapProfilePreviewStatus(profile) === 'ready',
                        'is-blocked': mapProfilePreviewStatus(profile) === 'blocked',
                        'is-current': mapProfilePreviewStatus(profile) === 'current'
                      }"
                    >
                      {{ mapProfilePreviewStatusText(profile) }}
                    </div>
                    <div
                      v-if="mapProfilePreviewReasonItems(profile).length > 0"
                      class="map-profile-preview-reasons"
                    >
                      <div class="map-profile-preview-reason-title">
                        {{ settingsLocale.mapProfilePreviewReasonTitle }}
                      </div>
                      <ul class="map-size-preview-list compact">
                        <li
                          v-for="reason in mapProfilePreviewReasonItems(profile)"
                          :key="`${profile.key}-${reason.key}`"
                        >
                          <button
                            type="button"
                            class="map-size-preview-reason-action"
                            @click.stop="focusMapResizeReasonItem(reason)"
                          >
                            {{ reason.text }}
                          </button>
                        </li>
                      </ul>
                    </div>
                    <div class="map-profile-actions">
                      <button
                        :class="canForceApplyMapProfile(profile) ? 'btn-danger' : 'btn-secondary'"
                        type="button"
                        :disabled="isCurrentMapProfile(profile) || Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting || !canApplyMapProfileWithCapability(profile)"
                        :title="buildMapProfileApplyTitle(profile)"
                        @click="applyMapProfile(profile)"
                      >
                        {{
                          isCurrentMapProfile(profile)
                            ? settingsLocale.mapProfileCurrent
                            : isMapProfileApplying(profile)
                              ? settingsLocale.mapProfileApplying
                            : canForceApplyMapProfile(profile)
                              ? settingsLocale.mapProfileForceApply
                              : settingsLocale.mapProfileApply
                        }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting || isMapProfilePreviewing(profile)"
                        @click="previewMapProfile(profile)"
                      >
                        {{
                          isMapProfilePreviewing(profile)
                            ? settingsLocale.mapProfilePreviewing
                            : settingsLocale.mapProfilePreview
                          }}
                      </button>
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting"
                        @click="exportMapProfile(profile)"
                      >
                        {{
                          isMapProfileExporting(profile)
                            ? settingsLocale.mapProfileExporting
                            : settingsLocale.mapProfileExport
                        }}
                      </button>
                      <button
                        v-if="profile.deletable"
                        class="btn-delete"
                        type="button"
                        :disabled="!authCanMapWrite || Boolean(mapProfileApplyingKey) || Boolean(mapProfileDeletingKey) || Boolean(mapProfileExportingKey) || mapProfileImporting"
                        :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                        @click="deleteMapProfile(profile)"
                      >
                        {{
                          isMapProfileDeleting(profile)
                            ? settingsLocale.mapProfileDeleting
                            : settingsLocale.mapProfileDelete
                        }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="map-settings-group">
                <div class="map-settings-subtitle">{{ settingsLocale.resizeGroup }}</div>
                <p class="panel-hint map-settings-hint">{{ settingsLocale.resizeGroupHint }}</p>
                <div class="map-settings-inline-grid">
                  <label class="map-settings-select-group">
                    <span class="map-settings-select-label">{{ settingsLocale.resizePreviewCols }}</span>
                    <input
                      v-model="mapResizePreviewColsInput"
                      class="map-settings-number-input"
                      type="number"
                      min="1"
                      step="1"
                      @input="markMapResizePreviewDirty"
                      @blur="normalizeMapResizePreviewInputs"
                    />
                  </label>
                  <label class="map-settings-select-group">
                    <span class="map-settings-select-label">{{ settingsLocale.resizePreviewRows }}</span>
                    <input
                      v-model="mapResizePreviewRowsInput"
                      class="map-settings-number-input"
                      type="number"
                      min="1"
                      step="1"
                      @input="markMapResizePreviewDirty"
                      @blur="normalizeMapResizePreviewInputs"
                    />
                  </label>
                </div>
                <div class="map-settings-actions">
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="mapResizePreviewLoading"
                    @click="runMapResizePrecheck()"
                  >
                    {{ settingsLocale.resizePreviewRun }}
                  </button>
                  <button
                    class="btn-primary"
                    type="button"
                    :disabled="!authCanMapWrite || mapResizePreviewLoading || !canApplyMapResize"
                    :title="buildCapabilityLockedTitle('map', authCanMapWrite)"
                    @click="applyMapResize"
                  >
                    {{ settingsLocale.resizeApply }}
                  </button>
                </div>
                <div class="map-settings-info-grid">
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewCurrent }}</div>
                    <div class="map-settings-info-value">{{ currentGridCols }} x {{ currentGridRows }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewRequested }}</div>
                    <div class="map-settings-info-value">{{ mapResizeRequestedSizeLabel }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewResult }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreviewStatusLabel }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewActiveTasks }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreview?.active_task_count ?? '—' }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewBusyAgvs }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreview?.busy_agv_count ?? '—' }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowAgvs }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreview?.agv_overflow_count ?? '—' }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowPoints }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreview?.point_overflow_count ?? '—' }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowTemplates }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreview?.template_overflow_count ?? '—' }}</div>
                  </div>
                  <div class="map-settings-info-card">
                    <div class="map-settings-info-label">{{ settingsLocale.resizePreviewOverflowObstacles }}</div>
                    <div class="map-settings-info-value">{{ mapResizePreview?.blocked_overflow_count ?? '—' }}</div>
                  </div>
                </div>
                <div
                  v-if="mapResizePreviewReasonItems.length > 0"
                  :id="mapResizeSectionDomId('reasons')"
                  class="map-size-preview-reasons"
                  :class="{ 'is-highlighted': mapResizeHighlightedSection === 'reasons' }"
                >
                  <div class="map-settings-select-label">{{ settingsLocale.resizePreviewReasonTitle }}</div>
                  <ul class="map-size-preview-list">
                    <li v-for="reason in mapResizePreviewReasonItems" :key="reason.key">
                      <button
                        type="button"
                        class="map-size-preview-reason-action"
                        @click.stop="focusMapResizeReasonItem(reason)"
                      >
                        {{ reason.text }}
                      </button>
                    </li>
                  </ul>
                </div>
                <div v-if="mapResizePreviewDetailSections.length > 0" class="map-size-preview-details">
                  <div class="map-settings-select-label">{{ settingsLocale.resizePreviewDetailTitle }}</div>
                  <div class="map-size-preview-detail-grid">
                    <article
                      v-for="section in mapResizePreviewDetailSections"
                      :key="section.key"
                      :id="mapResizeSectionDomId(section.key)"
                      class="map-size-preview-detail-card"
                      :class="{ 'is-highlighted': mapResizeHighlightedSection === section.key }"
                    >
                      <div class="map-size-preview-detail-title">{{ section.title }}</div>
                      <ul class="map-size-preview-list compact">
                        <li v-for="item in section.items" :key="item.key">
                          <button
                            v-if="item.focus"
                            type="button"
                            class="map-size-preview-detail-action"
                            :class="{ 'is-highlighted': mapResizeHighlightedItemKeys.includes(item.key) }"
                            :title="item.text"
                            @click="
                              highlightMapResizeItems([item.key]);
                              focusMapPreviewCell(item.focus)
                            "
                          >
                            {{ item.text }}
                          </button>
                          <span
                            v-else
                            :class="{ 'map-size-preview-detail-item-highlighted': mapResizeHighlightedItemKeys.includes(item.key) }"
                          >
                            {{ item.text }}
                          </span>
                        </li>
                      </ul>
                    </article>
                  </div>
                </div>
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
              :style="{
                left: `${agv.x * CELL_SIZE * minimapScale + (CELL_SIZE * minimapScale) / 2 - 4}px`,
                top: `${agv.y * CELL_SIZE * minimapScale + (CELL_SIZE * minimapScale) / 2 - 4}px`,
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
              <button
                class="dispatch-summary dispatch-summary-button dispatch-algorithm-note"
                type="button"
                @click="toggleAlgorithmMode"
              >
                <span class="dispatch-summary-label">{{ t('algorithm') }}</span>
                <strong>{{ algorithmText(algorithm) }}</strong>
                <p>{{ algorithmHintText }}</p>
              </button>

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
                  <AlgorithmCompareWorkspace :ui="algorithmCompareWorkspaceBindings" />
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
                <div v-if="!authCanFaultWrite" class="permission-gate-card">
                  <div class="empty-note">
                    {{ buildCapabilityReadonlyHint('fault') }}
                  </div>
                  <div v-if="buildEnterprisePanelReadonlyHint('fault')" class="task-line permission-gate-extra">
                    {{ buildEnterprisePanelReadonlyHint('fault') }}
                  </div>
                  <button class="btn-primary" type="button" @click="openAuthDialog">
                    {{ buildOperationsEntryActionText() }}
                  </button>
                </div>

                <template v-if="selectedBackendAgv">
                  <div
                    ref="faultSelectedAgvCardRef"
                    class="fault-selected-agv"
                    :class="{ 'recovery-focus': faultSelectedAgvPulse }"
                  >
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
                        :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id || selectedBackendAgv.status === 'fault'"
                        :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
                        @click="emergencyStopSelectedAgv"
                      >
                        {{ faultLocale.emergencyStop }}
                      </button>
                      <button
                        v-else
                        class="btn-secondary fault-action-button"
                        type="button"
                        :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id"
                        :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
                        @click="resumeSelectedAgv"
                      >
                        {{ faultLocale.resume }}
                      </button>
                      <button
                        class="btn-secondary fault-action-button"
                        type="button"
                        :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id"
                        :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
                        @click="showFaultReportForm = !showFaultReportForm"
                      >
                        {{ faultLocale.reportFault }}
                      </button>
                      <button
                        class="btn-secondary fault-action-button"
                        type="button"
                        :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id || ['running', 'relocating'].includes(selectedBackendAgv.status)"
                        :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
                        @click="moveSelectedAgvToMaintenance"
                      >
                        {{ moveToMaintenanceText() }}
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
                          :disabled="!authCanFaultWrite || agvActionLoadingId === selectedBackendAgv.id"
                          :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
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

                <div v-if="maintenanceBackendAgvs.length > 0" class="fault-maintenance-panel">
                  <div class="dispatch-summary-label">{{ maintenanceListTitleText() }}</div>
                  <div class="fault-maintenance-list">
                    <article v-for="maintenanceAgv in maintenanceBackendAgvs" :key="`maintenance-${maintenanceAgv.id}`" class="fault-maintenance-item">
                      <strong>AGV #{{ maintenanceAgv.id }}</strong>
                      <button
                        class="btn-secondary fault-action-button"
                        type="button"
                        :disabled="!authCanFaultWrite || agvActionLoadingId === maintenanceAgv.id"
                        :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
                        @click="returnAgvToService(maintenanceAgv.id)"
                      >
                        {{ returnToServiceText() }}
                      </button>
                    </article>
                  </div>
                </div>

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
                    <div v-if="formatFaultReportedBy(eventItem)" class="task-line">
                      {{ formatFaultReportedBy(eventItem) }}
                    </div>
                    <div v-if="eventItem.resolved_at" class="task-line task-time">
                      {{ faultLocale.resolvedAt }}: {{ eventItem.resolved_at }}
                    </div>
                    <div v-if="formatFaultResolvedBy(eventItem)" class="task-line">
                      {{ formatFaultResolvedBy(eventItem) }}
                    </div>
                    <div class="task-actions">
                      <button
                        v-if="eventItem.status !== 'resolved'"
                        class="btn-secondary task-action-button"
                        type="button"
                        :disabled="!authCanFaultWrite || resolvingFaultId === eventItem.id"
                        :title="buildCapabilityLockedTitle('fault', authCanFaultWrite)"
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
                <div v-if="!authCanDispatchWrite" class="permission-gate-card compact">
                  <div class="empty-note">
                    {{ buildCapabilityReadonlyHint('dispatch') }}
                  </div>
                  <div v-if="buildEnterprisePanelReadonlyHint('dispatch')" class="task-line permission-gate-extra">
                    {{ buildEnterprisePanelReadonlyHint('dispatch') }}
                  </div>
                  <button class="btn-primary" type="button" @click="openAuthDialog">
                    {{ buildOperationsEntryActionText() }}
                  </button>
                </div>
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
                    <input v-model.number="taskForm.start_x" type="number" min="0" :max="currentGridCols - 1" />
                    <label>{{ singleTaskStartLabelY }}</label>
                    <input v-model.number="taskForm.start_y" type="number" min="0" :max="currentGridRows - 1" />
                    <label>{{ singleTaskEndLabelX }}</label>
                    <input v-model.number="taskForm.end_x" type="number" min="0" :max="currentGridCols - 1" />
                    <label>{{ singleTaskEndLabelY }}</label>
                    <input v-model.number="taskForm.end_y" type="number" min="0" :max="currentGridRows - 1" />
                  </div>
                  <button
                    class="btn-primary full-width"
                    type="button"
                    :disabled="!authCanDispatchWrite || !manualDispatchReady"
                    :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                    @click="addTaskFromForm"
                  >
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
                      <input v-model.number="stage.start_x" type="number" min="0" :max="currentGridCols - 1" />
                      <label>{{ t('form_start_y') }}</label>
                      <input v-model.number="stage.start_y" type="number" min="0" :max="currentGridRows - 1" />
                      <label>{{ t('form_end_x') }}</label>
                      <input v-model.number="stage.end_x" type="number" min="0" :max="currentGridCols - 1" />
                      <label>{{ t('form_end_y') }}</label>
                      <input v-model.number="stage.end_y" type="number" min="0" :max="currentGridRows - 1" />
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
                    :disabled="!authCanDispatchWrite || taskChainStages.length < 2 || !manualDispatchReady"
                    :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
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
                <div v-if="!authCanDispatchWrite" class="permission-gate-card compact">
                  <div class="empty-note">
                    {{ buildCapabilityReadonlyHint('dispatch') }}
                  </div>
                  <div v-if="buildEnterprisePanelReadonlyHint('dispatch')" class="task-line permission-gate-extra">
                    {{ buildEnterprisePanelReadonlyHint('dispatch') }}
                  </div>
                  <button class="btn-primary" type="button" @click="openAuthDialog">
                    {{ buildOperationsEntryActionText() }}
                  </button>
                </div>
                <div class="queue-toolbar">
                  <button
                    class="queue-bulk-button"
                    :class="{ active: taskQueueViewFilter === 'all' }"
                    type="button"
                    @click="taskQueueViewFilter = 'all'"
                  >
                    {{ t('queue_filter_all') }}
                  </button>
                  <button
                    class="queue-bulk-button"
                    :class="{ active: taskQueueViewFilter === 'orphaned' }"
                    type="button"
                    @click="taskQueueViewFilter = 'orphaned'"
                  >
                    {{ t('queue_filter_orphaned') }} ({{ orphanedTaskCount }})
                  </button>
                  <button
                    class="queue-bulk-button danger"
                    type="button"
                    :disabled="!authCanDispatchWrite || orphanedTaskCount === 0"
                    :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                    @click="deleteOrphanedTasks"
                  >
                    {{ t('queue_clear_orphaned') }}
                  </button>
                </div>
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
                        :disabled="!authCanDispatchWrite || countRetryableBlockedTasks(group) === 0"
                        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
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
                      <button
                        v-if="group.key === 'finished'"
                        class="queue-bulk-button"
                        type="button"
                        @click="exportFinishedTasksToJson"
                      >
                        {{ t('queue_export_finished') }}
                      </button>
                      <button
                        v-if="group.key === 'finished'"
                        class="queue-bulk-button danger"
                        type="button"
                        :disabled="!authCanDispatchWrite"
                        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                        @click="deleteFinishedTasks"
                      >
                        {{ t('queue_delete_finished') }}
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
                        <div v-if="formatTaskCreatedBy(task)" class="task-line">{{ formatTaskCreatedBy(task) }}</div>
                        <div v-if="isTaskOrphaned(task)" class="task-line task-reason alert">
                          {{ t('task_orphaned_hint') }}
                        </div>
                        <div v-if="formatTaskPathStats(task)" class="task-line">{{ formatTaskPathStats(task) }}</div>
                        <div class="task-line task-reason" :class="{ alert: isTaskReasonAlert(task) }">
                          {{ t('dispatch_reason') }}: {{ formatDispatchReason(task) }}
                        </div>
                        <div v-if="formatTaskLastAction(task)" class="task-line task-last-action">
                          {{ taskLastActionLabel() }}: {{ formatTaskLastAction(task) }}
                        </div>
                        <div v-if="formatTaskLastOperator(task)" class="task-line task-last-action">
                          {{ formatTaskLastOperator(task) }}
                        </div>
                        <div v-if="formatTaskTime(task)" class="task-line task-time">
                          {{ formatTaskTime(task) }}
                        </div>
                        <div class="task-actions">
                          <button
                            v-if="isTaskDeletable(task)"
                            class="btn-delete task-action-button"
                            type="button"
                            :disabled="!authCanDispatchWrite"
                            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                            @click="deleteTask(task)"
                          >
                            {{ t('delete_task') }}
                          </button>
                          <button
                            v-if="task.status === 'blocked' && !isRecoveryRequiredTask(task) && isCellOccupiedTimeoutTask(task)"
                            class="btn-secondary task-action-button"
                            type="button"
                            :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id) || !task.preferred_agv_id"
                            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                            @click="retryBlockedTaskFromCurrent(task)"
                          >
                            {{ retryFromCurrentButtonText() }}
                          </button>
                          <button
                            v-if="task.status === 'blocked' && !isRecoveryRequiredTask(task)"
                            class="btn-secondary task-action-button"
                            type="button"
                            :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id)"
                            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                            @click="retryBlockedTaskWithAStar(task)"
                          >
                            {{ t('task_retry_astar') }}
                          </button>
                          <button
                            v-if="task.status === 'blocked' && isRecoveryRequiredTask(task)"
                            class="btn-secondary task-action-button"
                            type="button"
                            :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id) || !task.preferred_agv_id"
                            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                            @click="recoverBlockedTask(task, 'bound')"
                          >
                            {{ recoveryActionText('bound', task) }}
                          </button>
                          <button
                            v-if="task.status === 'blocked' && isRecoveryRequiredTask(task)"
                            class="btn-secondary task-action-button"
                            type="button"
                            :disabled="!authCanDispatchWrite || isTaskRecoveryBusy(task.id)"
                            :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                            @click="recoverBlockedTask(task, 'reassign')"
                          >
                            {{ recoveryActionText('reassign', task) }}
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
                <div v-if="!authCanTemplateWrite" class="permission-gate-card compact">
                  <div class="empty-note">
                    {{ buildCapabilityReadonlyHint('data') }}
                  </div>
                  <div v-if="buildEnterprisePanelReadonlyHint('data')" class="task-line permission-gate-extra">
                    {{ buildEnterprisePanelReadonlyHint('data') }}
                  </div>
                  <button class="btn-primary" type="button" @click="openAuthDialog">
                    {{ buildOperationsEntryActionText() }}
                  </button>
                </div>

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
                    <button
                      class="btn-primary full-width"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="saveCurrentTaskTemplateWithAuth"
                    >
                      {{ t('template_save_current') }}
                    </button>
                    <button
                      class="btn-secondary full-width"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="saveCurrentTaskChainTemplateWithAuth"
                    >
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
                  <div class="template-json-action-grid">
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="importTaskTemplatesFromJsonWithAuth"
                    >
                      {{ templateJsonLocale.import }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="triggerTemplateFileImportWithAuth"
                    >
                      {{ templateJsonLocale.importFile }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="exportTaskTemplatesToJsonWithAuth"
                    >
                      {{ templateJsonLocale.export }}
                    </button>
                    <button
                      class="btn-secondary"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="downloadTemplateJsonFileWithAuth"
                    >
                      {{ templateJsonLocale.downloadFile }}
                    </button>
                  </div>
                  <div class="template-json-action-stack">
                    <button
                      class="btn-ghost"
                      type="button"
                      :disabled="!authCanTemplateWrite"
                      :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                      @click="clearTemplateJsonTextWithAuth"
                    >
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
                      <button
                        class="btn-ghost"
                        type="button"
                        :disabled="!authCanDispatchWrite"
                        :title="buildCapabilityLockedTitle('dispatch', authCanDispatchWrite)"
                        @click="createTaskFromTemplateWithAuth(template)"
                      >
                        {{ t('template_run') }}
                      </button>
                      <button
                        v-if="template.custom"
                        class="btn-delete"
                        type="button"
                        :disabled="!authCanTemplateWrite"
                        :title="buildCapabilityLockedTitle('data', authCanTemplateWrite)"
                        @click="deleteTaskTemplateWithAuth(template)"
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
                <div v-if="!authCanPointWrite" class="permission-gate-card compact">
                  <div class="empty-note">
                    {{ buildCapabilityReadonlyHint('data') }}
                  </div>
                  <div v-if="buildEnterprisePanelReadonlyHint('data')" class="task-line permission-gate-extra">
                    {{ buildEnterprisePanelReadonlyHint('data') }}
                  </div>
                  <button class="btn-primary" type="button" @click="openAuthDialog">
                    {{ buildOperationsEntryActionText() }}
                  </button>
                </div>

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
                    <input v-model.number="customPointForm.x" type="number" min="0" :max="currentGridCols - 1" />
                    <label>{{ t('form_start_y') }}</label>
                    <input v-model.number="customPointForm.y" type="number" min="0" :max="currentGridRows - 1" />
                  </div>
                  <button
                    class="btn-primary full-width"
                    type="button"
                    :disabled="!authCanPointWrite"
                    :title="buildCapabilityLockedTitle('data', authCanPointWrite)"
                    @click="addCustomPointWithAuth"
                  >
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
                        :disabled="!authCanPointWrite"
                        :title="buildCapabilityLockedTitle('data', authCanPointWrite)"
                        @click="deleteCustomPointWithAuth(point)"
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
                <div v-if="!authCanJsonWrite" class="permission-gate-card compact">
                  <div class="empty-note">
                    {{ buildCapabilityReadonlyHint('data') }}
                  </div>
                  <div v-if="buildEnterprisePanelReadonlyHint('data')" class="task-line permission-gate-extra">
                    {{ buildEnterprisePanelReadonlyHint('data') }}
                  </div>
                  <button class="btn-primary" type="button" @click="openAuthDialog">
                    {{ buildOperationsEntryActionText() }}
                  </button>
                </div>
                <div class="json-example-grid">
                  <button class="btn-secondary" type="button" @click="fillTaskJsonExample('single')">
                    {{ taskJsonLocale.singleExample }}
                  </button>
                  <button class="btn-secondary" type="button" @click="fillTaskJsonExample('chain')">
                    {{ taskJsonLocale.chainExample }}
                  </button>
                  <button class="btn-ghost" type="button" @click="downloadTaskJsonExample('single')">
                    {{ taskJsonExampleFileLocale.singleDownload }}
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
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanJsonWrite"
                    :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
                    @click="importTasksFromJson"
                  >
                    {{ t('import_json') }}
                  </button>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="!authCanJsonWrite"
                    :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
                    @click="exportTasksToJsonWithAuth"
                  >
                    {{ t('export_json') }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="!authCanJsonWrite"
                    :title="buildCapabilityLockedTitle('data', authCanJsonWrite)"
                    @click="clearJsonTextWithAuth"
                  >
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
              <ExperimentRecordsPanel :ui="experimentRecordsPanelBindings" />
            </div>
          </section>

          <section
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
      <div class="algorithm-compare-actions">
        <button class="btn-secondary" type="button" :disabled="pathCompareLoading" @click="compareCurrentRoute">
          {{ pathCompareLoading ? '...' : algorithmCompareLocale.run }}
        </button>
      </div>
      <AlgorithmCompareWorkspace :ui="algorithmCompareWorkspaceBindings" />
    </div>
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


