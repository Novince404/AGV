# v1.6.0 上传说明

这份说明用于把当前 `main` 分支上的 `v1.6.0` 内容整理成 GitHub Release。

## 当前建议发布信息

- Tag：`v1.6.0`
- Target：`main`
- Release title：`v1.6.0 - A3 Persistence Foundation and SQLite Validation Update`

Release 正文直接使用：

- `RELEASE_DRAFT_v1.6.0.md`

## 上传前确认

建议先确认以下两点：

1. 当前主分支已经包含这次版本提交：
   - `8f7aa27 release:v1.6.0`
2. 工作区没有未提交的重要改动。

## 如果还没有创建 tag

在项目根目录执行：

```bash
git -C . tag v1.6.0
git -C . push AGV v1.6.0
```

## GitHub 页面操作步骤

1. 打开仓库 Releases 页面。
2. 点击 `Draft a new release`。
3. 选择或填写：
   - Tag：`v1.6.0`
   - Target：`main`
4. 在标题中填写：

```text
v1.6.0 - A3 Persistence Foundation and SQLite Validation Update
```

5. 将以下文件内容完整复制到正文：
   - `RELEASE_DRAFT_v1.6.0.md`
6. 这次版本默认不需要上传桌面安装包附件。
7. 根据需要选择：
   - 先点 `Save draft`
   - 或直接点 `Publish release`

## 建议发布后自查

发布完成后建议确认：

1. Release 页能看到 `v1.6.0`
2. Tag 已正确关联到 `main`
3. 文案中的新增内容与当前代码一致
4. 若后续继续推进 A3，可在下一轮版本中继续补 MySQL 真实接入说明
