# Windows 独立包与本地试用

本文说明 v3.0.0 的 Windows 本地演示、独立包构建和运行方式。它适用于
单机 SQLite 演示或受控试用，不作为工业控制或高可用部署方案。正式 MySQL、
OIDC/Keycloak 试用请使用 [Docker trial deployment](../deployment/DOCKER_TRIAL.md)。

## 运行拓扑

v3 的 API 与确定性调度器是不同的运行角色：

```text
浏览器 → API 进程 → SQLite / MySQL
                    ↑         ↓
              Scheduler 进程 → SimulationDeviceAdapter
```

- API 只处理认证、请求和查询，不推进仿真车辆。
- Scheduler 是唯一推进仿真与持有数据库租约的进程。
- `tools\windows\run_sqlite_dev.bat`、`run_packaged_dev.bat` 和打包后的
  `start_agv.bat` 都会启动这两个角色。
- 通用的 `tools\windows\run_dev.bat` 为兼容 memory 模式，将调度器嵌入 API
  进程；验证 v3 运行时请改用 SQLite 启动器。

首次启动前，启动器会先完成 Alembic 数据库升级，再启动 API，最后启动
Scheduler，避免两个进程同时修改 SQLite 结构。

## 前置条件

- Windows 10/11。
- 源码模式：Python 3.10+、Node.js `^20.19.0` 或 `>=22.12.0`，以及
  `backend\venv` 已安装运行依赖。
- 打包模式：还需在后端虚拟环境安装 PyInstaller。

## 源码本地运行

### SQLite（推荐）

在仓库根目录运行：

```bat
tools\windows\run_sqlite_dev.bat
```

脚本会依次升级 `backend\agv_dispatch.db`、启动 API、启动 Scheduler，并通过
Vite 启动前端。关闭演示时，请关闭 API、Scheduler 和前端三个窗口。

### 类独立包运行

```bat
tools\windows\run_packaged_dev.bat
```

它先构建 `frontend\dist`，然后由 API 托管前端静态资源，浏览器打开
`http://127.0.0.1:8000/`。SQLite 数据文件位于 `data\agv_dispatch.db`。

### MySQL（仅已完成备份与迁移时）

在 `backend\.env` 或当前环境中设置 `AGV_DATABASE_URL` 后，先完成迁移：

```bat
cd backend
venv\Scripts\python.exe agv.py database upgrade --backup-confirmed
cd ..
tools\windows\run_mysql_dev.bat
```

该脚本会启动 API 监督进程与独立 Scheduler。停止时关闭两个窗口。不要依赖
`AGV_DATABASE_AUTO_CREATE` 在 MySQL 试用库中自动迁移。

## 构建独立包

安装打包依赖：

```bat
backend\venv\Scripts\python.exe -m pip install -r backend\requirements-package.txt
```

`requirements-package.txt` 会读取 `requirements.lock`，因此打包使用的运行时
依赖与 CI/Docker 验证的版本保持一致；`pyinstaller` 仅作为本机打包工具安装。

构建标准包：

```bat
build_windows_package.bat
```

构建企业客户端包：

```bat
build_enterprise_windows_package.bat
```

输出目录包含根 `VERSION` 对应的版本号，例如：

```text
dist\AGV_Dispatch_Package_3.0.0-beta.2\
dist\AGV_Enterprise_Client_3.0.0-beta.2\
```

打包配置会同时带入前端资源、Alembic 迁移脚本、版本文件和本说明所需的
数据库文档；不要把本机 `.env`、真实数据库或密钥打进公开发布包。

## 使用独立包

解压后双击：

```text
start_agv.bat
```

企业客户端包使用：

```text
start_enterprise_client.bat
```

启动器先启动 API 并等待 `/health/ready`，再以同一个 `backend.exe` 的
`--scheduler` 角色启动独立调度器，最后打开浏览器。关闭时需要关闭 API 与
Scheduler 两个控制台窗口。

可在包目录打开终端运行维护命令；它们使用同一个 `data\agv_dispatch.db`：

```bat
backend.exe database check
backend.exe database backup
backend.exe database verify
backend.exe database restore C:\safe-backups\agv_dispatch.backup.db --sha256 <checksum>
```

升级、恢复和备份前先停止 API 与 Scheduler。更完整的迁移与数据核验步骤见
包内 `docs\DATABASE_MIGRATIONS.md`。

## 验证与排障

启动后可检查：

```text
http://127.0.0.1:8000/health/live
http://127.0.0.1:8000/health/ready
http://127.0.0.1:8000/version
http://127.0.0.1:8000/api/v1/system/metrics
```

当 Scheduler 持有租约时，指标中的 `agv_scheduler_leader` 应为 `1`。若 API
已经可用但车辆命令没有推进，请确认 Scheduler 控制台仍在运行、数据库路径
与 API 使用的是同一个文件，并检查其输出中的迁移或租约错误。

## 安全边界

- SQLite 独立包仅适合单机演示/试用；多人或企业试用应使用 MySQL Docker
  方案，并完成备份恢复演练。
- 试用/生产环境请通过私有 `.env` 设置精确 CORS 来源、HTTPS Cookie、恢复
  管理员和 OIDC 配置；不要提交该文件。
- v3 仅包含 `SimulationDeviceAdapter`，不连接真实 AGV、PLC、MQTT、串口或
  传感器设备。
