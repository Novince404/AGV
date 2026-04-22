# AGV Dispatch Graduation Project

这是一个 AGV 调度平台，包含个人端、企业端、平台治理、地图配置、任务调度、路径规划、数据库持久化和 ComfyUI 素材生成能力。项目已通过毕业设计答辩，当前主线转向产品化收口和系统设计增强。

## 常用入口

- 个人端演示：双击 `start_agv.bat`。
- 企业独立客户端演示：双击 `start_enterprise_client.bat`。
- MySQL 开发模式：双击 `run_mysql_dev.bat`。
- Windows 打包：运行 `build_windows_package.bat` 或 `build_enterprise_windows_package.bat`。

## 目录导航

- `backend/`：FastAPI 后端、调度服务、路径规划、数据库 Repository、ComfyUI 对接。
- `frontend/agv-frontend/`：Vue 前端、地图交互、任务面板、企业设置、AI 素材工作台。
- `enterprise_client/`：企业独立客户端说明和验收文档。
- `demo/`：随包演示素材，包括地图、障碍物、任务 JSON 和演示说明。
- `docs/defense/`：中期答辩和系统讲解资料，优先阅读这里。
- `docs/plans/`：阶段计划、接口冻结和历史规划文档。
- `docs/acceptance/`：验收清单、人工验证和交付基线记录。
- `docs/demo/`：演示脚本、快速启动和故障排查说明。
- `docs/release/`：打包、发布和版本策略材料。
- `tools/windows/`：不常用的开发、检查、SQLite 和类封装启动脚本。

## 当前产品化主线

1. `docs/plans/POST_DEFENSE_PRODUCTIZATION_PLAN_2026-04-22.md`
2. `docs/acceptance/PHASE4_ACCEPTANCE_EXECUTION_PLAN_v1.md`
3. `enterprise_client/docs/PHASE4_ENTERPRISE_ACCEPTANCE_CHECKLIST.md`

## 答辩阅读顺序

1. `docs/defense/README.md`
2. `docs/defense/CODE_STRUCTURE.md`
3. `docs/defense/DISPATCH_AND_ALGORITHMS.md`
4. `docs/defense/DATABASE_FLOW.md`
5. `docs/defense/COMFYUI_FLOW.md`
6. `docs/defense/HIGHLIGHTS_AND_QA.md`

## Git 约定

- 远端：`AGV`
- 主分支：`main`
- 默认推送：`git -C "Repository/Package0.0/AGV_Graduation_Project" push AGV main`
- 不使用交互式 git，不随意 amend，不使用 `reset --hard` 或 `checkout --` 回滚用户改动。
