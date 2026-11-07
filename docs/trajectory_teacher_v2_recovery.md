# 035教师v2：复用8条、仅重建批准73来源

本入口执行[已批准工单](../collaboration/tasks/035_teacher_v2_recovery.md)。旧002实际合格2normal＋6个10共8条，全是两个train父来源；其余候选没有RGB训练HDF，不能通过改JSON变成成功。本轮软件只增加版本化教师资格与有界恢复，不修改正式评分、原划分或7:3/1000更新训练配方。

## 策略与输入

旧入口默认 `strict-event-unknown-v1`；恢复入口显式选 `table-drop-unknown-diagnostic-v2`。v2仅将table_drop未知放入diagnostics，原None/core事实不变。任意确认违规（含table_drop）、wrong_grasp/wrong_placement未知、完整任务/释放五观测确认、A保护及H520等均保留。新资格、metadata与lineage记录版本及诊断事件；这不进入模型输入。

[配置模板](../configs/trajectory_augmentation/recover_teacher_v2.example.json)只有format、evidence和path_roots。evidence必须与仓库[已批准refs](../collaboration/tasks/035_teacher_v2_recovery_refs.json)一致，不能换73清单或旧8条。它绑定原180 seeds、原generation config、旧报告/候选分析、候选qualification/metadata、旧8条sources/HDF/audit/qualification/lineage/journal字节。

`plan`读取JSON和文件SHA/大小，不打开HDF内容、不创建NativeSession/渲染/模型。先通过原 `cli.build_plan` 验证完整180、原自然前20及父分组，再选固定73（53train/20dev）。验证候选仅因table_drop未知拒绝且确认streak≥5；引用不一致直接失败，不选替代来源。旧8来自两个train父源且与73不相交。

`path_roots`仅为证据/legacy文件提供前缀重定位；**原generation config内部的manifest、数据、统计、解释器、core和native路径须在部署机仍有效**，不会偷偷重写原执行config。当前生产在原服务器复用已有路径，通常留空。若将配置模板复制到其他目录，要把evidence改为仓库refs的绝对路径。不要编辑refs来迁就缺失文件。

## 运行与输出

本实现复用原OFT/native环境与原版本锁，依赖不升级。Codex在新的隔离方法目录部署并绑定路径；原001/002输出与冻结方法目录保留。以下占位路径由Codex替换为实际路径后交用户。

```bash
conda run -p /absolute/path/to/export-env python -m pip install --no-deps -e /absolute/path/to/method035-v2

# 纯文件计划；输出文件必须不存在。
conda run -p /absolute/path/to/export-env python -m egrs.trajectory_augmentation.recovery plan \
  --config /absolute/path/to/method035-v2/configs/trajectory_augmentation/recover_teacher_v2.example.json \
  --output /absolute/path/to/new-recovery003-plan.json

# 用户亲自启动正式恢复；本轮实现与测试没有执行此真实命令。
conda run -p /absolute/path/to/export-env python -u -m egrs.trajectory_augmentation.recovery recover \
  --config /absolute/path/to/method035-v2/configs/trajectory_augmentation/recover_teacher_v2.example.json \
  --output /absolute/path/to/data/trajectory035/generated-003
```

`generate`是`recover`的等价子命令。输出必须是独立新目录，不得位于旧legacy run内或覆盖它。恢复过程先复制旧8条到 `reused/generated002/`，前后均核SHA和大小，无活动路径逃逸。旧qualification/lineage文件不重写，源ID/父组/split/映射/长度/HDF字节不变；新的source外围记录 `reused_from_generated002.new_execution=false`，不会声称这8条经过v2重判或新执行。

随后只对73来源调用现有正常重放→handoff→3起点×最多2桥接→B跟踪生成器。新物理上限73正常重放、219起点、438次10、265720控制步；初始化时间另计。旧8条不计新增物理次数，实际成功量不保证。每个任务预先固定第一个恢复来源的视频，不按结果挑选。

v2 rejected也保存已经实际完成的对齐前缀HDF（T+1观测/状态、T动作）。尚未捕获下一帧的动作只在journal/audit，初始化无帧不造HDF。确认HOLD仍只作审计，失败轨迹qualified=false且不进入导出训练索引。

主要产物：

- `recovery_plan.json`：原180、固定73/53:20、旧8/2父源和新增预算、批准引用身份。
- `reuse_manifest.json`、`reused/generated002/`：旧数据及原证据副本。
- `artifacts/source-NNN/`：新执行记录，保留所有失败、诊断、已对齐前缀。
- `recovery_progress.json`：每来源完成/73、百分比、技术错误、新normal/10合格、复用量及实际新attempts；控制台逐来源也打印。
- `export/`：复用原schema的sources/windows/attempts/report；只索引真实qualified，`generation_context`将v2、恢复plan身份与v1复用语义纳入sources/report身份。训练器及item whitelist不变。
- `recovery_report.json`：新执行、旧复用、合并数据和train/dev×10/normal四池，`training_ready`仅判断四池窗口非空，不加载模型或自动训练。

`new_execution.attempts`才是本轮实际物理尝试分母；`merged_data.attempts`是导出审计总记录，含旧8条。不能将438预算上限、来源处理100%或训练ready标记解释为生成成功率/模型SR。报告任务缺口；ready=false不自动补跑、改split或回退普通RAW。

## 训练与双条件评测

原一组1000更新、7:3、同adapter10/00各90与两基线保持。只有实际恢复报告四池非空，Codex才交用户最终训练命令；本轮未执行。示例仍复用原训练器：

```bash
conda run -p /absolute/path/to/oft-env python -m pip install --no-deps -e /absolute/path/to/method035-v2
conda run -p /absolute/path/to/oft-env python -u -m egrs.trajectory_augmentation.training \
  --config /absolute/path/to/method035-v2/configs/trajectory_augmentation/robot_rewind_mix.json \
  --export-dir /absolute/path/to/data/trajectory035/generated-003/export \
  --output-dir /absolute/path/to/new-mixed-training-run \
  --benchmark-root /absolute/path/to/accepted-core-d8541ef4 \
  --oft-root /absolute/path/to/official-oft-e4287e94 \
  --checkpoint /absolute/path/to/complete-SOG10-638918f3
```

`selected_checkpoint.json`仍固定末1000权重，adapter身份自动绑定新export文件字节。双条件原命令见[评测指南](trajectory_augmentation_evaluation.md)；无需重跑基线。真实生成、训练和模型评测由用户启动，软件通过不保证新数据产量或SR提高。
