export function useTemplatePointActions(options) {
  const {
    t,
    GRID_COLS,
    GRID_ROWS,
    taskForm,
    taskChainStages,
    taskBuilderMode,
    taskTemplateForm,
    customPointForm,
    customPoints,
    customTaskTemplates,
    pointFormStatus,
    pointFormStatusType,
    taskTemplateStatus,
    taskTemplateStatusType,
    templateJsonText,
    templateJsonStatus,
    templateJsonStatusType,
    templateFileInputRef,
    taskBuilderLocale,
    templateJsonLocale,
    normalizeTemplateStages,
    buildTemplateFromStages,
    buildTaskTemplateSignature,
    normalizeImportedTaskTemplate,
    formatTemplateJsonSummary,
    buildTemplateExportPayload,
    isValidGridCoordinate,
    createTaskChainStage,
    buildCustomPoint,
    savePointToBackend,
    deletePointFromBackend,
    saveTemplateToBackend,
    saveTemplatesBatchToBackend,
    deleteTemplateFromBackend,
    syncManualDispatchBuilderState,
    hideTaskBuilderJumpButton,
    showTaskBuilderJumpButton,
    focusTaskBuilder
  } = options

  let templateApplyClickTimer = null

  function resolveValue(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value
  }

  function gridCols() {
    return Number(resolveValue(GRID_COLS))
  }

  function gridRows() {
    return Number(resolveValue(GRID_ROWS))
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

  function setTemplateJsonStatus(type, message) {
    templateJsonStatusType.value = type
    templateJsonStatus.value = message
  }

  async function addCustomPoint() {
    const name = customPointForm.value.name.trim()
    const zone = customPointForm.value.zone.trim()
    const x = Number(customPointForm.value.x)
    const y = Number(customPointForm.value.y)

    if (!name || !zone) {
      setPointFormStatus('error', t('point_form_invalid_name'))
      return
    }

    if (!isValidGridCoordinate(x, gridCols()) || !isValidGridCoordinate(y, gridRows())) {
      setPointFormStatus('error', t('point_form_invalid_coords'))
      return
    }

    const point = buildCustomPoint({ name, zone, x, y })
    const handledByBackend = savePointToBackend ? await savePointToBackend(point) : false
    if (!handledByBackend) {
      customPoints.value = [...customPoints.value, point]
    }

    resetCustomPointForm()
    setPointFormStatus('success', t('point_form_saved'))
  }

  async function deleteCustomPoint(point) {
    if (!point.custom) return
    const ok = window.confirm(t('confirm_delete_point'))
    if (!ok) return

    const handledByBackend = deletePointFromBackend ? await deletePointFromBackend(point.id) : false
    if (!handledByBackend) {
      customPoints.value = customPoints.value.filter(item => item.id !== point.id)
    }
    setPointFormStatus('success', t('point_form_deleted'))
  }

  async function applyTaskTemplate(template, extra = {}) {
    const stages = normalizeTemplateStages(template)
    if (stages.length === 0) return

    const firstStage = stages[0]
    taskForm.value.start_x = firstStage.start_x
    taskForm.value.start_y = firstStage.start_y
    taskForm.value.end_x = firstStage.end_x
    taskForm.value.end_y = firstStage.end_y
    taskForm.value.priority = template.priority
    taskChainStages.value = stages.map(stage => createTaskChainStage(stage))
    taskBuilderMode.value = stages.length > 1 ? 'chain' : 'single'
    syncManualDispatchBuilderState()

    if (stages.length > 1) {
      setTaskTemplateStatus('info', `${taskBuilderLocale.value.loadedChain} ${taskBuilderLocale.value.jumpHint}`)
    } else {
      setTaskTemplateStatus('info', `${taskBuilderLocale.value.loadedSingle} ${taskBuilderLocale.value.jumpHint}`)
    }

    if (extra.focus) {
      hideTaskBuilderJumpButton()
      await focusTaskBuilder(taskBuilderMode.value)
      return
    }

    showTaskBuilderJumpButton()
  }

  function onTemplateApplyClick(template) {
    if (templateApplyClickTimer) {
      clearTimeout(templateApplyClickTimer)
    }
    templateApplyClickTimer = setTimeout(() => {
      templateApplyClickTimer = null
      void applyTaskTemplate(template)
    }, 220)
  }

  function onTemplateApplyDoubleClick(template) {
    if (templateApplyClickTimer) {
      clearTimeout(templateApplyClickTimer)
      templateApplyClickTimer = null
    }
    void applyTaskTemplate(template, { focus: true })
  }

  async function saveCurrentTaskAsTemplate() {
    const name = taskTemplateForm.value.name.trim()
    if (!name) {
      setTaskTemplateStatus('error', t('template_form_invalid_name'))
      return
    }

    const template = buildTemplateFromStages({
      name,
      priority: Number(taskForm.value.priority),
      stages: [
        {
          start_x: Number(taskForm.value.start_x),
          start_y: Number(taskForm.value.start_y),
          end_x: Number(taskForm.value.end_x),
          end_y: Number(taskForm.value.end_y)
        }
      ],
      custom: true
    })
    if (!template) {
      setTaskTemplateStatus('error', t('point_form_invalid_coords'))
      return
    }

    const handledByBackend = saveTemplateToBackend ? await saveTemplateToBackend(template) : false
    if (!handledByBackend) {
      customTaskTemplates.value = [...customTaskTemplates.value, template]
    }
    taskTemplateForm.value.name = ''
    hideTaskBuilderJumpButton()
    setTaskTemplateStatus('success', t('template_form_saved'))
  }

  async function saveCurrentTaskChainAsTemplate() {
    const name = taskTemplateForm.value.name.trim()
    if (!name) {
      setTaskTemplateStatus('error', t('template_form_invalid_name'))
      return
    }

    const template = buildTemplateFromStages({
      name,
      priority: Number(taskForm.value.priority),
      stages: taskChainStages.value,
      custom: true
    })
    if (!template || normalizeTemplateStages(template).length < 2) {
      setTaskTemplateStatus('error', t('point_form_invalid_coords'))
      return
    }

    const handledByBackend = saveTemplateToBackend ? await saveTemplateToBackend(template) : false
    if (!handledByBackend) {
      customTaskTemplates.value = [...customTaskTemplates.value, template]
    }
    taskTemplateForm.value.name = ''
    hideTaskBuilderJumpButton()
    setTaskTemplateStatus('success', t('template_form_saved'))
  }

  async function deleteTaskTemplate(template) {
    if (!template.custom) return
    const ok = window.confirm(t('confirm_delete_template'))
    if (!ok) return

    const handledByBackend = deleteTemplateFromBackend ? await deleteTemplateFromBackend(template.id) : false
    if (!handledByBackend) {
      customTaskTemplates.value = customTaskTemplates.value.filter(item => item.id !== template.id)
    }
    hideTaskBuilderJumpButton()
    setTaskTemplateStatus('success', t('template_form_deleted'))
  }

  function exportTaskTemplatesToJson() {
    if (customTaskTemplates.value.length === 0) {
      setTemplateJsonStatus('error', templateJsonLocale.value.exportEmpty)
      return
    }

    templateJsonText.value = JSON.stringify(buildTemplateExportPayload(), null, 2)
    setTemplateJsonStatus(
      'success',
      formatTemplateJsonSummary(templateJsonLocale.value.exportOk, customTaskTemplates.value.length)
    )
  }

  function clearTemplateJsonText() {
    templateJsonText.value = ''
    setTemplateJsonStatus('info', '')
  }

  async function importTaskTemplatesFromRaw(rawText) {
    if (!rawText.trim()) return
    setTemplateJsonStatus('info', '')

    let parsed
    try {
      parsed = JSON.parse(rawText)
    } catch {
      setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
      return
    }

    const templateItems = Array.isArray(parsed) ? parsed : parsed?.templates
    if (!Array.isArray(templateItems)) {
      setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
      return
    }

    const existingSignatures = new Set(customTaskTemplates.value.map(buildTaskTemplateSignature))
    const imported = []
    let skipped = 0

    for (const item of templateItems) {
      const normalized = normalizeImportedTaskTemplate(item)
      if (!normalized) {
        skipped += 1
        continue
      }

      const signature = buildTaskTemplateSignature(normalized)
      if (existingSignatures.has(signature)) {
        skipped += 1
        continue
      }

      existingSignatures.add(signature)
      imported.push(normalized)
    }

    if (imported.length === 0) {
      if (skipped > 0) {
        setTemplateJsonStatus('info', formatTemplateJsonSummary(templateJsonLocale.value.importOk, 0, skipped))
        return
      }

      setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
      return
    }

    const handledByBackend = saveTemplatesBatchToBackend ? await saveTemplatesBatchToBackend(imported) : false
    if (!handledByBackend) {
      customTaskTemplates.value = [...customTaskTemplates.value, ...imported]
    }
    setTemplateJsonStatus(
      'success',
      formatTemplateJsonSummary(templateJsonLocale.value.importOk, imported.length, skipped)
    )
  }

  function importTaskTemplatesFromJson() {
    void importTaskTemplatesFromRaw(templateJsonText.value)
  }

  function downloadTemplateJsonFile() {
    if (customTaskTemplates.value.length === 0) {
      setTemplateJsonStatus('error', templateJsonLocale.value.exportEmpty)
      return
    }

    const payloadText = JSON.stringify(buildTemplateExportPayload(), null, 2)
    templateJsonText.value = payloadText

    const blob = new Blob([payloadText], { type: 'application/json;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')

    link.href = url
    link.download = `agv-task-templates-${timestamp}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.setTimeout(() => window.URL.revokeObjectURL(url), 0)

    setTemplateJsonStatus(
      'success',
      formatTemplateJsonSummary(templateJsonLocale.value.exportOk, customTaskTemplates.value.length)
    )
  }

  function triggerTemplateFileImport() {
    templateFileInputRef.value?.click()
  }

  async function handleTemplateFileChange(event) {
    const file = event.target?.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      templateJsonText.value = text
      await importTaskTemplatesFromRaw(text)
    } catch (error) {
      console.error('Read template json file error:', error)
      setTemplateJsonStatus('error', templateJsonLocale.value.importFail)
    } finally {
      event.target.value = ''
    }
  }

  return {
    applyPointToTaskForm,
    resetCustomPointForm,
    setPointFormStatus,
    setTaskTemplateStatus,
    setTemplateJsonStatus,
    addCustomPoint,
    deleteCustomPoint,
    applyTaskTemplate,
    onTemplateApplyClick,
    onTemplateApplyDoubleClick,
    saveCurrentTaskAsTemplate,
    saveCurrentTaskChainAsTemplate,
    deleteTaskTemplate,
    exportTaskTemplatesToJson,
    clearTemplateJsonText,
    importTaskTemplatesFromRaw,
    importTaskTemplatesFromJson,
    downloadTemplateJsonFile,
    triggerTemplateFileImport,
    handleTemplateFileChange
  }
}
