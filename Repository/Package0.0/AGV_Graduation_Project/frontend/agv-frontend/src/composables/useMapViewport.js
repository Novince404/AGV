export function useMapViewport(options) {
  const {
    constants,
    refs,
    clampValue
  } = options

  const {
    MAP_WIDTH,
    MAP_HEIGHT,
    MINIMAP_WIDTH,
    MIN_ZOOM,
    MAX_ZOOM,
    CELL_SIZE,
    GRID_COLS,
    GRID_ROWS
  } = constants

  const {
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
  } = refs

  let mapViewReady = false
  let isMinimapDragging = false
  let isPanelResizing = false
  let panelResizeStartX = 0
  let panelResizeStartWidth = 0

  function syncPanelWidth(nextWidth = panelWidth.value) {
    if (isCompactLayout.value) return
    const layoutWidth = layoutRef.value?.clientWidth ?? windowWidth.value
    const minWidth = 320
    const maxWidth = Math.max(minWidth, layoutWidth - 280)
    panelWidth.value = clampValue(Math.round(nextWidth), minWidth, maxWidth)
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
    const minimapScale = MAP_WIDTH > 0 ? Math.min(MINIMAP_WIDTH / MAP_WIDTH, 1) : 1
    const rect = minimapRef.value?.getBoundingClientRect()
    if (!rect) return { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 }

    return {
      x: clampValue((event.clientX - rect.left) / minimapScale, 0, MAP_WIDTH),
      y: clampValue((event.clientY - rect.top) / minimapScale, 0, MAP_HEIGHT)
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

  function onMapWheel(event) {
    const rect = mapViewportRef.value?.getBoundingClientRect()
    if (!rect) return

    const pointerX = event.clientX - rect.left
    const pointerY = event.clientY - rect.top
    changeMapZoom(event.deltaY, pointerX, pointerY)
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

  function handleGlobalMouseMove(event) {
    if (isPanelResizing) {
      const deltaX = event.clientX - panelResizeStartX
      syncPanelWidth(panelResizeStartWidth - deltaX)
      return true
    }

    if (isMinimapDragging) {
      handleMinimapNavigation(event)
      return true
    }

    return false
  }

  function handleGlobalMouseUp() {
    let handled = false
    if (isPanelResizing) {
      isPanelResizing = false
      document.body.style.cursor = ''
      handled = true
    }

    if (isMinimapDragging) {
      isMinimapDragging = false
      handled = true
    }

    return handled
  }

  return {
    syncPanelWidth,
    centerMapView,
    resetMapView,
    updateMapZoom,
    changeMapZoom,
    clampMapTransform,
    updateMapViewportMetrics,
    focusMapAtWorld,
    getMapPointFromClient,
    getWorldPointFromMinimapEvent,
    getCellFromEvent,
    getCellFromClient,
    onMapWheel,
    startPanelResize,
    onMinimapMouseDown,
    onWindowResize,
    handleGlobalMouseMove,
    handleGlobalMouseUp
  }
}
