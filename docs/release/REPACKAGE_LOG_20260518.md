# 2026-05-18 重新打包并整理记录

## 基本信息

- 打包时间：2026-05-18 22:59:17 +08:00
- 打包前提交：`8104f5d Refine algorithm compare readiness states`
- 执行流程文档：`重新打包并整理流程.md`

## 旧版本归档

旧封装目录已移动到：

```text
dist/旧版本/归档_20260518_2256/
```

归档内容：

```text
AGV_Dispatch_Package/
AGV_Dispatch_Package_beta/
AGV_Dispatch_Package_v2/
AGV_Enterprise_Client_v1/
```

## 最新版本目录

最新封装目录已整理到：

```text
dist/最新版本/AGV调度系统_综合版_20260518/
dist/最新版本/AGV企业端独立客户端_20260518/
```

## 构建命令

综合版：

```powershell
cmd /c build_windows_package.bat
```

企业端独立客户端：

```powershell
cmd /c build_enterprise_windows_package.bat
```

## 检查结果

综合版检查：

- `backend.exe` 存在。
- `start_agv.bat` 存在。
- `data/` 存在。
- `demo/` 存在。
- `demo/json/` 中包含动态避让、企业拓扑避让等演示资产。
- 目录大小约 `36.81 MB`。

企业端独立客户端检查：

- `backend.exe` 存在。
- `start_enterprise_client.bat` 存在。
- `data/` 存在。
- `docs/` 存在。
- `demo/` 存在。
- `demo/json/` 中包含动态避让、企业拓扑避让等演示资产。
- 目录大小约 `36.82 MB`。

## 未执行项

- 未自动双击启动 `.bat`，避免在当前开发会话中启动额外后台服务或浏览器窗口。
- 建议人工复核：
  - 双击 `dist/最新版本/AGV调度系统_综合版_20260518/start_agv.bat`。
  - 双击 `dist/最新版本/AGV企业端独立客户端_20260518/start_enterprise_client.bat`。
  - 确认浏览器打开、登录页加载、地图加载和企业设置入口可用。

## Git 说明

- `dist/` 已在 `.gitignore` 中，不提交封装成品。
- 本次建议只提交流程文档和封装记录。
