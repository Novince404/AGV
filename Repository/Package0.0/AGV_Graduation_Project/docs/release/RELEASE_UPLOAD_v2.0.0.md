# v2.0.0 上传说明

这份说明用于把当前 `main` 分支上的 `v2.0.0` 内容整理成 GitHub Release。

## 当前建议发布信息

- Tag：`v2.0.0`
- Target：`main`
- Release title：`v2.0.0 - Minimum Deliverable Stable Release`

Release 正文直接使用：

- `Repository/Package0.0/AGV_Graduation_Project/RELEASE_DRAFT_v2.0.0.md`

## 上传前确认

建议先确认以下两点：

1. 当前主分支已经包含这次正式版提交。
2. Windows 封装产物已经重新构建完成。

## 如果还没有创建 tag

在项目根目录执行：

```bash
git -C Repository/Package0.0/AGV_Graduation_Project tag v2.0.0
git -C Repository/Package0.0/AGV_Graduation_Project push AGV v2.0.0
```

## GitHub 页面操作步骤

1. 打开仓库 Releases 页面。
2. 点击 `Draft a new release`。
3. 选择或填写：
   - Tag：`v2.0.0`
   - Target：`main`
4. 在标题中填写：

```text
v2.0.0 - Minimum Deliverable Stable Release
```

5. 将以下文件内容完整复制到正文：
   - `Repository/Package0.0/AGV_Graduation_Project/RELEASE_DRAFT_v2.0.0.md`
6. 如果你想上传 Windows 封装产物，可以附上：
   - `dist/AGV_Dispatch_Package`
7. 根据需要选择：
   - 先点 `Save draft`
   - 或直接点 `Publish release`

## 建议发布后自查

发布完成后建议确认：

1. Release 页能看到 `v2.0.0`
2. Tag 已正确关联到 `main`
3. `v2.0.0-beta.1` 仍作为历史 beta 版本保留
4. 正文中的稳定版说明与当前代码、封装产物一致
