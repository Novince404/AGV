<script setup>
import './assets/agv-map.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

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
const taskChainStages = ref(buildDefaultTaskChainStages())
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
const pathCompareResult = ref(null)
const pathCompareLoading = ref(false)
const pathCompareError = ref('')
const templateFileInputRef = ref(null)
const panelSearch = ref('')
const focusedPanelSection = ref('')
const panelSummaryMode = ref('compact')
const panelSections = ref({
  control: true,
  queue: true,
  templates: false,
  points: false,
  json: false
})
const queueGroupsCollapsed = ref(buildDefaultQueueGroupState())
const taskCardCollapsed = ref({})
const summaryZoomArmed = ref(false)

const selectedAgvId = ref(null)
const startPoint = ref(null)
const endPoint = ref(null)
const showDispatchHelp = ref(false)
const dispatchHelpPinned = ref(false)

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
const comparePanelRef = ref(null)
const queueSectionRef = ref(null)
const templatesSectionRef = ref(null)
const pointsSectionRef = ref(null)
const jsonSectionRef = ref(null)
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
const showMarkerIcons = ref(true)
const showPathArrows = ref(false)
const showMinimap = ref(true)
const obstacleEditMode = ref(false)
const obstacleMapSaving = ref(false)
const syncedBlockedCells = ref([...DEFAULT_BLOCKED_CELLS])
const obstaclePresets = ref([])
const selectedObstaclePreset = ref('default_shelves')
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
let dispatchHelpTimer = null
let templateApplyClickTimer = null
let taskBuilderJumpTimer = null
let localNextId = 1000
let autoScheduling = false
let polling = false
let mapResizeObserver = null
let mapViewReady = false
let mapPanCandidate = false
let mapPanMoved = false
let mapPanStartX = 0
let mapPanStartY = 0
let mapPanOriginX = 0
let mapPanOriginY = 0
let ignoreNextMapClick = false
let isMinimapDragging = false
let isPanelResizing = false
let panelResizeStartX = 0
let panelResizeStartWidth = 0
let panelSectionFocusTimer = null
let obstaclePaintActive = false
let obstaclePaintMode = 'add'
let obstaclePaintLastKey = ''
let compareFloatingDragging = false
let compareFloatingDragOffsetX = 0
let compareFloatingDragOffsetY = 0
let floatingCompareRefreshTimer = null

const messages = {
  zh: {
    title: 'AGV 状态监控',
    dispatch: '调度模式',
    dispatch_auto: '自动',
    dispatch_manual: '手动',
    dispatch_help_trigger: '点击或悬停查看模式说明',
    dispatch_help_title: '模式说明',
    dispatch_help_auto: '自动调度：设置任务起点和终点后，系统会按优先级和距离自动选择空闲 AGV，并先前往起点再执行任务。',
    dispatch_help_manual: '手动调车：先选中一台空闲 AGV，再点击目标格，这台车会按你的指定前往目标位置。',
    dispatch_help_form: '任务表单和 JSON 导入更适合自动调度；手动模式主要用于临时指定车辆执行简单移动。',
    algorithm: '路径算法',
    algo_simple: '直线路径',
    algo_astar: 'A*',
    selected: '当前选中',
    selected_none: '无',
    hint: '自动模式按优先级和距离调度。手动模式先选 AGV 再点终点。双击空地可新增本地 AGV。',
    tasks: '任务队列',
    tasks_empty: '暂无任务',
    task_start: '起点',
    task_end: '终点',
    task_agv: 'AGV',
    task_priority: '优先级',
    task_pending: '未分配',
    task_blocked: '不可达',
    task_assigned: '已分配',
    task_running: '执行中',
    task_finished: '已完成',
    confirm_dispatch: '确认调度该小车前往目标点吗？',
    status_idle: '空闲',
    status_relocating: '就位中',
    status_relocating_desc: 'AGV 正在前往任务起点，尚未开始执行任务。',
    status_running: '运行中',
    status_fault: '故障',
    language: '语言',
    priority: '任务优先级',
    agv_status: 'AGV 状态',
    show_auto_path: '显示自动路径',
    map_settings: '地图显示',
    map_settings_toggle: '显示设置',
    map_reset_view: '重置视图',
    map_setting_icons: '显示起点/终点图标',
    map_setting_arrows: '显示路径方向箭头',
    panel_back_to_top: '回到顶部',
    map_overview: '地图总览',
    delete_task: '删除',
    task_retry_astar: '改用 A*',
    task_retry_astar_queued: '任务已切换为 A*，将在 AGV 空闲后自动重试。',
    confirm_delete_task: '确认删除该未分配或不可达任务吗？',
    task_form: '任务添加',
    form_start_x: '起点X',
    form_start_y: '起点Y',
    form_end_x: '终点X',
    form_end_y: '终点Y',
    add_task: '添加任务',
    template_library: '任务模板',
    template_hint: '保存高频任务，后续可一键载入表单或直接创建任务。',
    template_manage: '保存当前表单',
    template_name: '模板名称',
    template_name_placeholder: '例如：入库A到装配1',
    template_save_current: '保存当前为模板',
    template_apply: '载入表单',
    template_run: '直接创建',
    template_delete: '删除模板',
    template_form_saved: '模板已保存',
    template_form_deleted: '模板已删除',
    template_form_invalid_name: '请填写模板名称',
    confirm_delete_template: '确认删除这个自定义模板吗？',
    template_builtin: '预设',
    template_custom: '自定义',
    template_name_inbound_a_to_storage_c1: '入库口A到存储区C1',
    template_name_inbound_b_to_storage_c2: '入库口B到存储区C2',
    template_name_storage_c1_to_assembly_1: '存储区C1到装配台1',
    template_name_assembly_1_to_outbound_a: '装配台1到出库口A',
    json_tools: 'JSON 导入/导出',
    import_json: '导入',
    export_json: '导出',
    clear_json: '清空',
    json_placeholder: '粘贴 JSON，例如 { "tasks": [...] }',
    json_import_ok: '导入成功',
    json_import_fail: '导入失败',
    queue_pending: '待分配队列',
    queue_blocked: '不可达队列',
    queue_retry_all_astar: '一键 A*',
    queue_assigned: '已分配队列',
    queue_running: '执行队列',
    queue_finished: '完成队列',
    queue_empty: '当前分组为空',
    dispatch_reason: '调度说明',
    dispatch_waiting: '等待空闲 AGV 调度',
    dispatch_blocked: '当前算法下不可达，请切换算法或修改点位',
    reason_distance: '距起点',
    reason_algorithm: '算法',
    reason_mode: '方式',
    reason_auto: '自动',
    reason_manual: '手动',
    point_library: '常用点位',
    point_fill_hint: '点击按钮可快速写入任务表单',
    point_manage: '自定义点位',
    point_manage_hint: '新增常用取货点、装配点或临时作业点，刷新页面后仍会保留在本机。',
    point_search_placeholder: '搜索点位名称、分区或坐标',
    point_search_empty: '没有匹配点位',
    point_apply_start: '设为起点',
    point_apply_end: '设为终点',
    point_add: '保存点位',
    point_delete: '删除点位',
    point_custom: '自定义',
    point_builtin: '预设',
    point_form_name: '点位名称',
    point_form_zone: '所属分区',
    point_form_name_placeholder: '例如：备料台 A',
    point_form_zone_placeholder: '例如：装配区',
    point_form_saved: '点位已保存',
    point_form_deleted: '点位已删除',
    point_form_invalid_name: '请填写点位名称和分区',
    point_form_invalid_coords: '坐标超出地图范围',
    task_blocked_alert: '当前算法下路径不可达，任务已移入不可达队列。',
    task_manual_unreachable: '当前算法下无法到达，请切换算法或修改点位。',
    confirm_delete_point: '确认删除这个自定义点位吗？',
    point_category: '分区',
    point_coords: '坐标',
    point_name_inbound_a: '入库口 A',
    point_name_inbound_b: '入库口 B',
    point_name_outbound_a: '出库口 A',
    point_name_outbound_b: '出库口 B',
    point_name_storage_c1: '存储区 C1',
    point_name_storage_c2: '存储区 C2',
    point_name_assembly_1: '装配台 1',
    point_name_assembly_2: '装配台 2',
    point_name_charge: '充电区',
    point_name_maintenance: '维护区',
    point_zone_inbound: '入库',
    point_zone_outbound: '出库',
    point_zone_storage: '存储',
    point_zone_assembly: '装配',
    point_zone_service: '服务',
    time_created: '创建',
    time_assigned: '分配',
    time_started: '开始',
    time_finished: '完成'
  },
  ja: {
    title: 'AGV 状態モニター',
    dispatch: '割当モード',
    dispatch_auto: '自動',
    dispatch_manual: '手動',
    dispatch_help_trigger: 'クリックまたはホバーでモード説明を表示',
    dispatch_help_title: 'モード説明',
    dispatch_help_auto: '自動調度：タスクの始点と終点を設定すると、優先度と距離に基づいて空き AGV を自動選択し、始点へ移動してから実行します。',
    dispatch_help_manual: '手動調車：空き AGV を1台選択してから目標マスをクリックすると、その車両だけを指定位置へ向かわせます。',
    dispatch_help_form: 'タスク入力欄と JSON 取込は自動調度向きです。手動モードは臨時の単純移動に使います。',
    algorithm: '経路アルゴリズム',
    algo_simple: '直線',
    algo_astar: 'A*',
    selected: '選択中',
    selected_none: 'なし',
    hint: '自動モードは優先度と距離で割当。手動モードは AGV を選択してから終点を指定。空白ダブルクリックでローカル AGV を追加。',
    tasks: 'タスクキュー',
    tasks_empty: 'タスクなし',
    task_start: '始点',
    task_end: '終点',
    task_agv: 'AGV',
    task_priority: '優先度',
    task_pending: '未割当',
    task_blocked: '到達不可',
    task_assigned: '割当済',
    task_running: '実行中',
    task_finished: '完了',
    confirm_dispatch: 'この AGV を目的地へ向かわせますか？',
    status_idle: '待機',
    status_relocating: '就位中',
    status_relocating_desc: 'AGV はタスク開始地点へ移動中で、まだ実行を開始していません。',
    status_running: '走行中',
    status_fault: '故障',
    language: '言語',
    priority: 'タスク優先度',
    agv_status: 'AGV 状態',
    show_auto_path: '自動経路を表示',
    map_settings: 'マップ表示',
    map_settings_toggle: '表示設定',
    map_reset_view: 'ビューを初期化',
    map_setting_icons: '始点/終点アイコンを表示',
    map_setting_arrows: '経路方向の矢印を表示',
    panel_back_to_top: '先頭へ戻る',
    map_overview: 'マップ全体',
    delete_task: '削除',
    task_retry_astar: 'A*で再試行',
    task_retry_astar_queued: 'タスクを A* に切り替えました。AGV が空き次第、自動で再試行します。',
    confirm_delete_task: 'この未割当または到達不可タスクを削除しますか？',
    task_form: 'タスク追加',
    form_start_x: '始点X',
    form_start_y: '始点Y',
    form_end_x: '終点X',
    form_end_y: '終点Y',
    add_task: '追加',
    template_library: 'タスクテンプレート',
    template_hint: 'よく使うタスクを保存し、次回は入力欄へ反映またはそのまま作成できます。',
    template_manage: '現在の入力を保存',
    template_name: 'テンプレート名',
    template_name_placeholder: '例：搬入口Aから組立1へ',
    template_save_current: '現在内容を保存',
    template_apply: '入力欄へ反映',
    template_run: 'そのまま作成',
    template_delete: '削除',
    template_form_saved: 'テンプレートを保存しました',
    template_form_deleted: 'テンプレートを削除しました',
    template_form_invalid_name: 'テンプレート名を入力してください',
    confirm_delete_template: 'このカスタムテンプレートを削除しますか？',
    template_builtin: '既定',
    template_custom: 'カスタム',
    template_name_inbound_a_to_storage_c1: '搬入口Aから保管C1へ',
    template_name_inbound_b_to_storage_c2: '搬入口Bから保管C2へ',
    template_name_storage_c1_to_assembly_1: '保管C1から組立1へ',
    template_name_assembly_1_to_outbound_a: '組立1から搬出口Aへ',
    json_tools: 'JSON 取込/出力',
    import_json: '取込',
    export_json: '出力',
    clear_json: 'クリア',
    json_placeholder: 'JSON を貼り付け { "tasks": [...] }',
    json_import_ok: '取込成功',
    json_import_fail: '取込失敗',
    queue_pending: '未割当キュー',
    queue_blocked: '到達不可キュー',
    queue_retry_all_astar: '一括 A*',
    queue_assigned: '割当済キュー',
    queue_running: '実行キュー',
    queue_finished: '完了キュー',
    queue_empty: 'このグループは空です',
    dispatch_reason: '割当理由',
    dispatch_waiting: '空き AGV を待機中',
    dispatch_blocked: '現在のアルゴリズムでは到達できません。アルゴリズムを切り替えるか点位を修正してください。',
    reason_distance: '開始点まで',
    reason_algorithm: 'アルゴリズム',
    reason_mode: '方式',
    reason_auto: '自動',
    reason_manual: '手動',
    point_library: '共通ポイント',
    point_fill_hint: 'ボタンでタスク入力欄にすばやく反映します',
    point_manage: 'カスタムポイント',
    point_manage_hint: 'よく使う搬送点や一時作業点を追加できます。ページ更新後もこの端末に保持されます。',
    point_search_placeholder: '名称・エリア・座標で検索',
    point_search_empty: '一致するポイントがありません',
    point_apply_start: '始点に設定',
    point_apply_end: '終点に設定',
    point_add: 'ポイント保存',
    point_delete: '削除',
    point_custom: 'カスタム',
    point_builtin: '既定',
    point_form_name: 'ポイント名',
    point_form_zone: 'エリア',
    point_form_name_placeholder: '例：段取り台 A',
    point_form_zone_placeholder: '例：組立区',
    point_form_saved: 'ポイントを保存しました',
    point_form_deleted: 'ポイントを削除しました',
    point_form_invalid_name: 'ポイント名とエリアを入力してください',
    point_form_invalid_coords: '座標がマップ範囲外です',
    task_blocked_alert: '現在のアルゴリズムでは到達できないため、タスクを到達不可キューへ移動しました。',
    task_manual_unreachable: '現在のアルゴリズムでは到達できません。アルゴリズムを切り替えるか点位を修正してください。',
    confirm_delete_point: 'このカスタムポイントを削除しますか？',
    point_category: 'エリア',
    point_coords: '座標',
    point_name_inbound_a: '搬入口 A',
    point_name_inbound_b: '搬入口 B',
    point_name_outbound_a: '搬出口 A',
    point_name_outbound_b: '搬出口 B',
    point_name_storage_c1: '保管区画 C1',
    point_name_storage_c2: '保管区画 C2',
    point_name_assembly_1: '組立台 1',
    point_name_assembly_2: '組立台 2',
    point_name_charge: '充電エリア',
    point_name_maintenance: '保守エリア',
    point_zone_inbound: '搬入',
    point_zone_outbound: '搬出',
    point_zone_storage: '保管',
    point_zone_assembly: '組立',
    point_zone_service: 'サービス',
    time_created: '作成',
    time_assigned: '割当',
    time_started: '開始',
    time_finished: '完了'
  },
  en: {
    title: 'AGV Status Monitor',
    dispatch: 'Dispatch',
    dispatch_auto: 'Auto',
    dispatch_manual: 'Manual',
    dispatch_help_trigger: 'Click or hover to view mode details',
    dispatch_help_title: 'Mode Details',
    dispatch_help_auto: 'Auto dispatch: after you set task start and end, the system selects an idle AGV by priority and distance, then moves to the start before executing.',
    dispatch_help_manual: 'Manual dispatch: select one idle AGV first, then click a target cell to send only that vehicle to the specified position.',
    dispatch_help_form: 'The task form and JSON import are mainly for auto dispatch. Manual mode is intended for temporary vehicle relocation.',
    algorithm: 'Algorithm',
    algo_simple: 'Simple',
    algo_astar: 'A*',
    selected: 'Selected',
    selected_none: 'None',
    hint: 'Auto mode schedules by priority and distance. Manual mode selects an AGV first, then the destination. Double-click empty cells to add local AGVs.',
    tasks: 'Task Queue',
    tasks_empty: 'No tasks',
    task_start: 'Start',
    task_end: 'End',
    task_agv: 'AGV',
    task_priority: 'Priority',
    task_pending: 'Pending',
    task_blocked: 'Blocked',
    task_assigned: 'Assigned',
    task_running: 'Running',
    task_finished: 'Finished',
    confirm_dispatch: 'Confirm dispatch to the target point?',
    status_idle: 'Idle',
    status_relocating: 'Relocating',
    status_relocating_desc: 'AGV is moving to the task start before execution.',
    status_running: 'Running',
    status_fault: 'Fault',
    language: 'Language',
    priority: 'Task Priority',
    agv_status: 'AGV Status',
    show_auto_path: 'Show Auto Paths',
    map_settings: 'Map Display',
    map_settings_toggle: 'Display Settings',
    map_reset_view: 'Reset View',
    map_setting_icons: 'Show Start/End Icons',
    map_setting_arrows: 'Show Path Direction Arrows',
    panel_back_to_top: 'Back To Top',
    map_overview: 'Map Overview',
    delete_task: 'Delete',
    task_retry_astar: 'Retry with A*',
    task_retry_astar_queued: 'The task has been switched to A* and will retry automatically when an AGV becomes idle.',
    confirm_delete_task: 'Delete this pending or blocked task?',
    task_form: 'Add Task',
    form_start_x: 'Start X',
    form_start_y: 'Start Y',
    form_end_x: 'End X',
    form_end_y: 'End Y',
    add_task: 'Add Task',
    template_library: 'Task Templates',
    template_hint: 'Save frequent tasks so you can load them into the form or create them directly later.',
    template_manage: 'Save Current Form',
    template_name: 'Template Name',
    template_name_placeholder: 'Example: Inbound A to Assembly 1',
    template_save_current: 'Save Current As Template',
    template_apply: 'Load To Form',
    template_run: 'Create Now',
    template_delete: 'Delete Template',
    template_form_saved: 'Template saved',
    template_form_deleted: 'Template deleted',
    template_form_invalid_name: 'Please enter a template name',
    confirm_delete_template: 'Delete this custom template?',
    template_builtin: 'Built-in',
    template_custom: 'Custom',
    template_name_inbound_a_to_storage_c1: 'Inbound A to Storage C1',
    template_name_inbound_b_to_storage_c2: 'Inbound B to Storage C2',
    template_name_storage_c1_to_assembly_1: 'Storage C1 to Assembly 1',
    template_name_assembly_1_to_outbound_a: 'Assembly 1 to Outbound A',
    json_tools: 'JSON Import/Export',
    import_json: 'Import',
    export_json: 'Export',
    clear_json: 'Clear',
    json_placeholder: 'Paste JSON, for example { "tasks": [...] }',
    json_import_ok: 'Import success',
    json_import_fail: 'Import failed',
    queue_pending: 'Pending Queue',
    queue_blocked: 'Blocked Queue',
    queue_retry_all_astar: 'Retry All with A*',
    queue_assigned: 'Assigned Queue',
    queue_running: 'Running Queue',
    queue_finished: 'Finished Queue',
    queue_empty: 'This section is empty',
    dispatch_reason: 'Dispatch Reason',
    dispatch_waiting: 'Waiting for an idle AGV',
    dispatch_blocked: 'Unreachable with the current algorithm. Switch algorithm or adjust points.',
    reason_distance: 'To start',
    reason_algorithm: 'Algorithm',
    reason_mode: 'Mode',
    reason_auto: 'Auto',
    reason_manual: 'Manual',
    point_library: 'Common Points',
    point_fill_hint: 'Use the buttons to fill the task form quickly',
    point_manage: 'Custom Points',
    point_manage_hint: 'Add frequently used pickup, assembly, or temporary work points. They stay on this browser after refresh.',
    point_search_placeholder: 'Search by name, zone, or coordinates',
    point_search_empty: 'No matching points',
    point_apply_start: 'Set Start',
    point_apply_end: 'Set End',
    point_add: 'Save Point',
    point_delete: 'Delete Point',
    point_custom: 'Custom',
    point_builtin: 'Built-in',
    point_form_name: 'Point Name',
    point_form_zone: 'Zone',
    point_form_name_placeholder: 'Example: Prep Station A',
    point_form_zone_placeholder: 'Example: Assembly Area',
    point_form_saved: 'Point saved',
    point_form_deleted: 'Point deleted',
    point_form_invalid_name: 'Please enter both point name and zone',
    point_form_invalid_coords: 'Coordinates are outside the grid',
    task_blocked_alert: 'The current algorithm cannot reach this route. The task has been moved to the blocked queue.',
    task_manual_unreachable: 'The current algorithm cannot reach this route. Switch algorithm or adjust points.',
    confirm_delete_point: 'Delete this custom point?',
    point_category: 'Zone',
    point_coords: 'Coordinates',
    point_name_inbound_a: 'Inbound A',
    point_name_inbound_b: 'Inbound B',
    point_name_outbound_a: 'Outbound A',
    point_name_outbound_b: 'Outbound B',
    point_name_storage_c1: 'Storage C1',
    point_name_storage_c2: 'Storage C2',
    point_name_assembly_1: 'Assembly 1',
    point_name_assembly_2: 'Assembly 2',
    point_name_charge: 'Charging Area',
    point_name_maintenance: 'Maintenance Area',
    point_zone_inbound: 'Inbound',
    point_zone_outbound: 'Outbound',
    point_zone_storage: 'Storage',
    point_zone_assembly: 'Assembly',
    point_zone_service: 'Service',
    time_created: 'Created',
    time_assigned: 'Assigned',
    time_started: 'Started',
    time_finished: 'Finished'
  }
}

const DEFAULT_POINT_LIBRARY = [
  {
    id: 'inbound_a',
    x: 0,
    y: 1,
    nameKey: 'point_name_inbound_a',
    zoneKey: 'point_zone_inbound',
    aliases: ['dock', 'receiving', '入库', '搬入', '0,1']
  },
  {
    id: 'inbound_b',
    x: 0,
    y: 6,
    nameKey: 'point_name_inbound_b',
    zoneKey: 'point_zone_inbound',
    aliases: ['dock', 'receiving', '入库', '搬入', '0,6']
  },
  {
    id: 'outbound_a',
    x: 9,
    y: 1,
    nameKey: 'point_name_outbound_a',
    zoneKey: 'point_zone_outbound',
    aliases: ['shipping', 'delivery', '出库', '搬出', '9,1']
  },
  {
    id: 'outbound_b',
    x: 9,
    y: 6,
    nameKey: 'point_name_outbound_b',
    zoneKey: 'point_zone_outbound',
    aliases: ['shipping', 'delivery', '出库', '搬出', '9,6']
  },
  {
    id: 'storage_c1',
    x: 3,
    y: 2,
    nameKey: 'point_name_storage_c1',
    zoneKey: 'point_zone_storage',
    aliases: ['rack', 'buffer', '存储', '保管', '3,2']
  },
  {
    id: 'storage_c2',
    x: 3,
    y: 5,
    nameKey: 'point_name_storage_c2',
    zoneKey: 'point_zone_storage',
    aliases: ['rack', 'buffer', '存储', '保管', '3,5']
  },
  {
    id: 'assembly_1',
    x: 6,
    y: 2,
    nameKey: 'point_name_assembly_1',
    zoneKey: 'point_zone_assembly',
    aliases: ['station', 'line', '装配', '組立', '6,2']
  },
  {
    id: 'assembly_2',
    x: 6,
    y: 5,
    nameKey: 'point_name_assembly_2',
    zoneKey: 'point_zone_assembly',
    aliases: ['station', 'line', '装配', '組立', '6,5']
  },
  {
    id: 'charge',
    x: 1,
    y: 7,
    nameKey: 'point_name_charge',
    zoneKey: 'point_zone_service',
    aliases: ['charger', 'battery', '充电', '充電', '1,7']
  },
  {
    id: 'maintenance',
    x: 8,
    y: 7,
    nameKey: 'point_name_maintenance',
    zoneKey: 'point_zone_service',
    aliases: ['repair', 'service', '维护', '保守', '8,7']
  }
]

function getDefaultPoint(id) {
  return DEFAULT_POINT_LIBRARY.find(point => point.id === id)
}

const DEFAULT_TASK_TEMPLATES = [
  {
    id: 'template_inbound_a_to_storage_c1',
    nameKey: 'template_name_inbound_a_to_storage_c1',
    start_x: getDefaultPoint('inbound_a').x,
    start_y: getDefaultPoint('inbound_a').y,
    end_x: getDefaultPoint('storage_c1').x,
    end_y: getDefaultPoint('storage_c1').y,
    priority: 3,
    custom: false
  },
  {
    id: 'template_inbound_b_to_storage_c2',
    nameKey: 'template_name_inbound_b_to_storage_c2',
    start_x: getDefaultPoint('inbound_b').x,
    start_y: getDefaultPoint('inbound_b').y,
    end_x: getDefaultPoint('storage_c2').x,
    end_y: getDefaultPoint('storage_c2').y,
    priority: 3,
    custom: false
  },
  {
    id: 'template_storage_c1_to_assembly_1',
    nameKey: 'template_name_storage_c1_to_assembly_1',
    start_x: getDefaultPoint('storage_c1').x,
    start_y: getDefaultPoint('storage_c1').y,
    end_x: getDefaultPoint('assembly_1').x,
    end_y: getDefaultPoint('assembly_1').y,
    priority: 4,
    custom: false
  },
  {
    id: 'template_assembly_1_to_outbound_a',
    nameKey: 'template_name_assembly_1_to_outbound_a',
    start_x: getDefaultPoint('assembly_1').x,
    start_y: getDefaultPoint('assembly_1').y,
    end_x: getDefaultPoint('outbound_a').x,
    end_y: getDefaultPoint('outbound_a').y,
    priority: 5,
    custom: false
  }
]

const t = key => messages[locale.value]?.[key] ?? messages.en[key] ?? key

const API_POINT_TEXT = {
  zh: {
    start: '起点',
    end: '终点'
  },
  ja: {
    start: '開始点',
    end: '終了点'
  },
  en: {
    start: 'start point',
    end: 'end point'
  }
}

const API_ALGORITHM_TEXT = {
  zh: {
    simple: '直线路径',
    astar: 'A*'
  },
  ja: {
    simple: '直線経路',
    astar: 'A*'
  },
  en: {
    simple: 'simple',
    astar: 'A*'
  }
}

const API_ERROR_TEXT = {
  zh: {
    stage_out_of_grid: '第 {stage} 阶段的{point}坐标超出地图范围。',
    stage_blocked: '第 {stage} 阶段的{point}位于障碍格，无法使用。',
    task_coordinates_required: '请填写完整的任务坐标。',
    task_not_found: '未找到任务。',
    task_not_schedulable: '该任务当前不可调度。',
    task_not_running: '该任务当前不在运行中。',
    related_agv_not_found: '未找到关联的 AGV。',
    task_delete_not_allowed: '仅可删除待分配或不可达任务。',
    agv_not_found: '未找到 AGV。',
    agv_not_idle: '该 AGV 当前不是空闲状态。',
    no_idle_agv: '当前没有空闲 AGV。',
    no_pending_tasks: '当前没有可调度任务。',
    no_reachable_tasks: '当前没有可达任务。',
    task_start_unreachable: '当前算法 {algorithm} 下，没有空闲 AGV 可以到达任务起点。',
    task_route_unreachable: '当前算法 {algorithm} 下，任务路径不可达，请切换算法或修改点位。',
    unsupported_algorithm: '不支持的路径算法。',
    blocked_retry_requires_astar: '不可达任务仅支持使用 A* 重试。',
    task_not_blocked: '该任务当前不在不可达队列中。',
    preset_not_found: '未找到对应的障碍预设。',
    retry_waiting_for_idle_agv: '任务已切换为 {algorithm}，将在 AGV 空闲后自动重试。'
  },
  ja: {
    stage_out_of_grid: '第 {stage} 段階の{point}座標がマップ範囲外です。',
    stage_blocked: '第 {stage} 段階の{point}が障害物セル上にあります。',
    task_coordinates_required: 'タスク座標をすべて入力してください。',
    task_not_found: 'タスクが見つかりません。',
    task_not_schedulable: 'このタスクは現在スケジュールできません。',
    task_not_running: 'このタスクは現在実行中ではありません。',
    related_agv_not_found: '関連する AGV が見つかりません。',
    task_delete_not_allowed: '未割当または不可達タスクのみ削除できます。',
    agv_not_found: 'AGV が見つかりません。',
    agv_not_idle: 'この AGV は現在待機状態ではありません。',
    no_idle_agv: '現在、空き AGV がありません。',
    no_pending_tasks: '現在、スケジュール可能なタスクがありません。',
    no_reachable_tasks: '現在、到達可能なタスクがありません。',
    task_start_unreachable: '現在の {algorithm} では、タスク開始点に到達できる空き AGV がありません。',
    task_route_unreachable: '現在の {algorithm} ではタスク経路が到達不能です。アルゴリズムまたは点位を変更してください。',
    unsupported_algorithm: '未対応の経路アルゴリズムです。',
    blocked_retry_requires_astar: '不可達タスクの再試行は A* のみ対応しています。',
    task_not_blocked: 'このタスクは不可達キューにありません。',
    preset_not_found: '指定した障害物プリセットが見つかりません。',
    retry_waiting_for_idle_agv: 'タスクを {algorithm} に切り替えました。AGV が空き次第、自動で再試行します。'
  },
  en: {
    stage_out_of_grid: 'Stage {stage} {point} is outside the map bounds.',
    stage_blocked: 'Stage {stage} {point} is on a blocked cell.',
    task_coordinates_required: 'Task coordinates are required.',
    task_not_found: 'Task not found.',
    task_not_schedulable: 'This task cannot be scheduled right now.',
    task_not_running: 'This task is not running.',
    related_agv_not_found: 'Related AGV not found.',
    task_delete_not_allowed: 'Only pending or blocked tasks can be deleted.',
    agv_not_found: 'AGV not found.',
    agv_not_idle: 'The selected AGV is not idle.',
    no_idle_agv: 'No idle AGV is available.',
    no_pending_tasks: 'No schedulable tasks are available.',
    no_reachable_tasks: 'No reachable tasks are available.',
    task_start_unreachable: 'No idle AGV can reach the task start with algorithm {algorithm}.',
    task_route_unreachable: 'The task route is unreachable with algorithm {algorithm}.',
    unsupported_algorithm: 'Unsupported path algorithm.',
    blocked_retry_requires_astar: 'Blocked task retry only supports A*.',
    task_not_blocked: 'This task is not in the blocked queue.',
    preset_not_found: 'Obstacle preset not found.',
    retry_waiting_for_idle_agv: 'The task has been switched to {algorithm} and will retry automatically when an AGV becomes idle.'
  }
}

function fillTemplate(template, variables = {}) {
  return String(template ?? '').replace(/\{(\w+)\}/g, (_, key) => String(variables[key] ?? ''))
}

function apiPointText(pointType) {
  return (
    API_POINT_TEXT[locale.value]?.[pointType] ??
    API_POINT_TEXT.en[pointType] ??
    String(pointType ?? '')
  )
}

function apiAlgorithmText(algorithmName) {
  return (
    API_ALGORITHM_TEXT[locale.value]?.[algorithmName] ??
    API_ALGORITHM_TEXT.en[algorithmName] ??
    String(algorithmName ?? '')
  )
}

function localizeApiErrorDetail(detail, fallbackMessage = '') {
  const fallback = fallbackMessage || ''

  if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.error_code) {
    const template =
      API_ERROR_TEXT[locale.value]?.[detail.error_code] ??
      API_ERROR_TEXT.en[detail.error_code] ??
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
          API_ERROR_TEXT[locale.value]?.[errorCode] ??
          API_ERROR_TEXT.en[errorCode] ??
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
        API_ERROR_TEXT[locale.value]?.task_start_unreachable ??
          API_ERROR_TEXT.en.task_start_unreachable,
        { algorithm: apiAlgorithmText(algorithmName) }
      )
    }

    return detail
  }

  return fallback
}

function localizeDispatchReason(reason) {
  if (!reason || typeof reason !== 'string') return ''

  const [errorCode, rawAlgorithm] = reason.split(':')
  if (!rawAlgorithm) return ''

  if (!['task_start_unreachable', 'task_route_unreachable', 'retry_waiting_for_idle_agv'].includes(errorCode)) {
    return ''
  }

  const template =
    API_ERROR_TEXT[locale.value]?.[errorCode] ??
    API_ERROR_TEXT.en[errorCode] ??
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

const displayAgvs = computed(() => {
  const backendAgvs = agvs.value.map(agv => ({ ...agv, source: 'backend' }))
  return [...backendAgvs, ...localAgvs.value]
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
const blockedCellCount = computed(() => blockedCells.value.length)
const selectedObstaclePresetInfo = computed(
  () => obstaclePresets.value.find(preset => preset.key === selectedObstaclePreset.value) ?? null
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
const mainStartMarker = computed(() => {
  return (
    startPoint.value ??
    manualPathToStart.value.at(-1) ??
    manualPathToEnd.value[0] ??
    (shouldShowAutoPath.value ? autoPathToStart.value.at(-1) ?? autoPathToEnd.value[0] : null) ??
    null
  )
})
const mainEndMarker = computed(() => {
  return (
    endPoint.value ??
    manualPathToEnd.value.at(-1) ??
    (shouldShowAutoPath.value ? autoPathToEnd.value.at(-1) : null) ??
    null
  )
})
const chainMidMarkers = computed(() => {
  if (!taskChainMapPickActive.value) return []
  return taskChainMapPickPoints.value.slice(1, -1).map((point, index) => ({
    ...point,
    order: index + 1
  }))
})
const minimapStartMarker = computed(() => mainStartMarker.value)
const minimapEndMarker = computed(() => mainEndMarker.value)
const pointLibrary = computed(() => [...DEFAULT_POINT_LIBRARY, ...customPoints.value])
const taskTemplates = computed(() => [...DEFAULT_TASK_TEMPLATES, ...customTaskTemplates.value])
const templateJsonLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: 'テンプレート JSON',
      hint: 'カスタムテンプレートを JSON で保存したり、一括で取り込めます。',
      placeholder:
        '{ "templates": [{ "name": "搬入口Aから組立1", "start_x": 0, "start_y": 0, "end_x": 6, "end_y": 2, "priority": 3 }] }',
      import: 'テンプレート取込',
      export: 'カスタムを書出',
      importFile: 'ファイル取込',
      downloadFile: 'JSON 保存',
      clear: 'JSON クリア',
      exportEmpty: '書き出せるカスタムテンプレートがありません',
      exportOk: '書き出した件数',
      importOk: '取り込んだ件数',
      importFail: 'テンプレート JSON が不正か、取込に失敗しました',
      skipped: 'スキップ'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '模板 JSON',
      hint: '可导出自定义模板，也可从 JSON 批量导入。',
      placeholder:
        '{ "templates": [{ "name": "入库A到装配1", "start_x": 0, "start_y": 0, "end_x": 6, "end_y": 2, "priority": 3 }] }',
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
        json: 'JSON ツール'
      },
      expandAll: 'すべて展開',
      collapseAll: 'すべて折りたたむ',
      collapse: '折りたたむ',
      expand: '展開',
      currentMode: '現在モード',
      modeAuto: '自動配車',
      modeManual: '手動調車',
      modeAutoHint: '起点と終点を指定すると、システムが空き AGV を選択して実行します。',
      modeManualHint: '先に AGV を選択し、その後に目的地を指定してその車両だけを移動させます。'
    }
  }

  if (locale.value === 'zh') {
    return {
      sections: {
        control: '调度控制',
        queue: '任务队列',
        templates: '任务模板',
        points: '常用点位',
        json: 'JSON 工具'
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
      json: 'JSON Tools'
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
const panelSummaryLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: 'システム概要',
      mode: '現在モード',
      selectedAgv: '選択 AGV',
      noAgv: '未選択',
      noAgvCompact: '未選',
      zoom: 'ズーム',
      pending: '未割当',
      running: '実行中',
      hidden: '非表示',
      compact: '簡潔',
      full: '詳細',
      autoShort: '自動',
      manualShort: '手動',
      pendingShort: '未割',
      runningShort: '実行'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '系统摘要',
      mode: '当前模式',
      selectedAgv: '已选 AGV',
      noAgv: '未选择',
      noAgvCompact: '未选',
      zoom: '缩放',
      pending: '待分配',
      running: '运行中',
      hidden: '隐藏',
      compact: '精简',
      full: '完整',
      autoShort: '自动',
      manualShort: '手动',
      pendingShort: '待分',
      runningShort: '运行'
    }
  }

  return {
    title: 'System Summary',
    mode: 'Mode',
    selectedAgv: 'Selected AGV',
    noAgv: 'None',
    noAgvCompact: 'NONE',
    zoom: 'Zoom',
    pending: 'Pending',
    running: 'Running',
    hidden: 'Hidden',
    compact: 'Compact',
    full: 'Full',
    autoShort: 'AUTO',
    manualShort: 'MANUAL',
    pendingShort: 'PEND',
    runningShort: 'RUN'
  }
})
const settingsLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: '設定',
      mapGroup: 'マップ表示',
      obstacleGroup: '障害物マップ',
      promptGroup: '提示項目',
      showAgvStatus: 'AGV 状態表示を表示',
      showMarkerIcons: '開始/終了アイコンを表示',
      showPathArrows: '経路方向矢印を表示',
      showAutoPath: '自動経路を表示',
      showMinimap: 'ミニマップを表示',
      obstacleEdit: '障害物を編集',
      obstacleHint: '有効にすると、地図セルをクリックして障害物の追加・削除ができます。保存後、比較と調度に反映されます。',
      obstaclePreset: 'プリセット',
      obstaclePresetApply: 'プリセット適用',
      obstacleExport: '配置を書き出す',
      obstacleImport: '配置を読み込む',
      obstacleSave: '障害物を保存',
      obstacleReset: '初期配置に戻す',
      obstacleDirty: '未保存の変更あり',
      obstacleSaved: '同期済み',
      obstacleImported: '障害物レイアウトを読み込みました。',
      obstacleApplied: '障害物プリセットを適用しました。',
      obstacleResetDone: '初期障害物レイアウトに戻しました。',
      obstaclePresetNone: '先にプリセットを選択してください。',
      compareGroup: 'アルゴリズム比較',
      compareDisplay: '表示方式',
      compareDisplayPanel: '右側パネル',
      compareDisplayFloating: 'フローティング',
      compareOpacity: '透明度',
      resetView: '視点をリセット'
    }
  }

  if (locale.value === 'zh') {
    return {
      title: '设置',
      mapGroup: '地图显示',
      obstacleGroup: '障碍地图',
      promptGroup: '提示项',
      showAgvStatus: '显示 AGV 状态提示',
      showMarkerIcons: '显示起点/终点图标',
      showPathArrows: '显示路径方向箭头',
      showAutoPath: '显示自动路径',
      showMinimap: '显示小地图',
      obstacleEdit: '编辑障碍',
      obstacleHint: '开启后可点击地图格子增删障碍，保存后会同步用于路径对比与实际调度。',
      obstaclePreset: '预设场景',
      obstaclePresetApply: '应用预设',
      obstacleExport: '导出布局',
      obstacleImport: '导入布局',
      obstacleSave: '保存障碍',
      obstacleReset: '恢复默认',
      obstacleDirty: '存在未保存修改',
      obstacleSaved: '已同步',
      obstacleImported: '已导入障碍布局。',
      obstacleApplied: '已应用障碍预设。',
      obstacleResetDone: '已恢复默认障碍布局。',
      obstaclePresetNone: '请先选择一个预设。',
      compareGroup: '算法对比',
      compareDisplay: '显示方式',
      compareDisplayPanel: '右侧栏展开',
      compareDisplayFloating: '悬浮窗',
      compareOpacity: '透明度',
      resetView: '重置视图'
    }
  }

  return {
    title: 'Settings',
    mapGroup: 'Map Display',
    obstacleGroup: 'Obstacle Map',
    promptGroup: 'Hints',
    showAgvStatus: 'Show AGV Status Legend',
    showMarkerIcons: 'Show Start/End Icons',
    showPathArrows: 'Show Path Direction Arrows',
    showAutoPath: 'Show Auto Path',
    showMinimap: 'Show Minimap',
    obstacleEdit: 'Edit Obstacles',
    obstacleHint: 'When enabled, click map cells to add or remove blocked cells. Save applies to future comparison and dispatch.',
    obstaclePreset: 'Preset Scene',
    obstaclePresetApply: 'Apply Preset',
    obstacleExport: 'Export Layout',
    obstacleImport: 'Import Layout',
    obstacleSave: 'Save Obstacles',
    obstacleReset: 'Reset Default',
    obstacleDirty: 'Unsaved changes',
    obstacleSaved: 'Synced',
    obstacleImported: 'Obstacle layout imported.',
    obstacleApplied: 'Obstacle preset applied.',
    obstacleResetDone: 'Default obstacle layout restored.',
    obstaclePresetNone: 'Select a preset first.',
    compareGroup: 'Algorithm Compare',
    compareDisplay: 'Display Mode',
    compareDisplayPanel: 'Side Panel',
    compareDisplayFloating: 'Floating Window',
    compareOpacity: 'Opacity',
    resetView: 'Reset View'
  }
})
const taskChainLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      title: '段階タスク',
      hint: 'A -> B -> C のような連続工程を 1 件のタスクとして順番に実行します。',
      stage: '段階',
      stageLabel: '段階名',
      stageLabelPlaceholder: '例: 組立工程',
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
      jumpHint: '読込後、右下の黄色ボタンから移動できます。ダブルクリックなら直接移動します。',
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
      singleLoaded: '単一タスクの JSON サンプルを入力しました。',
      chainLoaded: '段階タスクの JSON サンプルを入力しました。'
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
      singleDownloaded: '単一タスクの JSON サンプルを保存しました。',
      chainDownloaded: '段階タスクの JSON サンプルを保存しました。'
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
const taskChainMapPickLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      start: '地図3点入力',
      cancel: '入力取消',
      step1: '1 点目: 開始点 A をクリック',
      step2: '2 点目: 中継点 B をクリック',
      step3: '3 点目: 終点 C をクリック'
    }
  }

  if (locale.value === 'zh') {
    return {
      start: '地图三击建两段',
      cancel: '取消地图选点',
      step1: '第 1 点：点击起点 A',
      step2: '第 2 点：点击中转点 B',
      step3: '第 3 点：点击终点 C'
    }
  }

  return {
    start: '3-Click Build',
    cancel: 'Cancel Picking',
    step1: 'Point 1: click start A',
    step2: 'Point 2: click transfer B',
    step3: 'Point 3: click end C'
  }
})
const taskChainMapPickUiLocale = computed(() => {
  if (locale.value === 'ja') {
    return {
      start: '選点',
      cancel: '取消',
      stageCount: '預選',
      idle: (required, stages) => `預選 ${stages} 段 / 必要 ${required} 点。先に「選点」を押してから地図をクリックしてください。`,
      status: (picked, required, stages) =>
        picked >= required
          ? `${required} 点已選択。確認後に ${stages} 段タスクを作成します。`
          : `已選 ${picked}/${required} 点。続けて選点してください。`
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
      collapseCards: 'カード折りたたみ',
      expandCards: 'カード展開'
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
const currentTaskBuilderHint = computed(() =>
  taskBuilderMode.value === 'chain' ? taskChainLocale.value.hint : taskBuilderLocale.value.singleHint
)
const taskChainMapPickStatusText = computed(() => {
  if (!taskChainMapPickActive.value) {
    return taskChainMapPickUiLocale.value.idle(taskChainRequiredPointCount.value, taskChainMapPickStageCount.value)
  }

  return taskChainMapPickUiLocale.value.status(
    taskChainMapPickPoints.value.length,
    taskChainRequiredPointCount.value,
    taskChainMapPickStageCount.value
  )
})
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
    return `${algorithmCompareLocale.value.title} · ${algorithmText(recommendedCompareAlgorithm.value)}`
  }

  return `${algorithmCompareLocale.value.title} · ${algorithmCompareLocale.value.unreachable}`
})
const compareResultEntries = computed(() => Object.entries(pathCompareResult.value?.results ?? {}))
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
      : `直線経路は横移動優先の簡化経路で、障害物で失敗する場合があります。${obstacleSummaryText.value}。`
  }
  if (locale.value === 'zh') {
    return algorithm.value === 'astar'
      ? `A* 会绕开障碍寻找可达路径。${obstacleSummaryText.value}。`
      : `直线路径仅做简化横纵通行，遇到障碍时可能无法调度。${obstacleSummaryText.value}。`
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

function createTaskChainStage(seed = {}) {
  return {
    label: seed.label ?? '',
    start_x: Number(seed.start_x ?? 0),
    start_y: Number(seed.start_y ?? 0),
    end_x: Number(seed.end_x ?? 0),
    end_y: Number(seed.end_y ?? 0)
  }
}

function buildDefaultTaskChainStages(stageCount = 2) {
  const normalizedCount = Math.max(2, Math.floor(Number(stageCount) || 2))
  const firstStage = createTaskChainStage({
    start_x: Number(taskForm.value.start_x),
    start_y: Number(taskForm.value.start_y),
    end_x: Number(taskForm.value.end_x),
    end_y: Number(taskForm.value.end_y)
  })
  const stages = [firstStage]

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

  return stages
}

function buildTaskJsonExamplePayload(mode) {
  if (mode === 'chain') {
    return {
      version: 2,
      tasks: [
        {
          priority: 4,
          stages: [
            { label: '入库', start_x: 1, start_y: 1, end_x: 4, end_y: 1 },
            { label: '装配', start_x: 4, start_y: 1, end_x: 4, end_y: 5 },
            { label: '出库', start_x: 4, start_y: 5, end_x: 8, end_y: 5 }
          ]
        },
        {
          priority: 2,
          stages: [
            { label: '取货', start_x: 0, start_y: 6, end_x: 3, end_y: 6 },
            { label: '补货', start_x: 3, start_y: 6, end_x: 3, end_y: 2 }
          ]
        }
      ]
    }
  }

  return {
    tasks: [
      { start_x: 1, start_y: 1, end_x: 7, end_y: 1, priority: 3 },
      { start_x: 2, start_y: 6, end_x: 8, end_y: 4, priority: 5 },
      { start_x: 0, start_y: 0, end_x: 5, end_y: 3, priority: 2 }
    ]
  }
}

function normalizeTaskStages(task) {
  if (Array.isArray(task.stages) && task.stages.length > 0) {
    return task.stages
  }
  return [
    {
      index: 0,
      start_x: task.start_x,
      start_y: task.start_y,
      end_x: task.end_x,
      end_y: task.end_y,
      label: ''
    }
  ]
}

function isTaskChain(task) {
  return Number(task.total_stages ?? normalizeTaskStages(task).length) > 1
}

function overallTaskStart(task) {
  return {
    x: task.overall_start_x ?? normalizeTaskStages(task)[0]?.start_x ?? task.start_x,
    y: task.overall_start_y ?? normalizeTaskStages(task)[0]?.start_y ?? task.start_y
  }
}

function overallTaskEnd(task) {
  const stages = normalizeTaskStages(task)
  const lastStage = stages[stages.length - 1]
  return {
    x: task.overall_end_x ?? lastStage?.end_x ?? task.end_x,
    y: task.overall_end_y ?? lastStage?.end_y ?? task.end_y
  }
}

function currentTaskStage(task) {
  const stages = normalizeTaskStages(task)
  const index = clampValue(Number(task.current_stage_index ?? 0), 0, stages.length - 1)
  return stages[index]
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
    relocating: '#ef6c00'
  }
  return map[status] ?? '#333'
}

function statusText(status) {
  return t(`status_${status}`) ?? status
}

function compactStatusText(status) {
  const map = {
    zh: {
      idle: '空闲',
      running: '运行',
      fault: '故障',
      relocating: '就位'
    },
    ja: {
      idle: '待機',
      running: '走行',
      fault: '故障',
      relocating: '移動'
    },
    en: {
      idle: 'IDLE',
      running: 'RUN',
      fault: 'FAULT',
      relocating: 'MOVE'
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
  if (!task.dispatch_mode && task.status === 'pending') {
    return t('dispatch_waiting')
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
      parts.push(`执行区間 ${task.path_length_to_end}`)
    } else if (locale.value === 'zh') {
      parts.push(`执行段 ${task.path_length_to_end}`)
    } else {
      parts.push(`run ${task.path_length_to_end}`)
    }
  }
  return parts.join(' | ')
}

function blockedTaskAlertText(task) {
  return localizeDispatchReason(task?.dispatch_reason) || task?.dispatch_reason || t('task_blocked_alert')
}

function buildTaskChainPayloadFromPoints(points) {
  if (points.length < taskChainRequiredPointCount.value) return null

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
  const rawStages = Array.isArray(template?.stages) && template.stages.length > 0
    ? template.stages
    : [
        {
          label: '',
          start_x: template?.start_x,
          start_y: template?.start_y,
          end_x: template?.end_x,
          end_y: template?.end_y
        }
      ]

  return rawStages
    .map(stage => ({
      ...createTaskChainStage(stage),
      label: String(stage?.label ?? '').trim()
    }))
    .filter(
      stage =>
        isValidGridCoordinate(stage.start_x, GRID_COLS) &&
        isValidGridCoordinate(stage.start_y, GRID_ROWS) &&
        isValidGridCoordinate(stage.end_x, GRID_COLS) &&
        isValidGridCoordinate(stage.end_y, GRID_ROWS)
    )
}

function buildTemplateFromStages({
  id = `task_template_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  name,
  priority,
  stages,
  custom = true
}) {
  const normalizedStages = normalizeTemplateStages({ stages })
  if (!name || normalizedStages.length === 0) return null

  const firstStage = normalizedStages[0]
  const lastStage = normalizedStages[normalizedStages.length - 1]
  return {
    id,
    customName: String(name).trim(),
    start_x: firstStage.start_x,
    start_y: firstStage.start_y,
    end_x: lastStage.end_x,
    end_y: lastStage.end_y,
    stages: normalizedStages,
    priority: clampValue(Number(priority), 1, 5),
    custom
  }
}

function isTaskChainTemplate(template) {
  return normalizeTemplateStages(template).length > 1
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

function applyPointToTaskForm(target, point) {
  if (target === 'start') {
    taskForm.value.start_x = point.x
    taskForm.value.start_y = point.y
    return
  }

  taskForm.value.end_x = point.x
  taskForm.value.end_y = point.y
}

function resetCustomPointForm() {
  customPointForm.value = {
    name: '',
    zone: '',
    x: 0,
    y: 0
  }
}

function setPointFormStatus(type, message) {
  pointFormStatusType.value = type
  pointFormStatus.value = message
}

function setTaskTemplateStatus(type, message) {
  taskTemplateStatusType.value = type
  taskTemplateStatus.value = message
}

function setTemplateJsonStatus(type, message) {
  templateJsonStatusType.value = type
  templateJsonStatus.value = message
}

function isValidGridCoordinate(value, max) {
  return Number.isInteger(value) && value >= 0 && value < max
}

function buildTaskTemplateSignature(template) {
  const stages = normalizeTemplateStages(template)
  return [
    String(template.customName ?? template.nameKey ?? '').trim().toLowerCase(),
    template.priority,
    ...stages.flatMap(stage => [stage.label, stage.start_x, stage.start_y, stage.end_x, stage.end_y])
  ].join('|')
}

function normalizeImportedTaskTemplate(template) {
  const name = String(template?.name ?? template?.customName ?? '').trim()
  const priority = Number(template?.priority)
  const stages = normalizeTemplateStages(template)

  if (!name || stages.length === 0 || !Number.isInteger(priority)) {
    return null
  }

  return buildTemplateFromStages({
    name,
    priority,
    stages,
    custom: true
  })
}

function formatTemplateJsonSummary(primaryLabel, primaryCount, skippedCount = 0) {
  const separator = locale.value === 'en' ? ', ' : '，'
  const parts = [`${primaryLabel}: ${primaryCount}`]
  if (skippedCount > 0) {
    parts.push(`${templateJsonLocale.value.skipped}: ${skippedCount}`)
  }
  return parts.join(separator)
}

function matchesSearchFields(fields, keyword) {
  if (!keyword) return false
  return fields.some(value => String(value ?? '').toLowerCase().includes(keyword))
}

function loadPanelSections() {
  try {
    const raw = window.localStorage.getItem(PANEL_SECTION_STORAGE_KEY)
    if (!raw) return

    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return

    panelSections.value = {
      control: typeof parsed.control === 'boolean' ? parsed.control : panelSections.value.control,
      queue: typeof parsed.queue === 'boolean' ? parsed.queue : panelSections.value.queue,
      templates:
        typeof parsed.templates === 'boolean' ? parsed.templates : panelSections.value.templates,
      points: typeof parsed.points === 'boolean' ? parsed.points : panelSections.value.points,
      json: typeof parsed.json === 'boolean' ? parsed.json : panelSections.value.json
    }
  } catch (error) {
    console.error('Load panel sections error:', error)
  }
}

function savePanelSections() {
  try {
    window.localStorage.setItem(PANEL_SECTION_STORAGE_KEY, JSON.stringify(panelSections.value))
  } catch (error) {
    console.error('Save panel sections error:', error)
  }
}

function loadPanelSummaryMode() {
  try {
    const raw = window.localStorage.getItem(PANEL_SUMMARY_MODE_STORAGE_KEY)
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
    window.localStorage.setItem(PANEL_SUMMARY_MODE_STORAGE_KEY, panelSummaryMode.value)
  } catch (error) {
    console.error('Save panel summary mode error:', error)
  }
}

function loadTaskQueueView() {
  try {
    const raw = window.localStorage.getItem(TASK_QUEUE_VIEW_STORAGE_KEY)
    if (!raw) return

    const parsed = JSON.parse(raw)
    if (parsed?.groups && typeof parsed.groups === 'object') {
      queueGroupsCollapsed.value = {
        ...queueGroupsCollapsed.value,
        pending: typeof parsed.groups.pending === 'boolean' ? parsed.groups.pending : queueGroupsCollapsed.value.pending,
        blocked: typeof parsed.groups.blocked === 'boolean' ? parsed.groups.blocked : queueGroupsCollapsed.value.blocked,
        assigned: typeof parsed.groups.assigned === 'boolean' ? parsed.groups.assigned : queueGroupsCollapsed.value.assigned,
        running: typeof parsed.groups.running === 'boolean' ? parsed.groups.running : queueGroupsCollapsed.value.running,
        finished: typeof parsed.groups.finished === 'boolean' ? parsed.groups.finished : queueGroupsCollapsed.value.finished
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
      TASK_QUEUE_VIEW_STORAGE_KEY,
      JSON.stringify({
        groups: queueGroupsCollapsed.value,
        cards: taskCardCollapsed.value
      })
    )
  } catch (error) {
    console.error('Save task queue view error:', error)
  }
}

function pruneTaskCardCollapsedState() {
  const visibleIds = new Set(tasks.value.map(task => String(task.id)))
  const nextState = Object.fromEntries(
    Object.entries(taskCardCollapsed.value).filter(([taskId]) => visibleIds.has(taskId))
  )

  if (Object.keys(nextState).length !== Object.keys(taskCardCollapsed.value).length) {
    taskCardCollapsed.value = nextState
  }
}

function panelSectionRefByKey(sectionKey) {
  const sectionMap = {
    control: controlSectionRef.value,
    queue: queueSectionRef.value,
    templates: templatesSectionRef.value,
    points: pointsSectionRef.value,
    json: jsonSectionRef.value
  }
  return sectionMap[sectionKey] ?? null
}

function focusPanelSection(sectionKey) {
  focusedPanelSection.value = sectionKey
  if (panelSectionFocusTimer) {
    clearTimeout(panelSectionFocusTimer)
  }
  panelSectionFocusTimer = setTimeout(() => {
    focusedPanelSection.value = ''
    panelSectionFocusTimer = null
  }, 1600)
}

async function jumpToPanelSearchResult(sectionKey) {
  panelSections.value = {
    ...panelSections.value,
    [sectionKey]: true
  }

  await nextTick()

  const panelSection = panelSectionRefByKey(sectionKey)
  const panelElement = panelRef.value
  if (panelSection && panelElement) {
    const top = Math.max(panelSection.offsetTop - 12, 0)
    panelElement.scrollTo({ top, behavior: 'smooth' })
  }

  focusPanelSection(sectionKey)
}

async function scrollToComparePanel() {
  panelSections.value = {
    ...panelSections.value,
    control: true
  }
  comparePanelExpanded.value = true

  await nextTick()

  const panelElement = panelRef.value
  const comparePanelElement = comparePanelRef.value
  if (panelElement && comparePanelElement) {
    const top = Math.max(comparePanelElement.offsetTop - 12, 0)
    panelElement.scrollTo({ top, behavior: 'smooth' })
  } else {
    await jumpToPanelSearchResult('control')
    return
  }

  focusPanelSection('control')
}

function shouldAutoRefreshFloatingCompare() {
  return compareDisplayMode.value === 'floating' && showFloatingCompare.value
}

function stopFloatingCompareRefresh() {
  if (floatingCompareRefreshTimer) {
    clearTimeout(floatingCompareRefreshTimer)
    floatingCompareRefreshTimer = null
  }
}

function requestFloatingCompareRefresh() {
  if (!shouldAutoRefreshFloatingCompare()) return
  stopFloatingCompareRefresh()
  floatingCompareRefreshTimer = setTimeout(() => {
    floatingCompareRefreshTimer = null
    if (pathCompareLoading.value) {
      requestFloatingCompareRefresh()
      return
    }
    void compareCurrentRoute()
  }, 360)
}

function positionFloatingCompareBelowEntry() {
  const button = compareEntryButtonRef.value
  if (!button || typeof window === 'undefined') return

  const rect = button.getBoundingClientRect()
  const floatingWidth = Math.min(360, Math.max(window.innerWidth - 24, 240))
  const maxX = Math.max(window.innerWidth - floatingWidth - 12, 12)
  compareFloatingX.value = Math.min(Math.max(rect.left, 12), maxX)
  compareFloatingY.value = Math.max(rect.bottom + 10, 12)
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

function clearPanelSearch() {
  panelSearch.value = ''
}

function fillTaskJsonExample(mode) {
  jsonText.value = JSON.stringify(buildTaskJsonExamplePayload(mode), null, 2)
  jsonStatus.value = mode === 'chain' ? taskJsonLocale.value.chainLoaded : taskJsonLocale.value.singleLoaded
}

function downloadJsonFile(filename, payloadText) {
  const blob = new Blob([payloadText], { type: 'application/json;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => window.URL.revokeObjectURL(url), 0)
}

function downloadTaskJsonExample(mode) {
  const payloadText = JSON.stringify(buildTaskJsonExamplePayload(mode), null, 2)
  const fileName =
    mode === 'chain' ? 'agv-stage-task-example.json' : 'agv-single-task-example.json'

  downloadJsonFile(fileName, payloadText)
  jsonStatus.value =
    mode === 'chain'
      ? taskJsonExampleFileLocale.value.chainDownloaded
      : taskJsonExampleFileLocale.value.singleDownloaded
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
  hideTaskBuilderJumpButton()
}

function cancelTaskChainMapPick(resetMarkers = true) {
  taskChainMapPickActive.value = false
  taskChainMapPickPoints.value = []
  if (resetMarkers) {
    clearAutoMarkers()
  }
}

function toggleTaskChainMapPick() {
  if (dispatchMode.value !== 'auto') return

  if (taskChainMapPickActive.value) {
    cancelTaskChainMapPick()
    return
  }

  taskBuilderMode.value = 'chain'
  taskChainMapPickActive.value = true
  taskChainMapPickPoints.value = []
  clearAutoMarkers()
}

function toggleDispatchModeFromSummary() {
  dispatchMode.value = dispatchMode.value === 'auto' ? 'manual' : 'auto'
}

function loadCustomPoints() {
  try {
    const raw = window.localStorage.getItem(CUSTOM_POINTS_STORAGE_KEY)
    if (!raw) return

    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return

    customPoints.value = parsed
      .filter(point => {
        return (
          typeof point?.id === 'string' &&
          typeof point?.customName === 'string' &&
          typeof point?.customZone === 'string' &&
          isValidGridCoordinate(point?.x, GRID_COLS) &&
          isValidGridCoordinate(point?.y, GRID_ROWS)
        )
      })
      .map(point => ({
        id: point.id,
        x: point.x,
        y: point.y,
        customName: point.customName.trim(),
        customZone: point.customZone.trim(),
        aliases: Array.isArray(point.aliases) ? point.aliases : [],
        custom: true
      }))
  } catch (error) {
    console.error('Load custom points error:', error)
  }
}

function saveCustomPoints() {
  try {
    window.localStorage.setItem(CUSTOM_POINTS_STORAGE_KEY, JSON.stringify(customPoints.value))
  } catch (error) {
    console.error('Save custom points error:', error)
  }
}

function addCustomPoint() {
  const name = customPointForm.value.name.trim()
  const zone = customPointForm.value.zone.trim()
  const x = Number(customPointForm.value.x)
  const y = Number(customPointForm.value.y)

  if (!name || !zone) {
    setPointFormStatus('error', t('point_form_invalid_name'))
    return
  }

  if (!isValidGridCoordinate(x, GRID_COLS) || !isValidGridCoordinate(y, GRID_ROWS)) {
    setPointFormStatus('error', t('point_form_invalid_coords'))
    return
  }

  customPoints.value = [
    ...customPoints.value,
    {
      id: `custom_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      x,
      y,
      customName: name,
      customZone: zone,
      aliases: [name, zone, `${x},${y}`, `${x} ${y}`],
      custom: true
    }
  ]

  resetCustomPointForm()
  setPointFormStatus('success', t('point_form_saved'))
}

function deleteCustomPoint(point) {
  if (!point.custom) return
  const ok = window.confirm(t('confirm_delete_point'))
  if (!ok) return

  customPoints.value = customPoints.value.filter(item => item.id !== point.id)
  setPointFormStatus('success', t('point_form_deleted'))
}

function loadMapDisplaySettings() {
  try {
    const raw = window.localStorage.getItem(MAP_DISPLAY_STORAGE_KEY)
    if (!raw) return

    const parsed = JSON.parse(raw)
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
    if (typeof parsed?.showMinimap === 'boolean') {
      showMinimap.value = parsed.showMinimap
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
      MAP_DISPLAY_STORAGE_KEY,
      JSON.stringify({
        showAutoPath: showAutoPath.value,
        showMarkerIcons: showMarkerIcons.value,
        showPathArrows: showPathArrows.value,
        showStatusLegend: showStatusLegend.value,
        showMinimap: showMinimap.value,
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
    const raw = window.localStorage.getItem(TASK_TEMPLATE_STORAGE_KEY)
    if (!raw) return

    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return

    customTaskTemplates.value = parsed
      .map(template =>
        buildTemplateFromStages({
          id: typeof template?.id === 'string' ? template.id : undefined,
          name: template?.customName,
          priority: template?.priority,
          stages: normalizeTemplateStages(template),
          custom: true
        })
      )
      .filter(Boolean)
  } catch (error) {
    console.error('Load task templates error:', error)
  }
}

function saveTaskTemplates() {
  try {
    window.localStorage.setItem(TASK_TEMPLATE_STORAGE_KEY, JSON.stringify(customTaskTemplates.value))
  } catch (error) {
    console.error('Save task templates error:', error)
  }
}

async function applyTaskTemplate(template, options = {}) {
  const stages = normalizeTemplateStages(template)
  if (stages.length === 0) return

  const firstStage = stages[0]
  taskForm.value.start_x = firstStage.start_x
  taskForm.value.start_y = firstStage.start_y
  taskForm.value.end_x = firstStage.end_x
  taskForm.value.end_y = firstStage.end_y
  taskForm.value.priority = template.priority
  taskChainStages.value = stages.map(stage => createTaskChainStage(stage))
  taskBuilderMode.value = stages.length > 1 ? 'chain' : 'single'

  if (stages.length > 1) {
    setTaskTemplateStatus('info', `${taskBuilderLocale.value.loadedChain} ${taskBuilderLocale.value.jumpHint}`)
  } else {
    setTaskTemplateStatus('info', `${taskBuilderLocale.value.loadedSingle} ${taskBuilderLocale.value.jumpHint}`)
  }

  if (options.focus) {
    hideTaskBuilderJumpButton()
    await focusTaskBuilder(taskBuilderMode.value)
    return
  }

  showTaskBuilderJumpButton()
}

function onTemplateApplyClick(template) {
  if (templateApplyClickTimer) {
    clearTimeout(templateApplyClickTimer)
  }
  templateApplyClickTimer = setTimeout(() => {
    templateApplyClickTimer = null
    void applyTaskTemplate(template)
  }, 220)
}

function onTemplateApplyDoubleClick(template) {
  if (templateApplyClickTimer) {
    clearTimeout(templateApplyClickTimer)
    templateApplyClickTimer = null
  }
  void applyTaskTemplate(template, { focus: true })
}

function saveCurrentTaskAsTemplate() {
  const name = taskTemplateForm.value.name.trim()
  if (!name) {
    setTaskTemplateStatus('error', t('template_form_invalid_name'))
    return
  }

  const template = buildTemplateFromStages({
    name,
    priority: Number(taskForm.value.priority),
    stages: [
      {
        start_x: Number(taskForm.value.start_x),
        start_y: Number(taskForm.value.start_y),
        end_x: Number(taskForm.value.end_x),
        end_y: Number(taskForm.value.end_y)
      }
    ],
    custom: true
  })
  if (!template) {
    setTaskTemplateStatus('error', t('point_form_invalid_coords'))
    return
  }

  customTaskTemplates.value = [
    ...customTaskTemplates.value,
    template
  ]

  taskTemplateForm.value.name = ''
  hideTaskBuilderJumpButton()
  setTaskTemplateStatus('success', t('template_form_saved'))
}

function saveCurrentTaskChainAsTemplate() {
  const name = taskTemplateForm.value.name.trim()
  if (!name) {
    setTaskTemplateStatus('error', t('template_form_invalid_name'))
    return
  }

  const template = buildTemplateFromStages({
    name,
    priority: Number(taskForm.value.priority),
    stages: taskChainStages.value,
    custom: true
  })
  if (!template || normalizeTemplateStages(template).length < 2) {
    setTaskTemplateStatus('error', t('point_form_invalid_coords'))
    return
  }

  customTaskTemplates.value = [...customTaskTemplates.value, template]
  taskTemplateForm.value.name = ''
  hideTaskBuilderJumpButton()
  setTaskTemplateStatus('success', t('template_form_saved'))
}

function deleteTaskTemplate(template) {
  if (!template.custom) return
  const ok = window.confirm(t('confirm_delete_template'))
  if (!ok) return

  customTaskTemplates.value = customTaskTemplates.value.filter(item => item.id !== template.id)
  hideTaskBuilderJumpButton()
  setTaskTemplateStatus('success', t('template_form_deleted'))
}

function buildTemplateExportPayload() {
  return {
    version: 2,
    templates: customTaskTemplates.value.map(template => {
      const stages = normalizeTemplateStages(template)
      const firstStage = stages[0]
      const lastStage = stages[stages.length - 1]
      return {
        name: template.customName,
        start_x: firstStage.start_x,
        start_y: firstStage.start_y,
        end_x: lastStage.end_x,
        end_y: lastStage.end_y,
        stages: stages.map(stage => ({
          label: stage.label || undefined,
          start_x: stage.start_x,
          start_y: stage.start_y,
          end_x: stage.end_x,
          end_y: stage.end_y
        })),
        priority: template.priority
      }
    })
  }
}

function exportTaskTemplatesToJson() {
  if (customTaskTemplates.value.length === 0) {
    setTemplateJsonStatus('error', templateJsonLocale.value.exportEmpty)
    return
  }

  templateJsonText.value = JSON.stringify(buildTemplateExportPayload(), null, 2)
  setTemplateJsonStatus(
    'success',
    formatTemplateJsonSummary(templateJsonLocale.value.exportOk, customTaskTemplates.value.length)
  )
}

function clearTemplateJsonText() {
  templateJsonText.value = ''
  setTemplateJsonStatus('info', '')
}

function importTaskTemplatesFromRaw(rawText) {
  if (!rawText.trim()) return
  setTemplateJsonStatus('info', '')

  let parsed
  try {
    parsed = JSON.parse(rawText)
  } catch {
    setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
    return
  }

  const templateItems = Array.isArray(parsed) ? parsed : parsed?.templates
  if (!Array.isArray(templateItems)) {
    setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
    return
  }

  const existingSignatures = new Set(customTaskTemplates.value.map(buildTaskTemplateSignature))
  const imported = []
  let skipped = 0

  for (const item of templateItems) {
    const normalized = normalizeImportedTaskTemplate(item)
    if (!normalized) {
      skipped += 1
      continue
    }

    const signature = buildTaskTemplateSignature(normalized)
    if (existingSignatures.has(signature)) {
      skipped += 1
      continue
    }

    existingSignatures.add(signature)
    imported.push(normalized)
  }

  if (imported.length === 0) {
    if (skipped > 0) {
      setTemplateJsonStatus('info', formatTemplateJsonSummary(templateJsonLocale.value.importOk, 0, skipped))
      return
    }

    setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
    return
  }

  customTaskTemplates.value = [...customTaskTemplates.value, ...imported]
  setTemplateJsonStatus(
    'success',
    formatTemplateJsonSummary(templateJsonLocale.value.importOk, imported.length, skipped)
  )
}

function importTaskTemplatesFromJson() {
  importTaskTemplatesFromRaw(templateJsonText.value)
}

function downloadTemplateJsonFile() {
  if (customTaskTemplates.value.length === 0) {
    setTemplateJsonStatus('error', templateJsonLocale.value.exportEmpty)
    return
  }

  const payloadText = JSON.stringify(buildTemplateExportPayload(), null, 2)
  templateJsonText.value = payloadText

  const blob = new Blob([payloadText], { type: 'application/json;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')

  link.href = url
  link.download = `agv-task-templates-${timestamp}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => window.URL.revokeObjectURL(url), 0)

  setTemplateJsonStatus(
    'success',
    formatTemplateJsonSummary(templateJsonLocale.value.exportOk, customTaskTemplates.value.length)
  )
}

function triggerTemplateFileImport() {
  templateFileInputRef.value?.click()
}

async function handleTemplateFileChange(event) {
  const file = event.target?.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    templateJsonText.value = text
    importTaskTemplatesFromRaw(text)
  } catch (error) {
    console.error('Read template json file error:', error)
    setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
  } finally {
    event.target.value = ''
  }
}

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

function cancelSelection() {
  selectedAgvId.value = null
  startPoint.value = null
  clearManualDestination()
}

function findAgvById(id) {
  return displayAgvs.value.find(agv => agv.id === id)
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

  const manualTask = findLatestActiveTask('manual')
  if (manualTask) {
    manualPathToStart.value = manualTask.path_to_start ?? []
    manualPathToEnd.value = manualTask.path_to_end ?? []
  } else {
    clearManualPaths()
  }
}

function isCellOccupied(x, y) {
  return displayAgvs.value.some(agv => agv.x === x && agv.y === y)
}

function syncPanelWidth(nextWidth = panelWidth.value) {
  if (isCompactLayout.value) return
  const layoutWidth = layoutRef.value?.clientWidth ?? windowWidth.value
  const minWidth = 320
  const maxWidth = Math.max(minWidth, layoutWidth - 280)
  panelWidth.value = clampValue(Math.round(nextWidth), minWidth, maxWidth)
}

function centerMapView() {
  mapOffsetX.value = (mapViewportWidth.value - MAP_WIDTH * mapZoom.value) / 2
  mapOffsetY.value = (mapViewportHeight.value - MAP_HEIGHT * mapZoom.value) / 2
  clampMapTransform()
}

function resetMapView() {
  mapZoom.value = 1
  centerMapView()
}

function updateMapZoom(nextZoom, pointerX = mapViewportWidth.value / 2, pointerY = mapViewportHeight.value / 2) {
  const clampedZoom = clampValue(Number(nextZoom.toFixed(3)), MIN_ZOOM, MAX_ZOOM)
  if (clampedZoom === mapZoom.value) return false

  const worldX = (pointerX - mapOffsetX.value) / mapZoom.value
  const worldY = (pointerY - mapOffsetY.value) / mapZoom.value

  mapZoom.value = clampedZoom
  mapOffsetX.value = pointerX - worldX * clampedZoom
  mapOffsetY.value = pointerY - worldY * clampedZoom
  clampMapTransform()
  return true
}

function changeMapZoom(deltaY, pointerX = mapViewportWidth.value / 2, pointerY = mapViewportHeight.value / 2) {
  const ratio = deltaY < 0 ? 1.12 : 0.88
  return updateMapZoom(mapZoom.value * ratio, pointerX, pointerY)
}

function clampMapTransform() {
  const scaledWidth = MAP_WIDTH * mapZoom.value
  const scaledHeight = MAP_HEIGHT * mapZoom.value

  if (scaledWidth <= mapViewportWidth.value) {
    mapOffsetX.value = (mapViewportWidth.value - scaledWidth) / 2
  } else {
    mapOffsetX.value = clampValue(mapOffsetX.value, mapViewportWidth.value - scaledWidth, 0)
  }

  if (scaledHeight <= mapViewportHeight.value) {
    mapOffsetY.value = (mapViewportHeight.value - scaledHeight) / 2
  } else {
    mapOffsetY.value = clampValue(mapOffsetY.value, mapViewportHeight.value - scaledHeight, 0)
  }
}

function updateMapViewportMetrics(shouldCenter = false) {
  const viewport = mapViewportRef.value
  if (!viewport) return

  mapViewportWidth.value = viewport.clientWidth || MAP_WIDTH
  mapViewportHeight.value = viewport.clientHeight || MAP_HEIGHT

  if (!mapViewReady || shouldCenter) {
    centerMapView()
    mapViewReady = true
    return
  }

  clampMapTransform()
}

function focusMapAtWorld(worldX, worldY) {
  mapOffsetX.value = mapViewportWidth.value / 2 - worldX * mapZoom.value
  mapOffsetY.value = mapViewportHeight.value / 2 - worldY * mapZoom.value
  clampMapTransform()
}

function getMapPointFromClient(clientX, clientY) {
  const rect = mapViewportRef.value?.getBoundingClientRect()
  if (!rect) return null

  const worldX = (clientX - rect.left - mapOffsetX.value) / mapZoom.value
  const worldY = (clientY - rect.top - mapOffsetY.value) / mapZoom.value

  if (worldX < 0 || worldX >= MAP_WIDTH || worldY < 0 || worldY >= MAP_HEIGHT) {
    return null
  }

  return {
    x: worldX,
    y: worldY
  }
}

function getWorldPointFromMinimapEvent(event) {
  const rect = minimapRef.value?.getBoundingClientRect()
  if (!rect) return { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 }

  return {
    x: clampValue((event.clientX - rect.left) / minimapScale.value, 0, MAP_WIDTH),
    y: clampValue((event.clientY - rect.top) / minimapScale.value, 0, MAP_HEIGHT)
  }
}

function getCellFromEvent(event) {
  const point = getMapPointFromClient(event.clientX, event.clientY)
  if (!point) return null
  return {
    x: clampValue(Math.floor(point.x / CELL_SIZE), 0, GRID_COLS - 1),
    y: clampValue(Math.floor(point.y / CELL_SIZE), 0, GRID_ROWS - 1)
  }
}

function getCellFromClient(clientX, clientY) {
  const rect = mapViewportRef.value?.getBoundingClientRect()
  if (!rect) return null
  if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) {
    return null
  }

  const point = getMapPointFromClient(clientX, clientY)
  if (!point) return null
  return {
    x: clampValue(Math.floor(point.x / CELL_SIZE), 0, GRID_COLS - 1),
    y: clampValue(Math.floor(point.y / CELL_SIZE), 0, GRID_ROWS - 1)
  }
}

function buildSimpleCandidatePath(sx, sy, ex, ey, axisOrder) {
  const path = [{ x: sx, y: sy }]
  let x = sx
  let y = sy

  for (const axis of axisOrder) {
    if (axis === 'x') {
      while (x !== ex) {
        x += ex > x ? 1 : -1
        if (isBlockedCell(x, y)) return []
        path.push({ x, y })
      }
    } else {
      while (y !== ey) {
        y += ey > y ? 1 : -1
        if (isBlockedCell(x, y)) return []
        path.push({ x, y })
      }
    }
  }

  return path
}

function buildSimplePath(sx, sy, ex, ey) {
  if (isBlockedCell(sx, sy) || isBlockedCell(ex, ey)) return []
  if (sx === ex && sy === ey) return [{ x: sx, y: sy }]

  const xFirst = buildSimpleCandidatePath(sx, sy, ex, ey, ['x', 'y'])
  if (xFirst.length > 0) return xFirst

  return buildSimpleCandidatePath(sx, sy, ex, ey, ['y', 'x'])
}

function buildAStarPath(sx, sy, ex, ey) {
  if (isBlockedCell(sx, sy) || isBlockedCell(ex, ey)) return []
  if (sx === ex && sy === ey) return [{ x: sx, y: sy }]

  const startKey = blockedCellKey(sx, sy)
  const goalKey = blockedCellKey(ex, ey)
  const open = [{ x: sx, y: sy, key: startKey, f: 0 }]
  const cameFrom = new Map()
  const gScore = new Map([[startKey, 0]])

  while (open.length > 0) {
    open.sort((a, b) => a.f - b.f)
    const current = open.shift()
    if (!current) break

    if (current.x === ex && current.y === ey) {
      const path = [{ x: ex, y: ey }]
      let cursorKey = goalKey
      while (cameFrom.has(cursorKey)) {
        const previous = cameFrom.get(cursorKey)
        path.push({ x: previous.x, y: previous.y })
        cursorKey = blockedCellKey(previous.x, previous.y)
      }
      path.reverse()
      return path
    }

    for (const [dx, dy] of [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1]
    ]) {
      const nx = current.x + dx
      const ny = current.y + dy
      if (nx < 0 || nx >= GRID_COLS || ny < 0 || ny >= GRID_ROWS) continue
      if (isBlockedCell(nx, ny)) continue

      const neighborKey = blockedCellKey(nx, ny)
      const tentative = (gScore.get(current.key) ?? 0) + 1
      if (tentative >= (gScore.get(neighborKey) ?? Number.POSITIVE_INFINITY)) continue

      cameFrom.set(neighborKey, { x: current.x, y: current.y })
      gScore.set(neighborKey, tentative)
      const heuristic = Math.abs(nx - ex) + Math.abs(ny - ey)
      const existing = open.find(item => item.key === neighborKey)
      const nextNode = { x: nx, y: ny, key: neighborKey, f: tentative + heuristic }
      if (existing) {
        existing.f = nextNode.f
      } else {
        open.push(nextNode)
      }
    }
  }

  return []
}

function buildPreviewPathByAlgorithm(sx, sy, ex, ey) {
  return algorithm.value === 'astar' ? buildAStarPath(sx, sy, ex, ey) : buildSimplePath(sx, sy, ex, ey)
}

function blockedCellAlertText() {
  if (locale.value === 'ja') return '障害物セルは始点・終点・中継点に設定できません。'
  if (locale.value === 'zh') return '障碍格不能作为起点、终点或中转点。'
  return 'Blocked cells cannot be used as start, end, or transfer points.'
}

function onAgvClick(agv, event) {
  event.stopPropagation()
  if (dispatchMode.value !== 'manual') return
  if (agv.source !== 'backend') return
  if (agv.status !== 'idle') return
  selectedAgvId.value = agv.id
  startPoint.value = { x: agv.x, y: agv.y }
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

function onMapWheel(event) {
  const rect = mapViewportRef.value?.getBoundingClientRect()
  if (!rect) return

  const pointerX = event.clientX - rect.left
  const pointerY = event.clientY - rect.top
  changeMapZoom(event.deltaY, pointerX, pointerY)
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

  if (dispatchMode.value === 'manual') {
    if (!selectedAgvId.value) return
    const agv = findAgvById(selectedAgvId.value)
    if (!agv || agv.status !== 'idle') return

    startPoint.value = { x: agv.x, y: agv.y }
    void confirmAndSchedule(x, y, agv.id)
    return
  }

  if (dispatchMode.value === 'auto' && taskBuilderMode.value === 'chain' && taskChainMapPickActive.value) {
    void handleTaskChainMapClick(x, y)
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
    clearAutoMarkers()
    taskChainMapPickPoints.value = []
  }
}

async function confirmAndSchedule(x, y, agvId = null) {
  const ok = window.confirm(t('confirm_dispatch'))
  if (!ok) return
  endPoint.value = { x, y }
  await createTaskAndSchedule(agvId)
}

async function createTaskAndSchedule(agvId) {
  if (!startPoint.value || !endPoint.value) return
  if (!(await ensureBlockedCellsSynced())) return

  try {
    const createRes = await fetch(`${API_BASE}/task/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_x: startPoint.value.x,
        start_y: startPoint.value.y,
        end_x: endPoint.value.x,
        end_y: endPoint.value.y,
        priority: taskPriority.value
      })
    })
    const createData = await createRes.json()
    if (!createRes.ok) {
      throw createApiError(createData, 'Task create failed')
    }

    await fetchTasks()

    if (dispatchMode.value === 'auto') {
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
      throw createApiError(scheduleData, 'Schedule failed')
    }

    startPoint.value = {
      x: scheduleData.task.start_x,
      y: scheduleData.task.start_y
    }
    endPoint.value = {
      x: scheduleData.task.end_x,
      y: scheduleData.task.end_y
    }
    manualPathToStart.value = scheduleData.path_to_start ?? []
    manualPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []

    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Schedule error:', error)
    if (dispatchMode.value === 'manual') {
      clearManualDestination()
    }
  }
}

function onDispatchHelpEnter() {
  if (dispatchHelpTimer) {
    clearTimeout(dispatchHelpTimer)
  }
  dispatchHelpTimer = setTimeout(() => {
    if (!dispatchHelpPinned.value) {
      showDispatchHelp.value = true
    }
  }, 450)
}

function onDispatchHelpLeave() {
  if (dispatchHelpTimer) {
    clearTimeout(dispatchHelpTimer)
    dispatchHelpTimer = null
  }
  if (!dispatchHelpPinned.value) {
    showDispatchHelp.value = false
  }
}

function toggleDispatchHelp() {
  dispatchHelpPinned.value = !dispatchHelpPinned.value
  showDispatchHelp.value = dispatchHelpPinned.value
}

function onPanelScroll() {
  showPanelBackToTop.value = (panelRef.value?.scrollTop ?? 0) > 140
}

function scrollPanelToTop() {
  panelRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function startPanelResize(event) {
  if (isCompactLayout.value || event.button !== 0) return
  event.preventDefault()
  isPanelResizing = true
  panelResizeStartX = event.clientX
  panelResizeStartWidth = panelWidth.value
  document.body.style.cursor = 'col-resize'
}

function handleMinimapNavigation(event) {
  const point = getWorldPointFromMinimapEvent(event)
  focusMapAtWorld(point.x, point.y)
}

function onMinimapMouseDown(event) {
  if (event.button !== 0) return
  event.preventDefault()
  event.stopPropagation()
  isMinimapDragging = true
  handleMinimapNavigation(event)
}

function onWindowResize() {
  windowWidth.value = window.innerWidth
  syncPanelWidth()
  updateMapViewportMetrics()
}

function onGlobalMouseMove(event) {
  if (compareFloatingDragging) {
    compareFloatingX.value = Math.max(event.clientX - compareFloatingDragOffsetX, 12)
    compareFloatingY.value = Math.max(event.clientY - compareFloatingDragOffsetY, 12)
    return
  }

  if (isPanelResizing) {
    const deltaX = event.clientX - panelResizeStartX
    syncPanelWidth(panelResizeStartWidth - deltaX)
    return
  }

  if (isMinimapDragging) {
    handleMinimapNavigation(event)
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

  if (isPanelResizing) {
    isPanelResizing = false
    document.body.style.cursor = ''
  }

  if (isMinimapDragging) {
    isMinimapDragging = false
  }

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

async function tryAutoSchedule() {
  if (dispatchMode.value !== 'auto') return
  if (autoScheduling) return
  if (obstacleEditMode.value || obstacleLayoutDirty.value) return
  if (!hasIdleAgv() || !hasPendingTask()) return

  autoScheduling = true
  try {
    const scheduleRes = await fetch(`${API_BASE}/schedule/with_path`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: null,
        agv_id: null,
        algorithm: algorithm.value,
        grid_cols: GRID_COLS,
        grid_rows: GRID_ROWS
      })
    })
    const scheduleData = await scheduleRes.json()
    if (!scheduleRes.ok) {
      await fetchTasks()
      return
    }

    autoPathToStart.value = scheduleData.path_to_start ?? []
    autoPathToEnd.value = scheduleData.path_to_end ?? scheduleData.path ?? []

    await Promise.all([fetchAgvs(), fetchTasks()])
  } catch (error) {
    console.error('Auto schedule error:', error)
  } finally {
    autoScheduling = false
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

    if (data?.queued) {
      clearAutoPaths()
      window.alert(t('task_retry_astar_queued'))
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
  if (!(await ensureBlockedCellsSynced())) return false
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

  try {
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
    }
    return createdTask
  } catch (error) {
    console.error('Create task form error:', error)
    window.alert(error instanceof Error ? error.message : String(error))
    return false
  }
}

function clearPathCompare() {
  pathCompareResult.value = null
  pathCompareError.value = ''
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
    pathCompareError.value = algorithmCompareLocale.value.invalid
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

async function openCompareDisplay() {
  if (compareDisplayMode.value === 'floating') {
    showFloatingCompare.value = true
    await nextTick()
    positionFloatingCompareBelowEntry()
    requestFloatingCompareRefresh()
    return
  }

  await scrollToComparePanel()
  void compareCurrentRoute()
}

function handleCompareEntryClick() {
  void openCompareDisplay()
}

function toggleComparePanelExpanded() {
  comparePanelExpanded.value = !comparePanelExpanded.value
}

function closeFloatingCompare() {
  stopFloatingCompareRefresh()
  showFloatingCompare.value = false
}

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

function addTaskChainStage() {
  setTaskChainStageCount(taskChainStageCount.value + 1)
}

function removeTaskChainStage(index) {
  if (taskChainStages.value.length <= 2) return
  taskChainStages.value = taskChainStages.value.filter((_, stageIndex) => stageIndex !== index)
}

function resetTaskChainStages() {
  taskChainStages.value = buildDefaultTaskChainStages(taskChainStageCount.value)
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
    if (dispatchMode.value === 'auto') {
      await tryAutoSchedule()
    }
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

function onTaskHover(task) {
  if (!['pending', 'blocked'].includes(task.status)) return
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    previewTaskId.value = task.id
    previewStart.value = { x: task.start_x, y: task.start_y }
    previewEnd.value = { x: task.end_x, y: task.end_y }
    previewPath.value = buildPreviewPathByAlgorithm(task.start_x, task.start_y, task.end_x, task.end_y)
  }, 400)
}

function onTaskLeave() {
  clearPreview()
}

function setObstacleLayoutStatus(type, message) {
  obstacleLayoutStatusType.value = type
  obstacleLayoutStatus.value = message
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

function toggleObstacleEditMode() {
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
  obstacleMapSaving.value = true
  try {
    const res = await fetch(`${API_BASE}/status/map`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        blocked_cells: normalizeBlockedCellList(blockedCells.value),
        grid_cols: GRID_COLS,
        grid_rows: GRID_ROWS
      })
    })
    const data = await res.json()
    if (!res.ok) {
      throw createApiError(data, 'Save blocked cells failed')
    }
    const normalized = normalizeBlockedCellList(data.blocked_cells ?? [])
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    clearPreview()
    cancelSelection()
    setObstacleLayoutStatus('success', settingsLocale.value.obstacleSaved)
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
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    clearPreview()
    cancelSelection()
    setObstacleLayoutStatus('success', settingsLocale.value.obstacleResetDone)
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
  return await saveBlockedCells()
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
      return
    }

    const normalized = normalizeBlockedCellList(
      data.blocked_cells.map(cell => ({
        x: Number(cell.x),
        y: Number(cell.y)
      }))
    )
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
  } catch (error) {
    console.error('Fetch map layout error:', error)
    blockedCells.value = [...DEFAULT_BLOCKED_CELLS]
    syncedBlockedCells.value = [...DEFAULT_BLOCKED_CELLS]
  }
}

async function applyObstaclePreset() {
  if (!selectedObstaclePreset.value) {
    setObstacleLayoutStatus('error', settingsLocale.value.obstaclePresetNone)
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
    blockedCells.value = normalized
    syncedBlockedCells.value = normalized
    clearPreview()
    cancelSelection()
    setObstacleLayoutStatus('success', settingsLocale.value.obstacleApplied)
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
  obstacleLayoutFileInputRef.value?.click()
}

async function importObstacleLayout(rawText) {
  try {
    const parsed = JSON.parse(rawText)
    const rawCells = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed?.blocked_cells)
        ? parsed.blocked_cells
        : null
    if (!rawCells) {
      throw new Error('Invalid obstacle layout')
    }

    blockedCells.value = normalizeBlockedCellList(
      rawCells.map(cell => ({
        x: Number(cell?.x),
        y: Number(cell?.y)
      }))
    )
    const saved = await saveBlockedCells()
    if (saved) {
      setObstacleLayoutStatus('success', settingsLocale.value.obstacleImported)
    }
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

async function refreshState() {
  if (polling) return
  polling = true
  try {
    await Promise.all([fetchAgvs(), fetchTasks()])
    syncDisplayedPathsFromTasks()
    if (dispatchMode.value === 'auto') {
      if (!hasActiveTask()) {
        clearAutoPaths()
      }
      await tryAutoSchedule()
    }
  } finally {
    polling = false
  }
}

function onKeyDown(event) {
  if (event.key === 'f' || event.key === 'F') {
    cancelSelection()
  }
}

function onMapContextMenu(event) {
  event.preventDefault()
  cancelSelection()
}

watch(dispatchMode, mode => {
  cancelSelection()
  clearPreview()
  dispatchHelpPinned.value = false
  showDispatchHelp.value = false
  if (mode !== 'auto') {
    cancelTaskChainMapPick(false)
  }
  if (mode === 'manual') {
    clearAutoPaths()
    clearAutoMarkers()
  }
})

watch(obstacleEditMode, enabled => {
  stopObstaclePaint()
  if (!enabled) return
  cancelSelection()
  clearPreview()
  cancelTaskChainMapPick(false)
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

watch([showAutoPath, showMarkerIcons, showPathArrows, showStatusLegend, showMinimap, compareDisplayMode, compareFloatingOpacity], () => {
  saveMapDisplaySettings()
})

watch(
  [queueGroupsCollapsed, taskCardCollapsed],
  () => {
    saveTaskQueueView()
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

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (clickTimer) clearTimeout(clickTimer)
  if (previewTimer) clearTimeout(previewTimer)
  if (dispatchHelpTimer) clearTimeout(dispatchHelpTimer)
  if (templateApplyClickTimer) clearTimeout(templateApplyClickTimer)
  if (taskBuilderJumpTimer) clearTimeout(taskBuilderJumpTimer)
  if (panelSectionFocusTimer) clearTimeout(panelSectionFocusTimer)
  stopFloatingCompareRefresh()
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

      <div class="field field-with-help">
        <span class="field-label">
          {{ t('dispatch') }}
          <span
            class="help-anchor"
            @mouseenter="onDispatchHelpEnter"
            @mouseleave="onDispatchHelpLeave"
          >
            <button
              class="info-button"
              :class="{ active: showDispatchHelp }"
              type="button"
              :title="t('dispatch_help_trigger')"
              @click.stop="toggleDispatchHelp"
            >
              i
            </button>
            <div
              v-if="showDispatchHelp"
              class="help-popover"
              @mouseenter="onDispatchHelpEnter"
              @mouseleave="onDispatchHelpLeave"
            >
              <div class="help-title">{{ t('dispatch_help_title') }}</div>
              <div class="help-line">{{ t('dispatch_help_auto') }}</div>
              <div class="help-line">{{ t('dispatch_help_manual') }}</div>
              <div class="help-line">{{ t('dispatch_help_form') }}</div>
            </div>
          </span>
        </span>
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
    </div>

    <p class="toolbar-hint">{{ t('hint') }}</p>
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
              v-if="mainStartMarker"
              :class="showMarkerIcons ? 'point-icon point-icon-start' : 'marker start'"
              :style="pointStyle(mainStartMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>

            <div
              v-if="mainEndMarker"
              :class="showMarkerIcons ? 'point-icon point-icon-end' : 'marker end'"
              :style="pointStyle(mainEndMarker, CELL_SIZE, showMarkerIcons ? 24 : 12)"
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
                  <input :checked="obstacleEditMode" type="checkbox" @change="toggleObstacleEditMode" />
                  <span>{{ settingsLocale.obstacleEdit }}</span>
                </label>
                <p class="panel-hint map-settings-hint">{{ settingsLocale.obstacleHint }}</p>
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
                    :disabled="obstacleMapSaving || obstaclePresets.length === 0"
                    @click="applyObstaclePreset"
                  >
                    {{ settingsLocale.obstaclePresetApply }}
                  </button>
                  <button
                    class="btn-secondary"
                    type="button"
                    :disabled="obstacleMapSaving || !obstacleLayoutDirty"
                    @click="saveBlockedCells"
                  >
                    {{ settingsLocale.obstacleSave }}
                  </button>
                  <button class="btn-ghost" type="button" @click="downloadObstacleLayout">
                    {{ settingsLocale.obstacleExport }}
                  </button>
                  <button class="btn-ghost" type="button" @click="triggerObstacleLayoutImport">
                    {{ settingsLocale.obstacleImport }}
                  </button>
                  <button
                    class="btn-ghost"
                    type="button"
                    :disabled="obstacleMapSaving"
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
              v-if="minimapStartMarker"
              :class="showMarkerIcons ? 'minimap-point-icon minimap-point-start' : 'marker start minimap-marker-dot'"
              :style="pointStyle(minimapStartMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
            >
              <span v-if="showMarkerIcons">S</span>
            </div>
            <div
              v-if="minimapEndMarker"
              :class="showMarkerIcons ? 'minimap-point-icon minimap-point-end' : 'marker end minimap-marker-dot'"
              :style="pointStyle(minimapEndMarker, minimapCellSize, showMarkerIcons ? 12 : 8)"
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
                <p>{{ currentDispatchModeHint }}</p>
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
                </template>
              </div>

              <div class="task-form task-builder">
                <div class="task-builder-header">
                  <h2>{{ taskBuilderLocale.title }}</h2>
                  <button class="task-builder-mode-toggle" type="button" @click="toggleTaskBuilderMode">
                    <span class="task-builder-mode-toggle-label">{{ taskBuilderLocale.switchLabel }}</span>
                    <strong>{{ currentTaskBuilderModeCompactLabel }}</strong>
                  </button>
                </div>
                <p class="panel-hint">{{ currentTaskBuilderHint }}</p>
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
                    <label>{{ t('form_start_x') }}</label>
                    <input v-model.number="taskForm.start_x" type="number" min="0" :max="GRID_COLS - 1" />
                    <label>{{ t('form_start_y') }}</label>
                    <input v-model.number="taskForm.start_y" type="number" min="0" :max="GRID_ROWS - 1" />
                    <label>{{ t('form_end_x') }}</label>
                    <input v-model.number="taskForm.end_x" type="number" min="0" :max="GRID_COLS - 1" />
                    <label>{{ t('form_end_y') }}</label>
                    <input v-model.number="taskForm.end_y" type="number" min="0" :max="GRID_ROWS - 1" />
                  </div>
                  <button class="btn-primary full-width" type="button" @click="addTaskFromForm">
                    {{ t('add_task') }}
                  </button>
                </template>

                <template v-else>
                  <div class="task-chain-map-actions">
                    <div class="task-chain-map-toolbar">
                      <button
                        class="btn-secondary"
                        type="button"
                        :class="{ active: taskChainMapPickActive }"
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
                    :disabled="taskChainStages.length < 2"
                    @click="addTaskChainFromForm"
                  >
                    {{ taskChainLocale.createTask }}
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
    </div>
  </div>
</template>
