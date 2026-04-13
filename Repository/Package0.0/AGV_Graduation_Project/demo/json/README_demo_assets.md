# Demo JSON Assets

## 文件说明
- `task_auto_single_demo.json`
  - 自动派发的单阶段任务示例。
- `task_manual_single_demo.json`
  - 手动派发的单阶段任务示例。
  - 默认不预绑定 AGV，导入后应显示“待指定车辆 / 待绑定 AGV”说明。
- `task_multi_stage_demo.json`
  - 自动派发的多阶段任务示例。
- `obstacle_layout_demo.json`
  - 地图障碍布局导入示例。
- `map_profile_irregular_demo.json`
  - 异形地图 Profile 导入示例。

## 推荐用途
- 任务 JSON
  - 用于 `JSON 导入/导出` 验收。
- 障碍布局 JSON
  - 用于地图障碍快速恢复。
- 地图 Profile JSON
  - 用于异形地图 / Profile 演示。

## 当前约定
- 所有任务示例默认基于 `10 x 8` 地图。
- 自动与多阶段任务示例应能导入成功，并继续进入自动调度。
- `task_manual_single_demo.json` 当前用于验证“手动任务导入后保留在待绑定队列，并显示清楚说明”。
- 如果需要演示“已绑定手动任务自动接管”，请使用系统内手动创建流程，或单独准备绑定版示例。
- `map_profile_irregular_demo.json` 依赖 `valid_cells` 字段来表达异形轮廓。
