# 导师演示步骤 v2

## 1. 启动

1. 双击 `start_agv.bat`。
2. 等待浏览器自动打开前端页面。
3. 使用默认 SQLite 数据即可开始演示。

## 2. 个人端答辩主线

推荐优先演示个人端，因为它最直观，导师能快速看到“地图、障碍、任务、车辆、路径”的闭环。

1. 使用个人账号登录，例如 `personal_demo` / `personal123`。
2. 打开地图设置。
3. 导入 `demo/json/personal_defense_map_profile_10x8.json`。
4. 在地图方案列表中点击“应用”。
5. 回到主地图，打开 JSON 导入/导出。
6. 导入 `demo/json/personal_defense_busy_tasks.json`。
7. 观察多台 AGV 同时运行、任务排队、路径绕开障碍物。
8. 根据现场节奏打开或关闭常用点位显示，分别讲业务点位和调度运行。

详细脚本见 `demo/docs/PERSONAL_DEFENSE_DEMO_RUNBOOK.md`。

## 3. 平台管理员治理工作台

1. 使用平台管理员账号登录。
2. 默认展示治理优先工作台。
3. 重点演示：
   - 企业审批队列
   - 账号治理
   - 平台 Bug 反馈
   - 审计摘要
4. 打开账号治理，演示个人用户、企业账号、平台管理员账号的集中管理。
5. 展示封禁、解封、停用和导出 JSON / CSV 的入口。

## 4. 企业端能力建议

1. 打开企业设置。
2. 展示企业角色、组织数据隔离和地图设置。
3. 导入或切换地图 Profile。
4. 打开路网拓扑，说明企业端相比个人端增加了路网、站点、容量和回仓回充语义。
5. 如时间允许，再演示企业独立客户端启动流程。

## 5. 示例 JSON

### 个人答辩推荐

- `personal_defense_map_profile_10x8.json`
- `personal_defense_obstacle_layout_10x8.json`
- `personal_defense_busy_tasks.json`

### 通用验收示例

- `task_auto_single_demo.json`
- `task_manual_single_demo.json`
- `task_multi_stage_demo.json`
- `obstacle_layout_demo.json`
- `map_profile_irregular_demo.json`

## 6. 收尾说明

- 个人端用于展示基础调度闭环和算法可视化。
- 企业端用于展示角色隔离、治理能力、拓扑路网和独立客户端。
- 演示时不要把常用点位里的业务地标讲成充电站或停车站；充电站、停车站属于路网拓扑和 AGV 运行资源。
