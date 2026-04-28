export const ENTERPRISE_AVOIDANCE_DEMOS = [
  {
    key: 'headon',
    titleKey: 'enterprise_demo_headon_title',
    hintKey: 'enterprise_demo_headon_hint',
    mapFileName: 'enterprise_topology_headon_map_profile_12x8.json',
    taskFileName: 'enterprise_topology_headon_tasks.json',
    agvStarts: [
      { x: 1, y: 3, nodeKey: 'west_gate' },
      { x: 10, y: 3, nodeKey: 'east_gate' }
    ],
    profile: {
      name: 'Enterprise topology head-on demo 12x8 v2',
      description: 'Enterprise topology head-on scenario. Two AGVs enter one bidirectional lane from opposite ends so the lower-priority AGV should wait or reroute.',
      grid_cols: 12,
      grid_rows: 8,
      blocked_cells: [
        { x: 4, y: 2 },
        { x: 5, y: 2 },
        { x: 6, y: 2 },
        { x: 7, y: 2 },
        { x: 4, y: 4 },
        { x: 5, y: 4 },
        { x: 6, y: 4 },
        { x: 7, y: 4 }
      ],
      topology: {
        topology_version: 1,
        nodes: [
          { key: 'west_gate', x: 1, y: 3, label: 'West Gate', node_type: 'station', capacity: 1 },
          { key: 'lane_mid', x: 6, y: 3, label: 'Single Lane Mid', node_type: 'waypoint', capacity: 1 },
          { key: 'east_gate', x: 10, y: 3, label: 'East Gate', node_type: 'station', capacity: 1 }
        ],
        edges: [
          { key: 'edge_west_mid', source: 'west_gate', target: 'lane_mid', direction: 'bidirectional', lane_type: 'main', weight: 5, speed_multiplier: 0.8 },
          { key: 'edge_mid_east', source: 'lane_mid', target: 'east_gate', direction: 'bidirectional', lane_type: 'main', weight: 4, speed_multiplier: 0.8 }
        ],
        stations: [],
        parking_nodes: [],
        charge_nodes: []
      }
    },
    tasks: [
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 8,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise topology head-on demo: high-priority AGV should pass first.',
        start_x: 1,
        start_y: 3,
        end_x: 10,
        end_y: 3
      },
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 4,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise topology head-on demo: low-priority AGV should wait or reroute when the lane is occupied.',
        start_x: 10,
        start_y: 3,
        end_x: 1,
        end_y: 3
      }
    ]
  },
  {
    key: 'intersection',
    titleKey: 'enterprise_demo_intersection_title',
    hintKey: 'enterprise_demo_intersection_hint',
    mapFileName: 'enterprise_topology_intersection_map_profile_12x8.json',
    taskFileName: 'enterprise_topology_intersection_tasks.json',
    agvStarts: [
      { x: 1, y: 3, nodeKey: 'west_gate' },
      { x: 6, y: 1, nodeKey: 'north_gate' },
      { x: 10, y: 3, nodeKey: 'east_gate' }
    ],
    profile: {
      name: 'Enterprise topology intersection demo 12x8 v2',
      description: 'Enterprise topology intersection scenario. Three AGVs approach the center node so reservation and waiting labels can be observed.',
      grid_cols: 12,
      grid_rows: 8,
      blocked_cells: [
        { x: 2, y: 2 },
        { x: 3, y: 2 },
        { x: 4, y: 2 },
        { x: 8, y: 2 },
        { x: 9, y: 2 },
        { x: 2, y: 4 },
        { x: 3, y: 4 },
        { x: 4, y: 4 },
        { x: 8, y: 4 },
        { x: 9, y: 4 },
        { x: 6, y: 5 }
      ],
      topology: {
        topology_version: 1,
        nodes: [
          { key: 'west_gate', x: 1, y: 3, label: 'West Gate', node_type: 'station', capacity: 1 },
          { key: 'north_gate', x: 6, y: 1, label: 'North Gate', node_type: 'station', capacity: 1 },
          { key: 'center_cross', x: 6, y: 3, label: 'Center Cross', node_type: 'waypoint', capacity: 1 },
          { key: 'south_gate', x: 6, y: 6, label: 'South Gate', node_type: 'station', capacity: 1 },
          { key: 'east_gate', x: 10, y: 3, label: 'East Gate', node_type: 'station', capacity: 1 }
        ],
        edges: [
          { key: 'edge_west_center', source: 'west_gate', target: 'center_cross', direction: 'bidirectional', lane_type: 'main', weight: 5, speed_multiplier: 0.82 },
          { key: 'edge_center_east', source: 'center_cross', target: 'east_gate', direction: 'bidirectional', lane_type: 'main', weight: 4, speed_multiplier: 0.82 },
          { key: 'edge_north_center', source: 'north_gate', target: 'center_cross', direction: 'bidirectional', lane_type: 'main', weight: 2, speed_multiplier: 0.78 },
          { key: 'edge_center_south', source: 'center_cross', target: 'south_gate', direction: 'bidirectional', lane_type: 'main', weight: 3, speed_multiplier: 0.78 }
        ],
        stations: [],
        parking_nodes: [],
        charge_nodes: []
      }
    },
    tasks: [
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 8,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise topology intersection demo: west-to-east high-priority AGV should pass first.',
        start_x: 1,
        start_y: 3,
        end_x: 10,
        end_y: 3
      },
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 5,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise topology intersection demo: north-to-south AGV waits for the center node.',
        start_x: 6,
        start_y: 1,
        end_x: 6,
        end_y: 6
      },
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 3,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise topology intersection demo: low-priority AGV waits or reroutes when the center is reserved.',
        start_x: 10,
        start_y: 3,
        end_x: 1,
        end_y: 3
      }
    ]
  },
  {
    key: 'station_entry',
    titleKey: 'enterprise_demo_station_title',
    hintKey: 'enterprise_demo_station_hint',
    mapFileName: 'enterprise_topology_station_entry_map_profile_12x8.json',
    taskFileName: 'enterprise_topology_station_entry_tasks.json',
    agvStarts: [
      { x: 1, y: 2, nodeKey: 'parking_a' },
      { x: 10, y: 2, nodeKey: 'charge_a' },
      { x: 1, y: 4, nodeKey: 'parking_b' }
    ],
    profile: {
      name: 'Enterprise topology station entry demo 12x8 v2',
      description: 'Enterprise topology station entry scenario. Parking nodes, charge nodes, and trunk-lane merge points are used to observe station capacity and entry/exit conflict handling.',
      grid_cols: 12,
      grid_rows: 8,
      blocked_cells: [
        { x: 4, y: 2 },
        { x: 5, y: 2 },
        { x: 7, y: 2 },
        { x: 8, y: 2 },
        { x: 4, y: 5 },
        { x: 5, y: 5 },
        { x: 7, y: 5 },
        { x: 8, y: 5 }
      ],
      topology: {
        topology_version: 1,
        nodes: [
          { key: 'parking_a', x: 1, y: 2, label: 'Parking A', node_type: 'parking', capacity: 2 },
          { key: 'parking_b', x: 1, y: 4, label: 'Parking B', node_type: 'parking', capacity: 2 },
          { key: 'west_merge', x: 3, y: 3, label: 'Parking Merge', node_type: 'waypoint', capacity: 1 },
          { key: 'center_lane', x: 6, y: 3, label: 'Trunk Center', node_type: 'waypoint', capacity: 1 },
          { key: 'east_merge', x: 9, y: 3, label: 'Charge Merge', node_type: 'waypoint', capacity: 1 },
          { key: 'charge_a', x: 10, y: 2, label: 'Charge A', node_type: 'charge', capacity: 1 },
          { key: 'charge_b', x: 10, y: 4, label: 'Charge B', node_type: 'charge', capacity: 1 }
        ],
        edges: [
          { key: 'edge_parking_a_merge', source: 'parking_a', target: 'west_merge', direction: 'bidirectional', lane_type: 'service', weight: 3, speed_multiplier: 0.9 },
          { key: 'edge_parking_b_merge', source: 'parking_b', target: 'west_merge', direction: 'bidirectional', lane_type: 'service', weight: 3, speed_multiplier: 0.9 },
          { key: 'edge_west_center', source: 'west_merge', target: 'center_lane', direction: 'bidirectional', lane_type: 'main', weight: 3, speed_multiplier: 0.85 },
          { key: 'edge_center_east', source: 'center_lane', target: 'east_merge', direction: 'bidirectional', lane_type: 'main', weight: 3, speed_multiplier: 0.85 },
          { key: 'edge_east_charge_a', source: 'east_merge', target: 'charge_a', direction: 'bidirectional', lane_type: 'service', weight: 2, speed_multiplier: 0.9 },
          { key: 'edge_east_charge_b', source: 'east_merge', target: 'charge_b', direction: 'bidirectional', lane_type: 'service', weight: 2, speed_multiplier: 0.9 }
        ],
        stations: [],
        parking_nodes: ['parking_a', 'parking_b'],
        charge_nodes: ['charge_a', 'charge_b']
      }
    },
    tasks: [
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 7,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise station entry demo: parking AGV leaves station and enters the trunk lane.',
        start_x: 1,
        start_y: 2,
        end_x: 10,
        end_y: 4
      },
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 5,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise station entry demo: charge AGV leaves charge point and meets trunk traffic near the east merge.',
        start_x: 10,
        start_y: 2,
        end_x: 1,
        end_y: 4
      },
      {
        grid_cols: 12,
        grid_rows: 8,
        priority: 3,
        dispatch_mode: 'auto',
        dispatch_algorithm: 'astar',
        dispatch_reason: 'Enterprise station entry demo: low-priority parking AGV enters the trunk lane and waits for merge clearance.',
        start_x: 1,
        start_y: 4,
        end_x: 10,
        end_y: 2
      }
    ]
  }
]
