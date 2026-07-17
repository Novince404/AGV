import { ENTERPRISE_AVOIDANCE_DEMOS } from '../src/config/enterpriseAvoidanceDemos.js'

const SPECIAL_NODE_TYPES = new Set(['station', 'parking', 'charge'])
const ALL_NODE_TYPES = new Set(['waypoint', ...SPECIAL_NODE_TYPES])

function fail(message) {
  throw new Error(message)
}

function expect(condition, message) {
  if (!condition) fail(message)
}

function asInt(value, label) {
  const parsed = Number(value)
  expect(Number.isInteger(parsed), `${label} must be an integer, got ${value}`)
  return parsed
}

function cellKey(x, y) {
  return `${x},${y}`
}

function assertCellInsideGrid(x, y, cols, rows, label) {
  expect(x >= 0 && x < cols, `${label} x=${x} is outside grid cols=${cols}`)
  expect(y >= 0 && y < rows, `${label} y=${y} is outside grid rows=${rows}`)
}

function assertNotBlocked(x, y, blockedCells, label) {
  expect(!blockedCells.has(cellKey(x, y)), `${label} (${x}, ${y}) is blocked`)
}

function validateDemo(demo) {
  expect(demo && typeof demo === 'object', 'demo must be an object')
  expect(typeof demo.key === 'string' && demo.key.trim(), 'demo key is required')
  expect(typeof demo.titleKey === 'string' && demo.titleKey.trim(), `${demo.key} titleKey is required`)
  expect(typeof demo.hintKey === 'string' && demo.hintKey.trim(), `${demo.key} hintKey is required`)
  expect(String(demo.mapFileName || '').endsWith('.json'), `${demo.key} mapFileName must be a json file`)
  expect(String(demo.taskFileName || '').endsWith('.json'), `${demo.key} taskFileName must be a json file`)

  const profile = demo.profile || {}
  expect(typeof profile.name === 'string' && profile.name.trim(), `${demo.key} profile.name is required`)
  expect(profile.name.includes('v2'), `${demo.key} profile.name should include v2 to avoid reusing stale saved profiles`)

  const cols = asInt(profile.grid_cols, `${demo.key} grid_cols`)
  const rows = asInt(profile.grid_rows, `${demo.key} grid_rows`)
  expect(cols > 0 && rows > 0, `${demo.key} grid size must be positive`)

  const blockedCells = new Set()
  for (const blocked of profile.blocked_cells || []) {
    const x = asInt(blocked.x, `${demo.key} blocked cell x`)
    const y = asInt(blocked.y, `${demo.key} blocked cell y`)
    assertCellInsideGrid(x, y, cols, rows, `${demo.key} blocked cell`)
    blockedCells.add(cellKey(x, y))
  }

  const topology = profile.topology || {}
  expect(Array.isArray(topology.nodes) && topology.nodes.length > 0, `${demo.key} topology.nodes is required`)
  expect(Array.isArray(topology.edges) && topology.edges.length > 0, `${demo.key} topology.edges is required`)

  const nodeByKey = new Map()
  for (const node of topology.nodes) {
    const key = String(node.key || '').trim()
    expect(key, `${demo.key} topology node key is required`)
    expect(!nodeByKey.has(key), `${demo.key} duplicate topology node key ${key}`)
    const nodeType = String(node.node_type || 'waypoint').trim()
    expect(ALL_NODE_TYPES.has(nodeType), `${demo.key} node ${key} has invalid node_type ${nodeType}`)
    const x = asInt(node.x, `${demo.key} node ${key} x`)
    const y = asInt(node.y, `${demo.key} node ${key} y`)
    assertCellInsideGrid(x, y, cols, rows, `${demo.key} node ${key}`)
    assertNotBlocked(x, y, blockedCells, `${demo.key} node ${key}`)
    nodeByKey.set(key, { ...node, x, y, node_type: nodeType })
  }

  const edgeKeys = new Set()
  for (const edge of topology.edges) {
    const key = String(edge.key || '').trim()
    expect(key, `${demo.key} topology edge key is required`)
    expect(!edgeKeys.has(key), `${demo.key} duplicate topology edge key ${key}`)
    edgeKeys.add(key)
    expect(nodeByKey.has(String(edge.source || '').trim()), `${demo.key} edge ${key} source does not exist`)
    expect(nodeByKey.has(String(edge.target || '').trim()), `${demo.key} edge ${key} target does not exist`)
  }

  expect(Array.isArray(demo.agvStarts) && demo.agvStarts.length > 0, `${demo.key} agvStarts is required`)
  const startCells = new Set()
  for (const start of demo.agvStarts) {
    const x = asInt(start.x, `${demo.key} agv start x`)
    const y = asInt(start.y, `${demo.key} agv start y`)
    const nodeKey = String(start.nodeKey || '').trim()
    assertCellInsideGrid(x, y, cols, rows, `${demo.key} AGV start`)
    assertNotBlocked(x, y, blockedCells, `${demo.key} AGV start`)
    expect(nodeKey, `${demo.key} AGV start (${x}, ${y}) must declare nodeKey`)
    const node = nodeByKey.get(nodeKey)
    expect(node, `${demo.key} AGV start (${x}, ${y}) nodeKey=${nodeKey} does not exist`)
    expect(SPECIAL_NODE_TYPES.has(node.node_type), `${demo.key} AGV start node ${nodeKey} must be station, parking, or charge`)
    expect(node.x === x && node.y === y, `${demo.key} AGV start (${x}, ${y}) does not match node ${nodeKey} (${node.x}, ${node.y})`)
    startCells.add(cellKey(x, y))
  }

  expect(Array.isArray(demo.tasks) && demo.tasks.length > 0, `${demo.key} tasks is required`)
  const taskStartCells = new Set()
  for (const [index, task] of demo.tasks.entries()) {
    const prefix = `${demo.key} task ${index + 1}`
    const startX = asInt(task.start_x, `${prefix} start_x`)
    const startY = asInt(task.start_y, `${prefix} start_y`)
    const endX = asInt(task.end_x, `${prefix} end_x`)
    const endY = asInt(task.end_y, `${prefix} end_y`)
    expect(asInt(task.grid_cols, `${prefix} grid_cols`) === cols, `${prefix} grid_cols does not match profile`)
    expect(asInt(task.grid_rows, `${prefix} grid_rows`) === rows, `${prefix} grid_rows does not match profile`)
    assertCellInsideGrid(startX, startY, cols, rows, `${prefix} start`)
    assertCellInsideGrid(endX, endY, cols, rows, `${prefix} end`)
    assertNotBlocked(startX, startY, blockedCells, `${prefix} start`)
    assertNotBlocked(endX, endY, blockedCells, `${prefix} end`)
    expect(String(task.dispatch_mode || '') === 'auto', `${prefix} dispatch_mode should be auto`)
    expect(String(task.dispatch_algorithm || '') === 'astar', `${prefix} dispatch_algorithm should be astar`)
    taskStartCells.add(cellKey(startX, startY))
  }

  for (const startCell of startCells) {
    expect(taskStartCells.has(startCell), `${demo.key} AGV start ${startCell} is not used by any task start`)
  }
}

function main() {
  expect(Array.isArray(ENTERPRISE_AVOIDANCE_DEMOS), 'ENTERPRISE_AVOIDANCE_DEMOS must be an array')
  expect(ENTERPRISE_AVOIDANCE_DEMOS.length === 3, 'expected exactly 3 enterprise avoidance demos')

  const keys = new Set()
  const profileNames = new Set()
  for (const demo of ENTERPRISE_AVOIDANCE_DEMOS) {
    validateDemo(demo)
    expect(!keys.has(demo.key), `duplicate demo key ${demo.key}`)
    keys.add(demo.key)
    expect(!profileNames.has(demo.profile.name), `duplicate profile name ${demo.profile.name}`)
    profileNames.add(demo.profile.name)
  }

  console.log(`ENTERPRISE_AVOIDANCE_DEMO_SMOKE_OK demos=${ENTERPRISE_AVOIDANCE_DEMOS.length}`)
}

main()
