# A3 接口冻结清单（基线）

生成时间：2026-03-13
基线提交：`17f9f34`（chore: baseline before A3）
适用范围：`backend/main.py` 当前已挂载路由。

## 冻结原则
- A3 阶段优先做后端分层（api/schemas/services/repositories/core）。
- 以下接口路径、核心字段名、状态语义默认不做破坏性变更。
- 如必须变更：先保留旧字段兼容，再新增字段，最后再计划迁移。

## 公共状态语义（冻结）
- AGV status：`idle | running | fault | emergency_stop | maintenance`
- Task status：`pending | assigned | running | finished | blocked`
- 算法标识：`simple | astar`

## 1) AGV 接口（`/agv`）
### GET `/agv/list`
- 功能：获取 AGV 列表
- 关键返回字段：`id, x, y, status, task_id, active_fault_event_id`

### POST `/agv/{agv_id}/emergency-stop`
- 功能：急停指定 AGV
- 请求体：`message?`, `reported_by`
- 关键返回：AGV 新状态、关联任务阻塞信息（若有）

### POST `/agv/{agv_id}/resume`
- 功能：恢复急停/故障后 AGV
- 关键返回：AGV 当前状态与位置、任务恢复结果（若有）

### POST `/agv/{agv_id}/to-maintenance`
- 功能：将 AGV 置为维修态

### POST `/agv/{agv_id}/return-to-service`
- 功能：AGV 维修结束返回可服务态

## 2) 故障接口（`/fault`）
### POST `/fault/report`
- 功能：上报故障
- 请求体：`agv_id, fault_type, severity, message?, reported_by`
- 关键返回：`event_id`、故障状态

### GET `/fault/list`
- 功能：故障事件列表

### POST `/fault/{event_id}/resolve`
- 功能：关闭故障事件

## 3) 任务接口（`/task`）
### GET `/task/list`
- 功能：任务列表
- 关键返回字段：
  - 顶层：`id,start_x,start_y,end_x,end_y,priority,status,agv_id,...`
  - 路径：`path_to_start,path_to_end,path_length_to_start,path_length_to_end`
  - 调度：`dispatch_mode,dispatch_algorithm,dispatch_reason,dispatch_distance`
  - 阶段：`current_stage_index,total_stages,stages[]`

### POST `/task/create`
- 功能：创建单段/多段任务
- 请求体（冻结字段名）：
  - 单段：`start_x,start_y,end_x,end_y,priority`
  - 多段：`stages[]`（每段 `start_x,start_y,end_x,end_y,label?`）
  - 调度相关：`dispatch_mode,preferred_agv_id,dispatch_origin_x,dispatch_origin_y,dispatch_algorithm,dispatch_reason`

### POST `/task/finish/{task_id}`
- 功能：手动完成任务（测试/兜底）

### POST `/task/import_json`
- 功能：导入任务 JSON

### GET `/task/export_json`
- 功能：导出任务 JSON

### DELETE `/task/{task_id}`
- 功能：删除任务

## 4) 调度接口（`/schedule`）
### POST `/schedule/`
- 功能：触发一次调度（兼容入口）

### POST `/schedule/with_path`
- 功能：按算法分配 AGV + 生成路径 + 启动运动
- 请求体：`task_id?`, `agv_id?`, `algorithm`, `grid_cols`, `grid_rows`

### POST `/schedule/compare_path`
- 功能：路径算法对比（simple vs astar）
- 请求体：单段坐标或 `stages[]`

### POST `/schedule/retry_blocked/{task_id}`
- 功能：blocked 任务重试

### POST `/schedule/retry_blocked_from_current/{task_id}`
- 功能：从当前 AGV 位置重试（避免回起点重走）

### POST `/schedule/recover_blocked/{task_id}`
- 功能：恢复 blocked 任务（带调度恢复策略）

## 5) 状态与地图接口（`/status`）
### GET `/status/agv`
- 功能：AGV 状态颜色映射

### GET `/status/task`
- 功能：任务状态颜色映射

### GET `/status/map`
- 功能：当前地图障碍与尺寸

### GET `/status/map/presets`
- 功能：障碍预设列表

### PUT `/status/map`
- 功能：整体更新障碍布局
- 请求体：`blocked_cells[]`, `grid_cols`, `grid_rows`

### POST `/status/map/preset/{preset_key}`
- 功能：应用预设障碍布局

### POST `/status/map/reset`
- 功能：重置默认障碍布局

## 6) 根接口
### GET `/`
- 功能：后端健康提示

## A3 分层迁移约束
- `api` 仅保留参数校验、调用服务、返回响应。
- 调度核心逻辑迁移到 `services/`，数据访问迁移到 `repositories/`。
- 对外 JSON 字段名保持兼容。
- 错误建议统一为：`{ code, message, detail? }`，但需兼容现有前端读取方式。

## 已知后续可扩展（不在本冻结范围）
- 登录/角色/企业审核接口。
- 数据库持久化后分页、过滤、审计查询。
- 设备下位机信号接口（仅预留）。
