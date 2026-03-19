# 毕设后续实施计划 v2.0

最后更新：2026-03-18

## 总览
- 计划目标：在现有 A3 基线之上，先完成“最低可交付系统”，再继续推进完整产品路线。
- 落地策略：两段式推进。
  - 前半段：地图设置 MVP、数据库稳定、Windows 封装试运行、交付收口。
  - 后半段：动态地图尺寸、登录与角色、企业端与更完整的产品化能力。
- 当前已有基线：
  - A3 接口冻结
  - SQLite / MySQL 接入
  - 点位 / 模板 / 障碍预设持久化
  - 任务队列管理
  - Windows 启动脚本

## 当前模块状态

| 模块 | 名称 | 状态 | 说明 |
| --- | --- | --- | --- |
| 模块 0 | 基线固化 | 已完成（首版） | 当前 UI/文案优化已纳入新基线；本计划文档与 `CHANGELOG.md` 已同步落地。 |
| 模块 1 | 地图设置 MVP | 已完成（首版） | 已补 `/status/ui-settings`、前端地图显示设置后端持久化、地图信息区展示。 |
| 模块 2 | 最低可交付版封装试运行 | 已完成（首版试运行） | 已完成前端 `dist` 构建、后端静态托管、PyInstaller one-folder 打包与封装包烟雾测试。 |
| 模块 3 | 最低可交付系统收口 | 进行中（自动化基线与人工终验资产已完成） | 已补文档资产、自动化回归与人工终验执行/记录模板；下一步是实际执行人工终验。 |
| 模块 4 | 动态地图尺寸与地图方案重构 | 进行中（profile 元数据与尺寸预检已完成） | 已补地图 profile 元数据、当前方案、尺寸编辑前置条件展示，以及目标尺寸变更的只读预检面板；真正尺寸保存仍放在后续重构阶段。 |
| 模块 5 | 登录、角色与产品化主线 | 未开始 | 属于完整产品路线。 |
| 模块 6 | 企业端与完整产品路线 | 未开始 | 在角色体系稳定后推进。 |

## 模块 0：基线固化

### 目标
- 提交当前未提交的前端改动，形成“地图与任务管理优化”基线。
- 更新 `CHANGELOG.md`，把数据库接入、障碍预设、任务管理、当前 UI 优化统一收口到一个稳定节点。
- 计划文档落地到项目根目录，后续每完成一个模块同步更新文档状态。

### 本轮落地结果
- 已新增本计划文件：`PROJECT_IMPLEMENTATION_PLAN_v2.0.md`
- 已新增配套文档：`PROJECT_IMPLEMENTATION_PLAN_v2.0.docx`
- 已在 `CHANGELOG.md` 中加入 `Unreleased` 记录，用于收口模块 0 / 1 的阶段性成果

## 模块 1：地图设置 MVP

### 目标
- 做出“毕设可展示”的地图设置，而不是一上来做高风险自由地图编辑器。

### 设置面板范围
- 地图显示设置：
  - 小地图
  - 图标显示
  - 路径箭头
  - 图例显示
  - 图例布局
  - 图例透明度
  - 算法对比显示方式
- 地图布局设置：
  - 应用预设
  - 保存为预设
  - 删除预设
  - 保存障碍
  - 导入 / 导出布局
  - 恢复默认布局
- 地图信息区：
  - 当前地图尺寸
  - 当前预设名
  - 障碍格数量
  - 当前后端模式（memory / sqlite / mysql）

### 新增后端接口
- `GET /status/ui-settings`
- `PUT /status/ui-settings`

### `ui-settings` 持久化范围
- `showMinimap`
- `showMarkerIcons`
- `showPathArrows`
- `showStatusLegend`
- `statusLegendLayout`
- `statusLegendOpacity`
- `compareDisplayMode`
- 侧栏 section 展开状态

### 持久化策略
- 后端优先，localStorage 保留兜底。
- 在未登录阶段，设置按“单机全局配置”处理，不做用户隔离。

### 本模块不做
- 任意地图尺寸编辑
- 拖拽式可视化地图编辑器

### 完成标准
- 刷新页面后地图显示设置仍保留。
- SQLite / MySQL 模式下设置也能保留。
- 现有障碍预设、导入导出、保存删除功能不回退。

### 本轮落地结果
- 后端已落地 `ui-settings` 仓储与 API
- 前端已通过 `useUiSettingsBackend.js` 接入后端持久化
- 地图设置面板已新增地图信息区
- 现有地图布局相关功能已接入当前网格尺寸与预设信息显示

## 模块 2：最低可交付版封装试运行

### 目标
- 做出一个 Windows 可运行的“Web 展示包 + EXE/启动器”。

### 封装方案
- 前端执行生产构建 `dist`
- 后端在“封装模式”下直接托管 `dist` 静态资源
- 后端使用 `PyInstaller` 打成 Windows one-folder 包
- 默认数据库模式为 `sqlite`
- 启动器双击后自动启动后端并打开浏览器

### 产物目标
- `AGV_Dispatch_Package/`
- `backend.exe`
- `data/agv_dispatch.db`
- `frontend/dist/*`
- `start_agv.bat`

### 完成标准
- 新机器或干净环境下，只靠封装包即可启动演示。
- 不需要先手动跑 Vite、Uvicorn、MySQL。
- 自动 / 手动 / 多段任务、点位、模板、障碍预设均可操作。

### 本轮落地结果
- 已新增 `build_frontend_dist.bat`
- 已新增 `run_packaged_dev.bat`
- 已新增 `build_windows_package.bat`
- 已新增 `start_agv.bat`
- 已新增 `backend/package_entry.py`
- 已新增 `backend/packaging/backend.spec`
- 已新增 `backend/requirements-package.txt`
- 已新增 `PACKAGING_WINDOWS.md`
- 后端已支持在 `AGV_SERVE_FRONTEND_DIST=true` 时直接托管前端 `dist`
- 前端 API 地址已调整为兼容“Vite 开发模式”和“后端同源托管模式”
- 已成功构建 `dist/AGV_Dispatch_Package/`
- 已完成封装包 `backend.exe` 烟雾测试：
  - 根路径返回前端 HTML
  - `/status/ui-settings` 接口可正常访问

## 模块 3：最低可交付系统收口

### 目标
- 把“能开发”变成“能交付、能演示、能答辩”。

### 需要补齐
- 一键启动说明
- SQLite 演示说明
- 演示脚本与测试清单
- 发布说明与版本策略
- 常见故障排查页

### 固定回归范围
- 自动单段
- 手动单段
- 自动多段
- 急停 / 恢复
- 故障 / 解除
- 送修 / 恢复
- 点位库 CRUD
- 模板库 CRUD
- 障碍预设 CRUD
- 已完成任务批量导出 / 删除

### 本轮落地结果
- 已新增 `QUICKSTART_MINIMUM_DELIVERY.md`
- 已新增 `SQLITE_DEMO_GUIDE.md`
- 已新增 `DEMO_SCRIPT_MINIMUM_DELIVERY.md`
- 已新增 `TEST_CHECKLIST_MINIMUM_DELIVERY.md`
- 已新增 `TROUBLESHOOTING_MINIMUM_DELIVERY.md`
- 已新增 `RELEASE_STRATEGY.md`
- 已新增 `MINIMUM_DELIVERY_BASELINE_v2.0.md`
- 已新增 `MANUAL_VERIFICATION_RUNBOOK_v2.0.md`
- 已新增 `MANUAL_VERIFICATION_RECORD_v2.0.md`
- 已完成自动化回归：
  - 前端 lint / build
  - 后端 compileall
  - SQLite smoke
  - MySQL config check
  - packaged dev smoke
  - packaged exe smoke
- 模块 3 当前已形成“可答辩版自动化基线”
- 人工终验的执行手册与记录模板也已补齐
- 模块 3 后续重点从“补资产”转为“按手册执行一轮人工终验并固化结论”

## 模块 4：动态地图尺寸与地图方案重构

### 说明
- 这是地图设置第二阶段，不放在 MVP 前面做。
- 原因：当前前端 `GRID_COLS / GRID_ROWS` 是硬编码常量，分布面广，直接上动态尺寸风险高。

### 目标
- 将 `GRID_COLS / GRID_ROWS / MAP_WIDTH / MAP_HEIGHT` 提取为运行时响应式配置。
- 地图方案升级为“地图 profile”：
  - `name`
  - `grid_cols`
  - `grid_rows`
  - `blocked_cells`
  - `description`
  - `custom/default`

### 当前已落地的低风险第一步
- 已新增只读地图 profile 元数据接口：`GET /status/map/profiles`
- 已新增地图尺寸变更只读预检接口：`GET /status/map/resize-precheck`
- 已在地图设置面板中展示：
  - 当前地图方案
  - 地图方案列表
  - 尺寸编辑前置条件状态
- 已在前端加入目标列数 / 行数预检面板，可提前看到：
  - 活动任务数
  - 忙碌 AGV 数
  - AGV / 点位 / 模板 / 障碍越界数量
  - 当前阻塞原因
- 已为地图预设补充尺寸与 profile 关联元数据，为后续真正的尺寸切换做铺垫
- 当前仍不开放地图尺寸编辑，只做元数据与状态展示

### 安全规则
- 只有当没有活动任务、所有 AGV 都处于 `idle/maintenance` 时，允许切换或修改地图尺寸。
- 缩小地图时，如果 AGV、点位、模板、障碍中有任一对象超出新边界，则直接拒绝，不做自动裁剪。

## 模块 5：登录、角色与产品化主线

### 角色规划
- `guest/demo`
- `operator`
- `enterprise`
- `admin`

### 第一批接口
- `/auth/login`
- `/auth/logout`
- `/auth/me`

### 第一批前端行为
- 登录页
- 基础路由守卫
- 操作身份展示
- 任务 / 故障 / 操作记录带操作者字段

## 模块 6：企业端与完整产品路线

### 目标方向
- 企业申请 / 审核
- 企业空间或数据边界
- 企业模板 / 点位 / 地图方案归属
- 管理端审核与配置

### 说明
- 数据后端默认从 SQLite 演示模式转向 MySQL 正式部署模式。
- 这部分不影响最低可交付版，但属于最终完整产品路线。

## 重要接口与类型
- 新增接口：
  - `GET /status/ui-settings`
  - `PUT /status/ui-settings`
- 扩展现有返回：
  - `GET /status/map` 继续保证返回 `grid_cols / grid_rows / blocked_cells`
  - `GET /status/map/presets` 后续统一返回每个预设 / 方案的尺寸元数据
- 封装模式新增行为：
  - FastAPI 在封装模式下托管前端静态资源
  - 默认读取 SQLite 数据库文件

## 测试计划

### 地图设置 MVP
- 切换小地图、图例、箭头、图标后刷新，设置仍保留
- SQLite / MySQL 模式下设置一致生效
- 不破坏现有障碍预设、导入导出、恢复默认功能

### 封装试运行
- 封装包双击启动成功
- 浏览器自动打开
- 自动 / 手动 / 多段 / 点位 / 模板 / 障碍预设均可操作
- SQLite 数据重启后仍保留

### 最低可交付收口
- 全链路回归无严重阻断
- 无必须依赖开发环境才能运行的步骤

### 动态地图尺寸模块
- 地图尺寸变化后绘制正确
- 越界点位 / 模板 / 障碍会被阻止而不是静默破坏
- 活动任务存在时不能改尺寸

### 登录与角色
- 未登录不能进入受保护操作
- 不同角色看到不同入口
- 任务 / 故障操作能记录操作者

## 当前建议的下一步
1. 进入模块 2：完成封装模式下后端托管前端静态资源。
2. 增加 `PyInstaller` 打包脚本与 `start_agv.bat` 封装启动器。
3. 在 SQLite 模式下完成第一次“无开发环境依赖”的演示包试运行。

## 说明
- 本文档是实施过程中的维护源文件。
- `PROJECT_IMPLEMENTATION_PLAN_v2.0.docx` 与本文件保持同内容同步更新。
