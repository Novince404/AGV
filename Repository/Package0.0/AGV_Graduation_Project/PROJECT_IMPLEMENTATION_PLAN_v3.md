# AGV 三端分流与企业平台路线任务书 v3

## Summary
- 根目录目标文档固定为：
  - `PROJECT_IMPLEMENTATION_PLAN_v3.md`
  - `PROJECT_IMPLEMENTATION_PLAN_v3.docx`
- 总实施顺序固定为 4 个阶段：
  1. 平台管理员企业审批页面
  2. `ComfyUI` 一期接入：`JSON -> 企业素材生成`
  3. 企业三岗位框架 + 企业设置弹窗
  4. 企业端第二代系统架构重构
- 当前版本明确不做：
  - 双车道
  - 不规则地图
  - 连续移动动画
  - 装卸停留仿真
  - 自动避让
  - 回仓/回充
  - 企业独立 EXE 客户端
- 这些全部延期到“企业端第二代系统架构重构”阶段。

## Key Changes
### 阶段 1：平台管理员企业审批页面
- 角色模型固定为：
  - `guest`
  - `personal`
  - `enterprise_operator`
  - `enterprise_logistics`
  - `enterprise_admin`
  - `platform_admin`
- 兼容迁移规则固定为：
  - 现有 `enterprise` 旧角色迁移为 `enterprise_admin`
  - 现有 `admin` 旧角色迁移为 `platform_admin`
- 平台管理员入口单独存在，不混入企业设置弹窗。
- 第一版平台管理员页面目标：
  - 查看企业注册申请列表
  - 查看申请详情
  - 审批通过
  - 驳回申请
  - 查看审批历史摘要
- 第一批后端接口固定为：
  - `POST /auth/register-enterprise`
  - `GET /auth/enterprise-applications`
  - `GET /auth/enterprise-applications/{id}`
  - `POST /auth/enterprise-applications/{id}/approve`
  - `POST /auth/enterprise-applications/{id}/reject`
- 企业申请状态固定为：
  - `pending`
  - `approved`
  - `rejected`
- 审批动作必须进入操作审计。

### 阶段 2：ComfyUI 一期接入
- 第一阶段 `ComfyUI` 用途固定为：`JSON -> 企业素材生成`
- 本期不做：
  - AI 直接回写点位库
  - AI 直接改业务数据库
  - AI 参与实时调度决策
- 输入源固定为当前系统可导出的业务 JSON，优先支持：
  - 地图方案 JSON
  - 点位/模板导出 JSON
  - 实验记录导出 JSON
  - 地图 profile 差异 JSON
- 输出目标固定为企业展示素材：
  - 场景图
  - 展示图
  - 功能性图片
- 第一版接入方式固定为“桥接层”：
  - 系统负责整理业务 JSON
  - 生成用于 `ComfyUI` 的标准化提示数据/工作流参数
  - 请求 `ComfyUI` 生成图片
  - 保存生成结果元数据与文件引用
- 第一版不要求把 `ComfyUI` 融入核心调度链。
- 新增企业素材相关模块：
  - 素材生成任务列表
  - 素材输入摘要
  - 生成结果预览
  - 失败重试
- 第一批接口固定为：
  - `POST /ai/comfyui/render`
  - `GET /ai/comfyui/jobs`
  - `GET /ai/comfyui/jobs/{id}`
  - `GET /ai/comfyui/assets`
- 企业素材生成只对企业角色和平台管理员开放，游客与个人默认不可见。

### 阶段 3：企业三岗位框架 + 企业设置弹窗
- 在 `ComfyUI` 一期接入完成后，先做企业三岗位框架，而不是直接进入企业大重构。
- 企业三岗位第一版固定为：
  - `enterprise_operator`
  - `enterprise_logistics`
  - `enterprise_admin`
- 第一版先做“框架差异”，不做深度功能分化：
  - 顶部标题差异
  - 默认展开面板差异
  - 只读/可操作面板差异
  - 企业设置弹窗左侧分栏差异
- 企业设置必须改为新的独立弹窗，不与平台管理员审批混合。
- 企业设置弹窗结构固定为：
  - 左侧分栏
  - 右侧内容区
- 第一版左侧分栏固定为：
  - 企业概览
  - 地图方案
  - 点位与模板
  - 运行规则
  - AI 素材
  - 审计与记录
- 三岗位第一版默认关注点固定为：
  - 操作工：调度与任务执行
  - 后勤岗：地图方案、点位模板、运行规则
  - 企业管理员：审计、设置、AI 素材、企业资料
- 第一版只做“整体框架与显示分流”，不引入双车道、不规则地图、连续移动。

### 阶段 4：企业端第二代系统架构重构
- 该阶段才进入真正的大工程。
- 本阶段范围固定包括：
  - 双车道路线模型
  - 不规则地图
  - AGV 连续移动
  - 装卸停留时长模拟
  - 优先级避让
  - 空闲让有任务
  - 返仓逻辑
  - 空闲超时回充
  - 企业独立 EXE 客户端
- 第二代系统架构开始前，前 3 阶段必须已经稳定：
  - 平台管理员审批
  - ComfyUI 素材生成
  - 企业三岗位框架
- 第二代阶段不与当前版本混做。

## Important Interfaces / Types
- 认证角色枚举固定为：
  - `guest`
  - `personal`
  - `enterprise_operator`
  - `enterprise_logistics`
  - `enterprise_admin`
  - `platform_admin`
- `GET /auth/me` 返回体必须包含：
  - `role`
  - `capabilities`
  - `capability_groups`
  - `account_status`
  - `organization_id`
  - `organization_name`
- 企业注册申请实体固定字段：
  - `id`
  - `company_name`
  - `contact_name`
  - `contact_email`
  - `username`
  - `status`
  - `submitted_at`
  - `reviewed_at`
  - `reviewed_by`
  - `review_note`
- `ComfyUI` 一期生成任务实体固定字段：
  - `id`
  - `source_type`
  - `source_ref`
  - `input_summary`
  - `workflow_payload`
  - `status`
  - `created_by`
  - `created_at`
  - `completed_at`
  - `asset_urls`
  - `error_message`
- 企业设置弹窗状态第一版固定包含：
  - `isOpen`
  - `activeTab`
  - `enterpriseProfile`
  - `mapProfileSettings`
  - `pointTemplateSettings`
  - `runtimeRuleSettings`
  - `aiAssetSettings`
  - `auditSettings`

## Test Plan
- 平台管理员审批：
  - 平台管理员可查看申请列表
  - 可审批/驳回
  - 企业申请状态变更正确
  - 审批动作写入审计
- `ComfyUI` 一期：
  - 可从业务 JSON 发起素材生成
  - 生成任务可查看状态
  - 成功后可看到素材结果
  - 失败后可看到错误信息
  - 不会回写业务数据库核心表
- 企业三岗位框架：
  - 三岗位标题正确
  - 默认展开面板符合岗位定位
  - 企业设置弹窗左侧分栏正常切换
  - AI 素材页只在企业角色和平台管理员下可见
- 兼容性：
  - 旧 `enterprise` / `admin` 账号迁移后仍可登录
  - 现有个人模式与游客模式不被破坏
- 权限一致性：
  - 前端禁用与后端拒绝保持一致
  - 无权限用户不能调用审批和素材生成接口

## Assumptions
- 本计划文件版本固定为 `v3`，不覆盖旧的 `v2.0` 计划。
- 平台管理员审批页面优先级高于企业端重构。
- `ComfyUI` 一期明确只做素材生成桥接，不参与实时调度与数据库业务写回。
- 企业三岗位第一版只做显示框架与权限骨架，不做重型仿真能力。
- 企业第二代系统架构的高风险能力统一后置，不在本轮近期实施范围。
