# A3 接口冻结清单（基线）

生成时间：2026-03-13
基线提交：`17f9f34`（chore: baseline before A3）
适用范围：`backend/main.py` 当前已挂载路由。

## 冻结原则
- A3 阶段优先做后端分层（api/schemas/services/repositories/core）。
- 以下接口路径、核心字段名、状态语义默认不做破坏性变更。
- 如必须变更：先保留旧字段兼容，再新增字段，最后再计划迁移。
- 本文档优先约束“现有前端已依赖”的字段；未列出的字段可扩展，但不应删改已列字段的语义。

## 前端硬依赖字段（A3 必须保持兼容）
### 任务对象（`task`）
- 必需字段：`id, status, priority, start_x, start_y, end_x, end_y`
- 调度字段：`agv_id, preferred_agv_id, dispatch_mode, dispatch_algorithm, dispatch_reason, dispatch_distance`
- 路径字段：`path_to_start, path_to_end, path_length_to_start, path_length_to_end`
- 多段字段：`current_stage_index, total_stages, stages, overall_start_x, overall_start_y, overall_end_x, overall_end_y`
- 时间字段：`created_at, assigned_at, started_at, finished_at`

### 阶段对象（`task.stages[]`）
- 必需字段：`index, start_x, start_y, end_x, end_y`
- 当前前端已使用/兼容字段：`label, path_to_start, path_to_end, path_length_to_start, path_length_to_end, started_at, finished_at`

### AGV 对象（`agv`）
- 必需字段：`id, x, y, status`
- 当前前端依赖字段：`task_id, active_fault_event_id`

### 故障事件对象（`event` / `fault list item`）
- 必需字段：`id, agv_id, fault_type, severity, event_type, status, reported_at`
- 当前前端依赖字段：`message, resolved_at, reported_by, task_id`

### 地图状态
- 必需字段：`grid_cols, grid_rows, blocked_cells`
- `blocked_cells[]` 需兼容 `{ x, y }`

## 公共状态语义（冻结）
- AGV status：`idle | running | fault | emergency_stop | maintenance`
- Task status：`pending | assigned | running | finished | blocked`
- 算法标识：`simple | astar`

## 错误返回兼容约束（A3 冻结）
- 当前前端优先读取 FastAPI `HTTPException` 的 `detail.error_code`。
- A3 阶段不要改成仅返回纯字符串错误。
- 兼容格式应保持：
  - `{"detail": {"error_code": "task_not_found"}}`
  - `{"detail": {"error_code": "stage_out_of_grid", "stage_index": 1, "point_type": "start"}}`
  - `{"detail": {"error_code": "task_start_unreachable", "algorithm": "simple"}}`
- 若后续要引入 `{ code, message, detail }` 统一错误模型，必须继续兼容现有 `detail.error_code` 读取方式。

## 前端当前已本地化的关键错误码
- `task_coordinates_required`
- `stage_out_of_grid`
- `stage_blocked`
- `task_not_found`
- `task_not_schedulable`
- `task_not_running`
- `related_agv_not_found`
- `task_delete_not_allowed`
- `agv_not_found`
- `agv_not_idle`
- `no_idle_agv`
- `no_pending_tasks`
- `no_reachable_tasks`
- `task_start_unreachable`
- `task_route_unreachable`
- `unsupported_algorithm`
- `blocked_retry_requires_astar`
- `task_not_blocked`
- `task_has_no_bound_agv`
- `task_not_recoverable`
- `unsupported_recover_mode`
- `preset_not_found`

## 1) AGV 接口（`/agv`）
### GET `/agv/list`
- 功能：获取 AGV 列表
- 关键返回字段：`id, x, y, status, task_id, active_fault_event_id`

### POST `/agv/{agv_id}/emergency-stop`
- 功能：急停指定 AGV
- 请求体：`message?`, `reported_by`
- 关键返回：`message, agv, task, event`
- `task` 为空或为被阻塞的关联任务；`event` 为急停事件

### POST `/agv/{agv_id}/resume`
- 功能：恢复急停/故障后 AGV
- 关键返回：`message, agv, event`

### POST `/agv/{agv_id}/to-maintenance`
- 功能：将 AGV 置为维修态
- 关键返回：`message, agv`

### POST `/agv/{agv_id}/return-to-service`
- 功能：AGV 维修结束返回可服务态
- 关键返回：`message, agv`

## 2) 故障接口（`/fault`）
### POST `/fault/report`
- 功能：上报故障
- 请求体：`agv_id, fault_type, severity, message?, reported_by`
- 关键返回：`message, event, agv, task`

### GET `/fault/list`
- 功能：故障事件列表
- 关键返回字段：`id, agv_id, fault_type, severity, message, event_type, status, reported_at, resolved_at, reported_by, task_id`

### POST `/fault/{event_id}/resolve`
- 功能：关闭故障事件
- 关键返回：`message, event, agv`

## 3) 任务接口（`/task`）
### GET `/task/list`
- 功能：任务列表
- 关键返回字段：
  - 顶层：`id,start_x,start_y,end_x,end_y,priority,status,agv_id,...`
  - 路径：`path_to_start,path_to_end,path_length_to_start,path_length_to_end`
  - 调度：`dispatch_mode,dispatch_algorithm,dispatch_reason,dispatch_distance`
  - 阶段：`current_stage_index,total_stages,stages[]`
  - 全局起终点：`overall_start_x,overall_start_y,overall_end_x,overall_end_y`

### POST `/task/create`
- 功能：创建单段/多段任务
- 请求体（冻结字段名）：
  - 单段：`start_x,start_y,end_x,end_y,priority`
  - 多段：`stages[]`（每段 `start_x,start_y,end_x,end_y,label?`）
  - 调度相关：`dispatch_mode,preferred_agv_id,dispatch_origin_x,dispatch_origin_y,dispatch_algorithm,dispatch_reason`
- 关键返回：`message, task`

### POST `/task/finish/{task_id}`
- 功能：手动完成任务（测试/兜底）
- 关键返回：`message, task, agv`

### POST `/task/import_json`
- 功能：导入任务 JSON
- 请求体：`{ "tasks": [...] }`
- 关键返回：`message, count, task_ids`

### GET `/task/export_json`
- 功能：导出任务 JSON
- 关键返回：`version, exported_at, tasks[]`

### DELETE `/task/{task_id}`
- 功能：删除任务
- 关键返回：`message, task_id`

## 4) 调度接口（`/schedule`）
### POST `/schedule/`
- 功能：触发一次调度（兼容入口）
- 当前固定使用：`simple + 10x8`

### POST `/schedule/with_path`
- 功能：按算法分配 AGV + 生成路径 + 启动运动
- 请求体：`task_id?`, `agv_id?`, `algorithm`, `grid_cols`, `grid_rows`
- 关键返回：`message, task, agv, algorithm, path_to_start, path_to_end, path_stats, blocked_cells`
- `path_stats` 当前至少兼容：`path_length_to_start, path_length_to_end, dispatch_distance`

### POST `/schedule/compare_path`
- 功能：路径算法对比（simple vs astar）
- 请求体：单段坐标或 `stages[]`
- 关键返回：`grid_cols, grid_rows, stage_count, blocked_cells, results`
- `results.simple / results.astar` 需兼容：
  - `algorithm, reachable, total_length, failed_stage_index, stage_results[]`

### POST `/schedule/retry_blocked/{task_id}`
- 功能：blocked 任务重试
- 关键返回：
  - 立即重试：兼容 `/schedule/with_path`
  - 排队等待：`message, queued, algorithm, task, blocked_cells`

### POST `/schedule/retry_blocked_from_current/{task_id}`
- 功能：从当前 AGV 位置重试（避免回起点重走）
- 关键返回：
  - 立即重试：兼容 `/schedule/with_path`，并补充 `queued=false, resume_from_current=true`
  - 排队等待：`message, queued, algorithm, task, blocked_cells`

### POST `/schedule/recover_blocked/{task_id}`
- 功能：恢复 blocked 任务（带调度恢复策略）
- 请求体：`mode, algorithm?, grid_cols, grid_rows`
- `mode` 冻结值：`bound | reassign`
- 关键返回：
  - 立即恢复：兼容 `/schedule/with_path`，并补充 `queued=false, recover_mode`
  - 排队等待：`message, queued, recover_mode, algorithm, task, blocked_cells`

## 5) 状态与地图接口（`/status`）
### GET `/status/agv`
- 功能：AGV 状态颜色映射
- 关键返回：状态码到颜色/标签映射

### GET `/status/task`
- 功能：任务状态颜色映射
- 关键返回：状态码到颜色/标签映射

### GET `/status/map`
- 功能：当前地图障碍与尺寸
- 关键返回：`grid_cols, grid_rows, blocked_cells`

### GET `/status/map/presets`
- 功能：障碍预设列表
- 关键返回：`presets[]`
- 每个预设至少兼容：`key, name, blocked_cells`

### PUT `/status/map`
- 功能：整体更新障碍布局
- 请求体：`blocked_cells[]`, `grid_cols`, `grid_rows`
- 关键返回：`grid_cols, grid_rows, blocked_cells`

### POST `/status/map/preset/{preset_key}`
- 功能：应用预设障碍布局
- 关键返回：`grid_cols, grid_rows, blocked_cells, preset_key?`

### POST `/status/map/reset`
- 功能：重置默认障碍布局
- 关键返回：`grid_cols, grid_rows, blocked_cells`

## 6) 根接口
### GET `/`
- 功能：后端健康提示

## A3 分层迁移约束
- `api` 仅保留参数校验、调用服务、返回响应。
- 调度核心逻辑迁移到 `services/`，数据访问迁移到 `repositories/`。
- 对外 JSON 字段名保持兼容。
- 错误建议统一为：`{ code, message, detail? }`，但需兼容现有前端读取方式。
- 当前项目后续数据库目标为 MySQL；A3 阶段文档和字段命名应按 MySQL 持久化约束收口，但本冻结不强制改动现有内存实现。

## 已知后续可扩展（不在本冻结范围）
- 登录/角色/企业审核接口。
- 数据库持久化后分页、过滤、审计查询。
- 设备下位机信号接口（仅预留）。
