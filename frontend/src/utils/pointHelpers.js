export function normalizeStoredCustomPoints(points, options) {
  const { gridCols, gridRows, isValidGridCoordinate } = options
  if (!Array.isArray(points)) return []

  return points
    .filter(point => {
      return (
        typeof point?.id === 'string' &&
        typeof point?.customName === 'string' &&
        typeof point?.customZone === 'string' &&
        isValidGridCoordinate(point?.x, gridCols) &&
        isValidGridCoordinate(point?.y, gridRows)
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
}

export function buildCustomPoint({ name, zone, x, y }) {
  return {
    id: `custom_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    x,
    y,
    customName: name,
    customZone: zone,
    aliases: [name, zone, `${x},${y}`, `${x} ${y}`],
    custom: true
  }
}
