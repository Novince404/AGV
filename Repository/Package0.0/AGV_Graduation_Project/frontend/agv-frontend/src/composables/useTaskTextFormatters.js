export function useTaskTextFormatters({
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
}) {
  function statusColor(status) {
    const map = {
      idle: '#7f8c8d',
      running: '#2e7d32',
      fault: '#c62828',
      relocating: '#ef6c00',
      idle_returning: '#1976d2',
      waiting_for_charge: '#8e24aa',
      charging: '#00838f',
      emergency_stop: '#7b1f2f',
      maintenance: '#546e7a'
    }
    return map[status] ?? '#333'
  }

  function statusText(status) {
    const localized = {
      zh: {
        emergency_stop: faultLocale.value.emergencyStopped,
        maintenance: '维护中',
        idle_returning: '回仓中',
        waiting_for_charge: '前往充电',
        charging: '充电中'
      },
      ja: {
        emergency_stop: faultLocale.value.emergencyStopped,
        maintenance: '整備中',
        idle_returning: '回庫中',
        waiting_for_charge: '充電へ移動',
        charging: '充電中'
      },
      en: {
        emergency_stop: faultLocale.value.emergencyStopped,
        maintenance: 'Maintenance',
        idle_returning: 'Returning',
        waiting_for_charge: 'To Charge',
        charging: 'Charging'
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
        idle_returning: '回仓',
        waiting_for_charge: '充电',
        charging: '充电',
        emergency_stop: '急停',
        maintenance: '维护'
      },
      ja: {
        idle: '待機',
        running: '運行',
        fault: '故障',
        relocating: '移動',
        idle_returning: '回庫',
        waiting_for_charge: '充電',
        charging: '充電',
        emergency_stop: '急停',
        maintenance: '整備'
      },
      en: {
        idle: 'IDLE',
        running: 'RUN',
        fault: 'FAULT',
        relocating: 'MOVE',
        idle_returning: 'RETURN',
        waiting_for_charge: 'CHARGE',
        charging: 'CHG',
        emergency_stop: 'STOP',
        maintenance: 'MAIN'
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

  function moveToMaintenanceText() {
    if (locale.value === 'ja') return '送修下線'
    if (locale.value === 'zh') return '送修下线'
    return 'To Maintenance'
  }

  function returnToServiceText() {
    if (locale.value === 'ja') return '恢复上岗'
    if (locale.value === 'zh') return '恢复上岗'
    return 'Return To Service'
  }

  function maintenanceListTitleText() {
    if (locale.value === 'ja') return '维护中 AGV'
    if (locale.value === 'zh') return '维护中 AGV'
    return 'AGVs In Maintenance'
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
        if (locale.value === 'ja') return `${algorithmText(task.dispatch_algorithm)} で再調度待機中です。待機中または回庫中の AGV を待っています。`
        if (locale.value === 'zh') return `任务将按 ${algorithmText(task.dispatch_algorithm)} 重试，当前正在等待空闲或回仓中的 AGV。`
        return `Waiting for an idle or returning AGV to retry this task with ${algorithmText(task.dispatch_algorithm)}.`
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
      if (locale.value === 'ja') parts.push(`始点まで ${task.path_length_to_start}`)
      else if (locale.value === 'zh') parts.push(`到起点 ${task.path_length_to_start}`)
      else parts.push(`to start ${task.path_length_to_start}`)
    }
    if (task.path_length_to_end !== null && task.path_length_to_end !== undefined) {
      if (locale.value === 'ja') parts.push(`実行区間 ${task.path_length_to_end}`)
      else if (locale.value === 'zh') parts.push(`执行段 ${task.path_length_to_end}`)
      else parts.push(`run ${task.path_length_to_end}`)
    }
    return parts.join(' | ')
  }

  function formatTaskInitialPoint(task) {
    if (task?.dispatch_mode !== 'manual') return ''
    const origin = taskDispatchOrigin(task)
    if (!origin) return ''
    if (locale.value === 'ja') return `初期位置 (${origin.x},${origin.y})`
    if (locale.value === 'zh') return `初始点 (${origin.x},${origin.y})`
    return `Initial (${origin.x},${origin.y})`
  }

  function blockedTaskAlertText(task) {
    return localizeDispatchReason(task?.dispatch_reason) || task?.dispatch_reason || t('task_blocked_alert')
  }

  function isRecoveryRequiredTask(task) {
    if (!task || task.status !== 'blocked') return false
    const reason = String(task.dispatch_reason ?? '')
    return reason === 'recover_required_emergency_stop' || reason === 'recover_required_fault'
  }

  function isCellOccupiedTimeoutTask(task) {
    if (!task || task.status !== 'blocked') return false
    const reason = String(task.dispatch_reason ?? '')
    return reason === 'cell_occupied_timeout' || reason.startsWith('cell_occupied_timeout:')
  }

  function retryFromCurrentButtonText() {
    if (locale.value === 'ja') return '現在地から再試行'
    if (locale.value === 'zh') return '从当前位置重试'
    return 'Retry From Current'
  }

  function retryFromCurrentQueuedText(task, algorithmName) {
    const alg = algorithmText(algorithmName || task?.dispatch_algorithm || algorithm.value)
    if (locale.value === 'ja') return `原車待機中です。空き次第、現在地から ${alg} で再開します。`
    if (locale.value === 'zh') return `原车忙碌中，空闲后将从当前位置按 ${alg} 自动继续。`
    return `Bound AGV is busy. It will resume from current position with ${alg} when idle.`
  }

  function agvRecoveryJumpButtonText() {
    const targetAgvId = agvRecoveryJumpTargetAgvId.value
    if (!targetAgvId) return ''
    if (locale.value === 'ja') return `AGV #${targetAgvId} の復旧カードへ`
    if (locale.value === 'zh') return `跳转到 AGV #${targetAgvId} 处理卡`
    return `Jump To AGV #${targetAgvId}`
  }

  function formatTaskLastAction(task) {
    const reason = String(task?.dispatch_reason ?? '')
    if (!reason) return ''
    if (reason === 'recover_required_fault') {
      if (locale.value === 'ja') return '故障中断 -> 復旧待ち'
      if (locale.value === 'zh') return '故障中断 -> 待恢复'
      return 'Fault interrupted -> waiting recovery'
    }
    if (reason === 'recover_required_emergency_stop') {
      if (locale.value === 'ja') return '急停中断 -> 復旧待ち'
      if (locale.value === 'zh') return '急停中断 -> 待恢复'
      return 'Emergency stop interrupted -> waiting recovery'
    }
    if (reason === 'cell_occupied_timeout' || reason.startsWith('cell_occupied_timeout:')) {
      if (locale.value === 'ja') return '占有タイムアウト -> 復旧待ち'
      if (locale.value === 'zh') return '占位超时 -> 待恢复'
      return 'Cell occupied timeout -> waiting recovery'
    }
    if (reason.startsWith('recover_waiting_for_bound_agv')) {
      if (locale.value === 'ja') return '原車復旧待ち'
      if (locale.value === 'zh') return '等待原车恢复'
      return 'Waiting bound AGV recovery'
    }
    if (reason.startsWith('recover_waiting_for_idle_agv')) {
      if (locale.value === 'ja') return '改派待機中'
      if (locale.value === 'zh') return '等待改派空闲车'
      return 'Waiting for reassignment on an idle or returning AGV'
    }
    if (reason.startsWith('retry_from_current_waiting_for_bound_agv')) {
      if (locale.value === 'ja') return '原地復旧待機中'
      if (locale.value === 'zh') return '等待原地续跑'
      return 'Waiting bound AGV for resume from current'
    }
    return ''
  }

  function taskLastActionLabel() {
    if (locale.value === 'ja') return '最新処理'
    if (locale.value === 'zh') return '最近动作'
    return 'Last action'
  }

  function isTaskReasonAlert(task) {
    const reason = String(task?.dispatch_reason ?? '')
    if (!reason) return false
    return (
      reason === 'recover_required_fault' ||
      reason === 'recover_required_emergency_stop' ||
      reason === 'cell_occupied_timeout' ||
      reason.startsWith('cell_occupied_timeout:')
    )
  }

  function recoveryActionText(mode, task) {
    if (mode === 'bound') {
      if (locale.value === 'ja') return task?.preferred_agv_id ? `原車継続 #${task.preferred_agv_id}` : '原車継続'
      if (locale.value === 'zh') return task?.preferred_agv_id ? `原车继续 #${task.preferred_agv_id}` : '原车继续'
      return task?.preferred_agv_id ? `Resume Bound #${task.preferred_agv_id}` : 'Resume Bound'
    }
    if (locale.value === 'ja') return '改派実行'
    if (locale.value === 'zh') return '改派执行'
    return 'Reassign'
  }

  function recoveryQueuedText(mode, task, algorithmName) {
    const alg = algorithmText(algorithmName || task?.dispatch_algorithm || algorithm.value)
    if (mode === 'bound') {
      if (locale.value === 'ja') return `原車復旧待ちにしました。${alg} で再開します。`
      if (locale.value === 'zh') return `已进入原车恢复等待，车辆空闲后将按 ${alg} 自动继续。`
      return `Queued for bound AGV recovery. Will resume with ${alg} when idle.`
    }
    if (locale.value === 'ja') return `改派待機にしました。待機中または回庫中の AGV で ${alg} を再試行します。`
    if (locale.value === 'zh') return `已进入改派等待，空闲或回仓中的 AGV 可用后将按 ${alg} 自动重试。`
    return `Queued for reassignment. Will retry with ${alg} when any idle or returning AGV is available.`
  }

  function countRetryableBlockedTasks(taskGroup) {
    return (taskGroup?.tasks ?? []).filter(task => task.status === 'blocked' && !isRecoveryRequiredTask(task)).length
  }

  return {
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
  }
}
