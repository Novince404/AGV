# 数据库接入说明（A3 过渡版）

当前后端默认仍使用内存仓储（`AGV_DATA_BACKEND=memory`），以保证现有功能稳定。

## 已完成
- 新增 `core/settings.py`：统一读取数据库与 CORS 配置。
- 新增 `core/database.py`：SQLAlchemy 引擎与会话工厂。
- 新增 `repositories/sql_models.py`：AGV / Task / TaskStage / FaultEvent 的 ORM 实体。
- 新增 `repositories/db_init.py`：建表入口 `create_all_tables()`。
- 新增 `repositories/runtime.py`：运行时后端判定（memory / mysql / sqlite）。
- `main.py` 在 SQL 后端模式下可自动尝试建表。

## 环境变量
- `AGV_DATA_BACKEND`：`memory` / `mysql` / `sqlite`（默认 `memory`）
- `AGV_DATABASE_URL`：SQLAlchemy 连接串  
  - MySQL 示例：`mysql+pymysql://root:password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4`
  - SQLite 示例：`sqlite:///./agv_dispatch.db`
- `AGV_DATABASE_ECHO`：是否打印 SQL（默认 `false`）
- `AGV_DATABASE_AUTO_CREATE`：启动时是否自动建表（默认 `true`）

## 重要说明
- 当前业务读写仍走内存仓储，SQL 模型用于 A3 结构落地与下一阶段切换准备。
- 下一阶段会把 repositories 从“内存列表”切换为“SQL 读写实现”，并保持 API 兼容。

