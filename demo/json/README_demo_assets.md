# Demo JSON Assets

## 动态避让 v2 说明

- `dynamic_avoidance_split_map_profile_12x8.json` 现在是个人端纯网格 A* 演示地图，不再携带企业路网拓扑节点和边。
- `dynamic_avoidance_split_tasks.json` 用于观察网格级动态避让：系统会把其它 AGV 的当前格、运动源格和运动目标格作为临时障碍；遇到对向边段冲突时会短暂等待并触发重新规划。
- 如果需要演示企业端拓扑边、节点容量和站点调度，请使用企业路网拓扑编辑器单独配置，不建议与个人端动态避让演示混用。

## 文件说明

- `personal_defense_map_profile_10x8.json`
  - 个人端综合演示推荐地图 Profile。
  - 导入后在地图方案列表中点击“应用”，即可恢复 10x8 货架通道地图。
- `personal_defense_obstacle_layout_10x8.json`
  - 个人端综合演示备用障碍物布局。
  - 只想临时恢复障碍物时使用，导入后需要点击“保存障碍”。
- `personal_defense_busy_tasks.json`
  - 个人端综合演示批量任务。
  - 一次导入多条任务，默认 3 台 AGV 会先运行一部分任务，其余任务进入队列等待空闲车。
  - 坐标避开默认障碍和 `personal_defense_obstacle_layout_10x8.json`，即使现场还没切到配套地图，也不容易踩到“终点位于障碍格”。
- `dynamic_avoidance_map_profile_12x8.json`
  - 动态避让分流演示地图 Profile。
  - 中部横向窄通道用于制造主通道冲突，上侧绕行支路和下侧服务支路用于观察等待、绕行和恢复。
- `dynamic_avoidance_conflict_tasks.json`
  - 动态避让批量任务。
  - 配合 `dynamic_avoidance_map_profile_12x8.json` 使用，一次导入多条任务，观察高优先级主通道、低优先级跟车等待和服务支路并行。
- `dynamic_avoidance_split_map_profile_12x8.json`
  - 动态避让分流演示地图 v2，推荐优先使用。
  - 文件名和地图名都带 `split` / `v2`，用于避开旧版“窄通道演示地图”残留方案。
- `dynamic_avoidance_split_tasks.json`
  - 动态避让分流演示任务 v2，推荐优先使用。
  - 配合 `dynamic_avoidance_split_map_profile_12x8.json` 使用，降低三车挤入同一个中心瓶颈的概率。
- `enterprise_topology_headon_map_profile_12x8.json` / `enterprise_topology_headon_tasks.json`
  - 企业端拓扑单通道对向会车演示。
- `enterprise_topology_intersection_map_profile_12x8.json` / `enterprise_topology_intersection_tasks.json`
  - 企业端十字交汇三车抢占演示。
- `enterprise_topology_station_entry_map_profile_12x8.json` / `enterprise_topology_station_entry_tasks.json`
  - 企业端停车点、充电点和主干道出入站冲突演示。
- `task_auto_single_demo.json`
  - 自动派发的单阶段任务示例。
- `task_manual_single_demo.json`
  - 手动派发的单阶段任务示例。
  - 默认不预绑定 AGV，导入后应显示“待指定车辆 / 待绑定 AGV”说明，并保留在待分配队列，不应被自动派车。
- `task_multi_stage_demo.json`
  - 自动派发的多阶段任务示例。
- `obstacle_layout_demo.json`
  - 通用地图障碍布局导入示例。
- `map_profile_irregular_demo.json`
  - 异形地图 Profile 导入示例。

## 推荐用法

- 个人端综合演示：
  - 先导入并应用 `personal_defense_map_profile_10x8.json`。
  - 再导入 `personal_defense_busy_tasks.json`。
  - 观察多台 AGV 同时运行、任务队列接续、路径绕开货架障碍。
- 临时恢复障碍物：
  - 导入 `personal_defense_obstacle_layout_10x8.json`。
  - 点击“保存障碍”后再导入任务。
- 企业端或地图能力展示：
  - 使用 `map_profile_irregular_demo.json` 演示异形地图 Profile。
- 动态避让演示：
  - 先导入并应用 `dynamic_avoidance_split_map_profile_12x8.json`。
  - 再导入 `dynamic_avoidance_split_tasks.json`。
  - 观察中部主通道、上侧等待位、下侧服务支路之间的跟车等待、让行倾向和恢复继续运行。
  - 详细步骤见 `docs/demo/DYNAMIC_AVOIDANCE_DEMO_RUNBOOK.md`。
- 企业端拓扑避让演示：
  - 先在企业端导入并应用 `enterprise_topology_headon_map_profile_12x8.json`，再导入配套任务，观察单通道对向会车。
  - 再分别导入十字交汇和站点出入站演示资产，开启“显示运行冲突原因”，观察等待、让行、重规划和站点容量。

## 当前约定

- 个人端综合演示资产默认基于 `10 x 8` 地图。
- 动态避让演示资产默认基于 `12 x 8` 地图，建议至少保留 3 台空闲 AGV。
- 批量任务导入依赖配套地图障碍物；如果任务导入提示阶段被阻塞，请先应用配套地图 Profile。
- 常用点位用于表达业务地标，不等同于停车点、充电点、停车站或充电站。

## 动态避让 v3 观察提示

- 个人端动态避让现在会同时使用临时障碍、边段锁和临时让行格。
- 如果任务说明里出现 `grid_dynamic_yield`，表示低优先级或较晚车辆主动让到附近安全空格，随后会继续重新规划到目标点。
- 正常效果是“停一下、让一步、再继续”，不是平滑穿车，也不是一次跳过多格。
- `dynamic_avoidance_split_tasks.json` 更适合观察多车分流；如果要专门验证面对面让行，请在应用同一地图后手动创建两条相向任务，例如 `(2,3) -> (10,3)` 与 `(10,3) -> (2,3)`。
