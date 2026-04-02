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
  - `JSON 导入/导出` 面板
- 障碍布局 JSON：
  - 地图障碍导入入口
- 地图方案 JSON：
  - 地图方案 / Profile 导入入口

## 使用提醒
- 三个任务示例默认面向标准 `10 x 8` 演示仓库。
- 如果你当前切换到了别的地图尺寸、异形有效区或自定义障碍布局，任务示例可能因为坐标落在无效格或障碍格上而导入失败。
- `map_profile_irregular_demo.json` 已包含 `valid_cells`，适合先演示异形地图，再配合对应任务测试。
