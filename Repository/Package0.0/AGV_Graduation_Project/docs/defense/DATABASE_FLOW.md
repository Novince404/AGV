# 数据库读写链路

## 数据后端选择

系统通过 `AGV_DATA_BACKEND` 决定数据后端：

- `memory`：内存模式，适合快速开发和临时演示。
- `sqlite`：本地文件数据库，适合单机演示和打包版本。
- `mysql`：正式开发和多用户演示时使用。

配置入口在 `backend/app/core/settings.py`，数据库连接由 `backend/app/core/database.py` 创建，启动初始化由 `backend/app/core/lifecycle.py` 完成。

## Repository 设计

服务层不直接操作数据库表，而是调用 `backend/app/repositories/*_repository.py` 这些门面函数。门面会根据当前配置选择 `memory/` 或 `sql/` 下的实现。

这样做的好处是：业务逻辑可以保持稳定，底层从内存切换到 SQLite 或 MySQL 时，不需要重写调度服务。

## SQL 表位置

SQLAlchemy 表结构集中在 `backend/app/repositories/sql_models.py`。

常见表包括：

- `agv`：车辆状态、电量、位置、任务绑定。
- `task`、`task_stage`：任务和多阶段任务。
- `map_layout`、`map_blocked_cell`、`map_valid_cell`：当前地图、障碍物、异形有效区。
- `map_layout_topology_node`、`map_layout_topology_edge`：企业路网拓扑节点和边。
- `map_profile`、`map_profile_cell`、`map_profile_valid_cell`：可复用地图方案。
- `auth_user`、`auth_session`：用户和登录会话。
- `enterprise_application`、`enterprise_request`：企业入驻和企业治理。
- `platform_bug_feedback`：平台反馈。
- `comfy_render_job`、`comfy_workflow_template`：ComfyUI 渲染任务和工作流模板。
- `operation_audit`：受保护操作审计记录。

## 写入数据库的例子

### 保存障碍物

前端地图设置提交障碍格后，请求进入 `status_api.py`，再到 `status_service.py`。服务层校验坐标、地图尺寸和有效区域后，调用地图 Repository。SQL 模式下最终由 `repositories/sql/map_store.py` 写入地图布局和障碍格表。

### 创建或调度任务

前端创建任务后，请求进入任务或调度 API。服务层创建任务对象，调度服务绑定 AGV、生成路径、更新状态，最终通过任务 Repository 和 AGV Repository 写入任务表、阶段表和车辆表。

### 保存 AI 渲染任务

前端提交 ComfyUI 渲染请求后，后端先创建 `ComfyRenderJob`。调用 ComfyUI 成功后保存 `prompt_id` 和状态，之后轮询历史记录时继续更新任务状态和图片 URL。

## 读取数据库的例子

### 地图状态

前端刷新状态时，后端读取当前地图布局、障碍物、有效区和拓扑，再返回给前端渲染。

### 车辆和任务

状态接口会读取 AGV 列表、任务队列、路径进度、阻塞状态、电量和调度提示，前端据此更新地图和任务卡片。

### AI 作业

AI 工作台刷新时读取最近渲染任务列表。每次查看详情时，后端会根据 `prompt_id` 向 ComfyUI 查询历史结果，并同步更新数据库中的作业状态。

## 答辩口径

数据库部分可以强调“分层”：配置层决定用哪种数据库，Repository 层屏蔽存储差异，服务层负责业务规则，API 层负责对外接口。这让系统既能快速演示，也能迁移到更正式的数据库环境。
