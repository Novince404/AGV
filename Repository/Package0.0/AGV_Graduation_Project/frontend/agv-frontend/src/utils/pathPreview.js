function toCellKey(x, y) {
  return `${x},${y}`
}

function buildSimpleCandidatePath(sx, sy, ex, ey, axisOrder, isBlockedCell) {
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

export function buildSimplePath(sx, sy, ex, ey, isBlockedCell) {
  if (isBlockedCell(sx, sy) || isBlockedCell(ex, ey)) return []
  if (sx === ex && sy === ey) return [{ x: sx, y: sy }]

  const xFirst = buildSimpleCandidatePath(sx, sy, ex, ey, ['x', 'y'], isBlockedCell)
  if (xFirst.length > 0) return xFirst

  return buildSimpleCandidatePath(sx, sy, ex, ey, ['y', 'x'], isBlockedCell)
}

export function buildAStarPath(sx, sy, ex, ey, gridCols, gridRows, isBlockedCell) {
  if (isBlockedCell(sx, sy) || isBlockedCell(ex, ey)) return []
  if (sx === ex && sy === ey) return [{ x: sx, y: sy }]

  const startKey = toCellKey(sx, sy)
  const goalKey = toCellKey(ex, ey)
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
        cursorKey = toCellKey(previous.x, previous.y)
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
      if (nx < 0 || nx >= gridCols || ny < 0 || ny >= gridRows) continue
      if (isBlockedCell(nx, ny)) continue

      const neighborKey = toCellKey(nx, ny)
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
