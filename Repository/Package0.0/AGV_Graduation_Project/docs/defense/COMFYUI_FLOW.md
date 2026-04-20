# ComfyUI 渲染链路

## 功能定位

ComfyUI 模块用于把地图方案、点位模板、实验记录或自定义 JSON 转成可视化素材。它不是调度核心算法的一部分，而是展示和汇报增强能力。

## 前端入口

前端入口在 AI 素材工作台：

- 主状态和提交逻辑在 `frontend/agv-frontend/src/App.vue`。
- 交互组件在 `frontend/agv-frontend/src/components/ComfyAiWorkspace.vue`。
- 内置工作流模板在 `frontend/agv-frontend/src/utils/comfyWorkflowTemplates.js`。

用户可以选择素材来源、工作流预设、提示词风格、Checkpoint 和模板，然后提交渲染。

## 后端接口

后端接口集中在 `backend/app/api/ai_api.py`，主要路径是：

- `POST /ai/comfyui/render`：提交渲染任务。
- `GET /ai/comfyui/jobs`：读取渲染任务列表。
- `GET /ai/comfyui/jobs/{job_id}`：读取并刷新单个任务。
- `GET /ai/comfyui/assets`：读取可用图片资产。
- `GET /ai/comfyui/templates`：读取共享工作流模板。

## 服务层流程

`backend/app/services/comfyui_service.py` 负责真实调用：

1. 校验 `AGV_COMFYUI_ENABLED` 是否开启。
2. 根据前端输入创建 `ComfyRenderJob`。
3. 组装 ComfyUI prompt payload。
4. 请求 ComfyUI 的 `/prompt` 接口。
5. 保存返回的 `prompt_id`。
6. 后续通过 `/history/{prompt_id}` 轮询结果。
7. 从 history 输出中提取图片文件名、子目录和类型。
8. 生成 `/view?...` 图片地址并返回给前端。

## 数据库存储

渲染任务和模板会进入数据库：

- `comfy_render_job`：保存任务状态、输入摘要、提示词、workflow、`prompt_id`、图片 URL、错误信息。
- `comfy_workflow_template`：保存共享工作流模板，便于企业端复用。

SQL 实现在 `backend/app/repositories/sql/comfy_job_store.py` 和 `backend/app/repositories/sql/comfy_template_store.py`。

## 失败处理

如果 ComfyUI 未开启、连接失败、返回格式异常或 history 查询失败，后端会给出明确错误状态。这样前端不会静默失败，用户能看到是配置问题、服务不可达还是渲染任务仍在等待。

## 答辩口径

可以把它讲成“调度系统的可视化扩展”：核心调度结果本身来自系统数据，ComfyUI 只是把地图、点位和实验记录转成更适合汇报和展示的视觉素材。
