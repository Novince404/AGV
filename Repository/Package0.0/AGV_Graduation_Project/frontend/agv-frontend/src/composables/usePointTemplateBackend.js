import { ref } from 'vue'

function normalizeAliases(value) {
  return Array.isArray(value) ? value.filter(item => typeof item === 'string') : []
}

function normalizeText(value) {
  return String(value ?? '').trim().toLowerCase()
}

export function usePointTemplateBackend(options) {
  const {
    API_BASE,
    GRID_COLS,
    GRID_ROWS,
    defaultPoints,
    defaultTemplates,
    builtinPoints: builtinPointsRef,
    builtinTemplates: builtinTemplatesRef,
    pointsLoadedFromApi: pointsLoadedFromApiRef,
    templatesLoadedFromApi: templatesLoadedFromApiRef,
    customPoints,
    customTaskTemplates,
    normalizeTemplateStages,
    isValidGridCoordinate,
    createApiError,
    buildAuthHeaders
  } = options

  const builtinPoints = builtinPointsRef ?? ref([...defaultPoints])
  const builtinTemplates = builtinTemplatesRef ?? ref([...defaultTemplates])
  const pointsLoadedFromApi = pointsLoadedFromApiRef ?? ref(false)
  const templatesLoadedFromApi = templatesLoadedFromApiRef ?? ref(false)

  function resolveValue(value) {
    return value && typeof value === 'object' && 'value' in value ? value.value : value
  }

  function gridCols() {
    return Number(resolveValue(GRID_COLS))
  }

  function gridRows() {
    return Number(resolveValue(GRID_ROWS))
  }

  function normalizeBackendPoint(point) {
    const x = Number(point?.x)
    const y = Number(point?.y)
    if (!isValidGridCoordinate(x, gridCols()) || !isValidGridCoordinate(y, gridRows())) {
      return null
    }

    const isCustom = Boolean(point?.custom)
    return {
      id: String(point?.id ?? ''),
      x,
      y,
      nameKey: !isCustom && typeof point?.name_key === 'string' ? point.name_key : undefined,
      zoneKey: !isCustom && typeof point?.zone_key === 'string' ? point.zone_key : undefined,
      customName: typeof point?.custom_name === 'string' ? point.custom_name : undefined,
      customZone: isCustom && typeof point?.zone_key === 'string' ? point.zone_key : undefined,
      aliases: normalizeAliases(point?.aliases),
      custom: isCustom
    }
  }

  function normalizeBackendTemplate(template) {
    const stages = Array.isArray(template?.stages)
      ? template.stages
          .map(stage => ({
            index: Number(stage?.index ?? 0),
            start_x: Number(stage?.start_x),
            start_y: Number(stage?.start_y),
            end_x: Number(stage?.end_x),
            end_y: Number(stage?.end_y),
            label: typeof stage?.label === 'string' ? stage.label : ''
          }))
          .filter(
            stage =>
              isValidGridCoordinate(stage.start_x, gridCols()) &&
              isValidGridCoordinate(stage.start_y, gridRows()) &&
              isValidGridCoordinate(stage.end_x, gridCols()) &&
              isValidGridCoordinate(stage.end_y, gridRows())
          )
      : []

    if (stages.length === 0) {
      return null
    }

    const firstStage = stages[0]
    const lastStage = stages[stages.length - 1]
    return {
      id: String(template?.id ?? ''),
      nameKey: typeof template?.name_key === 'string' ? template.name_key : undefined,
      customName: typeof template?.custom_name === 'string' ? template.custom_name : undefined,
      start_x: firstStage.start_x,
      start_y: firstStage.start_y,
      end_x: lastStage.end_x,
      end_y: lastStage.end_y,
      stages,
      priority: Number.isFinite(Number(template?.priority)) ? Number(template.priority) : 1,
      custom: Boolean(template?.custom)
    }
  }

  async function readJsonResponse(response) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }

  async function fetchPointLibraryFromBackend() {
    try {
      const response = await fetch(`${API_BASE}/point/list`, {
        headers: buildAuthHeaders ? buildAuthHeaders() : undefined
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Load points failed')
      }

      const normalized = (Array.isArray(data) ? data : [])
        .map(normalizeBackendPoint)
        .filter(Boolean)

      builtinPoints.value = normalized.filter(point => !point.custom)
      customPoints.value = normalized.filter(point => point.custom)
      pointsLoadedFromApi.value = true
      return true
    } catch (error) {
      console.warn('Load point library from backend failed:', error)
      return false
    }
  }

  async function fetchTaskTemplatesFromBackend() {
    try {
      const response = await fetch(`${API_BASE}/template/list`, {
        headers: buildAuthHeaders ? buildAuthHeaders() : undefined
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Load templates failed')
      }

      const normalized = (Array.isArray(data) ? data : [])
        .map(normalizeBackendTemplate)
        .filter(Boolean)

      builtinTemplates.value = normalized.filter(template => !template.custom)
      customTaskTemplates.value = normalized.filter(template => template.custom)
      templatesLoadedFromApi.value = true
      return true
    } catch (error) {
      console.warn('Load task templates from backend failed:', error)
      return false
    }
  }

  function buildPointPayload(point) {
    return {
      id: point.id,
      x: Number(point.x),
      y: Number(point.y),
      name_key: point.custom ? null : point.nameKey ?? null,
      zone_key: point.custom ? point.customZone ?? null : point.zoneKey ?? null,
      custom_name: point.custom ? point.customName ?? null : null,
      aliases: normalizeAliases(point.aliases),
      custom: Boolean(point.custom)
    }
  }

  function buildPointSignature(point) {
    return [
      normalizeText(point.customName ?? point.nameKey),
      normalizeText(point.customZone ?? point.zoneKey),
      Number(point.x),
      Number(point.y)
    ].join('|')
  }

  function buildTemplatePayload(template) {
    return {
      id: template.id,
      priority: Number(template.priority ?? 1),
      name_key: template.custom ? null : template.nameKey ?? null,
      custom_name: template.custom ? template.customName ?? null : null,
      custom: Boolean(template.custom),
      stages: normalizeTemplateStages(template).map((stage, index) => ({
        index,
        start_x: Number(stage.start_x),
        start_y: Number(stage.start_y),
        end_x: Number(stage.end_x),
        end_y: Number(stage.end_y),
        label: String(stage.label ?? '').trim() || null
      }))
    }
  }

  function buildTemplateSignature(template) {
    return [
      normalizeText(template.customName ?? template.nameKey),
      Number(template.priority ?? 1),
      ...normalizeTemplateStages(template).flatMap(stage => [
        Number(stage.start_x),
        Number(stage.start_y),
        Number(stage.end_x),
        Number(stage.end_y),
        normalizeText(stage.label)
      ])
    ].join('|')
  }

  async function savePointToBackend(point) {
    try {
      const response = await fetch(`${API_BASE}/point/upsert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(buildAuthHeaders ? buildAuthHeaders() : {})
        },
        body: JSON.stringify(buildPointPayload(point))
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Save point failed')
      }
      await fetchPointLibraryFromBackend()
      return true
    } catch (error) {
      console.warn('Save point to backend failed:', error)
      return false
    }
  }

  async function deletePointFromBackend(pointId) {
    try {
      const response = await fetch(`${API_BASE}/point/${encodeURIComponent(pointId)}`, {
        method: 'DELETE',
        headers: buildAuthHeaders ? buildAuthHeaders() : undefined
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Delete point failed')
      }
      await fetchPointLibraryFromBackend()
      return true
    } catch (error) {
      console.warn('Delete point from backend failed:', error)
      return false
    }
  }

  async function postTemplateToBackend(template, shouldRefresh = true) {
    const response = await fetch(`${API_BASE}/template/upsert`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(buildAuthHeaders ? buildAuthHeaders() : {})
      },
      body: JSON.stringify(buildTemplatePayload(template))
    })
    const data = await readJsonResponse(response)
    if (!response.ok) {
      throw createApiError(data, 'Save template failed')
    }
    if (shouldRefresh) {
      await fetchTaskTemplatesFromBackend()
    }
    return true
  }

  async function saveTemplateToBackend(template) {
    try {
      await postTemplateToBackend(template, true)
      return true
    } catch (error) {
      console.warn('Save template to backend failed:', error)
      return false
    }
  }

  async function saveTemplatesBatchToBackend(templates) {
    try {
      for (const template of templates) {
        await postTemplateToBackend(template, false)
      }
      await fetchTaskTemplatesFromBackend()
      return true
    } catch (error) {
      console.warn('Save templates batch to backend failed:', error)
      return false
    }
  }

  async function deleteTemplateFromBackend(templateId) {
    try {
      const response = await fetch(`${API_BASE}/template/${encodeURIComponent(templateId)}`, {
        method: 'DELETE',
        headers: buildAuthHeaders ? buildAuthHeaders() : undefined
      })
      const data = await readJsonResponse(response)
      if (!response.ok) {
        throw createApiError(data, 'Delete template failed')
      }
      await fetchTaskTemplatesFromBackend()
      return true
    } catch (error) {
      console.warn('Delete template from backend failed:', error)
      return false
    }
  }

  async function syncLegacyCustomPointsToBackend(points) {
    if (!Array.isArray(points) || points.length === 0 || !pointsLoadedFromApi.value) {
      return false
    }

    const existingIds = new Set(customPoints.value.map(point => point.id))
    const existingSignatures = new Set(customPoints.value.map(buildPointSignature))
    const missingPoints = points.filter(point => {
      if (!point?.custom) return false
      if (existingIds.has(point.id)) return false
      return !existingSignatures.has(buildPointSignature(point))
    })

    if (missingPoints.length === 0) {
      return false
    }

    try {
      for (const point of missingPoints) {
        const response = await fetch(`${API_BASE}/point/upsert`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(buildAuthHeaders ? buildAuthHeaders() : {})
          },
          body: JSON.stringify(buildPointPayload(point))
        })
        const data = await readJsonResponse(response)
        if (!response.ok) {
          throw createApiError(data, 'Migrate points failed')
        }
      }
      await fetchPointLibraryFromBackend()
      return true
    } catch (error) {
      console.warn('Sync legacy custom points to backend failed:', error)
      return false
    }
  }

  async function syncLegacyCustomTemplatesToBackend(templates) {
    if (!Array.isArray(templates) || templates.length === 0 || !templatesLoadedFromApi.value) {
      return false
    }

    const existingIds = new Set(customTaskTemplates.value.map(template => template.id))
    const existingSignatures = new Set(customTaskTemplates.value.map(buildTemplateSignature))
    const missingTemplates = templates.filter(template => {
      if (!template?.custom) return false
      if (existingIds.has(template.id)) return false
      return !existingSignatures.has(buildTemplateSignature(template))
    })

    if (missingTemplates.length === 0) {
      return false
    }

    try {
      for (const template of missingTemplates) {
        const response = await fetch(`${API_BASE}/template/upsert`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(buildAuthHeaders ? buildAuthHeaders() : {})
          },
          body: JSON.stringify(buildTemplatePayload(template))
        })
        const data = await readJsonResponse(response)
        if (!response.ok) {
          throw createApiError(data, 'Migrate templates failed')
        }
      }
      await fetchTaskTemplatesFromBackend()
      return true
    } catch (error) {
      console.warn('Sync legacy custom templates to backend failed:', error)
      return false
    }
  }

  return {
    builtinPoints,
    builtinTemplates,
    pointsLoadedFromApi,
    templatesLoadedFromApi,
    fetchPointLibraryFromBackend,
    fetchTaskTemplatesFromBackend,
    savePointToBackend,
    deletePointFromBackend,
    saveTemplateToBackend,
    saveTemplatesBatchToBackend,
    deleteTemplateFromBackend,
    syncLegacyCustomPointsToBackend,
    syncLegacyCustomTemplatesToBackend
  }
}
