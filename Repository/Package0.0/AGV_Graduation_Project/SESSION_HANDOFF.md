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
