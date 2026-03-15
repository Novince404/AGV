import { computed, ref } from 'vue'
import { buildAStarPath, buildSimplePath } from '../utils/pathPreview'

export function useTaskPreview(options) {
  const {
    algorithm,
    GRID_COLS,
    GRID_ROWS,
    isBlockedCell,
    currentTaskStage,
    taskRemainingWaypoints,
    resolveTaskDisplayStartMarker,
    resolveTaskDisplayEndMarker,
    toSvgPoints,
    toArrowSegments
  } = options

  const previewTaskId = ref(null)
  const previewStart = ref(null)
  const previewEnd = ref(null)
  const previewPath = ref([])

  let previewTimer = null

  const previewPathPoints = computed(() => toSvgPoints(previewPath.value))
  const previewPathArrows = computed(() => toArrowSegments(previewPath.value))

  function buildPreviewPathByAlgorithm(sx, sy, ex, ey) {
    return algorithm.value === 'astar'
      ? buildAStarPath(sx, sy, ex, ey, GRID_COLS, GRID_ROWS, isBlockedCell)
      : buildSimplePath(sx, sy, ex, ey, isBlockedCell)
  }

  function buildPreviewPathForTask(task) {
    const waypoints =
      Number(task?.total_stages ?? 1) > 1
        ? taskRemainingWaypoints(task)
        : (() => {
            const stage = currentTaskStage(task)
            const startX = Number(stage?.start_x ?? task.start_x)
            const startY = Number(stage?.start_y ?? task.start_y)
            const endX = Number(stage?.end_x ?? task.end_x)
            const endY = Number(stage?.end_y ?? task.end_y)
            if (![startX, startY, endX, endY].every(Number.isFinite)) return []
            return [
              { x: startX, y: startY },
              { x: endX, y: endY }
            ]
          })()

    if (waypoints.length < 2) return []

    const path = []
    for (let index = 0; index < waypoints.length - 1; index += 1) {
      const from = waypoints[index]
      const to = waypoints[index + 1]
      const segment = buildPreviewPathByAlgorithm(from.x, from.y, to.x, to.y)
      if (!segment.length) continue
      if (path.length && segment[0]?.x === path[path.length - 1]?.x && segment[0]?.y === path[path.length - 1]?.y) {
        path.push(...segment.slice(1))
      } else {
        path.push(...segment)
      }
    }
    return path
  }

  function canPreviewTask(task) {
    return ['pending', 'blocked', 'assigned', 'running'].includes(task?.status)
  }

  function refreshTaskPreview(task) {
    if (!task) return
    previewTaskId.value = task.id
    previewStart.value = resolveTaskDisplayStartMarker(task)
    previewEnd.value = resolveTaskDisplayEndMarker(task)
    previewPath.value = buildPreviewPathForTask(task)
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

  function onTaskHover(task) {
    if (!canPreviewTask(task)) return
    if (previewTimer) clearTimeout(previewTimer)
    refreshTaskPreview(task)
  }

  function onTaskLeave() {
    clearPreview()
  }

  return {
    previewTaskId,
    previewStart,
    previewEnd,
    previewPath,
    previewPathPoints,
    previewPathArrows,
    buildPreviewPathForTask,
    canPreviewTask,
    refreshTaskPreview,
    clearPreview,
    onTaskHover,
    onTaskLeave
  }
}
