# Contributing to AGV

感谢你愿意参与这个项目。当前主线面向 `v3.0.0` 企业试用版，优先处理安全、数据迁移、调度可靠性、自动化测试和可解释的运行状态。

## 开始之前

1. 先搜索现有 Issue，确认问题尚未被记录。
2. 对较大的功能或架构修改先创建 Issue，说明目标、边界和验收方式。
3. 不要提交真实企业数据、账号、密钥、数据库、日志、论文或个人答辩材料。
4. 提交贡献即表示你同意贡献内容继续按照仓库的 PolyForm Noncommercial License 1.0.0 发布。

## 本地检查

后端：

```powershell
python -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
backend\venv\Scripts\python.exe -m pytest backend\tests
backend\venv\Scripts\python.exe -m compileall -q backend\app backend\main.py
```

前端：

```powershell
cd frontend
npm ci
npm run lint
npm run build
npm run smoke:enterprise-demos
```

## 提交要求

- 一个提交只解决一个清晰问题，提交信息使用简短祈使句。
- 新行为必须补测试；修复缺陷时先补能复现问题的测试。
- API 变化必须同步 OpenAPI、兼容说明和前端调用层。
- 数据库结构变化必须使用 Alembic，不允许在 Repository 中加入临时 DDL。
- 旧 API 在 v4.0.0 前继续兼容，并返回弃用提示。

## Pull Request

PR 描述应包括：改了什么、为什么改、用户影响、验证方式、迁移或回滚注意事项。涉及界面的改动请附截图，涉及调度的改动请附可复现场景。
