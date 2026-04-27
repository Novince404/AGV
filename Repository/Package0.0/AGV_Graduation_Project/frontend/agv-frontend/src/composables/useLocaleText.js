import { computed } from 'vue'
import { LOCALE_TEXTS } from '../locales'

export function useLocaleText(locale) {
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

    if (reason.startsWith('cell_occupied_retrying:')) {
      const retryCount = Number(reason.split(':')[1] ?? 1)
      if (locale.value === 'ja') return `前方占有が続くため、経路を再計算して自動再試行中 (${retryCount})。`
      if (locale.value === 'zh') return `前方占位持续，正在重算路径并自动重试（第 ${retryCount} 次）。`
      return `Cell is still occupied. Replanning and auto retrying (${retryCount}).`
    }

    if (reason.startsWith('grid_dynamic_yield:')) {
      const blockerMatch = reason.match(/blocker_agv=(\d+)/)
      const targetMatch = reason.match(/yield_to=(-?\d+),(-?\d+)/)
      const blockerText = blockerMatch ? `AGV #${blockerMatch[1]}` : 'another AGV'
      const targetText = targetMatch ? `(${targetMatch[1]}, ${targetMatch[2]})` : ''
      if (locale.value === 'ja') {
        return targetText
          ? `前方が ${blockerText} に占有されています。退避格 ${targetText} に一時退避しています。`
          : `前方が ${blockerText} に占有されています。近くの退避格に一時退避しています。`
      }
      if (locale.value === 'zh') {
        return targetText
          ? `前方被 ${blockerText} 占用，正在临时让行到 ${targetText}。`
          : `前方被 ${blockerText} 占用，正在临时让行。`
      }
      return targetText
        ? `Path occupied by ${blockerText}. Yielding to ${targetText}.`
        : `Path occupied by ${blockerText}. Yielding to a nearby safe cell.`
    }

    if (reason.startsWith('grid_dynamic_replan:')) {
      const blockerMatch = reason.match(/blocker_agv=(\d+)/)
      const retryMatch = reason.match(/retry=(\d+)/)
      const blockerText = blockerMatch ? `AGV #${blockerMatch[1]}` : 'another AGV'
      const retryText = retryMatch ? retryMatch[1] : ''
      if (locale.value === 'ja') {
        return retryText
          ? `前方が ${blockerText} に占有されています。経路を再計算しています（${retryText} 回目）。`
          : `前方が ${blockerText} に占有されています。経路を再計算しています。`
      }
      if (locale.value === 'zh') {
        return retryText
          ? `前方被 ${blockerText} 占用，正在重新规划路线（第 ${retryText} 次）。`
          : `前方被 ${blockerText} 占用，正在重新规划路线。`
      }
      return retryText
        ? `Path occupied by ${blockerText}. Replanning route (${retryText}).`
        : `Path occupied by ${blockerText}. Replanning route.`
    }

    if (reason.startsWith('topology_edge_waiting:') || reason.startsWith('topology_edge_reroute:')) {
      const [, rawPayload = ''] = reason.split(':')
      const payload = Object.fromEntries(
        rawPayload
          .split(';')
          .map(item => item.split('='))
          .filter(parts => parts.length === 2 && parts[0])
          .map(([key, value]) => [key.trim(), value.trim()])
      )
      const blockerText = payload.agv ? `AGV #${payload.agv}` : 'another AGV'
      const nodeText = payload.node || ''
      const edgeText = payload.edge || ''
      const isReroute = reason.startsWith('topology_edge_reroute:')
      const isIntersection = payload.kind === 'intersection_reserved'
      const isFollowGap = payload.kind === 'follow_gap'
      if (locale.value === 'ja') {
        if (isReroute) return isIntersection ? `交差点 ${nodeText || edgeText} が ${blockerText} に予約されています。別経路を再計算しています。` : `路段 ${edgeText} が ${blockerText} に占有されています。別経路を再計算しています。`
        if (isFollowGap) return `前方の ${blockerText} と安全間隔を保つため待機しています。`
        return isIntersection ? `交差点 ${nodeText || edgeText} が ${blockerText} に予約されています。通過可能になるまで待機しています。` : `路段 ${edgeText} が ${blockerText} に占有されています。通過可能になるまで待機しています。`
      }
      if (locale.value === 'zh') {
        if (isReroute) return isIntersection ? `交汇节点 ${nodeText || edgeText} 已被 ${blockerText} 预约，正在重新规划路线。` : `路段 ${edgeText} 被 ${blockerText} 占用，正在重新规划路线。`
        if (isFollowGap) return `正在与前方 ${blockerText} 保持安全间距，暂时等待。`
        return isIntersection ? `交汇节点 ${nodeText || edgeText} 已被 ${blockerText} 预约，正在等待放行。` : `路段 ${edgeText} 被 ${blockerText} 占用，正在等待放行。`
      }
      if (isReroute) return isIntersection ? `Intersection ${nodeText || edgeText} is reserved by ${blockerText}. Replanning route.` : `Edge ${edgeText} is occupied by ${blockerText}. Replanning route.`
      if (isFollowGap) return `Keeping a safe gap behind ${blockerText}. Waiting.`
      return isIntersection ? `Intersection ${nodeText || edgeText} is reserved by ${blockerText}. Waiting for clearance.` : `Edge ${edgeText} is occupied by ${blockerText}. Waiting for clearance.`
    }

    if (reason.startsWith('topology_edge_waiting:')) {
      if (locale.value === 'ja') return '路網エッジまたは目標ノードが他の AGV に占有されているため、一時的に待機しています。'
      if (locale.value === 'zh') return '当前拓扑路段或目标节点被其他 AGV 占用，任务正在等待可通行路段。'
      return 'The selected topology edge or target node is occupied by another AGV. Waiting for the route to clear.'
    }

    if (reason.startsWith('topology_edge_reroute:')) {
      if (locale.value === 'ja') return '路网占用冲突を検知したため、別の利用可能なエッジへ迂回するよう再計算しています。'
      if (locale.value === 'zh') return '当前拓扑路段存在会车或占用冲突，正在重算路线并尝试改走其他可用边。'
      return 'A topology occupancy conflict was detected. Replanning and trying an alternate edge.'
    }
    if (reason === 'cell_occupied_timeout' || reason.startsWith('cell_occupied_timeout:')) {
      if (locale.value === 'ja') return '前方セル占有が長時間続いたため、タスクを中断して復旧待ちにしました。'
      if (locale.value === 'zh') return '前方格子被占用超时，任务已中断并进入待恢复状态。'
      return 'The next cell stayed occupied for too long. Task paused and moved to recovery queue.'
    }

    if (reason === 'recover_required_fault') {
      if (locale.value === 'ja') return 'AGV 故障によりタスクを中断しました。復旧後に原車継続または改派を選択してください。'
      if (locale.value === 'zh') return '任务因 AGV 故障中断，请在车辆恢复后选择原车继续或改派执行。'
      return 'Task interrupted by AGV fault. Resume on bound AGV or reassign after recovery.'
    }

    if (reason === 'recover_required_emergency_stop') {
      if (locale.value === 'ja') return 'AGV 急停によりタスクを中断しました。解除後に原車継続または改派を選択してください。'
      if (locale.value === 'zh') return '任务因 AGV 急停中断，请在解除后选择原车继续或改派执行。'
      return 'Task interrupted by AGV emergency stop. Resume on bound AGV or reassign after release.'
    }

    const directReason =
      localeTexts.value.dispatchReasonText?.[reason] ??
      LOCALE_TEXTS.en.dispatchReasonText?.[reason] ??
      ''
    if (directReason) return directReason

    const [errorCode, rawAlgorithm] = reason.split(':')
    if (!rawAlgorithm) return ''

    if (
      ![
        'task_start_unreachable',
        'task_route_unreachable',
        'retry_waiting_for_idle_agv',
        'retry_waiting_for_bound_agv',
        'recover_waiting_for_idle_agv',
        'recover_waiting_for_bound_agv',
        'retry_from_current_waiting_for_bound_agv'
      ].includes(errorCode)
    ) {
      return ''
    }

    if (errorCode === 'recover_waiting_for_bound_agv') {
      const algText = apiAlgorithmText(rawAlgorithm.toLowerCase())
      if (locale.value === 'ja') return `原車の復旧待ちです。復旧後に ${algText} で再開します。`
      if (locale.value === 'zh') return `正在等待原车恢复，恢复后将按 ${algText} 继续执行。`
      return `Waiting for bound AGV recovery. Will resume with ${algText}.`
    }

    if (errorCode === 'recover_waiting_for_idle_agv') {
      const algText = apiAlgorithmText(rawAlgorithm.toLowerCase())
      if (locale.value === 'ja') return `待機中または回庫中の AGV を待っています。${algText} で改派再試行します。`
      if (locale.value === 'zh') return `正在等待空闲或回仓中的 AGV，将按 ${algText} 自动改派重试。`
      return `Waiting for an idle or returning AGV. Will retry reassignment with ${algText}.`
    }

    if (errorCode === 'retry_from_current_waiting_for_bound_agv') {
      const algText = apiAlgorithmText(rawAlgorithm.toLowerCase())
      if (locale.value === 'ja') return `原車待機中です。空き次第、現在地から ${algText} で再開します。`
      if (locale.value === 'zh') return `正在等待原车空闲，空闲后将从当前位置按 ${algText} 自动继续。`
      return `Waiting for bound AGV. It will resume from current position with ${algText}.`
    }

    const template =
      localeTexts.value.apiErrorText?.[errorCode] ??
      LOCALE_TEXTS.en.apiErrorText?.[errorCode] ??
      ''

    return fillTemplate(template, {
      algorithm: apiAlgorithmText(rawAlgorithm.toLowerCase())
    })
  }

  function localizeApiErrorDetail(detail, fallbackMessage = '') {
    const fallback = fallbackMessage || ''

    if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.error_code) {
      const localRecoverFallback = (() => {
        if (detail.error_code === 'task_has_no_bound_agv') {
          if (locale.value === 'ja') return '原車バインド情報がないため原車継続できません。改派を使用してください。'
          if (locale.value === 'zh') return '任务没有原车绑定信息，无法原车继续，请使用改派执行。'
          return 'This task has no bound AGV. Please use reassign.'
        }
        if (detail.error_code === 'task_not_recoverable') {
          if (locale.value === 'ja') return 'このタスクは現在、復旧操作の対象ではありません。'
          if (locale.value === 'zh') return '该任务当前不处于可恢复状态。'
          return 'This task is not recoverable right now.'
        }
        if (detail.error_code === 'unsupported_recover_mode') {
          if (locale.value === 'ja') return '未対応の復旧モードです。'
          if (locale.value === 'zh') return '不支持的恢复模式。'
          return 'Unsupported recovery mode.'
        }
        return fallback
      })()

      const template =
        localeTexts.value.apiErrorText?.[detail.error_code] ??
        LOCALE_TEXTS.en.apiErrorText?.[detail.error_code] ??
        localRecoverFallback

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
        [/^No idle(?: or returning)? AGV$/i, 'no_idle_agv'],
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
        /^No idle(?: or returning)? AGV can reach the task start with algorithm (simple|astar)$/i
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

  function createApiError(payload, fallbackMessage = '') {
    return new Error(localizeApiErrorDetail(payload?.detail, fallbackMessage))
  }

  return {
    t,
    localeTexts,
    localizeDispatchReason,
    localizeApiErrorDetail,
    createApiError
  }
}
