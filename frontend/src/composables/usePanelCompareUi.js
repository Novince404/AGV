export function usePanelCompareUi(options) {
  const {
    nextTick,
    panelSections,
    panelRef,
    controlSectionRef,
    queueSectionRef,
    templatesSectionRef,
    pointsSectionRef,
    jsonSectionRef,
    experimentsSectionRef,
    aiSectionRef,
    operationsSectionRef,
    focusedPanelSection,
    comparePanelExpanded,
    comparePanelRef,
    compareDisplayMode,
    showFloatingCompare,
    compareEntryButtonRef,
    compareFloatingX,
    compareFloatingY,
    pathCompareLoading,
    panelSearch,
    compareCurrentRoute
  } = options

  let panelSectionFocusTimer = null
  let floatingCompareRefreshTimer = null

  function panelSectionRefByKey(sectionKey) {
    const sectionMap = {
      control: controlSectionRef.value,
      queue: queueSectionRef.value,
      templates: templatesSectionRef.value,
      points: pointsSectionRef.value,
      json: jsonSectionRef.value,
      experiments: experimentsSectionRef.value,
      ai: aiSectionRef.value,
      operations: operationsSectionRef.value
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

  function clearPanelSearch() {
    panelSearch.value = ''
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

  function disposePanelCompareUi() {
    if (panelSectionFocusTimer) {
      clearTimeout(panelSectionFocusTimer)
      panelSectionFocusTimer = null
    }
    stopFloatingCompareRefresh()
  }

  return {
    jumpToPanelSearchResult,
    scrollToComparePanel,
    shouldAutoRefreshFloatingCompare,
    stopFloatingCompareRefresh,
    requestFloatingCompareRefresh,
    positionFloatingCompareBelowEntry,
    clearPanelSearch,
    handleCompareEntryClick,
    toggleComparePanelExpanded,
    closeFloatingCompare,
    disposePanelCompareUi
  }
}
