# 最低可交付版一键启动说明

最后更新：2026-03-18

## 目标
- 让毕业设计演示时尽量不依赖开发环境临场操作。
- 提供“开发模式”“SQLite 演示模式”“封装模式”三种常用启动方式。

## 启动方式总览

### 1. 日常开发模式
适用场景：
- 平时继续开发功能
- 需要前端热更新
- 需要分别观察前后端日志

启动脚本：

```bat
tools\windows\run_dev.bat
```

特点：
- 前端使用 Vite
- 后端读取 `backend/.env`
- 浏览器自动打开 `http://localhost:5173/`

### 2. SQLite 演示模式
适用场景：
- 本地演示
- 不想依赖 MySQL
- 希望数据可以落到 SQLite 文件里

启动脚本：

```bat
tools\windows\run_sqlite_dev.bat
```

特点：
- 后端强制使用 SQLite
- 前端仍使用 Vite
- 浏览器自动打开 `http://localhost:5173/`

### 3. 本地类封装演示模式
适用场景：
- 想模拟“封装包运行效果”
- 不想依赖 Vite 开发服务器
- 想验证后端直接托管前端 `dist`

启动脚本：

```bat
tools\windows\run_packaged_dev.bat
```

特点：
- 自动构建前端 `dist`
- 后端使用 SQLite
- 后端直接托管前端静态资源
- 浏览器打开 `http://127.0.0.1:8000/`

### 4. 封装包启动方式
适用场景：
- 演示交付
- 不依赖源码目录继续运行

启动脚本：

```bat
dist\AGV_Dispatch_Package\start_agv.bat
```

特点：
- 优先启动同目录下的 `backend.exe`
- 默认使用 SQLite
- 自动打开浏览器

## 推荐使用顺序

### 开发阶段
1. `tools\windows\run_dev.bat`
2. 有数据库验证需求时切 `tools\windows\run_sqlite_dev.bat` 或 `run_mysql_dev.bat`

### 演示彩排阶段
1. `tools\windows\run_packaged_dev.bat`
2. 验证无 Vite 环境下是否可运行

### 最终演示 / 交付阶段
1. `build_windows_package.bat`
2. 使用 `dist\AGV_Dispatch_Package\start_agv.bat`

## 启动前最少确认
- 已安装 Node.js，且前端依赖已装好
- `backend/venv` 已可用
- 若使用 MySQL：
  - `backend/.env` 已配置正确
  - `tools\windows\run_mysql_check.bat` 可通过

## 启动失败时先看哪里
- 前端启动失败：
  - 看前端窗口是否报 `vite` / `npm` 错误
- 后端启动失败：
  - 看后端窗口是否报 `uvicorn` / 数据库连接错误
- 封装模式失败：
  - 优先看 `docs/release/PACKAGING_WINDOWS.md`
  - 再看 `docs/demo/TROUBLESHOOTING_MINIMUM_DELIVERY.md`
