# AGV Graduation Project Session Handoff

## 2026-04-28 AI Materials ComfyUI UX Closure

- 本轮按“AI 素材板块体验收口优化计划 v1”完成可用性增强，没有重做 ComfyUI 主链路，也没有把生成结果接入地图业务数据。
- 后端新增轻量健康检查接口：
  - `GET /ai/comfyui/health`
  - 复用 `ai.render` 权限。
  - 返回 `enabled`、`base_url`、`reachable`、`checkpoint_count`、`preferred_checkpoint`、`error_code`、`error_message`、`checked_at`。
  - ComfyUI 禁用或离线时仍返回结构化 `200` 状态，便于前端展示“离线但页面可用”。
- 前端 AI 素材区已新增“渲染前检查”：
  - 源 JSON
  - ComfyUI 连接
  - 模型文件
  - Workflow
  - 支持手动“检查连接”，并根据成功 / 警告 / 错误显示不同状态。
- 源 JSON、Workflow JSON、提示补充已折叠进“高级编辑”，默认流程更轻：
  - 选择来源
  - 套用推荐模板
  - 载入源 JSON / 填入 Workflow
  - 提交渲染
- AI 渲染任务卡片增强：
  - 显示 `Prompt ID` 与 ComfyUI 地址。
  - 支持复制 `Prompt ID`。
  - 支持刷新单个任务。
  - 支持“基于此任务重新生成”，该操作只回填表单，不自动提交。
- 错误提示收口：
  - `Map profile request failed`、checkpoint 读取失败、任务读取 / 提交 / 删除失败改为本地化可操作提示。
  - ComfyUI 后端错误码已补进三语 `apiErrorText`，避免直接露出错误码。
- 模板区文案已梳理：
  - 本地模板和共享模板有独立说明。
  - 按钮区分“保存为本地模板 / 保存到共享模板 / 套用本地模板 / 套用共享模板”。
- 本轮涉及文件：
  - `backend/app/api/ai_api.py`
  - `backend/app/services/comfyui_service.py`
  - `frontend/agv-frontend/src/App.vue`
  - `frontend/agv-frontend/src/components/ComfyAiWorkspace.vue`
  - `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
  - `frontend/agv-frontend/src/assets/agv-map.css`
  - `frontend/agv-frontend/src/locales/zh.js`
  - `frontend/agv-frontend/src/locales/en.js`
  - `frontend/agv-frontend/src/locales/ja.js`
- 本轮验证：
  - `backend\venv\Scripts\python.exe -m compileall backend\app`
  - `npm run lint`
  - `npm run build`
  - `git diff --check`

### 2026-04-28 AI Materials Patch

- 修复 AI 任务卡新增按钮在部分运行态中显示 raw key 的问题：
  - `ai_render_copy_prompt_id`
  - `ai_render_refresh_job`
  - `ai_render_reuse_job`
- 按钮显示现在增加组件内中文兜底，即使异步语言包热更新没跟上，也不会直接露出 key。
- 修复企业设置中点击“预览素材”时图片弹层在企业设置页面下层的问题：
  - `.asset-preview-mask` 的 `z-index` 从 `120` 提升到 `4300`。
- 本补丁验证：
  - `npm run lint`
  - `npm run build`
  - `git diff --check`

## 2026-05-05 Algorithm Compare Scope Fix

- 修复个人端和企业端“算法对比”与实际派车结果不一致的问题。
- 问题表现：
  - 单段任务输入 `(0,0) -> (9,7)` 后点击算法对比，`simple` 和 `A*` 都显示不可达。
  - 但同样路线创建任务并派车可以正常到达。
- 根因：
  - 前端 `/schedule/compare_path` 请求只带 `Content-Type`，没有带当前登录 token。
  - 后端请求作用域因此可能落到 `guest:default`，读取的是默认/游客地图，而不是当前个人或企业账号的地图。
  - 实际派车 `/schedule/with_path` 会带授权头，所以使用的是正确账号作用域。
- 修复：
  - `compareCurrentRoute()` 改为使用 `buildAuthorizedJsonHeaders()`。
  - 算法对比现在会和派车链路读取同一套地图尺寸、障碍物、异形有效区和企业拓扑。
- 建议人工复测：
  - 个人端：输入 `(0,0) -> (9,7)` 后点击算法对比，再创建/派发同一路线，结果应一致。
  - 企业端：在当前企业地图中重复同样操作，确认对比不再落到游客默认地图。

### 2026-05-05 Algorithm Compare Dispatch Readiness

- 继续修复“算法对比显示可达，但派送提示没有 AGV 可到达任务起点”的体验不一致。
- 设计口径：
  - 路线可达：只表示任务起点到终点可走。
  - 可派送：还必须有至少一台空闲/回仓 AGV 能从当前位置到达任务起点。
- 后端 `/schedule/compare_path` 现在每个算法结果额外返回：
  - `dispatch_reachable`
  - `dispatch_distance`
  - `dispatch_agv_id`
  - `dispatch_origin`
  - `idle_agv_count`
- 前端算法对比卡片新增“车辆到起点”一行：
  - 若有车可到起点：显示 `AGV #x 可到达起点，距离 n`。
  - 若路线可达但无车可到起点：显示 `当前没有空闲/回仓 AGV 可到达任务起点`。
  - 若无空闲/回仓车辆：显示 `当前没有空闲或回仓中的 AGV`。
- 推荐算法现在优先选择“任务路线可达且车辆能到起点”的算法，避免推荐一个实际无法派送的算法。

## 2026-04-22 Post-Defense Productization Reset

- 用户确认毕业设计答辩已经通过。
- 项目状态从“答辩可用版收口”切换为“产品化收口与系统设计增强”。
- 新增当前主线计划：
  - `docs/plans/POST_DEFENSE_PRODUCTIZATION_PLAN_2026-04-22.md`
- 第四阶段状态重新定义：
  - 答辩版：已完成阶段目标。
  - 产品化版：继续围绕动态避让、站级调度实体、企业独立客户端验收、拓扑合法性校验等方向迭代。
- 动态避让口径：
  - 当前系统已有“调度层动态避让”，包括拓扑边预占、节点/边占用检测、同路不超车、双向相遇等待/让行、优先级与绕行代价决策、死锁超时重试。
  - 当前尚不是传感器级动态避障；后续可作为中长期扩展引入连续空间避障、速度规划或真实设备感知。
- 建议下一步：
  1. 新增动态避让演示 JSON。
  2. 新增动态避让设计说明。
  3. 做企业独立客户端完整人工验收记录。
  4. 再评估是否进入“停车站 / 充电站真正站级调度实体”专题。

## 2026-04-19 Personal Defense Demo Pack

- 新增个人端导师答辩演示方案：
  - `docs/demo/PERSONAL_DEFENSE_DEMO_PLAN_2026-04-19.md`
  - `demo/docs/PERSONAL_DEFENSE_DEMO_RUNBOOK.md`
- 新增个人端答辩演示 JSON 资产：
  - `demo/json/personal_defense_map_profile_10x8.json`
  - `demo/json/personal_defense_obstacle_layout_10x8.json`
  - `demo/json/personal_defense_busy_tasks.json`
- 资产设计要点：
  - 使用 `10 x 8` 货架通道地图，障碍物避开默认 3 台 AGV 和默认常用业务点位。
  - 批量任务一次导入 8 条，默认会让多台 AGV 先运行，其余任务进入队列，适合导师现场观察“车忙起来”的效果。
  - 常用点位只作为业务地标说明，停车点、充电点、停车站、充电站继续保留为运行资源语义，避免“充电区”和“充电站”概念混淆。
- 已做轻量校验：
  - 新增 3 个 JSON 文件均可正常解析。
  - 8 条任务在配套障碍物布局下均可达。

## 2026-04-20 Personal Demo Bugfix Notes

- 本轮针对个人端演示收口：
  - 前端 `normalizeBlockedCellList` 增加非数组防御，避免保存地图/任务相关更改时出现 `cells.filter is not a function`。
  - 个人用户隐藏地图设置里的“自治策略”组，降低个人端设置复杂度。
  - 自动调度不再接走未绑定 AGV 的 `manual` 导入任务，`task_manual_single_demo.json` 应保留在待绑定队列。
  - `personal_defense_busy_tasks.json` 坐标改为同时避开默认障碍与个人答辩演示障碍模板。

## 2026-04-12 Incremental Update

- 第四阶段验收执行计划 `v1` 已继续推进到“账号与数据隔离”高优先级链路：
  - SQLite 冒烟回归现在不仅验证“个人数据不会串到企业”，还补上了：
    - 企业管理员 / 企业操作工 / 企业后勤岗共享同一组织 scope
    - 个人 AGV 与企业 AGV 隔离
    - 同组织企业角色之间可见同一企业点位 / 模板 / 拓扑 / AGV
  - 相关后端文件：
    - `backend/scripts/sqlite_smoke_check.py`
- 前端切账号 / 切作用域的数据清理链已补强，避免“后端没串号，但界面保留上一账号数据”：
  - 作用域切换时，运行态 `AGV / task / fault` 列表会先清空，再加载当前作用域数据。
  - 点位库 / 模板库从后端加载失败时，会回退到默认内置数据并清空上一作用域的自定义数据，不再继续显示旧账号内容。
  - `AGV / task / fault` 拉取现在会校验响应状态和数据类型，异常时不会把错误 payload 当成当前作用域数据继续挂在界面上。
  - 相关前端文件：
    - `frontend/agv-frontend/src/App.vue`
    - `frontend/agv-frontend/src/composables/usePointTemplateBackend.js`
- 本轮已验证：
  - `backend\venv\Scripts\python.exe backend\scripts\sqlite_smoke_check.py` 通过
  - `backend\venv\Scripts\python.exe -m compileall backend\app` 通过
  - `frontend\agv-frontend\npm run lint` 通过
  - `frontend\agv-frontend\npm run build` 通过

- 第四阶段 `4F` 企业独立客户端登录链继续收口：
  - 新增 `backend/scripts/enterprise_client_login_smoke.py`
    - 直接以 API 级方式验证企业管理员、企业操作工、企业后勤岗三条登录链
    - 覆盖 `/auth/login`、`/auth/me`、`/status/map`、`/agv/list`、`/task/list`、`/status/ui-settings`
    - 额外校验企业管理员可访问 `/auth/enterprise-members`，而操作工 / 后勤岗会被正确拒绝
  - 已修复一个真实触发 `fail to fetch` 的后端根因：
    - 企业组织第一次读取自治策略设置时，`agv_autonomy` 只传入局部默认值
    - `backend/app/repositories/sql/ui_settings_store.py` 之前却按“完整 UI 设置”强制写入，导致缺少 `show_minimap` 等字段时直接 `KeyError`
    - 该问题会在企业客户端登录后拉取 `/agv/list` 时放大成 500，表现为前端 `fail to fetch`
    - 现在 UI 设置存储层已改成可安全接受局部默认值，企业 scope 首次启动不会再因为这条链炸掉
  - `start_enterprise_client.bat` 与 `run_enterprise_packaged_dev.bat` 的启动等待已从“只看首页能打开”升级成“首页 + `/auth/me` API 都 ready 再打开浏览器”，用来降低独立客户端刚启动就出现 `fail to fetch` 的概率
  - 相关文档已补：
    - `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`
    - `enterprise_client/docs/QUICKSTART_ENTERPRISE_CLIENT.md`

## 2026-04-11 Incremental Update

- 停车站视觉继续增强：
  - 运行地图中的连续 `parking` / `charge` 点位现在会显示为“整块站区底座 + 顶签 + 泊位标记”，不再只是两格旁边挂一个标题。
  - 企业路网拓扑编辑器中的连续停车点 / 充电点也同步增加了整块站区预览，编辑态和运行态语义保持一致。
- 站内 AGV “当前不可调度”链路继续收口：
  - 站内弹窗里现在会直接显示不可调度原因，而不只是统一文案。
  - 已新增的原因文案覆盖：任务执行中、前方等待、充电流程中、故障 / 急停、维护中、未知状态。
  - 站内统计已修正：正在边上运行、已经离开站位但 `current_node` 仍停留在源节点的 AGV，不再继续算作“站内 AGV”。
- 当前这轮相关前端文件：
  - `frontend/agv-frontend/src/App.vue`
  - `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
  - `frontend/agv-frontend/src/assets/agv-map.css`
  - `frontend/agv-frontend/src/locales/zh.js`
  - `frontend/agv-frontend/src/locales/en.js`
  - `frontend/agv-frontend/src/locales/ja.js`
- 本轮已验证：
  - 前端构建 `cmd /c npm run build` 通过。

更新时间：2026-04-10

## 1. 项目位置
- 仓库根目录：`Repository/Package0.0/AGV_Graduation_Project`
- 前端主入口：`frontend/agv-frontend/src/App.vue`
- 企业设置弹窗：`frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
- 主样式文件：`frontend/agv-frontend/src/assets/agv-map.css`
- 中文文案：`frontend/agv-frontend/src/locales/zh.js`
- 英文文案：`frontend/agv-frontend/src/locales/en.js`
- 日文文案：`frontend/agv-frontend/src/locales/ja.js`

## 2. 当前阶段
- 当前处于“企业版二代地图与运行优化收口”阶段。
- 已经完成大量 4C-4F、企业拓扑运行链、地图编辑器、账号隔离、AGV 上下岗与维护池相关工作。
- 最近这一轮刚完成：
  - 企业路网拓扑编辑器里，节点从“充电点”切换到“停车点”时的即时反馈增强
  - 连续相邻的充电点 / 停车点的轻量级“站群可视化”展示

## 3. 本轮刚完成的内容

### 3.1 拓扑节点类型切换反馈增强
- 目标：解决“企业路网拓扑编辑器中，选择一个点位为充电点，再切换成停车点就没有正确反馈”的问题。
- 已完成：
  - 选中格子的类型配色与选中态叠加，不再被统一选中底色盖掉
  - 节点列表不再优先显示晦涩 key，而是显示更可读的节点文案
  - 选中节点编辑区顶部新增节点摘要块，立即显示：
    - 节点徽标
    - 节点类型
    - 坐标
    - 当前显示名称

### 3.2 连续充电点 / 停车点的站群展示
- 目标：不改调度核心前提下，让连续多个充电点、停车点在视觉上更像“充电站 / 停车站”。
- 当前实现策略：
  - 只做“展示聚合”，不做“调度实体合并”
  - 相邻的 `parking` 或 `charge` 节点按 4 邻接规则自动分组
  - 组内节点数大于 1 时，渲染组边界轮廓和组标签
- 已完成效果：
  - 编辑器中显示虚线站群边框和组标签
  - 运行主地图显示站群轮廓与汇总标签
  - 小地图显示站群轮廓，不显示拥挤标签

## 4. 本轮涉及的关键文件

### 已修改
- `frontend/agv-frontend/src/App.vue`
  - 新增拓扑节点可读标签和站群构建辅助函数
  - 新增编辑器 / 运行态 / 小地图的站群分组计算
  - 把这些能力透传给 `EnterpriseSettingsDialog`
  - 运行地图模板里增加站群轮廓和标签层

- `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
  - 编辑器舞台增加站群轮廓层和标签层
  - 节点列表使用可读名称
  - 节点编辑区增加顶部摘要

- `frontend/agv-frontend/src/assets/agv-map.css`
  - 调整节点类型选中态视觉叠加
  - 新增编辑器站群轮廓 / 标签样式
  - 新增运行地图和小地图站群轮廓 / 标签样式

- `frontend/agv-frontend/src/locales/zh.js`
- `frontend/agv-frontend/src/locales/en.js`
- `frontend/agv-frontend/src/locales/ja.js`
  - 新增“充电站 / 停车站 / 站群标签”相关文案

## 5. 已确认的设计约定

### 5.1 站群语义
- 当前“连续点位变成站”采用轻量方案：
  - 展示上合站
  - 调度上仍按单点节点运行
- 也就是说：
  - 视觉层：像一个充电站 / 停车站
  - 数据层：仍然是多个独立节点
  - 调度层：仍然按原来的节点容量、节点占位、节点点击逻辑工作

### 5.2 为什么先不做真正的站级实体
- 因为真要把多个节点合成“一个站”，会同时影响：
  - 进站规则
  - 出站选车
  - 容量共享
  - 路径终点语义
  - 点位模板
  - 任务引用
- 当前项目已经进入收口期，所以先做展示增强，保持风险低。

## 6. 更早已完成但对后续很重要的工作

### 6.1 企业 / 个人 AGV 生命周期
- 企业端：
  - 已支持管理员对满足条件的 AGV 执行“下岗 / 退出运行位”
  - 下岗要求：空闲、无任务、且当前位于站点 / 停车点 / 充电点
  - 下岗后复用 `maintenance` 作为离线池/维护池状态
- 个人端：
  - 不再鼓励直接浅层误删
  - 先送修 / 下线，再允许删除
  - 删除只允许对 `maintenance` 状态的小车进行

### 6.2 小铃铛与地图点击交互
- 小铃铛展开后，点击地图空白处会优先关闭小铃铛
- 关闭这一击不会再误触发地图原本的点击逻辑

### 6.3 路网拓扑保存
- 企业路网拓扑保存逻辑已改为可绕过障碍编辑锁的那层旧限制
- 保存时走交互式强制应用链路，避免“点击保存无反应”

### 6.4 企业拓扑运行语义
- 已推进“拓扑边 = 主干道 / 快车道”的语义统一
- 已修过：
  - 纯拓扑视图边界显示
  - 单向边方向箭头表达
  - 路径显示时机
  - AGV 头顶运行信息
  - 站点 / 停车点 / 充电点多车容量
  - 部分拓扑中途接入 / 中途退出

## 7. 当前已知仍值得继续观察的问题

### 高优先级观察项
1. 企业 / 个人地图数据隔离
- 之前已经修过“AGV 数据不串账号”
- 但用户后续反馈过：
  - 切换账号后，个人用户地图仍可能被企业地图改动影响
- 这是后续应优先回归的一项

2. 企业拓扑保存后的反馈链
- 本轮修的是节点类型切换反馈
- 用户前一轮还提过一次“点击保存路网拓扑没有效果”
- 需要再做一次实机回归，确认没有回退

3. 站群展示与真实点击语义
- 当前站群只是视觉聚合
- 需要继续确认：
  - 点击组内单点时是否仍然准确
  - 运行地图点击站点小圆点是否仍正常打开站内调度弹窗

### 中优先级优化项
1. 站群命名
- 现在默认是“充电站 / 停车站”
- 后续可增加：
  - 自定义站群名称
  - 自动编号，例如“充电站 A / B”

2. 站群 hover 提示
- 现在主地图标签显示汇总占用
- 后续可以做：
  - 鼠标悬停显示组内节点数量
  - 显示组内 AGV 列表
  - 显示组内总容量和已占用

3. 真正站级调度实体
- 暂不建议现在做
- 如果后续时间足够，可以单列一个专题迭代

## 8. 最近一次实际验证结果
- 前端构建验证已通过
- 执行命令：

```powershell
cmd /c npm run build
```

- 执行目录：

```powershell
Repository/Package0.0/AGV_Graduation_Project/frontend/agv-frontend
```

## 9. 建议新聊天接手后的第一批动作
建议顺序如下：

1. 先读本交接文档
2. 先回归这次刚改的拓扑编辑器反馈
3. 再验证账号切换后的地图隔离
4. 最后再决定是否继续做“站群命名 / hover 提示”

### 推荐回归点
1. 拓扑编辑器里选中某节点
2. 把它从“充电点”切成“停车点”
3. 确认：
   - 格子底色变化立即正确
   - 节点摘要立即更新
   - 节点列表名称立即更新
4. 连续放置两个以上相邻停车点 / 充电点
5. 确认：
   - 编辑器里出现组轮廓和标签
   - 保存后运行地图里出现组轮廓和汇总标签

## 10. 给新聊天的启动提示词
可直接把下面这段发到新聊天：

```text
请先阅读 `Repository/Package0.0/AGV_Graduation_Project/SESSION_HANDOFF.md`。
这是一个 AGV 毕业设计项目，请基于交接文档里的当前状态继续开发，不要重做已完成部分。
请先用中文简要总结你理解到的当前进度、刚完成的改动、仍待处理的问题，再继续执行下一步。
```

## 11. 协作偏好
- 默认使用中文沟通
- 尽量直接执行，不要频繁追问
- 如果确实需要确认，优先给出清晰方案和推荐选项
- 保持现有布局和已经完成的交互，不随意“重做一版”
- 优先做“低风险收口”，再做“大语义重构”

## 12. 说明
- 本文档主要服务会话迁移与新聊天快速接手
- 不记录敏感口令、登录密码等信息
- 如需在新聊天中用一个识别短语延续语境，建议由用户在新聊天首句单独提供，而不是写入仓库

## 13. Git 与推送约定

### 当前仓库信息
- 仓库路径：`Repository/Package0.0/AGV_Graduation_Project`
- 当前远端名：`AGV`
- 远端地址：`https://github.com/Novince404/AGV.git`
- 当前主分支：`main`

### 默认推送方式
- 我们约定优先使用普通直推，不再额外加 `http.version=HTTP/1.1` 之类的兼容参数。
- 标准命令是：

```powershell
git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV main
```

### 如果是版本标签推送
- 之前用过的标签推送方式是：

```powershell
git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV v1.5.0
git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV v1.6.0
git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV v2.0.0
git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV v2.0.0-beta.1
```

### 如果 Codex 侧推送失败
- 之前出现过“Codex 无法正常 push，但用户在 VS Code 里点 `同步更改` 可以成功推送”的情况。
- 所以约定是：
  - 新聊天优先尝试正常 `git push`
  - 不要优先折腾 `http.version=HTTP/1.1`
  - 如果 Codex 侧 push 失败，而工作区改动已经确认没问题，可以提示用户直接用 VS Code 的 `同步更改` 完成推送

### Git 操作规则
- 不使用交互式 git 流程，优先非交互命令。
- 不随意改写历史，不 `amend`，除非用户明确要求。
- 不使用破坏性命令，例如：
  - `git reset --hard`
  - `git checkout --`
- 不回滚不属于当前任务的现有改动。
- 如果工作区本来就有别的未提交修改，要在其基础上继续工作，不要擅自清掉。

### 新聊天可直接遵守的推送流程
1. 先 `git status --short` 看变更范围
2. 确认只提交本次需要的文件
3. 使用非交互方式 `git add` / `git commit -m "..."`
4. 直接执行：

```powershell
git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV main
```

5. 若 Codex push 失败但本地提交已完成，则让用户直接点 VS Code 的 `同步更改`

## 14. 2026-04-12 第四阶段验收收口增量（4F + 任务路径生命周期）

### 14.1 本轮已完成
- 新增 `backend/scripts/enterprise_client_login_smoke.py`
  - 启动本地 uvicorn 临时服务
  - 用真实 HTTP 流程验证企业独立客户端三账号登录链：
    - `enterprise_demo / enterprise123`
    - `enterprise_operator_demo / operator123`
    - `enterprise_logistics_demo / logistics123`
  - 校验 `/auth/login`、`/auth/me`、`/status/map`、`/agv/list`、`/task/list`、`/status/ui-settings`
  - 校验企业成员管理接口的角色权限：
    - 管理员可访问
    - 操作工 / 后勤岗返回 `403`
- 已修复 4F 登录链里的一个真实后端根因：
  - 文件：`backend/app/repositories/sql/ui_settings_store.py`
  - 问题：自治/运行时只传入局部默认设置时，UI 设置仓储层仍按“完整 UI payload”强取字段，首次企业 scope 下访问 `/agv/list` 会抛 `KeyError('show_minimap')`
  - 结果：企业独立客户端会表现成 `fail to fetch`
  - 修复：仓储层先把局部默认值与完整 UI 默认值合并，再落到 `_apply_payload()`
- 已增强企业客户端启动脚本等待逻辑：
  - `start_enterprise_client.bat`
  - `run_enterprise_packaged_dev.bat`
  - 现在会同时等待前端主页和 `/auth/me` API 就绪，再打开浏览器，避免“页面已开但会话接口还没起好”
- 已修复“任务完成后路径字段未清理”的后端缺口：
  - `backend/app/services/task_service.py`
  - `backend/app/utils/agv_movement.py`
  - 覆盖两条链：
    - 人工完成任务 `finish_task`
    - AGV 自然跑完最后一段后的自动完成
  - 现在完成任务时会统一清掉：
    - `task.path_to_start`
    - `task.path_to_end`
    - `task.path_length_to_start`
    - `task.path_length_to_end`
  - 人工完成任务时也会同步 `agv.clear_motion()`，避免残留运动态
- 已把“派发即有路径、完成即清路径”补进 SQLite 冒烟：
  - 文件：`backend/scripts/sqlite_smoke_check.py`
  - 新增校验：
    - 调度返回时 `path_to_start` / `path_to_end` 立即存在
    - 自动完成后路径字段清空
    - 人工完成后路径字段清空

### 14.2 本轮验证结果
- `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
- `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过
- `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py` 通过

### 14.3 对第四阶段状态的最新判断
- `4F 企业独立客户端登录链`：已从“有产物但未稳定验收”推进到“核心登录链和启动就绪链已有自动化冒烟兜底”
- `4C 派发任务与路径显示`：已进一步收口，“派发立即显示 + 完成及时清理”后端链路已有明确回归覆盖
- 第四阶段仍不应宣告“全部正式完成”，因为 `4D 冲突避让 / 死锁打破` 等高风险逻辑包还需要继续按验收清单回归签收

### 14.4 新聊天接手时的优先顺序建议
1. 先跑：
   - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py`
   - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py`
2. 如果都通过，下一优先级继续推进第四阶段验收清单里的：
   - 同路不超车
   - 双向相遇避让
   - 死锁打破
3. 前端视觉类优化继续坚持“不重做稳定模块，只补未收口项”

### 14.5 2026-04-12 追加：4D 冲突避让自动化基线
- 本轮没有重写 `4D` 运行逻辑，而是先验证现有实现，并把关键规则固化进 `backend/scripts/sqlite_smoke_check.py`
- 新增回归覆盖：
  - 同路跟车时，后车会识别前车占道，不应出现“同路超车”判定空洞
  - 双向相遇时，低优先级任务应判定为绕行方
  - 同优先级相遇时，较新的任务应在死锁打破里承担绕行
- 当前结论：
  - `4D` 不是“完全签收”，但核心规则已具备自动化回归保护
  - 后续若继续推进 `4D`，优先做真实运行态长时间回归，而不是先改底层策略

### 14.6 2026-04-12 追加：4D 真实运行态冲突冒烟与边占用启动窗口修复
- 新增 `backend/scripts/runtime_conflict_smoke.py`
  - 这不是静态规则脚本，而是会真的启动调度线程，验证运行态冲突链
  - 当前覆盖四类场景：
    - 同路跟车时后车进入 `waiting / yielding`，且不会和前车同时占用同一条主干边
    - 双向相遇时，低优先级任务会在规划期直接改走支路
    - 同优先级双向相遇时，较新的任务会在规划期 tie-break 中改走支路
    - 两条相向任务几乎同时启动时，不会再双车同时占用同一条主干边
- 已修复 `backend/app/utils/agv_movement.py` 中的一个 4D 真实漏洞：
  - 问题：在极限并发启动下，两条相向任务可能在同一个启动窗口里同时进入同一条拓扑边
  - 表现：两个 AGV 会同时带着同一个 `current_edge` 运行，破坏“单边单车占用”预期
  - 修复：增加运行时拓扑边 claim/release 机制，并把 claim 也纳入边冲突探测
  - 结果：即使是并发启动窗口，也会先让一方进入 `waiting / yielding`，不再双占边
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py` 通过

### 14.7 2026-04-13 追加：第五项 JSON 任务导入已补齐自动化回归
- 新增 `backend/scripts/task_json_import_smoke.py`
  - 覆盖三条第四阶段清单里的 demo 导入链：
    - `task_auto_single_demo.json`
    - `task_manual_single_demo.json`
    - `task_multi_stage_demo.json`
  - 额外补了一条“手动绑定任务按 dispatch origin 自动重映射 preferred_agv_id”的兼容性回归，避免不同 scope 下默认 AGV id 不一致时导入失效
- 已对齐 demo 语义与验收清单：
  - `demo/json/task_manual_single_demo.json`
  - `dist/AGV_Dispatch_Package_v2/demo/json/task_manual_single_demo.json`
  - 现在手动 demo 默认不预绑定 AGV，用于验证“导入后保留在待绑定队列，并显示清楚说明”
  - 原先那条会撞上默认种子 AGV 的历史路线已移除，不再依赖某个固定 `AGV #1`
- 已补齐说明文档：
  - `demo/json/README_demo_assets.md`
  - `dist/AGV_Dispatch_Package_v2/demo/json/README_demo_assets.md`
  - `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`
  - 现在清单启动前健康检查也会显式跑 `backend/scripts/task_json_import_smoke.py`
- 已保留并验证后端兼容修复：
  - `backend/app/services/task_service.py`
  - 当手动导入 payload 带着旧的 `preferred_agv_id`，但当前 scope 下实际 AGV id 已变化时，系统会优先根据 `dispatch_origin_x / dispatch_origin_y` 解析当前作用域里的真实 AGV id
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\task_json_import_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py` 通过

### 14.8 2026-04-13 追加：第六项拓扑主干道默认权重与中途接入/离开已修复
- 已修复主干道路径规划的一个真实底层问题：
  - 文件：
    - `backend/app/utils/warehouse_map.py`
    - `backend/app/utils/path_planner.py`
  - 问题：
    - 当拓扑边没有显式 `weight` 时，系统一直按 `1.0` 处理，而不是按边的真实几何长度处理
    - 对长边来说，这会错误地让 planner 认为“先退回端点，再跑完整条主干道”更便宜
  - 典型错误现象：
    - `(3,1) -> (7,1)` 会被算成 `3 -> 1 -> 7`
    - `(1,1) -> (5,1)` 会被算成 `1 -> 7 -> 5`
  - 修复：
    - 规范化拓扑 payload 时，默认把边权重补成节点间真实网格长度
    - 运行时读取已有拓扑时，也把真实几何长度作为最小合法权重兜底，兼容历史上已经存成 `weight=1.0` 的长边
- 已把第四阶段清单第 6 项补进 SQLite 冒烟：
  - 文件：`backend/scripts/sqlite_smoke_check.py`
  - 新增 `assert_topology_trunk_lane_behavior()`
  - 当前覆盖：
    - 端点到端点会使用主干道，并保留速度倍率
    - 起点在主干道中段时，会直接沿边到目标端，不再回退到远端节点
    - 终点在主干道中段时，会直接在中段离边，不再先跑到远端再折返
    - 起终点都不在边上时，会在合适场景中途接入主干道再离开
    - 如果主干道并不划算，会直接走普通网格路
    - AGV 正在拓扑边上时使用主干道速度；离开拓扑边后恢复基础速率
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\task_json_import_smoke.py` 通过

### 14.9 2026-04-13 追加：第七项站点/停车点/充电点已补容量与电量趋势回归
- 本轮没有重做站点 UI，而是先把第七项里最关键的两条底层链补进自动化：
  - `backend/scripts/sqlite_smoke_check.py`
- 新增 `assert_special_node_capacity_runtime()`
  - 覆盖：
    - 停车节点的运行时占用统计会同时计入“已在站内的 AGV”和“正在返仓、已预留该节点的 AGV”
    - 当停车节点达到容量上限后，`build_runtime_special_node_constraints()` 会把该节点加入 `blocked_positions / avoid_node_keys`
    - 目标节点本身不会被错误地一起避让
  - 这条回归也再次确认了一个系统约束：
    - `parking / charge` 节点容量不会低于默认下限 `4`
    - 因此如果拓扑里手工写 `capacity: 2`，运行时仍会被规范化到默认下限
- 新增 `assert_battery_runtime_behavior()`
  - 直接验证 `_sync_battery_runtime()` 的四类趋势是否符合配置：
    - 行驶中按 `battery_active_drain_per_sec` 掉电
    - 等待/让行中按 `battery_waiting_drain_per_sec` 掉电
    - 停在停车点时按 `battery_parking_idle_drain_per_sec` 掉电
    - 普通空闲时按 `battery_idle_drain_per_sec` 掉电
    - 充电中按 `battery_charge_per_sec` 回电
  - 同时验证 `_release_from_charging_if_ready()`：
    - 电量达到释放阈值后，AGV 会退出 `charging`，恢复到 `idle`
    - `auto_target_node / auto_target_type` 与充电态运动字段会一起清理
- 当前结论：
  - 第七项里“容量允许的站内多车收纳”和“电量趋势符合配置”已经都有后端自动化护栏
  - 但第七项还不能完全算签收，因为前端层面的 `n/m` 遮挡、悬停交互、站内 AGV 列表观感仍要继续按界面实际回归
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py` 通过

### 14.10 2026-04-13 追加：第八项通知与协同已补后端自动化回归
- 新增 `backend/scripts/feedback_notification_smoke.py`
  - 这条脚本没有走 `fastapi.testclient`，而是和企业独立客户端登录冒烟保持一致，直接启动本地 uvicorn，再通过真实 HTTP 请求回归通知链
  - 这样不依赖额外的 `httpx` 开发包，也更贴近第四阶段验收场景
- 当前覆盖两条核心通知链：
  - 企业内部请求：
    - `enterprise_operator_demo` 创建面向后勤岗的内部请求
    - `enterprise_logistics_demo` 能在请求列表里看到新请求，摘要 `open` 计数同步变化
    - `enterprise_demo` 也能看到该请求
    - `personal_demo` 访问企业内部请求接口会收到 `403`
    - 后勤岗更新状态为 `in_progress` 后，企业管理员刷新列表能看到同步后的状态
  - 平台 Bug 反馈：
    - `personal_demo` 提交平台 Bug
    - 提交者自己能在个人反馈列表里看到新反馈，且 `management=false`
    - 企业操作工不会看到别人的平台 Bug
    - `platform_admin_demo` 能在平台治理侧看到该反馈，且摘要 `open` 计数同步变化
    - 平台管理员将状态更新为 `resolved` 后，提交者刷新列表能看到已解决状态
- 当前结论：
  - 第八项里“企业内部请求通知链”和“平台 Bug 反馈通知链”已经都有后端自动化护栏
  - 但第八项还没有完全签收，因为前端层面的“小铃铛未读态变化”和“右下角不遮挡返回顶部按钮”仍需要继续走界面回归
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\scripts` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\feedback_notification_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过

### 14.11 2026-04-14 追加：第四阶段当前完成度与新聊天接手顺序
- 已在文档中标注完成状态：
  - `PHASE4_ACCEPTANCE_EXECUTION_PLAN_v1.md`
  - `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`
- 当前可视为“已完成 / 已有自动化护栏”的项：
  - 启动前健康检查基线
  - 第 2 项账号与数据隔离
  - 第 3 项企业独立客户端登录核心链
  - 第 4 项派发任务与路线显示
  - 第 5 项 JSON 任务导入
  - 第 6 项拓扑主干道
  - 第 4D 的同路不超车 / 双向避让 / 死锁打破核心规则自动化
  - 第 7 项中的后端容量、电量趋势、充满释放
  - 第 8 项中的企业内部请求与平台 Bug 反馈后端通知链
- 当前仍未收口的项：
  - 第 7 项前端：停车站 / 充电站的站级显示、`n/m`、悬停、站内 AGV 列表观感
  - 第 8 项前端：小铃铛未读态、小铃铛与返回顶部按钮的布局关系
  - 第 9 项：说明中心首次打开、`H` 重开、和企业设置 / 页面设置的层级关系
  - 4B 补充项：拓扑保存链与运行态界面实机回归
  - 4F 补充项：完整 EXE 演示链人工签收
  - 4D 补充项：复杂交汇口、长时间运行稳定性
- 新聊天建议的继续顺序：
  1. 先处理第 9 项“说明中心与设置弹窗”，因为它和第 8 项前端弹层关系相邻，适合一起收口
  2. 再处理第 8 项剩余前端问题：小铃铛未读态与遮挡关系
  3. 接着回到第 7 项前端站级显示，把停车站 / 充电站的视觉与悬停继续收细
  4. 最后做 4F EXE 人工签收与 4D 长时稳定性回归
- 新聊天启动后建议先跑：
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\task_json_import_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\feedback_notification_smoke.py`
  - `cd frontend\\agv-frontend && npm run lint && npm run build`

### 14.12 2026-04-14 追加：修复“进站后 0/8 + 回仓/充电只走一步就卡住”
- 根因确认：
  - `backend/app/utils/agv_movement.py` 的自治移动线程里，`_begin_motion_segment()` 已经改成返回 4 个值，但 `move_agv_to_autonomy_target()` 里的调用方仍按 3 个值解包
  - 同一段代码在 `_finish_motion_segment()` 调用时也漏传了 `edge_key`
  - 结果是自治回仓 / 回充线程会在第一段移动刚开始时直接异常退出：
    - AGV 看起来只走了一步
    - `current_edge` 残留
    - 如果目标是站点 / 停车站 / 充电站，前端会把静止车隐藏掉，但占用统计又因为残留 `current_edge` 没把它重新计回去，于是出现“车消失且显示 0/8”
- 已做修复：
  - `backend/app/utils/agv_movement.py`
    - 修正自治线程对 `_begin_motion_segment()` 的返回值解包
    - 补上 `_finish_motion_segment()` 所需的 `edge_key`
  - `backend/app/utils/agv_autonomy.py`
    - 新增“残留 `current_edge` 的自治卡死恢复”
    - 当自治车仍处于 `idle_returning / waiting_for_charge`，但边状态明显过期时，会先把当前位置重新规范化，再自动续跑或直接在目标站点收尾
  - `frontend/agv-frontend/src/App.vue`
    - 运行态站点占用统计改为复用 `resolveEnterpriseRuntimeTopologyNodeForAgv()`
    - 当 AGV 仍带着过期 `current_edge` 但动画已结束时，前端不再错误忽略该 AGV，也不再继续拿旧的 `render_x / render_y` 作为停驻位置
- 已补自动化回归：
  - `backend/scripts/sqlite_smoke_check.py`
  - 新增 `assert_autonomy_target_motion_lifecycle()`
    - 覆盖“自治回仓一格到站后能正常收尾”
    - 覆盖“自治回充一格到站后会进入 charging”
    - 覆盖“历史残留 current_edge 的自治车会被自动恢复，不再长期卡死”
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过
  - `cd frontend\\agv-frontend && npm run lint` 通过
  - `cd frontend\\agv-frontend && npm run build` 通过

### 14.13 2026-04-14 追加：修复“电量耗尽后回弹成 100%”
- 根因确认：
  - `backend/app/utils/agv_autonomy.py` 中有两处把电量读取写成了 `float(getattr(agv, "battery_level", 100.0) or 100.0)`
  - 这会把合法的 `0.0` 当成假值处理，下一轮电量同步或低电量自治判断时直接回退到 `100.0`
  - 结果表现为：AGV 电量耗尽后，下一次自治同步会异常显示回到 `100%`
- 已做修复：
  - 新增 `_read_battery_level()`，统一按“只对 `None` 和非法值兜底，不吞掉 `0`”读取电量
  - `_sync_battery_runtime()` 改为使用 `_read_battery_level()`
  - `_start_autonomy_if_needed()` 改为使用 `_read_battery_level()`，确保 0 电量仍会被判定为低电量而不是满电
- 已补自动化回归：
  - `backend/scripts/sqlite_smoke_check.py`
  - 在 `assert_battery_runtime_behavior()` 中新增“耗尽电量 AGV”场景，验证 `0.0` 不会回弹成 `100.0`
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py` 通过

### 14.14 2026-04-16 追加：第四阶段第 8/9 项前端基础链补强
- 第 9 项“说明中心与设置弹窗”已补：
  - `GuideCenterDialog.vue` 改为 `Teleport to="body"`，并补 `role="dialog"` / `aria-modal`，让说明中心稳定浮在企业设置、页面设置等弹窗上层
  - 首次打开逻辑改为等工作台真正解锁后再自动打开，并按“角色 + 用户”只打开一次，避免登录页阶段误弹或切账号后状态混乱
  - `H` 快捷键可在非快捷键录制状态下重新打开说明中心，`Escape` 可关闭说明中心
  - 说明中心拓扑说明补入“空闲回仓、低电量回充、等待和让行仍遵守容量、主干道速度与冲突避让规则”
- 第 8 项“通知与协同”前端基础链已补：
  - 小铃铛未读数字现在同时统计企业内部请求与平台 Bug 反馈未读项
  - 平台 Bug 反馈菜单项增加未读徽标和高亮态
  - 小铃铛右下角位置上移，避开右侧面板“返回顶部”按钮的视觉占位
- 文档状态已同步：
  - `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`
  - `PHASE4_ACCEPTANCE_EXECUTION_PLAN_v1.md`
- 后续仍建议：
  - 在完整企业演示链中人工复核第 8/9 项一次
  - 继续推进第 7 项前端站级显示、4F EXE 演示签收、4D 长时间稳定性回归

### 14.15 2026-04-17 追加：第四阶段第 7 项运行态站级显示基础链补强
- 本轮只改前端运行态显示，不改调度、容量统计、回仓回充或路径逻辑。
- 已做修复：
  - `frontend/agv-frontend/src/App.vue`
    - 聚合停车站 / 充电站的 hover 标题改为多行详情：站点名、当前占用、点位数、站内 AGV 编号或空站提示
    - 聚合站点、异形站点徽标、单个特殊节点补 `role="button"`、`tabindex` 和 Enter / Space 打开站内详情
    - 单个站点 / 停车点 / 充电点也补前端 hover 卡片，避免只能依赖浏览器原生 title
  - `frontend/agv-frontend/src/assets/agv-map.css`
    - 聚合站点主图继续只保留 `P/C + n/m`，详细信息下沉到 hover 和点击详情
    - 停车站 / 充电站主体阴影从外扩阴影收敛为内描边，减少相邻站点互相遮蔽
    - 竖向连续站点、异形轮廓站点统一使用站级徽标和 hover 弹层
    - `n/m` 字号略微加粗放大，保持比站名/详情更克制
- 文档状态已同步：
  - `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`
  - `PHASE4_ACCEPTANCE_EXECUTION_PLAN_v1.md`
- 相关验证结果：
  - `cd frontend\\agv-frontend && npm run lint` 通过
  - `cd frontend\\agv-frontend && npm run build` 通过
- 后续仍建议：
  - 在实际企业地图中人工复核横向、竖向、L 形聚合站点显示
  - 继续推进 4F EXE 演示签收与 4D 长时间稳定性回归

### 14.16 2026-04-17 追加：4F 企业独立客户端打包链与包内后端 smoke 收口
- 发现并修复一个真实 4F 打包问题：
  - `build_enterprise_windows_package.bat` 原先把 PyInstaller 参数放在 spec 文件后面，脚本会返回成功，但 `backend\\dist\\AGV_Enterprise_Client\\backend.exe` 没有刷新
  - 结果是 `dist\\AGV_Enterprise_Client_v1\\backend.exe` 仍停留在 2026-04-09 旧版本，包内 `/status/ui-settings` 缺少近期新增的低电量阈值字段
- 已做修复：
  - `build_enterprise_windows_package.bat`
    - 将 PyInstaller 参数放到 spec 前面
    - 用显式删除 `backend\\build\\backend_enterprise` 和 `backend\\dist\\AGV_Enterprise_Client` 替代当前环境下不稳定的 `--clean`
    - 增加 `backend.exe` 产物存在性检查，避免“假成功”
  - `backend/scripts/enterprise_packaged_backend_smoke.py`
    - 新增包内 `backend.exe` smoke
    - 会启动 `dist\\AGV_Enterprise_Client_v1\\backend.exe`
    - 依次验证企业管理员、企业操作工、企业后勤岗登录
    - 验证地图、AGV、任务、UI 设置接口，并明确检查 `low_battery_threshold` 和 `idle_charge_battery_threshold`
- 已验证：
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py` 通过
  - `build_enterprise_windows_package.bat` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_packaged_backend_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
- 当前 4F 状态：
  - 源码三角色登录链已自动化
  - 包内 `backend.exe` 三角色核心链已自动化
  - 仍建议人工双击 `dist\\AGV_Enterprise_Client_v1\\start_enterprise_client.bat`，确认浏览器打开、页面登录、企业设置 / 反馈入口实际可操作

### 14.17 2026-04-17 追加：4D 复杂交汇口长跑自动化
- 本轮没有改调度逻辑，而是把“复杂交汇口 + 多轮长时间运行”补成可重复脚本。
- 新增：
  - `backend/scripts/runtime_long_run_smoke.py`
  - 使用独立 SQLite smoke 数据库
  - 构造十字交汇拓扑：东西向与南北向两条主干道共享中心点
  - 两台 AGV 连续 4 轮往返穿越中心点
  - 每轮检查：
    - 两个任务都能完成
    - 采样过程中参与车辆不会同格
    - 至少出现过 `waiting / yielding`，确认确实触发了交汇口冲突处理
    - 参与车辆最终回到 `idle`
    - `current_edge` 和 `task_id` 不残留
- 文档状态已同步：
  - `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`
  - `PHASE4_ACCEPTANCE_EXECUTION_PLAN_v1.md`
- 相关验证结果：
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_long_run_smoke.py` 通过
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app backend\\scripts` 通过
- 当前 4D 状态：
  - 同路不超车、双向避让、死锁打破、并发抢边、复杂交汇口多轮长跑都有自动化护栏
  - 仍建议最终演示前进行真实界面长时间人工复核

### 14.18 2026-04-17 追加：第四阶段最终演示前自动化总回归
- 已按 `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md` 的启动前健康检查做总回归。
- 本轮通过项：
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\sqlite_smoke_check.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_conflict_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\runtime_long_run_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\task_json_import_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_client_login_smoke.py`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\feedback_notification_smoke.py`
  - `build_enterprise_windows_package.bat`
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_packaged_backend_smoke.py`
  - `cd frontend\\agv-frontend && npm run lint`
  - `cd frontend\\agv-frontend && npm run build`
- 当前结论：
  - 第四阶段自动化健康检查链已整体通过
  - 4A/4C/4D/4E/4F 的核心后端与打包链均有自动化护栏
  - 仍不建议把“全部正式完成”写死，因为还剩浏览器/EXE 真实人工演示复核：
    - 双击 `dist\\AGV_Enterprise_Client_v1\\start_enterprise_client.bat`
    - 三个企业角色登录并观察页面、地图、AGV、任务、企业设置 / 反馈入口
    - 实机复核拓扑保存链、站级显示、说明中心、反馈铃和长时间运行观感

### 14.19 2026-04-19 追加：第四阶段人工演示签收前置记录
- 已复跑包内后端预检：
  - `backend\\venv\\Scripts\\python.exe backend\\scripts\\enterprise_packaged_backend_smoke.py` 通过
  - 输出：`PACKAGED_ENTERPRISE_BACKEND_SMOKE_OK enterprise_admin enterprise_operator enterprise_logistics`
- 新增人工演示签收记录：
  - `docs/acceptance/PHASE4_MANUAL_DEMO_SIGNOFF_2026-04-19.md`
- 本次只做签收资产和状态收口，不改业务逻辑。
- 当前边界：
  - 自动化总回归与包内后端三角色链已通过
  - 浏览器 / EXE 真实页面仍待人工双击 `dist\\AGV_Enterprise_Client_v1\\start_enterprise_client.bat` 后按签收记录逐项确认
  - 通过人工确认前，仍不建议把第四阶段写成“正式全部完成”

### 14.20 2026-04-19 追加：常用点位与充电站语义分离
- 用户已大体试过 `docs/acceptance/PHASE4_MANUAL_DEMO_SIGNOFF_2026-04-19.md`，反馈主要问题转向点位语义：
  - 常用点位设置在面板里有变化，但地图上没有持续体现
  - “充电区 / 充电位 / 服务 / 预设 / 坐标”容易和拓扑里的充电点、充电站混淆
  - 入库口、出库口等需要明确是业务地标，而不是调度站点
- 本轮收口原则：
  - 常用点位 = 任务起终点业务地标
  - 路网拓扑节点 = 调度、容量、回仓、回充依据
  - 默认常用点位不再提供“充电区 / 充电位”
- 已做修改：
  - `frontend/agv-frontend/src/config/defaultData.js`
    - 默认 `charge` 常用点位替换为 `inspection_1`，显示为“质检台 1”
  - `frontend/agv-frontend/src/locales/zh.js`
    - 常用点位提示明确“回仓、回充请在路网拓扑里设置停车点和充电点”
    - 新增质检位文案，弱化旧的充电类常用点位含义
  - `frontend/agv-frontend/src/App.vue`
    - 主地图和小地图新增常用点位业务标记层
    - 这些标记只展示业务位置，不参与容量、回仓、回充逻辑
  - `frontend/agv-frontend/src/assets/agv-map.css`
    - 新增业务点位标记样式，和停车站 / 充电站视觉区分

### 14.21 2026-04-19 追加：常用点位显示开关、左右键分工与说明中心重构
- 本轮继续收口用户提出的三个前端体验点：
  - 常用点位地图标记需要可开关，避免企业运行图过密
  - 运行态地图左键应优先用于起终点选点，右键才打开站点或点位详情
  - `H` 说明中心需要区分个人端 / 企业端，并通过折叠分组降低阅读压力
- 已做修改：
  - `frontend/agv-frontend/src/App.vue`
    - 新增 `showBusinessPoints`，主地图和小地图的常用点位标记受该开关控制
    - 新增常用点位右键详情弹窗，展示同一坐标下的业务点位、类型、分区和坐标，并保留“定位地图”
    - 运行态站点、聚合站点、异形站点从“左键打开详情”改为“右键打开详情”，左键事件回到地图选点流程
    - `H` 说明中心改为按当前角色生成个人端 / 企业端内容
  - `frontend/agv-frontend/src/components/MapSettingsPanel.vue`
    - 地图显示组新增“显示常用点位”开关
  - `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
    - 企业页面设置里同步新增“显示常用点位”开关
  - `frontend/agv-frontend/src/components/GuideCenterDialog.vue`
    - 说明中心改为折叠分组展示，保留旧结构兜底
  - `frontend/agv-frontend/src/composables/useLocalPersistence.js`
    - 本地持久化新增 `showBusinessPoints`
  - `frontend/agv-frontend/src/composables/useUiSettingsBackend.js`
    - UI 设置后端同步新增 `show_business_points`
  - `backend/app/schemas/status.py`
  - `backend/app/services/status_service.py`
  - `backend/app/repositories/sql_models.py`
  - `backend/app/repositories/sql/ui_settings_store.py`
    - UI 设置模型、默认值、SQLite 自动补列与读写 payload 新增 `show_business_points`
  - `frontend/agv-frontend/src/locales/zh.js`
  - `frontend/agv-frontend/src/locales/en.js`
  - `frontend/agv-frontend/src/locales/ja.js`
    - 补充常用点位开关、业务点位详情、个人/企业说明中心文案；同步弱化旧“充电类常用点位”语义
  - `PHASE4_ACCEPTANCE_EXECUTION_PLAN_v1.md`
  - `docs/acceptance/PHASE4_MANUAL_DEMO_SIGNOFF_2026-04-19.md`
    - 补充常用点位开关、左右键分工和说明中心专项验收项
- 后续需要验证：
  - 前端 `lint` / `build`
  - 后端 `compileall`
  - `sqlite_smoke_check.py`
  - 企业包重打与包内后端 smoke
  - 人工查看：关闭常用点位后地图是否更干净；左键站点/点位是否顺利选起终点；右键详情是否好用；H 说明中心是否足够清晰

### 14.22 2026-04-20 追加：手动导入任务指定小车与障碍物保存修复
- 本轮修复用户演示前发现的两个前端问题：
  - 手动导入的未绑定 AGV 任务只显示“等待指定车辆执行”，但任务卡没有指定入口。
  - 导入障碍物模板后点击“保存障碍物”会把障碍物清空。
- 已做修改：
  - `frontend/agv-frontend/src/components/TaskQueuePanel.vue`
    - 对未绑定 AGV 的手动待执行任务显示“指定小车”按钮。
    - 如果当前已经选中可调度 AGV，按钮文案变为“使用 AGV #x”。
  - `frontend/agv-frontend/src/App.vue`
    - 新增手动任务绑定状态。
    - 点击任务卡“指定小车”后，如果已有可调度选中 AGV，则直接派发该任务。
    - 如果没有选中 AGV，则进入地图点选模式，提示用户点击一台空闲小车完成绑定并派发。
    - 点到不可调度 AGV 时给出提示，不会错误派发。
    - `saveBlockedCells` 增加防御：非数组参数不再被当作障碍物列表，避免点击事件对象导致保存空列表。
  - `frontend/agv-frontend/src/components/MapSettingsPanel.vue`
    - “保存障碍物”按钮改为显式调用 `saveBlockedCells()`，避免 Vue 把 click event 传入保存函数。
- 已验证：
  - `frontend/agv-frontend` 下 `npm run lint` 通过。
  - `frontend/agv-frontend` 下 `npm run build` 通过。
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app` 通过。
- 后续人工复核建议：
  - 导入 `task_manual_single_demo.json` 后，不预选 AGV 时应出现“指定小车”，点击后再点地图空闲 AGV 应能派发。
  - 先选中空闲 AGV，再点击任务卡按钮，应直接使用该 AGV 派发。
  - 导入障碍物模板后点击保存，障碍物应保持不消失。

### 14.23 2026-04-20 追加：导入文本按钮与个人 AGV 管理空提示修复
- 本轮继续修复演示前个人端体验问题：
  - 用户把 `task_manual_single_demo.json` 内容粘贴到 JSON 工具后点击“导入文本”，界面显示“导入失败”。
  - 个人端未选中 AGV 时显示“个人 AGV 管理 / 先选中一台你创建的 AGV，才能在这里送修下线”，演示时显得多余。
- 已做修改：
  - `frontend/agv-frontend/src/components/JsonToolsPanel.vue`
    - “导入文本”按钮改为显式调用 `importTasksFromJson()`，避免 Vue 把 click event 当成 JSON 文本传入。
  - `frontend/agv-frontend/src/App.vue`
    - `importTasksFromJson` 增加防御：如果收到的不是字符串，回退使用文本框内的 `jsonText`。
  - `frontend/agv-frontend/src/components/DispatchControlSummaryPanel.vue`
    - 个人 AGV 管理卡片仅在已选中个人 AGV 时显示；未选车时不再显示重复提示。
- 已验证：
  - `frontend/agv-frontend` 下 `npm run lint` 通过。
  - `frontend/agv-frontend` 下 `npm run build` 通过。
- 后续人工复核建议：
  - 粘贴 `demo/json/task_manual_single_demo.json` 内容后点击“导入文本”，应成功导入并提示手动任务等待指定 AGV。
  - 个人端未选 AGV 时，右侧不再出现“个人 AGV 管理”空提示；选中 AGV 后再显示送修下线入口。

### 14.24 2026-04-20 追加：企业端反馈小铃铛位置微调
- 本轮修复企业端运行地图上的反馈 / 报错小铃铛位置问题：
  - 之前 `.feedback-fab` 使用 `bottom: 66px`，导致按钮悬在地图右下角上方一截。
  - 已改为 `bottom: 14px`，与地图右侧和底部内边距保持一致，更贴近地图右下角。
- 已修改：
  - `frontend/agv-frontend/src/assets/agv-map.css`
- 后续人工复核建议：
  - 企业端地图中，小铃铛应位于地图内部右下角，而不是右下角上方。

### 14.25 2026-04-20 追加：AI 素材地图方案请求失败修复
- 本轮修复用户使用 AI 素材时出现 `Map profile request failed` 的问题。
- 根因：
  - AI 素材默认以“当前地图方案”为输入源。
  - 当当前地图是运行时方案（例如 `runtime_10x8`，不是已保存/内置方案）时，前端仍请求 `/status/map/profile/runtime_10x8`。
  - 后端详情接口此前只支持内置方案和已保存自定义方案，因此返回找不到方案。
- 已做修改：
  - `frontend/agv-frontend/src/App.vue`
    - AI 素材构建地图方案输入时，如果目标 key 就是当前地图方案，且当前方案已经带有 `blocked_cells` / `valid_cells`，直接使用当前已加载数据，不再额外请求详情接口。
  - `backend/app/services/status_service.py`
    - `get_map_profile_detail` 在找不到内置/自定义方案时，会计算当前运行时地图方案；如果请求 key 与当前运行时方案 key 一致，则直接返回当前方案详情。
  - `frontend/agv-frontend/src/locales/zh.js`
  - `frontend/agv-frontend/src/locales/en.js`
  - `frontend/agv-frontend/src/locales/ja.js`
    - 补充地图方案未找到的本地化兜底文案。
- 已验证：
  - `frontend/agv-frontend` 下 `npm run lint` 通过。
  - `frontend/agv-frontend` 下 `npm run build` 通过。
  - `backend\\venv\\Scripts\\python.exe -m compileall backend\\app` 通过。
- 后续人工复核建议：
  - 在当前地图未保存为自定义方案时打开 AI 素材，选择“地图方案”输入并提交/加载源 JSON，不应再出现 `Map profile request failed`。

### 14.26 2026-04-22 追加：动态避让演示素材与设计说明
- 本轮不改调度核心逻辑，只补产品化演示和说明资产。
- 新增：
  - `demo/json/dynamic_avoidance_map_profile_12x8.json`
  - `demo/json/dynamic_avoidance_conflict_tasks.json`
  - `demo/json/dynamic_avoidance_split_map_profile_12x8.json`
  - `demo/json/dynamic_avoidance_split_tasks.json`
  - `docs/demo/DYNAMIC_AVOIDANCE_DEMO_RUNBOOK.md`
  - `docs/plans/DYNAMIC_AVOIDANCE_DESIGN_NOTE.md`
- 演示意图：
  - 12x8 地图中部设置主窄通道，上侧提供绕行支路，下侧提供服务支路。
  - 批量任务让高优先级车辆先走主通道，低优先级车辆跟随进入主通道并观察前车占用等待，第三台车走服务支路。
  - 用于观察同路不超车、对向相遇、等待、让行、重试和恢复，同时避免三车全部挤死在中心。
  - 2026-04-26 追加 `split` / `v2` 文件名，避免系统里旧版“动态避让窄通道演示地图”残留导致误用。
- 文档状态已同步：
  - `demo/json/README_demo_assets.md`
  - `docs/plans/POST_DEFENSE_PRODUCTIZATION_PLAN_2026-04-22.md`
  - `docs/plans/PLAN_INDEX_AND_OPEN_ITEMS_FOR_NEW_CHAT.md`
  - `docs/README.md`
- 后续建议：
  - 先人工导入并跑一遍动态避让演示包。
  - 如果效果稳定，下一步做前端等待 / 让行 / 重规划状态可视化。
  - 站级调度实体仍建议作为单独专题设计，不要和当前视觉聚合站点混在一起改。

### 14.27 2026-04-26 追加：个人端纯网格动态避让修复
- 背景：
  - 用户反馈 `dynamic_avoidance_split_tasks.json` 中车辆仍可能面对面卡住。
  - 已澄清个人端不应暴露或依赖企业路网拓扑；此前 v2 演示地图虽然在个人端使用，但 JSON 内仍带有 topology，容易造成后端按拓扑边规划。
- 本轮修复：
  - `backend/app/services/schedule_service.py`
    - 个人用户作用域下调度预览和初始路径规划强制使用纯网格路径，不再优先尝试 topology。
  - `backend/app/utils/agv_movement.py`
    - 个人用户作用域下运行时路径重算同样使用纯网格 A*。
    - 规划时把其它 AGV 的当前格、渲染格、运动源格、运动目标格加入临时障碍集合。
    - 运行时遇到同格占用或对向运动边段冲突时，先进入等待，再在短阈值后触发 `grid_dynamic_replan`，避免一直面对面僵住。
    - 保留企业端拓扑边占用、同廊道跟车和节点容量逻辑，不把个人端纯网格规则套到企业拓扑上。
  - `demo/json/dynamic_avoidance_split_map_profile_12x8.json`
    - 改为纯网格地图，只保留尺寸和障碍物，不再携带 topology。
  - `demo/json/dynamic_avoidance_split_tasks.json`
    - 更新说明文案，明确用于个人端纯网格 A* 动态避让。
  - `backend/scripts/runtime_conflict_smoke.py`
    - 增加个人端纯网格 head-on 对向交换烟测，检查不会同格、不会同运动边段，并确认触发动态重规划后完成。
- 已验证：
  - `backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_conflict_smoke.py`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_long_run_smoke.py`
  - `dynamic_avoidance_split_map_profile_12x8.json` / `dynamic_avoidance_split_tasks.json` JSON 解析
- 后续建议：
  - 在前端补充 `grid_dynamic_replan` / `cell_occupied_waiting` 的可读状态提示，例如“前方占用，正在重新规划”。
  - 如果还要继续强化，可做更完整的多车 reservation table 和集中式时间窗规划。

### 14.28 2026-04-26 追加：个人端真实让行格动态避让
- 背景：
  - 用户继续反馈个人端动态避让演示中仍可能面对面卡住。
  - 需要在“纯网格、一格一格走”的前提下，补上更接近真实调度的让行行为，而不是只等待或重规划。
- 本轮修复：
  - `backend/app/utils/agv_movement.py`
    - 新增个人端网格临时让行搜索，范围默认 4 格，单次让行路径最多 4 步。
    - 遇到同格占用或对向边段冲突时，优先级低或任务较晚的一方会尝试寻找附近安全空格，并走一步进入 `grid_dynamic_yield`。
    - 让行前仍检查运动边段锁和目标格占用，避免让行过程中穿车或进入其它 AGV 已占用位置。
    - 找不到让行格时保留原有 `grid_dynamic_replan` / 等待 / 超时重试兜底。
  - `backend/scripts/runtime_conflict_smoke.py`
    - 个人端 head-on smoke 从“必须看到 replan”升级为“必须看到动态避让，且本轮要求观测到 yield”。
    - 继续检查两车不同时占同一逻辑格、不同时使用同一无向运动边段，最后任务完成。
  - `docs/demo/DYNAMIC_AVOIDANCE_DEMO_RUNBOOK.md`
  - `demo/json/README_demo_assets.md`
    - 补充 `grid_dynamic_yield` 观察口径。
  - `frontend/agv-frontend/src/composables/useLocaleText.js`
    - 补充 `grid_dynamic_yield` / `grid_dynamic_replan` 的中英日可读调度说明，避免任务卡直接露出内部状态码。
- 已验证：
  - `backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_conflict_smoke.py`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_long_run_smoke.py`
  - `frontend/agv-frontend` 下 `npm run lint`
  - `frontend/agv-frontend` 下 `npm run build`
- 后续建议：
  - 前端可继续把 `grid_dynamic_yield` 显示成“前方占用，正在临时让行”，把 `grid_dynamic_replan` 显示成“前方占用，正在重新规划”。
  - 如果后续要进一步接近真实工业系统，可设计集中式时间窗 reservation table，提前按时间片预订格子和边段。

### 14.29 2026-04-27 追加：让行动作从“一步挪动”升级为“短路径退出冲突区”
- 背景：
  - 用户反馈现有 `grid_dynamic_yield` 虽然能看到避让动作，但经常只来回移动一格，没有真正让出可通行通道。
  - `dynamic_avoidance_split_tasks.json` 本身偏多车分流演示，不保证每次都制造正面对向会车。
- 本轮修复：
  - `backend/app/utils/agv_movement.py`
    - 让行候选格不再找到最近一格就停止，而是在搜索半径内综合选择更能离开冲突走廊的格子。
    - 候选评分优先选择离开当前冲突轴约 2 格的位置，再考虑路径长度、冲突距离和方向。
    - 执行让行时不再只走第一步，而是按离散网格逐步走完这段短让行路径；每一步仍做边段锁和目标格占用检查。
    - `grid_dynamic_yield` 调度说明增加 `step=x/y`，方便观察当前让行进度。
  - `backend/scripts/runtime_conflict_smoke.py`
    - 新增 `personal_grid_yield_path` 检查，确认有空间时让行目标会离开原冲突走廊至少 2 格。
  - `docs/demo/DYNAMIC_AVOIDANCE_DEMO_RUNBOOK.md`
  - `demo/json/README_demo_assets.md`
    - 补充 split 任务不是专门面对面压测；建议用 `(2,3)->(10,3)` 与 `(10,3)->(2,3)` 手动相向任务复核。
- 已验证：
  - `backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_conflict_smoke.py`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_long_run_smoke.py`
- 后续建议：
  - 如果三车交汇仍偶发僵持，下一步应上集中式时间窗 reservation table，而不是继续靠单车局部让行规则叠补丁。

### 14.30 2026-04-27 追加：企业端动态避让增强 v1
- 背景：
  - 用户确认个人端与企业端避让目标不同：个人端保持纯网格逐格行走；企业端继续基于拓扑节点、拓扑边、站点容量和运行状态做调度层避让。
  - 本轮不重写企业端核心调度，而是先按“验收基线 -> 可视化 -> 运行时预约”的顺序增强可测性与稳定性。
- 本轮新增：
  - `docs/plans/ENTERPRISE_DYNAMIC_AVOIDANCE_ENHANCEMENT_PLAN.md`
    - 记录企业端动态避让的目标、边界、接口兼容策略、测试场景和后续时间窗预约方向。
  - `demo/json/enterprise_topology_headon_map_profile_12x8.json`
  - `demo/json/enterprise_topology_headon_tasks.json`
  - `demo/json/enterprise_topology_intersection_map_profile_12x8.json`
  - `demo/json/enterprise_topology_intersection_tasks.json`
  - `demo/json/enterprise_topology_station_entry_map_profile_12x8.json`
  - `demo/json/enterprise_topology_station_entry_tasks.json`
    - 分别覆盖企业端单通道对向会车、十字交汇三车抢占、停车/充电站出入站冲突。
- 本轮修复：
  - `backend/app/utils/agv_movement.py`
    - 增加企业拓扑运行时内存预约表，先预约当前拓扑边和容量为 1 的目标节点。
    - 预约失败时返回更明确的冲突字段，包括 `conflict_type`、阻塞 AGV、目标节点和预约释放时间。
    - 运动完成、等待、取消、打断时统一释放拓扑边 claim 与运行时预约，避免残留占用。
  - `frontend/agv-frontend/src/composables/useLocaleText.js`
    - 增强 `topology_edge_waiting` / `topology_edge_reroute` 的中英日可读说明，区分交汇点预约、路段占用、同廊道跟车和重规划。
  - `backend/scripts/runtime_conflict_smoke.py`
    - 新增企业端 `enterprise_intersection` 与 `enterprise_station_entry` smoke，检查交汇点容量、站点入口冲突和最终恢复。
  - `demo/json/README_demo_assets.md`
    - 补充企业拓扑避让演示资产说明。
- 已验证：
  - 企业拓扑演示 JSON 均可解析。
  - `backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_conflict_smoke.py`
  - `backend\venv\Scripts\python.exe backend\scripts\runtime_long_run_smoke.py`
  - `frontend/agv-frontend` 下 `npm run lint`
  - `frontend/agv-frontend` 下 `npm run build`
- 后续建议：
  - 人工导入三套企业拓扑演示资产，开启“显示运行冲突原因”，观察等待、让行、重规划提示是否清楚。
  - 如果三车复杂交汇仍有僵持，再推进完整的未来多步时间窗预约表，而不是继续只靠当前边/节点瞬时预约。

### 14.31 2026-04-27 追加：企业端地图方案导入入口补齐
- 背景：
  - 用户反馈企业端找不到导入地图的位置。
  - 检查后确认普通 `MapSettingsPanel` 已有地图方案导入能力，但企业角色隐藏了普通页面设置齿轮；企业设置的“地图方案”页只有应用、预览、导出、删除，没有导入入口。
- 本轮修复：
  - `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
    - 在企业设置“地图方案”列表上方增加“导入地图方案”按钮。
    - 增加企业设置弹窗内部专用隐藏 file input，绑定现有 `onMapProfileFileChange`，避免依赖普通地图设置面板是否打开。
  - `frontend/agv-frontend/src/App.vue`
    - 将 `triggerMapProfileImport`、`mapProfileFileInputRef`、`onMapProfileFileChange` 传入企业设置弹窗。
- 人工复核建议：
  - 企业端打开“企业设置 -> 地图方案”，点击“导入地图方案”，选择 `demo/json/enterprise_topology_headon_map_profile_12x8.json`。
  - 导入成功后，应能在地图方案列表看到新方案，再点击“应用”切换地图。

### 14.32 2026-04-27 追加：企业端地图方案导入按钮位置优化
- 背景：
  - 用户测试企业端拓扑避让演示正常，但反馈“方案快照”下方单独出现“导入方案”按钮比较突兀。
- 本轮调整：
  - `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
    - 将“导入地图方案”移动到“方案快照”标题同行右侧，使其成为方案列表工具栏动作。
  - `frontend/agv-frontend/src/assets/agv-map.css`
    - 新增轻量标题栏布局样式，窄宽度下允许换行，避免标题和按钮互相挤压。
- 人工复核建议：
  - 企业端打开“企业设置 -> 地图方案”，确认“方案快照”右侧显示“导入方案”，按钮不再单独占一行。

### 14.33 2026-04-27 追加：企业端避让状态地图小标签
- 背景：
  - 企业端拓扑避让已能通过任务卡和 hover 查看原因，但演示时不够直观，难以一眼判断车辆是在等待路段、交汇预约、跟车还是重规划。
- 本轮修复：
  - `frontend/agv-frontend/src/App.vue`
    - 新增企业 AGV 避让短标签生成逻辑，复用现有 `motion_state`、`current_edge`、`dispatch_reason`，不改后端 API。
    - 在企业端 backend AGV 圆点上方显示短标签，受现有“显示等待/让行标签与原因”开关控制。
  - `frontend/agv-frontend/src/assets/agv-map.css`
    - 新增轻量工业风 badge 样式，区分交汇预约、安全跟车、等待路段、等待占用、让行和重规划。
  - `frontend/agv-frontend/src/locales/zh.js`
  - `frontend/agv-frontend/src/locales/en.js`
  - `frontend/agv-frontend/src/locales/ja.js`
    - 将设置项文案从“显示等待/让行原因”扩展为“显示等待/让行标签与原因”。
- 人工复核建议：
  - 企业端开启“显示等待/让行标签与原因”，导入对向会车、三车交汇和站点出入冲突演示任务，观察 AGV 上方出现短标签。
  - 关闭该开关后，地图短标签应消失，但 hover 详情、任务卡和 AGV 点击不受影响。

### 14.34 2026-04-27 追加：企业端避让演示助手
- 背景：
  - 用户已验证三套企业拓扑避让演示正常，但每次仍需手动导入地图、放置 AGV、导入任务，重复测试成本较高。
- 本轮修复：
  - `frontend/agv-frontend/src/config/enterpriseAvoidanceDemos.js`
    - 新增三套内置企业避让演示配置：对向会车、三车交汇、站点出入冲突。
  - `frontend/agv-frontend/src/App.vue`
    - 新增“载入演示”流程：保存/复用地图方案、应用地图、检查并补齐起点 AGV、导入配套任务并尝试调度。
    - 新增“定位起点”能力，用于在地图上高亮演示需要的起点坐标。
  - `frontend/agv-frontend/src/components/EnterpriseSettingsDialog.vue`
    - 在企业设置“地图方案”页增加“企业避让演示助手”区域。
  - `frontend/agv-frontend/src/assets/agv-map.css`
    - 补充演示助手卡片、状态提示和响应式布局样式。
  - `frontend/agv-frontend/src/locales/zh.js`
  - `frontend/agv-frontend/src/locales/en.js`
  - `frontend/agv-frontend/src/locales/ja.js`
    - 补充演示助手三语文案。
- 人工复核建议：
  - 企业端打开“企业设置 -> 地图方案 -> 企业避让演示助手”，分别点击三套演示的“载入演示”。
  - 载入后应自动切换地图、补齐起点 AGV、导入任务并尝试调度；若起点已有不可调度 AGV，应显示明确错误。

### 14.35 2026-04-28 追加：企业避让演示助手上岗与卡片布局修复
- 背景：
  - 用户测试时发现演示助手自动补车会出现“企业版新增 AGV 需要从站点、停车点或充电点上岗”。
  - 企业避让演示助手三张卡片在较窄弹窗宽度下出现文字/文件名溢出。
- 本轮修复：
  - `frontend/agv-frontend/src/config/enterpriseAvoidanceDemos.js`
    - 给演示起点补充 `nodeKey`，确保自动补车走企业端拓扑上岗点。
    - 将三套内置演示地图名称升级为 `v2`，避免复用旧的已保存方案导致仍按旧配置创建。
    - 将“站点出入冲突”第三台车起点从普通合流节点调整为停车点 `parking_b`，避免把 waypoint 当上岗点。
  - `frontend/agv-frontend/src/App.vue`
    - 演示助手补车时不再按 `{x, y}` 创建企业 AGV，而是解析特殊拓扑节点并按 `{point_id}` 创建。
    - 如果演示起点不是站点/停车点/充电点，前端先给出明确错误，避免落到后端通用错误。
  - `frontend/agv-frontend/src/assets/agv-map.css`
    - 企业演示卡片改为 `auto-fit` 自适应列宽，并让长文件名、中文提示、按钮区域自动换行。
  - `frontend/agv-frontend/src/locales/zh.js` / `en.js` / `ja.js`
    - 补充演示起点非法的三语提示。
- 人工复核建议：
  - 企业端打开“企业设置 -> 地图方案 -> 企业避让演示助手”，分别点击三张卡片“载入演示”。
  - 不应再出现“企业版新增 AGV 需要从站点、停车点或充电点上岗”。
  - 缩小企业设置弹窗或浏览器宽度时，三张演示卡片文字应留在卡片内部并自然换行。

### 14.36 2026-04-28 追加：企业避让演示验收收口
- 背景：
  - 用户确认企业避让演示助手三套场景人工测试通过。
  - 下一步目标不是继续扩大算法改动，而是把当前能力沉淀成可复测文档和自动检查。
- 本轮新增：
  - `docs/plans/ENTERPRISE_DYNAMIC_AVOIDANCE_ENHANCEMENT_PLAN.md`
    - 标记企业端拓扑避让、状态标签、演示助手和人工测试已完成。
    - 补充复测入口、后续方向和演示助手配置检查命令。
  - `docs/demo/ENTERPRISE_AVOIDANCE_DEMO_RUNBOOK.md`
    - 新增企业端避让演示助手复测说明，覆盖测试前准备、入口位置、三套场景预期、异常判断和回归建议。
  - `frontend/agv-frontend/scripts/enterprise-avoidance-demo-smoke.mjs`
    - 新增 Node smoke 检查，直接读取 `src/config/enterpriseAvoidanceDemos.js`。
    - 检查演示 key、地图/任务文件名、v2 方案名、拓扑节点/边、合法上岗节点、任务起终点和障碍冲突。
  - `frontend/agv-frontend/package.json`
    - 新增 `npm run smoke:enterprise-demos`。
  - `docs/README.md`
    - 更新 demo 分区说明，补充企业动态避让演示。
- 后续建议：
  - 若后续修改演示助手、企业拓扑演示或上岗节点，先跑 `npm run smoke:enterprise-demos`，再人工点击三张演示卡片。
  - 若继续改企业端调度算法，再配合后端 `runtime_conflict_smoke.py` 和 `runtime_long_run_smoke.py` 复测。
