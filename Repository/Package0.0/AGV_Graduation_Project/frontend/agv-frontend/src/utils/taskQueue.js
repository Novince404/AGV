export function buildDefaultQueueGroupState() {
  return {
    pending: false,
    blocked: false,
    assigned: false,
    running: false,
    finished: true
  }
}

export function compareTime(a, b) {
  const aTime = a ? Date.parse(a) : 0
  const bTime = b ? Date.parse(b) : 0
  return aTime - bTime
}

export function sortTasks(list, status) {
  const copy = [...list]
  if (status === 'pending' || status === 'blocked') {
    return copy.sort((a, b) => b.priority - a.priority || a.id - b.id)
  }
  if (status === 'finished') {
    return copy.sort((a, b) => compareTime(b.finished_at, a.finished_at) || b.id - a.id)
  }
  return copy.sort((a, b) => compareTime(b.assigned_at, a.assigned_at) || b.priority - a.priority || a.id - b.id)
}
