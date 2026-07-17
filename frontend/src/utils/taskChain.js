function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export function createTaskChainStage(seed = {}) {
  return {
    label: seed.label ?? '',
    start_x: Number(seed.start_x ?? 0),
    start_y: Number(seed.start_y ?? 0),
    end_x: Number(seed.end_x ?? 0),
    end_y: Number(seed.end_y ?? 0)
  }
}

export function buildDefaultTaskChainStages(stageCount = 2, firstStageSeed = {}) {
  const normalizedCount = Math.max(2, Math.floor(Number(stageCount) || 2))
  const firstStage = createTaskChainStage(firstStageSeed)
  const stages = [firstStage]

  while (stages.length < normalizedCount) {
    const previousStage = stages.at(-1)
    stages.push(
      createTaskChainStage({
        start_x: previousStage?.end_x ?? 0,
        start_y: previousStage?.end_y ?? 0,
        end_x: previousStage?.end_x ?? 0,
        end_y: previousStage?.end_y ?? 0
      })
    )
  }

  return stages
}

export function buildTaskJsonExamplePayload(mode) {
  if (mode === 'chain') {
    return {
      version: 2,
      tasks: [
        {
          priority: 4,
          stages: [
            { label: '入库', start_x: 1, start_y: 1, end_x: 4, end_y: 1 },
            { label: '装配', start_x: 4, start_y: 1, end_x: 4, end_y: 5 },
            { label: '出库', start_x: 4, start_y: 5, end_x: 8, end_y: 5 }
          ]
        },
        {
          priority: 2,
          stages: [
            { label: '取货', start_x: 0, start_y: 6, end_x: 3, end_y: 6 },
            { label: '补货', start_x: 3, start_y: 6, end_x: 3, end_y: 2 }
          ]
        }
      ]
    }
  }

  return {
    tasks: [
      { start_x: 1, start_y: 1, end_x: 7, end_y: 1, priority: 3 },
      { start_x: 2, start_y: 6, end_x: 8, end_y: 4, priority: 5 },
      { start_x: 0, start_y: 0, end_x: 5, end_y: 3, priority: 2 }
    ]
  }
}

export function normalizeTaskStages(task) {
  if (Array.isArray(task.stages) && task.stages.length > 0) {
    return task.stages
  }
  return [
    {
      index: 0,
      start_x: task.start_x,
      start_y: task.start_y,
      end_x: task.end_x,
      end_y: task.end_y,
      label: ''
    }
  ]
}

export function isTaskChain(task) {
  return Number(task.total_stages ?? normalizeTaskStages(task).length) > 1
}

export function overallTaskStart(task) {
  return {
    x: task.overall_start_x ?? normalizeTaskStages(task)[0]?.start_x ?? task.start_x,
    y: task.overall_start_y ?? normalizeTaskStages(task)[0]?.start_y ?? task.start_y
  }
}

export function overallTaskEnd(task) {
  const stages = normalizeTaskStages(task)
  const lastStage = stages[stages.length - 1]
  return {
    x: task.overall_end_x ?? lastStage?.end_x ?? task.end_x,
    y: task.overall_end_y ?? lastStage?.end_y ?? task.end_y
  }
}

export function currentTaskStage(task) {
  const stages = normalizeTaskStages(task)
  const index = clamp(Number(task.current_stage_index ?? 0), 0, stages.length - 1)
  return stages[index]
}
