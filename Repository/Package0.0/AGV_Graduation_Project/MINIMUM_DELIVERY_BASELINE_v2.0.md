# 最低可交付版可答辩基线 v2.0

最后更新：2026-03-18

## 目标
- 将当前系统整理为“可答辩版基线”。
- 本文档记录本轮已完成的自动化回归结果，以及答辩前仍建议人工复核的项目。

## 本轮环境
- 项目版本：`v2.0.0-beta.1` 基线继续推进
- 当前阶段：模块 3 收口中
- 数据模式覆盖：
  - SQLite
  - MySQL
  - Packaged SQLite

## 自动化回归结果

### 1. 前端质量检查
- `npm run lint`
  - 结果：通过
- `npm run build`
  - 结果：通过

### 2. 后端语法 / 结构检查
- `python -m compileall backend/app backend/main.py backend/package_entry.py`
  - 结果：通过

### 3. SQLite 回归
- `run_sqlite_smoke.bat`
  - 结果：通过
  - 输出：

```text
SQLITE_SMOKE_OK point/template/map
```

### 4. MySQL 回归
- `run_mysql_check.bat`
  - 结果：通过
  - 输出关键结果：

```text
connection: success
tables: auto-create completed
MYSQL_CONFIG_OK
```

### 5. 本地类封装回归
- 验证方式：后端托管前端 `dist`
- 结果：通过
- 关键结果：

```text
ROOT_STATUS=200 ROOT_TYPE=text/html; charset=utf-8
UI_STATUS=200
PACKAGED_DEV_SMOKE_OK
```

### 6. Windows one-folder 打包
- `build_windows_package.bat`
  - 结果：通过
- 产物目录：

```text
dist/AGV_Dispatch_Package
```

### 7. 封装包可执行文件回归
- 验证方式：直接启动 `dist/AGV_Dispatch_Package/backend.exe`
- 结果：通过
- 关键结果：

```text
ROOT_STATUS=200 ROOT_TYPE=text/html; charset=utf-8
UI_STATUS=200
PACKAGED_EXE_SMOKE_OK
```

## 本轮顺手修复

### 1. `start_agv.bat` 启动修复
- 修复了封装包启动脚本中 `backend.exe` 的错误调用方式
- 现在 `start_agv.bat` 会：
  - 先启动 `backend.exe`
  - 等待后端真正 ready
  - 再打开浏览器

### 2. `run_mysql_check.bat` 配置修复
- 修复了脚本里强塞默认 `root:password` 的问题
- 现在优先读取 `backend/.env` 中真实的 MySQL 配置

## 当前可认为已达成的答辩能力
- 具备自动 / 手动 / 多段任务主线
- 具备异常处理能力：
  - 急停 / 恢复
  - 故障 / 解除
  - 送修 / 恢复
- 具备点位 / 模板 / 障碍预设持久化
- 具备 SQLite / MySQL 双数据库模式
- 具备 Windows 最低可交付封装试运行能力

## 答辩前仍建议人工终验

以下项目本轮没有全部自动化，需要答辩前至少人工跑一遍：

### 调度主链
- 自动单段任务
- 手动单段任务
- 自动多段任务
- 自动多段任务运行中再次点地图创建新任务

### 异常链路
- 急停 / 恢复
- 故障上报 / 故障解除
- 送修下线 / 恢复上线

### 数据与管理
- 点位库 CRUD
- 模板库 CRUD
- 障碍预设 CRUD
- 已完成任务批量导出 / 删除
- 异常任务筛选 / 清理

### 多语言与界面
- 中文
- 英文
- 日文
- 地图设置面板
- JSON / 实验记录 / 障碍地图设置按钮排版

## 当前结论
- **自动化可验证部分已达到“可答辩版基线”**
- 若再补一轮人工终验并记录结果，可将模块 3 标记为完整完成

## 建议下一步
1. 按 `TEST_CHECKLIST_MINIMUM_DELIVERY.md` 跑一轮人工终验
2. 将人工终验结果追加到本文件
3. 如无严重阻断问题，可准备：
   - 新一版 beta release
   - 或直接迈向模块 4（动态地图尺寸与地图方案重构）
