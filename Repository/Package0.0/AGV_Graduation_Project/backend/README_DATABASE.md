# 数据库接入说明（A3 阶段）

当前后端默认仍使用：

- `AGV_DATA_BACKEND=memory`

这样做的目的是先保证当前演示功能稳定，再逐步把底层持久化切到 SQLite / MySQL。

## 当前已经完成

### 1. 配置层

已具备统一配置入口：

- `backend/app/core/settings.py`
- `backend/app/core/database.py`
- `backend/app/core/lifecycle.py`

目前支持的后端模式：

- `memory`
- `sqlite`
- `mysql`

### 2. Repository 分层

当前 repository 已经按 facade 方式拆开：

- `agv_repository`
- `task_repository`
- `fault_repository`
- `map_repository`
- `point_repository`
- `template_repository`

其底层实现已经区分为：

- `backend/app/repositories/memory/`
- `backend/app/repositories/sql/`

### 3. SQL 持久化骨架

当前 SQL 侧已经具备基础 ORM 支撑：

- AGV
- Task
- TaskStage
- FaultEvent
- MapLayout
- MapBlockedCell
- PointLibrary
- TaskTemplate
- TaskTemplateStage

并且已经过本地 SQLite 冒烟验证。

## 当前默认行为

### memory 模式

默认仍推荐用于当前主开发和演示：

- 不依赖数据库服务
- 最稳定
- 最适合当前前后端联调

### sqlite 模式

适合本地验证“数据库已接入”的阶段：

- 不需要单独安装 MySQL
- 适合做单机本地持久化验证
- 适合论文阶段说明“系统已具备数据库化能力”

### mysql 模式

适合后续正式进入：

- 账号系统
- 企业端
- 多角色
- 持久化场景管理
- 模板与点位库正式落库

## 关键环境变量

文件模板：

- `backend/.env.example`

主要字段如下：

### 基础模式

- `AGV_DATA_BACKEND`
  - 可选：`memory` / `sqlite` / `mysql`

### 数据库连接

- `AGV_DATABASE_URL`

示例：

- SQLite：
  - `sqlite:///./agv_dispatch.db`
- MySQL：
  - `mysql+pymysql://root:password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4`

### 调试项

- `AGV_DATABASE_ECHO`
- `AGV_DATABASE_AUTO_CREATE`
- `AGV_DATABASE_CONNECT_TIMEOUT_SEC`
- `AGV_DATABASE_POOL_PRE_PING`

## 推荐使用方式

### 1. 当前默认演示模式

直接使用：

- `AGV_DATA_BACKEND=memory`

适合：

- 当前页面功能开发
- 自动/手动调度联调
- 多段任务、急停恢复、地图交互验证

### 2. 本地 SQLite 验证模式

适合：

- 验证 repository / service / ORM 链路是否通畅
- 证明项目已经具备数据库切换能力

建议配置：

```env
AGV_DATA_BACKEND=sqlite
AGV_DATABASE_URL=sqlite:///./agv_dispatch.db
AGV_DATABASE_AUTO_CREATE=true
AGV_DATABASE_ECHO=false
```

### 3. 后续 MySQL 接入模式

等后面进入真正数据库阶段时，再切到：

```env
AGV_DATA_BACKEND=mysql
AGV_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4
AGV_DATABASE_AUTO_CREATE=true
AGV_DATABASE_ECHO=false
```

## 本地 SQLite 启动方法

已新增脚本：

- `run_sqlite_dev.bat`

该脚本会：

1. 设置 `AGV_DATA_BACKEND=sqlite`
2. 设置本地 SQLite 数据库文件
3. 启动后端
4. 启动前端
5. 自动打开浏览器

适合快速验证：

- SQLite 模式是否能正常启动
- 地图、任务、点位、模板的 SQL 存储骨架是否已接通

## 当前阶段限制

虽然 SQL 骨架已经接入，但当前仍有这些现实限制：

1. 前端点位库与模板库还没有正式切到后端接口
2. 当前服务层仍保留一部分“直接改对象字段”的旧风格写法
3. MySQL 真实联机验证还没有在当前机器上完成
4. 登录、企业角色、地图场景多版本等还没进入正式数据库阶段

## 下一步建议

下一阶段建议按这个顺序推进：

1. 继续保持默认 `memory` 模式开发主功能
2. 用 `sqlite` 做本地数据库化验证
3. 把 point/template 前端逐步切到后端接口
4. 再做 MySQL 真机配置与联调
5. 最后再进入登录、角色、企业端页面
