# v2.0.0-beta.1 上传说明

这份说明用于把当前 `main` 分支上的 `v2.0.0-beta.1` 内容整理成 GitHub Release。

## 当前建议发布信息

- Tag：`v2.0.0-beta.1`
- Target：`main`
- Release title：`v2.0.0-beta.1 - Database Integration Beta and A3 Persistence Upgrade`

Release 正文直接使用：

- `Repository/Package0.0/AGV_Graduation_Project/RELEASE_DRAFT_v2.0.0-beta.1.md`

## 上传前确认

建议先确认以下两点：

1. 当前主分支已经包含这次版本提交：
   - `6ed9933 release:v2.0.0-beta.1`
2. 工作区没有未提交的重要改动。

## 如果还没有创建 tag

在项目根目录执行：

```bash
git -C Repository/Package0.0/AGV_Graduation_Project tag v2.0.0-beta.1
git -C Repository/Package0.0/AGV_Graduation_Project push AGV v2.0.0-beta.1
```

## GitHub 页面操作步骤

1. 打开仓库 Releases 页面。
2. 点击 `Draft a new release`。
3. 选择或填写：
   - Tag：`v2.0.0-beta.1`
   - Target：`main`
4. 在标题中填写：

```text
v2.0.0-beta.1 - Database Integration Beta and A3 Persistence Upgrade
```

5. 将以下文件内容完整复制到正文：
   - `Repository/Package0.0/AGV_Graduation_Project/RELEASE_DRAFT_v2.0.0-beta.1.md`
6. 这次版本默认不需要上传桌面安装包附件。
7. 根据需要选择：
   - 先点 `Save draft`
   - 或直接点 `Publish release`

## 建议发布后自查

发布完成后建议确认：

1. Release 页能看到 `v2.0.0-beta.1`
2. Tag 已正确关联到 `main`
3. 文案中的数据库接入说明与当前代码一致
4. SQLite / MySQL 启动与检查脚本名称无误
5. 后续正式版 `v2.0.0` 时再根据联调结果决定是否去掉 beta 标记
