# GitHub 上传与发布流程

本文档用于记录本项目后续统一使用的 GitHub 提交流程，尽量保证：
- 上传前有基本检查
- 版本号和变更记录同步
- 分支、PR、合并、清理步骤清晰

当前仓库远程名称：
- `AGV`

当前推荐主分支：
- `main`

## 1. 开发前准备

每次开始新功能前，先切回主分支并更新：

```bash
git -C . checkout main
git -C . pull AGV main
```

然后新建功能分支：

```bash
git -C . checkout -b feature/功能名
```

示例：

```bash
git -C . checkout -b feature/mysql-repository
git -C . checkout -b fix/auto-dispatch-marker
git -C . checkout -b docs/a3-freeze-update
```

## 2. 开发完成后的本地检查

### 前端检查

```bash
cd frontend
npm run lint
```

### 后端基础编译检查

```bash
cd .
backend\venv\Scripts\python.exe -m py_compile backend\main.py
```

如果本次改动范围较大，可以补充检查关键文件：

```bash
backend\venv\Scripts\python.exe -m py_compile backend\app\services\schedule_service.py backend\app\services\task_service.py backend\app\services\agv_service.py
```

## 3. 上传前检查改动范围

先看当前修改了什么：

```bash
git -C . status
git -C . diff --stat
```

如果发现有不该提交的文件，例如：
- `__pycache__`
- 临时日志
- 本地测试输出

先处理干净，再上传。

## 4. 版本号与变更记录

准备正式上传时，优先同步以下两个文件：

### 版本号

文件：
- `frontend/package.json`

推荐规则：
- 修 bug：`1.5.0 -> 1.5.1`
- 小功能阶段：`1.5.0 -> 1.6.0`
- 里程碑版本：按阶段需要提升次版本

### 变更记录

文件：
- `CHANGELOG.md`

建议至少写三类：
- `Added`
- `Improved`
- `Fixed`

记录时保持真实，不把计划中的内容写成已完成。

## 5. 提交代码

统一流程：

```bash
git -C . add .
git -C . commit -m "提交说明"
```

推荐提交信息格式：
- `feat: add mysql repository scaffold`
- `fix: correct auto task schedule mode`
- `refactor: split task display logic from App.vue`
- `docs: update A3 interface freeze`
- `release:v1.5.0`

## 6. 推送到 GitHub

将当前功能分支推送到远程：

```bash
git -C . push AGV 当前分支名
```

示例：

```bash
git -C . push AGV feature/mysql-repository
```

## 7. 创建 Pull Request

推送成功后，GitHub 通常会给出 PR 链接。

PR 标题建议简洁明确，例如：
- `A3: repository layering and SQL preparation`
- `Fix auto/manual schedule mode consistency`
- `Refactor App.vue display state`

PR 描述建议包含：
- 本次做了什么
- 是否改动接口
- 是否影响前端行为
- 已做哪些检查

## 8. PR 合并后的操作

如果 GitHub 提示：

`Pull request successfully merged and closed`

表示：
- 代码已经成功合并到目标分支
- 当前 PR 已完成并自动关闭

这不是报错，而是成功提示。

合并后建议本地执行：

```bash
git -C . checkout main
git -C . pull AGV main
git -C . branch -d 已合并分支名
```

示例：

```bash
git -C . checkout main
git -C . pull AGV main
git -C . branch -d feature/a3-backend-layering
```

如果远程分支没有自动删除，也可以手动删：

```bash
git -C . push AGV --delete feature/a3-backend-layering
```

## 9. 下次上传时的默认执行清单

以后执行“上传 GitHub”时，默认按以下顺序处理：

1. 检查 `git status`
2. 整理本次改动摘要
3. 判断是否需要更新版本号
4. 更新 `CHANGELOG.md`
5. 跑基础检查
6. 本地提交
7. 推送到 GitHub
8. 给出 PR 链接或后续合并建议

## 10. 适合毕业设计项目的建议

本项目推荐保持以下习惯：
- 一个相对完整的小阶段再上传一次
- 每次上传都写简洁但真实的 changelog
- 重大阶段版本配合论文、周报、导师汇报同步整理
- 不要把临时测试文件和缓存文件提交到正式版本

## 11. 当前阶段建议

当前项目正处于 A3 结构整理阶段，后续上传时优先关注：
- 后端分层是否保持兼容
- MySQL 接入准备是否影响现有功能
- 前端 `App.vue` 拆分后是否保持行为一致
- 自动/手动调度显示逻辑是否回归正常
