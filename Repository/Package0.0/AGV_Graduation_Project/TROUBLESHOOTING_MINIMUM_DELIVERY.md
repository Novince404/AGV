# 最低可交付版常见故障排查

最后更新：2026-03-18

## 1. 前端打不开 / 白屏

### 现象
- 浏览器页面打不开
- 控制台报 Vite 或资源加载错误

### 优先检查
1. 前端是否正常启动
2. 后端是否正常启动
3. 当前使用的是哪种模式：
   - `run_dev.bat`
   - `run_sqlite_dev.bat`
   - `run_packaged_dev.bat`
   - `start_agv.bat`

### 常见处理
- 开发模式下：
  - 重启前端 `npm run dev`
- 封装模式下：
  - 先重新执行 `build_frontend_dist.bat`
  - 再运行 `run_packaged_dev.bat`

## 2. MySQL 检查失败

### 现象
- `run_mysql_check.bat` 输出 `MYSQL_CONFIG_FAILED`

### 常见原因
- 用户名或密码不对
- MySQL 服务没启动
- `cryptography` 未安装
- `AGV_DATABASE_URL` 配错

### 处理步骤
1. 检查 `backend/.env`
2. 确认 MySQL 服务正在运行
3. 重新执行：

```bat
run_mysql_check.bat
```

4. 如果提示缺依赖，确保后端虚拟环境已安装：

```bat
backend\venv\Scripts\python.exe -m pip install cryptography
```

## 3. SQLite 冒烟检查失败

### 现象
- `run_sqlite_smoke.bat` 未输出 `SQLITE_SMOKE_OK point/template/map`

### 处理步骤
1. 确认后端虚拟环境完整
2. 再执行一次：

```bat
run_sqlite_smoke.bat
```

3. 查看报错集中在哪一类：
- point
- template
- map

## 4. 前端构建失败，报 `spawn EPERM`

### 现象
- `npm run build` 或 `build_windows_package.bat` 中，Vite 构建失败
- 报 `spawn EPERM`

### 说明
- 这通常不是项目代码逻辑错误，而是当前环境对子进程执行有限制

### 建议处理
1. 关闭占用构建相关文件的程序
2. 重新运行构建
3. 如果在受限终端里失败，可换正常终端重试

## 5. 任务卡出现“已分配但 AGV: 无”

### 现象
- 任务状态显示 `已分配`
- 但 AGV 显示 `无`

### 当前处理方式
- 可通过任务删除或异常任务清理入口清掉
- 若频繁出现，需要重点回归：
  - MySQL 状态写入
  - 调度持久化

## 6. 自动多段任务运行中，再点地图新建任务首点异常

### 现象
- 第一下点击起点闪一下消失
- 需要快速点两下才能创建

### 当前结论
- 这类问题通常属于前端草稿显示与运行中任务显示的优先级冲突

### 建议处理
- 先回归最近一次相关修复
- 再检查 `App.vue` 中草稿显示与轮询刷新逻辑

## 7. 封装包启动后打不开页面

### 检查顺序
1. `dist/AGV_Dispatch_Package/backend.exe` 是否存在
2. `dist/AGV_Dispatch_Package/start_agv.bat` 是否存在
3. `frontend_dist` 是否已打进包
4. 端口是否被占用

### 可用替代方案
- 先用：

```bat
run_packaged_dev.bat
```

确认“后端托管 dist”模式是通的，再回头看打包。

## 8. 如何快速判断是前端问题还是后端问题

### 更像前端问题
- 只有显示错
- 数据刷新后仍正常
- API 返回正常

### 更像后端问题
- docs 接口就报错
- 数据库连不上
- 任务状态与 AGV 状态不一致

## 9. 遇到问题时优先保留什么信息
- 启动脚本名称
- 当前模式：
  - memory
  - sqlite
  - mysql
  - packaged
- 后端最后几行日志
- 前端控制台最后几行日志
- 是否能稳定复现
