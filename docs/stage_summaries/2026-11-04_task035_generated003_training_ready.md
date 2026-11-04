# 2026-11-04｜035数据恢复完成，进入正式混训

用户已完成003：73/73来源处理=100%、技术错误0。新增normal73/73合格=100%；新增10实际尝试220，合格215/220=97.73%，失败5（完整任务/释放3、释放确认2）。新执行293次合格288=98.29%；零重放复用002旧8条，合并审计301、合格296，normal75/10轨迹221。生成合格率不是模型SR，也不是296条独立父示范。

| 四池 | 轨迹 | 窗口 | 父示范组 |
|---|---:|---:|---:|
| train10 | 161 | 22640 | 54 |
| train normal | 55 | 14570 | 55 |
| dev10 | 60 | 8044 | 20 |
| dev normal | 20 | 5332 | 20 |

四池非空、training_ready=true；原53/20分组与两个旧train父来源保持，未知物理祖源不冒称完全独立。训练覆盖6/9任务，stove/mug_pudding/two_pots本批缺样本，仍按原九任务正式评测，不为补齐覆盖继续采集，也不提前假设其性能保持。

[R6数据审查](../../collaboration/reviews/035_round6.md)批准进入原定一组1000更新7:3动作损失混训，不追加MVP、GPU试训或原始模型评测。R5软件验收保持、生成代码无返修；训练与新模型eval此时0。底座/视觉/action head/proprio冻结，仅语言attention LoRA更新，固定末1000权重用于正式10/00各90，原24.44%/86.67%基线不重跑。

实际命令准备发现旧external/openvla-oft有历史Python改动，会被现有训练loader拒绝。已保留旧目录，另以本地Git对象创建独立干净副本external/openvla-oft-task035-e4287e94，仍同一e4287e94 commit，无网络拉取、无包升级。只读diff/AST证实修改集中在视频驱动/旧路径附加及未使用finetune脚本，实际模型加载/观测准备函数未变，其余推理helper字节相同；源hash差异据实记录。训练权重/统计/头与配方不变，后续eval也使用该干净副本，保留旧runtime/基线。

原003 recovery_report SHA `1ef486a9e6fda9337bfb28c3d18922d3fc5eef3f35e200a4a665df3ef751ced7`；export/report SHA `eb5ceb2b937a22d942d2103263f93ab50e4cdc4cf1aa2462a5024946d0aa2da4`；本地已取回并核验。未加载VLA、执行训练或新增仿真。

**下一执行者用户：按[完整混训命令](../experiment_plans/2026-11-04_task035_mixed_training_commands.md)启动训练**。X可并行已有非阻断评测实时SR/去重复读任务，不卡训练；Codex在用户交回训练产物后审查并给同adapter正式评测命令。不自动merge/清理，待删=[]；本总结提交GitHub并按来源commit/SHA备份本地。
