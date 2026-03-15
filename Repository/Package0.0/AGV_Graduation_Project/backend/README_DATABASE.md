# 数据库接入说明（A3 过渡版）

当前后端默认仍使用内存仓储（`AGV_DATA_BACKEND=memory`），以保证现有演示功能稳定。

## 已完成
- 新增 `app/core/settings.py`
  - 统一读取数据库与 CORS 配置
- 新增 `app/core/database.py`
  - 统一管理 SQLAlchemy engine / session
  - 增加数据库连通性检查
- 新增 `app/core/lifecycle.py`
  - 统一处理启动期数据库初始化
- 新增 `app/repositories/sql_models.py`
  - 提供 AGV / Task / TaskStage / FaultEvent 的 ORM 实体
- 新增 `app/repositories/db_init.py`
  - 提供建表入口 `create_all_tables()`
- 新增 `backend/.env.example`
  - 作为 MySQL / SQLite 环境变量模板

## 当前状态
- 业务主链仍以 memory repository 为默认实现
- repository / service / utils 已开始收口，后续可以更平滑地切到 SQL 实现
- 已新增 `repositories/sql/*_store.py` 适配层
  - 当前阶段仍代理到 memory store
  - 目的是先把“调用入口”稳定下来，再替换底层实现
- `main.py` 启动时会根据配置决定：
  - 继续走 memory backend
  - 或检查 SQL backend 是否可连通
  - 若允许自动建表，则执行建表

## 关键环境变量
- `AGV_DATA_BACKEND`
  - `memory` / `mysql` / `sqlite`
  - 默认：`memory`
- `AGV_DATABASE_URL`
  - MySQL 示例：
    - `mysql+pymysql://root:password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4`
  - SQLite 示例：
    - `sqlite:///./agv_dispatch.db`
- `AGV_DATABASE_ECHO`
  - 是否输出 SQL 日志
  - 默认：`false`
- `AGV_DATABASE_AUTO_CREATE`
  - 启动时是否自动建表
  - 默认：`true`
- `AGV_DATABASE_CONNECT_TIMEOUT_SEC`
  - SQL 连接超时时间（秒）
  - 默认：`5`
- `AGV_DATABASE_POOL_PRE_PING`
  - 是否在连接池取连接前做预检查
  - 默认：`true`

## 使用建议
### 1. 保持当前演示模式
- 使用：
  - `AGV_DATA_BACKEND=memory`
- 适合：
  - 论文演示
  - 前后端功能验证
  - 不希望数据库问题影响当前开发

### 2. 进入 MySQL 准备阶段
- 复制 `backend/.env.example`
- 设置：
  - `AGV_DATA_BACKEND=mysql`
  - `AGV_DATABASE_URL=...`
- 首次建议保留：
  - `AGV_DATABASE_AUTO_CREATE=true`

## 下一步计划
- 把 memory repository 和 SQL repository 做成统一接口
- 让 `services` 不再关心底层是内存还是 MySQL
- 将 `repositories/sql/*_store.py` 从临时代理替换为真实 ORM 读写实现
- 在不破坏现有接口字段的前提下，逐步接入持久化
