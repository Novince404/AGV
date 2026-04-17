# AGV Graduation Project Session Handoff

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
