export function isValidGridCoordinate(value, max) {
  return Number.isInteger(value) && value >= 0 && value < max
}

export function normalizeTemplateStages(template, options) {
  const { createTaskChainStage, gridCols, gridRows } = options
  const rawStages = Array.isArray(template?.stages) && template.stages.length > 0
    ? template.stages
    : [
        {
          label: '',
          start_x: template?.start_x,
          start_y: template?.start_y,
          end_x: template?.end_x,
          end_y: template?.end_y
        }
      ]

  return rawStages
    .map(stage => ({
      ...createTaskChainStage(stage),
      label: String(stage?.label ?? '').trim()
    }))
    .filter(
      stage =>
        isValidGridCoordinate(stage.start_x, gridCols) &&
        isValidGridCoordinate(stage.start_y, gridRows) &&
        isValidGridCoordinate(stage.end_x, gridCols) &&
        isValidGridCoordinate(stage.end_y, gridRows)
    )
}

export function buildTemplateFromStages(params, options) {
  const {
    id = `task_template_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    name,
    priority,
    stages,
    custom = true
  } = params
  const { normalizeStages, clampPriority } = options
  const normalizedStages = normalizeStages({ stages })
  if (!name || normalizedStages.length === 0) return null

  const firstStage = normalizedStages[0]
  const lastStage = normalizedStages[normalizedStages.length - 1]
  return {
    id,
    customName: String(name).trim(),
    start_x: firstStage.start_x,
    start_y: firstStage.start_y,
    end_x: lastStage.end_x,
    end_y: lastStage.end_y,
    stages: normalizedStages,
    priority: clampPriority(Number(priority)),
    custom
  }
}

export function buildTaskTemplateSignature(template, options) {
  const stages = options.normalizeStages(template)
  return [
    String(template.customName ?? template.nameKey ?? '').trim().toLowerCase(),
    template.priority,
    ...stages.flatMap(stage => [stage.label, stage.start_x, stage.start_y, stage.end_x, stage.end_y])
  ].join('|')
}

export function normalizeImportedTaskTemplate(template, options) {
  const { normalizeStages, buildTemplate } = options
  const name = String(template?.name ?? template?.customName ?? '').trim()
  const priority = Number(template?.priority)
  const stages = normalizeStages(template)

  if (!name || stages.length === 0 || !Number.isInteger(priority)) {
    return null
  }

  return buildTemplate({
    name,
    priority,
    stages,
    custom: true
  })
}

export function buildTemplateExportPayload(templates, options) {
  const { normalizeStages } = options
  return {
    version: 2,
    templates: templates.map(template => {
      const stages = normalizeStages(template)
      const firstStage = stages[0]
      const lastStage = stages[stages.length - 1]
      return {
        name: template.customName,
        start_x: firstStage.start_x,
        start_y: firstStage.start_y,
        end_x: lastStage.end_x,
        end_y: lastStage.end_y,
        stages: stages.map(stage => ({
          label: stage.label || undefined,
          start_x: stage.start_x,
          start_y: stage.start_y,
          end_x: stage.end_x,
          end_y: stage.end_y
        })),
        priority: template.priority
      }
    })
  }
}

export function formatTemplateJsonSummary(primaryLabel, primaryCount, skippedCount = 0, options = {}) {
  const separator = options.separator ?? '，'
  const skippedLabel = options.skippedLabel ?? '跳过'
  const parts = [`${primaryLabel}: ${primaryCount}`]
  if (skippedCount > 0) {
    parts.push(`${skippedLabel}: ${skippedCount}`)
  }
  return parts.join(separator)
}
