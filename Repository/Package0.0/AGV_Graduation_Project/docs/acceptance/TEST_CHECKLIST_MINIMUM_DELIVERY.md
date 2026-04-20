# 最低可交付版测试清单

最后更新：2026-03-18

## 使用说明
- 本清单用于模块 3 的交付收口测试。
- 每次准备演示、发布 beta、或生成封装包后，建议至少跑一遍。
- 如果要执行完整人工终验，请配合：
  - `MANUAL_VERIFICATION_RUNBOOK_v2.0.md`
  - `MANUAL_VERIFICATION_RECORD_v2.0.md`

## 一、启动与环境
- [ ] `tools\windows\run_dev.bat` 可正常启动
- [ ] `tools\windows\run_sqlite_dev.bat` 可正常启动
- [ ] `tools\windows\run_packaged_dev.bat` 可正常启动
- [ ] `tools\windows\run_mysql_check.bat` 在 MySQL 配置正确时可通过
- [ ] `build_windows_package.bat` 可成功产出 `dist/AGV_Dispatch_Package`
- [ ] `dist/AGV_Dispatch_Package/start_agv.bat` 可打开系统

## 二、基础页面与接口
- [ ] 前端页面正常打开
- [ ] `GET /status/ui-settings` 正常
- [ ] `GET /status/map` 正常
- [ ] `GET /point/list` 正常
- [ ] `GET /template/list` 正常

## 三、调度主流程
- [ ] 自动单段任务可创建并完成
- [ ] 手动单段任务可创建并完成
- [ ] 自动多段任务可创建并跨阶段完成
- [ ] 自动多段任务运行中再次点击地图新建任务时，首点显示正常

## 四、异常处理
- [ ] 急停后任务可中断
- [ ] 恢复后任务可继续
- [ ] 故障上报可成功
- [ ] 故障解除可成功
- [ ] 送修下线后车辆不可继续执行
- [ ] 恢复上线后车辆可重新参与调度

## 五、地图与设置
- [ ] 障碍编辑可保存
- [ ] 障碍预设可保存
- [ ] 障碍预设可应用
- [ ] 障碍预设可删除
- [ ] 导入布局后可另存为预设
- [ ] 恢复默认布局正常
- [ ] 地图信息区显示正常
- [ ] 小地图、图例、箭头、图标设置刷新后仍保留

## 六、点位与模板
- [ ] 自定义点位可新增
- [ ] 自定义点位刷新后仍保留
- [ ] 自定义点位可删除
- [ ] 模板可保存
- [ ] 模板刷新后仍保留
- [ ] 模板可删除
- [ ] 模板 JSON 导入正常
- [ ] 模板 JSON 导出正常

## 七、任务队列管理
- [ ] 单任务删除正常
- [ ] 运行中任务删除前有明确确认
- [ ] 异常任务可筛选
- [ ] 异常任务可批量清理
- [ ] 已完成任务可批量导出
- [ ] 已完成任务可批量删除

## 八、多语言
- [ ] 中文文案正常
- [ ] 英文文案正常
- [ ] 日文文案正常
- [ ] 最近新增按钮与提示无缺失翻译

## 九、数据库模式

### SQLite
- [ ] `tools\windows\run_sqlite_smoke.bat` 通过
- [ ] 刷新后点位、模板、障碍预设仍保留

### MySQL
- [ ] `tools\windows\run_mysql_check.bat` 通过
- [ ] MySQL 模式下自动 / 手动 / 多段任务正常

## 十、封装试运行
- [ ] `backend.exe` 可启动
- [ ] 封装模式根路径返回前端页面
- [ ] 封装模式 API 可访问
- [ ] 封装模式 SQLite 数据目录正常生成

## 结果记录建议
- 本次测试日期：
- 测试模式：`dev / sqlite / mysql / packaged`
- 是否通过：
- 发现问题：
- 修复后回归结果：
