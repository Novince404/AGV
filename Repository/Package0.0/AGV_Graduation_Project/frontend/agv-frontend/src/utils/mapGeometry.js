export function clampValue(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export function blockedCellKey(x, y) {
  return `${x},${y}`
}

export function pointStyle(point, cellSize = 50, size = 12) {
  return {
    left: `${point.x * cellSize + cellSize / 2 - size / 2}px`,
    top: `${point.y * cellSize + cellSize / 2 - size / 2}px`
  }
}

export function toSvgPoints(points, cellSize = 50) {
  return points
    .map(point => {
      const cx = point.x * cellSize + cellSize / 2
      const cy = point.y * cellSize + cellSize / 2
      return `${cx},${cy}`
    })
    .join(' ')
}

export function toArrowSegments(points, cellSize = 50) {
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

export function buildCellBoundarySegments(cells, cellSize = 50) {
  const normalizedCellSize = Math.max(Number(cellSize) || 0, 1)
  const cellSet = new Set(
    (Array.isArray(cells) ? cells : [])
      .filter(cell => Number.isInteger(cell?.x) && Number.isInteger(cell?.y))
      .map(cell => blockedCellKey(cell.x, cell.y))
  )
  const segments = []

  for (const cell of Array.isArray(cells) ? cells : []) {
    const x = Number(cell?.x)
    const y = Number(cell?.y)
    if (!Number.isInteger(x) || !Number.isInteger(y)) continue

    if (!cellSet.has(blockedCellKey(x, y - 1))) {
      segments.push({
        key: `top-${x}-${y}`,
        x1: x * normalizedCellSize,
        y1: y * normalizedCellSize,
        x2: (x + 1) * normalizedCellSize,
        y2: y * normalizedCellSize
      })
    }

    if (!cellSet.has(blockedCellKey(x + 1, y))) {
      segments.push({
        key: `right-${x}-${y}`,
        x1: (x + 1) * normalizedCellSize,
        y1: y * normalizedCellSize,
        x2: (x + 1) * normalizedCellSize,
        y2: (y + 1) * normalizedCellSize
      })
    }

    if (!cellSet.has(blockedCellKey(x, y + 1))) {
      segments.push({
        key: `bottom-${x}-${y}`,
        x1: x * normalizedCellSize,
        y1: (y + 1) * normalizedCellSize,
        x2: (x + 1) * normalizedCellSize,
        y2: (y + 1) * normalizedCellSize
      })
    }

    if (!cellSet.has(blockedCellKey(x - 1, y))) {
      segments.push({
        key: `left-${x}-${y}`,
        x1: x * normalizedCellSize,
        y1: y * normalizedCellSize,
        x2: x * normalizedCellSize,
        y2: (y + 1) * normalizedCellSize
      })
    }
  }

  return segments
}

export function buildDirectionalArrowSegments(edge, options = {}) {
  const {
    cellSize = 50,
    compact = false
  } = options
  const direction = String(edge?.direction || 'bidirectional')
  if (direction === 'bidirectional') return []

  const rawStartX = Number(direction === 'reverse' ? edge?.x2 : edge?.x1)
  const rawStartY = Number(direction === 'reverse' ? edge?.y2 : edge?.y1)
  const rawEndX = Number(direction === 'reverse' ? edge?.x1 : edge?.x2)
  const rawEndY = Number(direction === 'reverse' ? edge?.y1 : edge?.y2)
  const dx = rawEndX - rawStartX
  const dy = rawEndY - rawStartY
  const distance = Math.hypot(dx, dy)
  if (!Number.isFinite(distance) || distance <= 0) return []

  const unitX = dx / distance
  const unitY = dy / distance
  const normalizedCellSize = Math.max(Number(cellSize) || 0, 1)
  const arrowCount = compact
    ? 1
    : Math.max(2, Math.min(4, Math.round(distance / Math.max(normalizedCellSize * 1.15, 1))))
  const arrowLength = compact
    ? Math.min(distance * 0.58, normalizedCellSize * 0.8)
    : Math.min(distance * 0.32, normalizedCellSize * 0.72)

  const segments = []
  for (let index = 0; index < arrowCount; index += 1) {
    const progress = (index + 1) / (arrowCount + 1)
    const centerX = rawStartX + unitX * distance * progress
    const centerY = rawStartY + unitY * distance * progress
    segments.push({
      key: `${String(edge?.key || 'edge')}-${direction}-${compact ? 'compact' : 'full'}-${index}`,
      laneType: String(edge?.laneType || 'main'),
      x1: centerX - unitX * (arrowLength / 2),
      y1: centerY - unitY * (arrowLength / 2),
      x2: centerX + unitX * (arrowLength / 2),
      y2: centerY + unitY * (arrowLength / 2)
    })
  }

  return segments
}
