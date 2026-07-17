# 代码结构清单

## 主要功能块

| 功能块 | 位置 | 负责内容 |
| --- | --- | --- |
| 应用入口 | `backend/main.py` | 创建 FastAPI 应用，挂载路由，注入数据隔离 scope，启动运行时初始化。 |
| 配置与数据库 | `backend/app/core/` | 读取 `.env`，决定内存、SQLite 或 MySQL 后端，创建数据库连接和生命周期初始化。 |
| API 路由 | `backend/app/api/` | 对外提供车辆、任务、调度、地图状态、AI、登录、反馈等 HTTP 接口。 |
| 业务服务 | `backend/app/services/` | 承接 API 请求，执行地图校验、调度规则、状态汇总、ComfyUI 调用。 |
| 路径与运动 | `backend/app/utils/` | 路径规划、AGV 移动、电量消耗、自动回仓、自动充电、地图有效区域处理。 |
| 数据模型 | `backend/app/models/` | 后端内部使用的 AGV、任务、地图、模板、AI 作业等业务对象。 |
| Repository 门面 | `backend/app/repositories/*_repository.py` | 对服务层隐藏内存/SQL 存储差异，统一提供读写函数。 |
| SQL 存储 | `backend/app/repositories/sql/` | SQLAlchemy 读写实现，负责把对象同步到数据库表。 |
| 前端主应用 | `frontend/src/App.vue` | 全局状态、地图交互、任务导入、调度触发、企业设置、AI 工作台挂载。 |
| 前端组件 | `frontend/src/components/` | 地图设置、ComfyAI 工作台、登录弹窗、企业审批、反馈等组件。 |
| 前端样式 | `frontend/src/assets/` | 地图、站点、弹窗、布局等样式。 |
| 多语言文案 | `frontend/src/locales/` | 中文、英文、日文 UI 文案。 |
| 演示素材 | `demo/json/` | 可导入的地图 Profile、障碍物布局、批量任务 JSON。 |
| 企业客户端文档 | `enterprise_client/docs/` | 企业独立客户端启动、验收和使用说明。 |

## 文件夹结构说明

### `backend/`

后端主体。`main.py` 是入口，`app/api/` 管 HTTP 接口，`app/services/` 管业务规则，`app/repositories/` 管数据持久化，`app/utils/` 管算法和地图辅助逻辑。

### `frontend/`

前端主体。`src/App.vue` 承载大部分调度演示状态和交互，组件目录拆出较复杂的对话框和工作台，`locales/` 集中管理界面文案。

### `demo/`

演示资产目录。`json/` 存地图、障碍物、任务导入样例；`docs/` 存随包演示步骤。答辩现场如果数据被改乱，可以从这里恢复演示场景。

### `docs/`

文档归档目录。`defense/` 是当前答辩复习资料；`plans/` 是阶段计划；`acceptance/` 是验收记录；`demo/` 是演示文档；`release/` 是打包发布材料。

### `tools/windows/`

低频 Windows 辅助脚本。根目录保留常用启动器，这里放开发态、SQLite、类封装、检查类脚本，降低根目录噪声。

## 一句话总览

这个系统的核心链路是：前端地图和任务操作发起请求，FastAPI 路由进入服务层，服务层调用调度和路径算法，再通过 Repository 写入数据库，最后由状态接口把车辆、任务、地图和 AI 结果同步回前端。
