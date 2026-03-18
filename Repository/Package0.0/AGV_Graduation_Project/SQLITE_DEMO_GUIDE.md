# SQLite 演示说明

最后更新：2026-03-18

## 为什么演示优先用 SQLite
- 不需要额外安装和启动 MySQL 服务
- 数据可以持久化，不像纯 memory 模式那样重启即丢
- 更适合毕业设计“最低可交付版”的单机演示场景

## SQLite 演示使用方式

### 方式 1：开发态 SQLite 演示
运行：

```bat
run_sqlite_dev.bat
```

特点：
- 前端仍然是 Vite 开发模式
- 后端强制使用 SQLite
- 适合一边演示一边修小问题

### 方式 2：类封装 SQLite 演示
运行：

```bat
run_packaged_dev.bat
```

特点：
- 后端直接托管前端 `dist`
- 更接近最终打包交付效果

### 方式 3：封装包 SQLite 演示
先构建：

```bat
build_windows_package.bat
```

再运行：

```bat
dist\AGV_Dispatch_Package\start_agv.bat
```

## SQLite 数据文件位置

### 开发态
- 通常位于项目根目录下的 `data/agv_dispatch.db`

### 封装包
- 位于：

```text
dist\AGV_Dispatch_Package\data\agv_dispatch.db
```

## 适合用 SQLite 演示的功能
- 自动单段任务
- 手动单段任务
- 自动多段任务
- 急停 / 恢复
- 故障 / 解除
- 送修 / 恢复
- 点位库 CRUD
- 模板库 CRUD
- 障碍预设 CRUD
- 已完成任务批量导出 / 删除

## 演示前建议准备
1. 先跑一次：

```bat
run_sqlite_smoke.bat
```

2. 确认看到：

```text
SQLITE_SMOKE_OK point/template/map
```

3. 再使用 `run_packaged_dev.bat` 或封装包启动

## 演示时的建议说法
- 当前系统默认支持 `memory / sqlite / mysql` 三种后端模式
- 演示阶段采用 SQLite，兼顾单机部署简洁性与数据持久化能力
- 后续正式部署可平滑切换到 MySQL

## SQLite 模式下建议重点展示
1. 刷新页面后点位和模板仍然存在
2. 障碍预设刷新后仍然存在
3. 地图显示设置刷新后仍然存在
4. 一键启动后不依赖 MySQL 也能完整运行
