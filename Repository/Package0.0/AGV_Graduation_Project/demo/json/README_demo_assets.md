# Demo JSON Assets

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

## 当前约定

- 个人端综合演示资产默认基于 `10 x 8` 地图。
- 动态避让演示资产默认基于 `12 x 8` 地图，建议至少保留 3 台空闲 AGV。
- 批量任务导入依赖配套地图障碍物；如果任务导入提示阶段被阻塞，请先应用配套地图 Profile。
- 常用点位用于表达业务地标，不等同于停车点、充电点、停车站或充电站。
