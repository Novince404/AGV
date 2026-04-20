# Windows 封装试运行说明

最后更新：2026-03-18

## 目标
- 为最低可交付版准备 Windows 演示包。
- 默认使用 `sqlite`，不强制依赖 MySQL。
- 支持两种运行方式：
  - 本地“类封装”运行：`tools\windows\run_packaged_dev.bat`
  - 真正打包：`build_windows_package.bat`

## 目录与脚本
- `build_frontend_dist.bat`
  - 构建前端 `frontend/agv-frontend/dist`
- `tools\windows\run_packaged_dev.bat`
  - 本地直接用后端托管 `dist`，不再依赖 Vite
- `build_windows_package.bat`
  - 使用 `PyInstaller` 构建 one-folder 包
- `start_agv.bat`
  - 封装包启动器；若当前目录没有 `backend.exe`，则自动回退到 `tools\windows\run_packaged_dev.bat`
- `backend/package_entry.py`
  - PyInstaller 入口，默认将后端切到 `sqlite + serve_frontend_dist`
- `backend/packaging/backend.spec`
  - PyInstaller 打包配置
- `backend/requirements-package.txt`
  - 打包所需依赖（含 `pyinstaller`）

## 本地类封装运行
在项目根目录执行：

```bat
tools\windows\run_packaged_dev.bat
```

效果：
- 自动构建前端 `dist`
- 后端以 `sqlite` 模式启动
- 后端直接托管前端静态资源
- 浏览器打开 `http://127.0.0.1:8000/`

## 真正打包

### 1. 安装 PyInstaller
在后端虚拟环境中执行：

```bat
backend\venv\Scripts\python.exe -m pip install -r backend\requirements-package.txt
```

### 2. 执行打包
在项目根目录执行：

```bat
build_windows_package.bat
```

### 3. 打包结果
输出目录：

```text
dist\AGV_Dispatch_Package\
```

目标产物：
- `backend.exe`
- `start_agv.bat`
- `data\agv_dispatch.db`

## 运行逻辑
- `start_agv.bat` 优先启动当前目录下的 `backend.exe`
- 若当前目录没有 `backend.exe`，则回退为本地类封装模式
- 封装模式下默认：
  - `AGV_DATA_BACKEND=sqlite`
  - `AGV_SERVE_FRONTEND_DIST=true`
  - SQLite 数据文件位于 `data/agv_dispatch.db`
- 可选环境变量：
  - `AGV_HOST`
  - `AGV_PORT`
  用于调整本地验证时的监听地址与端口

## 当前阶段说明
- 本轮属于模块 2 的首版骨架落地。
- 已完成：
  - 前端 `dist` 构建脚本
  - 后端静态资源托管
  - PyInstaller 入口与 spec
  - 启动器脚本
- 下一步建议：
  - 安装 `PyInstaller`
  - 产出第一次 one-folder 包
  - 用 SQLite 跑完整演示回归
