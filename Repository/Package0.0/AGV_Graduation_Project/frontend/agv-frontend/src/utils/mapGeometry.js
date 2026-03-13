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
