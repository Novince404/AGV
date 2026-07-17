# v3.0.0-beta.1 发布说明

这份说明用于把产品化主线整理为 GitHub 预发布版本，旧的 `v2.0.0` 稳定标签保持不变。

## 发布字段

- Tag：`v3.0.0-beta.1`
- Target：版本 PR 合并后的 `main` 提交
- Release title：`v3.0.0-beta.1 - Productization and Enterprise Architecture Preview`
- Release type：Prerelease
- Release 正文：`docs/release/RELEASE_DRAFT_v3.0.0-beta.1.md`

## 发布前检查

1. `frontend/package.json` 与 `package-lock.json` 的项目版本均为 `3.0.0-beta.1`。
2. `CHANGELOG.md` 已把本阶段内容从 `Unreleased` 收口到 `v3.0.0-beta.1 - 2026-07-17`。
3. 根目录中英文 README 已指向 `v3.0.0-beta.1` 预发布页。
4. 后端编译、SQLite 冒烟测试、前端 ESLint、生产构建和企业避让演示测试通过。
5. `main` 已包含完整许可证与非商业使用说明。
6. GitHub 上不存在同名旧标签或 Release。

## 推荐发布命令

在版本 PR 合并并确认 `main` 后执行：

```powershell
gh release create v3.0.0-beta.1 `
  --repo Novince404/AGV `
  --target main `
  --title "v3.0.0-beta.1 - Productization and Enterprise Architecture Preview" `
  --notes-file "docs/release/RELEASE_DRAFT_v3.0.0-beta.1.md" `
  --prerelease
```

如果先单独创建标签，标签必须指向版本 PR 的最终合并提交，不得指向合并前的功能分支。

## 发布后核验

1. Releases 页面显示 `v3.0.0-beta.1`，并带有 `Pre-release` 标识。
2. 标签提交与发布完成时的 `main` 完全一致。
3. Release 正文完整展示 Highlights、Validation、兼容性说明和许可证边界。
4. `v2.0.0` 仍保留为稳定版本，没有被移动或覆盖。
5. 仓库首页的版本链接能够打开新的预发布页面。

## 附件策略

本次默认发布源码与文档，不强制上传预构建 EXE。若后续上传 Windows 包，必须先按 `PACKAGING_WINDOWS.md` 重新构建并完成对应的启动与数据库回归。
