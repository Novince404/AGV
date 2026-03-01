<script setup>
import './assets/agv-map.css'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const GRID_COLS = 10
const GRID_ROWS = 8
const CELL_SIZE = 50
const AGV_SIZE = 30
const API_BASE = 'http://127.0.0.1:8000'
const CUSTOM_POINTS_STORAGE_KEY = 'agv_custom_points'
const MAP_DISPLAY_STORAGE_KEY = 'agv_map_display_settings'
const TASK_TEMPLATE_STORAGE_KEY = 'agv_task_templates'
const MAP_WIDTH = GRID_COLS * CELL_SIZE
const MAP_HEIGHT = GRID_ROWS * CELL_SIZE
const MINIMAP_WIDTH = 168
const MIN_ZOOM = 0.75
const MAX_ZOOM = 3

const agvs = ref([])
const localAgvs = ref([])
const tasks = ref([])

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
const jsonText = ref('')
const jsonStatus = ref('')

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
const showMarkerIcons = ref(true)
const showPathArrows = ref(false)

let timer = null
let clickTimer = null
let previewTimer = null
let dispatchHelpTimer = null
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
    confirm_delete_task: '确认删除该未分配任务吗？',
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
    queue_assigned: '已分配队列',
    queue_running: '执行队列',
    queue_finished: '完成队列',
    queue_empty: '当前分组为空',
    dispatch_reason: '调度说明',
    dispatch_waiting: '等待空闲 AGV 调度',
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
    confirm_delete_task: 'この未割当タスクを削除しますか？',
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
    queue_assigned: '割当済キュー',
    queue_running: '実行キュー',
    queue_finished: '完了キュー',
    queue_empty: 'このグループは空です',
    dispatch_reason: '割当理由',
    dispatch_waiting: '空き AGV を待機中',
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
    confirm_delete_task: 'Delete this pending task?',
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
    queue_assigned: 'Assigned Queue',
    queue_running: 'Running Queue',
    queue_finished: 'Finished Queue',
    queue_empty: 'This section is empty',
    dispatch_reason: 'Dispatch Reason',
    dispatch_waiting: 'Waiting for an idle AGV',
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
const mapStageStyle = computed(() => ({
  width: `${MAP_WIDTH}px`,
  height: `${MAP_HEIGHT}px`,
  transform: `translate(${mapOffsetX.value}px, ${mapOffsetY.value}px) scale(${mapZoom.value})`
}))
const mapZoomLabel = computed(() => `${Math.round(mapZoom.value * 100)}%`)
const minimapScale = computed(() => MINIMAP_WIDTH / MAP_WIDTH)
const minimapHeight = computed(() => MAP_HEIGHT * minimapScale.value)
const minimapCellSize = computed(() => CELL_SIZE * minimapScale.value)
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
const minimapStartMarker = computed(() => mainStartMarker.value)
const minimapEndMarker = computed(() => mainEndMarker.value)
const pointLibrary = computed(() => [...DEFAULT_POINT_LIBRARY, ...customPoints.value])
const taskTemplates = computed(() => [...DEFAULT_TASK_TEMPLATES, ...customTaskTemplates.value])
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
    { key: 'assigned', title: t('queue_assigned') },
    { key: 'running', title: t('queue_running') },
    { key: 'finished', title: t('queue_finished') }
  ]

  return groups.map(group => ({
    ...group,
    tasks: sortTasks(tasks.value.filter(task => task.status === group.key), group.key)
  }))
})

function clampValue(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function pointStyle(point, cellSize = CELL_SIZE, size = 12) {
  return {
    left: `${point.x * cellSize + cellSize / 2 - size / 2}px`,
    top: `${point.y * cellSize + cellSize / 2 - size / 2}px`
  }
}

function sortTasks(list, status) {
  const copy = [...list]
  if (status === 'pending') {
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

function taskStatusText(status) {
  return t(`task_${status}`) ?? status
}

function algorithmText(value) {
  return value === 'astar' ? t('algo_astar') : t('algo_simple')
}

function dispatchModeText(value) {
  return value === 'manual' ? t('reason_manual') : t('reason_auto')
}

function formatTaskMeta(task) {
  return `${t('task_start')} (${task.start_x}, ${task.start_y}) -> ${t('task_end')} (${task.end_x}, ${task.end_y})`
}

function formatTaskAgv(task) {
  return `${t('task_agv')}: ${task.agv_id ?? t('selected_none')}`
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

function formatDispatchReason(task) {
  if (!task.dispatch_mode && task.status === 'pending') {
    return t('dispatch_waiting')
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

  return parts.join(' | ')
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

function isValidGridCoordinate(value, max) {
  return Number.isInteger(value) && value >= 0 && value < max
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
        showPathArrows: showPathArrows.value
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
      .filter(template => {
        return (
          typeof template?.id === 'string' &&
          typeof template?.customName === 'string' &&
          isValidGridCoordinate(template?.start_x, GRID_COLS) &&
          isValidGridCoordinate(template?.start_y, GRID_ROWS) &&
          isValidGridCoordinate(template?.end_x, GRID_COLS) &&
          isValidGridCoordinate(template?.end_y, GRID_ROWS) &&
          Number.isInteger(template?.priority)
        )
      })
      .map(template => ({
        id: template.id,
        customName: template.customName.trim(),
        start_x: template.start_x,
        start_y: template.start_y,
        end_x: template.end_x,
        end_y: template.end_y,
        priority: clampValue(template.priority, 1, 5),
        custom: true
      }))
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

function applyTaskTemplate(template) {
  taskForm.value.start_x = template.start_x
  taskForm.value.start_y = template.start_y
  taskForm.value.end_x = template.end_x
  taskForm.value.end_y = template.end_y
  taskForm.value.priority = template.priority
}

function saveCurrentTaskAsTemplate() {
  const name = taskTemplateForm.value.name.trim()
  if (!name) {
    setTaskTemplateStatus('error', t('template_form_invalid_name'))
    return
  }

  customTaskTemplates.value = [
    ...customTaskTemplates.value,
    {
      id: `task_template_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      customName: name,
      start_x: Number(taskForm.value.start_x),
      start_y: Number(taskForm.value.start_y),
      end_x: Number(taskForm.value.end_x),
      end_y: Number(taskForm.value.end_y),
      priority: Number(taskForm.value.priority),
      custom: true
    }
  ]

  taskTemplateForm.value.name = ''
  setTaskTemplateStatus('success', t('template_form_saved'))
}

function deleteTaskTemplate(template) {
  if (!template.custom) return
  const ok = window.confirm(t('confirm_delete_template'))
  if (!ok) return

  customTaskTemplates.value = customTaskTemplates.value.filter(item => item.id !== template.id)
  setTaskTemplateStatus('success', t('template_form_deleted'))
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

function cancelSelection() {
  selectedAgvId.value = null
  startPoint.value = null
  clearManualDestination()
}

function findAgvById(id) {
  return displayAgvs.value.find(agv => agv.id === id)
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
  if (!rect) return { x: 0, y: 0 }

  const worldX = (clientX - rect.left - mapOffsetX.value) / mapZoom.value
  const worldY = (clientY - rect.top - mapOffsetY.value) / mapZoom.value

  return {
    x: clampValue(worldX, 0, MAP_WIDTH - 1),
    y: clampValue(worldY, 0, MAP_HEIGHT - 1)
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
  return {
    x: clampValue(Math.floor(point.x / CELL_SIZE), 0, GRID_COLS - 1),
    y: clampValue(Math.floor(point.y / CELL_SIZE), 0, GRID_ROWS - 1)
  }
}

function buildSimplePath(sx, sy, ex, ey) {
  const path = []
  let x = sx
  let y = sy

  while (x !== ex || y !== ey) {
    path.push({ x, y })
    if (x < ex) x += 1
    else if (x > ex) x -= 1
    else if (y < ey) y += 1
    else if (y > ey) y -= 1
  }

  path.push({ x: ex, y: ey })
  return path
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

  mapPanCandidate = true
  mapPanMoved = false
  mapPanStartX = event.clientX
  mapPanStartY = event.clientY
  mapPanOriginX = mapOffsetX.value
  mapPanOriginY = mapOffsetY.value
}

function onMapDoubleClick(event) {
  if (ignoreNextMapClick) {
    ignoreNextMapClick = false
    return
  }
  if (clickTimer) {
    clearTimeout(clickTimer)
    clickTimer = null
  }

  const { x, y } = getCellFromEvent(event)
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
  const { x, y } = getCellFromEvent(event)
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
  const worldX = (pointerX - mapOffsetX.value) / mapZoom.value
  const worldY = (pointerY - mapOffsetY.value) / mapZoom.value
  const ratio = event.deltaY < 0 ? 1.12 : 0.88
  const nextZoom = clampValue(Number((mapZoom.value * ratio).toFixed(3)), MIN_ZOOM, MAX_ZOOM)
  if (nextZoom === mapZoom.value) return

  mapZoom.value = nextZoom
  mapOffsetX.value = pointerX - worldX * nextZoom
  mapOffsetY.value = pointerY - worldY * nextZoom
  clampMapTransform()
}

function toggleMapSettings() {
  showMapSettings.value = !showMapSettings.value
}

function handleSingleClick(x, y) {
  if (dispatchMode.value === 'manual') {
    if (!selectedAgvId.value) return
    const agv = findAgvById(selectedAgvId.value)
    if (!agv || agv.status !== 'idle') return

    startPoint.value = { x: agv.x, y: agv.y }
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

async function confirmAndSchedule(x, y, agvId = null) {
  const ok = window.confirm(t('confirm_dispatch'))
  if (!ok) return
  endPoint.value = { x, y }
  await createTaskAndSchedule(agvId)
}

async function createTaskAndSchedule(agvId) {
  if (!startPoint.value || !endPoint.value) return

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
      throw new Error(createData?.detail || 'Task create failed')
    }

    await fetchTasks()

    if (dispatchMode.value === 'auto') {
      await tryAutoSchedule()
      clearAutoMarkers()
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
      throw new Error(scheduleData?.detail || 'Schedule failed')
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
  if (isPanelResizing) {
    const deltaX = event.clientX - panelResizeStartX
    syncPanelWidth(panelResizeStartWidth - deltaX)
    return
  }

  if (isMinimapDragging) {
    handleMinimapNavigation(event)
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
  if (isPanelResizing) {
    isPanelResizing = false
    document.body.style.cursor = ''
  }

  if (isMinimapDragging) {
    isMinimapDragging = false
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
    if (!scheduleRes.ok) return

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
  if (task.status !== 'pending') return
  const ok = window.confirm(t('confirm_delete_task'))
  if (!ok) return

  try {
    const res = await fetch(`${API_BASE}/task/${task.id}`, {
      method: 'DELETE'
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data?.detail || 'Delete failed')
    }
    if (previewTaskId.value === task.id) {
      clearPreview()
    }
    await fetchTasks()
  } catch (error) {
    console.error('Delete task error:', error)
  }
}

async function submitTaskPayload(payload) {
  if (
    Number.isNaN(payload.start_x) ||
    Number.isNaN(payload.start_y) ||
    Number.isNaN(payload.end_x) ||
    Number.isNaN(payload.end_y)
  ) {
    return
  }

  try {
    const res = await fetch(`${API_BASE}/task/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data?.detail || 'Create task failed')
    }
    await fetchTasks()
    if (dispatchMode.value === 'auto') {
      await tryAutoSchedule()
    }
  } catch (error) {
    console.error('Create task form error:', error)
  }
}

async function addTaskFromForm() {
  const payload = {
    start_x: Number(taskForm.value.start_x),
    start_y: Number(taskForm.value.start_y),
    end_x: Number(taskForm.value.end_x),
    end_y: Number(taskForm.value.end_y),
    priority: Number(taskForm.value.priority)
  }

  await submitTaskPayload(payload)
}

async function createTaskFromTemplate(template) {
  await submitTaskPayload({
    start_x: Number(template.start_x),
    start_y: Number(template.start_y),
    end_x: Number(template.end_x),
    end_y: Number(template.end_y),
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
      throw new Error(data?.detail || 'Import failed')
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
      throw new Error(data?.detail || 'Export failed')
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
  if (task.status !== 'pending') return
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    previewTaskId.value = task.id
    previewStart.value = { x: task.start_x, y: task.start_y }
    previewEnd.value = { x: task.end_x, y: task.end_y }
    previewPath.value = buildSimplePath(task.start_x, task.start_y, task.end_x, task.end_y)
  }, 400)
}

function onTaskLeave() {
  clearPreview()
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
  if (mode === 'manual') {
    clearAutoPaths()
    clearAutoMarkers()
  }
})

onMounted(() => {
  loadCustomPoints()
  loadTaskTemplates()
  loadMapDisplaySettings()
  syncPanelWidth()
  updateMapViewportMetrics(true)
  if (typeof ResizeObserver !== 'undefined') {
    mapResizeObserver = new ResizeObserver(() => {
      updateMapViewportMetrics()
    })
    if (mapViewportRef.value) {
      mapResizeObserver.observe(mapViewportRef.value)
    }
  }
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

watch([showAutoPath, showMarkerIcons, showPathArrows], () => {
  saveMapDisplaySettings()
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (clickTimer) clearTimeout(clickTimer)
  if (previewTimer) clearTimeout(previewTimer)
  if (dispatchHelpTimer) clearTimeout(dispatchHelpTimer)
  if (mapResizeObserver) mapResizeObserver.disconnect()
  document.body.style.cursor = ''
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('mousemove', onGlobalMouseMove)
  window.removeEventListener('mouseup', onGlobalMouseUp)
})
</script>

<template>
  <div class="page-shell">
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

      <label class="field checkbox-field">
        <input v-model="showAutoPath" type="checkbox" />
        <span>{{ t('show_auto_path') }}</span>
      </label>

      <div class="status-pill">
        {{ t('selected') }}:
        <span v-if="selectedAgv">#{{ selectedAgv.id }} / {{ statusText(selectedAgv.status) }}</span>
        <span v-else>{{ t('selected_none') }}</span>
      </div>
    </div>

    <p class="toolbar-hint">{{ t('hint') }}</p>

    <div ref="layoutRef" class="layout" :style="layoutStyle">
      <div class="map-pane">
        <div class="map-legend legend">
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

        <section
          ref="mapViewportRef"
          class="map"
          :class="{ panning: isMapPanning }"
          @mousedown="onMapMouseDown"
          @click="onMapClick"
          @dblclick="onMapDoubleClick"
          @wheel.prevent="onMapWheel"
          @contextmenu="onMapContextMenu"
        >
          <div class="map-stage" :style="mapStageStyle">
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
              {{ t('map_settings_toggle') }}
            </button>
            <div v-if="showMapSettings" class="map-settings-panel">
              <div class="map-settings-title">{{ t('map_settings') }}</div>
              <label class="map-setting-row">
                <input v-model="showMarkerIcons" type="checkbox" />
                <span>{{ t('map_setting_icons') }}</span>
              </label>
              <label class="map-setting-row">
                <input v-model="showPathArrows" type="checkbox" />
                <span>{{ t('map_setting_arrows') }}</span>
              </label>
              <button class="map-settings-action" type="button" @click="resetMapView">
                {{ t('map_reset_view') }}
              </button>
            </div>
          </div>

          <div
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
            <div class="minimap-viewport" :style="minimapViewportStyle"></div>
          </div>
        </section>
      </div>

      <div class="panel-resizer" @mousedown="startPanelResize"></div>

      <aside class="panel-shell">
        <div ref="panelRef" class="panel" @scroll="onPanelScroll">
      <div class="task-form">
        <h2>{{ t('task_form') }}</h2>
        <div class="form-grid">
          <label>{{ t('form_start_x') }}</label>
          <input v-model.number="taskForm.start_x" type="number" min="0" :max="GRID_COLS - 1" />
          <label>{{ t('form_start_y') }}</label>
          <input v-model.number="taskForm.start_y" type="number" min="0" :max="GRID_ROWS - 1" />
          <label>{{ t('form_end_x') }}</label>
          <input v-model.number="taskForm.end_x" type="number" min="0" :max="GRID_COLS - 1" />
          <label>{{ t('form_end_y') }}</label>
          <input v-model.number="taskForm.end_y" type="number" min="0" :max="GRID_ROWS - 1" />
          <label>{{ t('task_priority') }}</label>
          <select v-model.number="taskForm.priority">
            <option :value="5">5</option>
            <option :value="4">4</option>
            <option :value="3">3</option>
            <option :value="2">2</option>
            <option :value="1">1</option>
          </select>
        </div>
        <button class="btn-primary full-width" type="button" @click="addTaskFromForm">
          {{ t('add_task') }}
        </button>
      </div>

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
          <button class="btn-primary full-width" type="button" @click="saveCurrentTaskAsTemplate">
            {{ t('template_save_current') }}
          </button>
          <div v-if="taskTemplateStatus" class="template-status" :class="taskTemplateStatusType">
            {{ taskTemplateStatus }}
          </div>
        </div>

        <div class="template-list">
          <article v-for="template in taskTemplates" :key="template.id" class="template-card">
            <div class="template-head">
              <strong>{{ taskTemplateName(template) }}</strong>
              <span class="point-badge" :class="{ custom: template.custom }">
                {{ taskTemplateTypeText(template) }}
              </span>
            </div>
            <div class="template-meta">
              {{ t('task_start') }} ({{ template.start_x }}, {{ template.start_y }}) ->
              {{ t('task_end') }} ({{ template.end_x }}, {{ template.end_y }})
            </div>
            <div class="template-meta">{{ t('task_priority') }}: {{ template.priority }}</div>
            <div class="template-actions">
              <button class="btn-secondary" type="button" @click="applyTaskTemplate(template)">
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
          <article v-for="point in filteredPoints" :key="point.id" class="point-card">
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

      <div class="json-tools">
        <h2>{{ t('json_tools') }}</h2>
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

      <div class="queue-panel">
        <h2>{{ t('tasks') }}</h2>
        <div v-if="tasks.length === 0" class="empty">{{ t('tasks_empty') }}</div>

        <section v-for="group in taskGroups" :key="group.key" class="queue-group">
          <div class="queue-header">
            <span>{{ group.title }}</span>
            <span class="queue-count">{{ group.tasks.length }}</span>
          </div>

          <div v-if="group.tasks.length === 0" class="queue-empty">
            {{ t('queue_empty') }}
          </div>

          <article
            v-for="task in group.tasks"
            :key="task.id"
            class="task-card"
            :class="{ previewing: previewTaskId === task.id }"
            @mouseenter="onTaskHover(task)"
            @mouseleave="onTaskLeave"
          >
            <div class="task-head">
              <strong>#{{ task.id }}</strong>
              <span class="status-badge" :class="task.status">{{ taskStatusText(task.status) }}</span>
            </div>
            <div class="task-line">{{ formatTaskMeta(task) }}</div>
            <div class="task-line">{{ t('task_priority') }}: {{ task.priority }}</div>
            <div class="task-line">{{ formatTaskAgv(task) }}</div>
            <div class="task-line task-reason">
              {{ t('dispatch_reason') }}: {{ formatDispatchReason(task) }}
            </div>
            <div v-if="formatTaskTime(task)" class="task-line task-time">
              {{ formatTaskTime(task) }}
            </div>
            <div class="task-actions">
              <button
                v-if="task.status === 'pending'"
                class="btn-delete"
                type="button"
                @click="deleteTask(task)"
              >
                {{ t('delete_task') }}
              </button>
            </div>
          </article>
        </section>
      </div>
        </div>
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
  </div>
</template>
