# Demo JSON Assets

## 文件用途
- `task_auto_single_demo.json`
  - 自动单段任务导入示例
- `task_manual_single_demo.json`
  - 手动单段任务导入示例
- `task_multi_stage_demo.json`
  - 多段任务链导入示例
- `obstacle_layout_demo.json`
  - 障碍布局导入示例
- `map_profile_irregular_demo.json`
  - 异形地图方案导入示例

## 推荐导入位置
- 任务 JSON：
  - 任务 JSON 工具 / 任务导入入口
- 障碍布局 JSON：
  - 地图障碍导入入口
- 地图方案 JSON：
  - 地图方案导入入口

## 兼容说明
- 所有坐标都基于当前仓库默认的网格系统
- 异形地图示例已经包含 `valid_cells`
- 若当前地图已存在自定义点位或任务，请先确认导入是否会覆盖当前演示草稿
