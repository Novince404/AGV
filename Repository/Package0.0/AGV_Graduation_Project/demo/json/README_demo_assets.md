# Demo JSON Assets

## 文件说明

- `personal_defense_map_profile_10x8.json`
  - 个人端答辩推荐地图 Profile。
  - 导入后在地图方案列表中点击“应用”，即可恢复 10x8 货架通道地图。
- `personal_defense_obstacle_layout_10x8.json`
  - 个人端答辩备用障碍物布局。
  - 只想临时恢复障碍物时使用，导入后需要点击“保存障碍”。
- `personal_defense_busy_tasks.json`
  - 个人端答辩批量任务。
  - 一次导入多条任务，默认 3 台 AGV 会先运行一部分任务，其余任务进入队列等待空闲车。
- `task_auto_single_demo.json`
  - 自动派发的单阶段任务示例。
- `task_manual_single_demo.json`
  - 手动派发的单阶段任务示例。
  - 默认不预绑定 AGV，导入后应显示“待指定车辆 / 待绑定 AGV”说明。
- `task_multi_stage_demo.json`
  - 自动派发的多阶段任务示例。
- `obstacle_layout_demo.json`
  - 通用地图障碍布局导入示例。
- `map_profile_irregular_demo.json`
  - 异形地图 Profile 导入示例。

## 推荐用法

- 导师答辩个人端演示：
  - 先导入并应用 `personal_defense_map_profile_10x8.json`。
  - 再导入 `personal_defense_busy_tasks.json`。
  - 观察多台 AGV 同时运行、任务队列接续、路径绕开货架障碍。
- 临时恢复障碍物：
  - 导入 `personal_defense_obstacle_layout_10x8.json`。
  - 点击“保存障碍”后再导入任务。
- 企业端或地图能力展示：
  - 使用 `map_profile_irregular_demo.json` 演示异形地图 Profile。

## 当前约定

- 个人端答辩资产默认基于 `10 x 8` 地图。
- 批量任务导入依赖配套地图障碍物；如果任务导入提示阶段被阻塞，请先应用配套地图 Profile。
- 常用点位用于表达业务地标，不等同于停车点、充电点、停车站或充电站。
