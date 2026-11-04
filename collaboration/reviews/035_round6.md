# 035 R6｜003真实数据审查通过，可启动已批准混训

2026-11-04，Codex。用户已完成generated-003，固定方法代码44b6ca02、teacher v2。**data_ready_for_approved_training**：本批恢复/数据阶段闭环，直接进入原定一组1000更新；不额外采集、试训或以九任务全部覆盖为新门槛。训练与方法效果尚未验证，X当前生成代码无返修。

## 实际结果（不是VLA评测SR）

- 来源73/73完成=100%，技术错误0/73=0%。
- 新normal73/73合格=100%；实际新10尝试220次，合格215/220=97.73%，失败5条（3条完整任务/释放未完成、2条释放确认不足），原失败保留。没有消耗438次上限或把未执行计作失败。
- 新执行共293次，合格288/293=98.29%。另零重放复用旧8条（2normal＋6个10、两个train父源）；合并审计301记录、合格296条。
- 合格总量normal75、10轨迹221；它们是变体/重复起点轨迹，不是296条独立父示范。四池非空，training_ready=true。

| 数据池 | 合格轨迹 | 窗口 | 父示范组 |
|---|---:|---:|---:|
| train10 | 161 | 22,640 | 54 |
| train normal | 55 | 14,570 | 55 |
| dev10 | 60 | 8,044 | 20 |
| dev normal | 20 | 5,332 | 20 |

新增候选沿原53/20父分组，旧两个train父源复用，未重分组或用正式90测试状态/模型轨迹补池；未知demo/init物理祖源保持unknown，不能声称完全物理独立。

数据覆盖6/9任务=66.67%：basket41个10/14normal、basket_cheese_butter57/19、bowl_drawer_close48/17、dual_mugs6/2、basket_soup_cheese48/16、mug_microwave_close21/7。stove、mug_pudding、two_pots没有本批样本，缺口如实报告；正式仍评全部九任务，不假设未覆盖任务性能保持，不扩数据作当前训练前置。

## 启动准备与原目录保护

原训练器要求固定OFT commit且Python源码无本地改动。服务器旧`external/openvla-oft`有历史修改：run_libero_eval.py增加旧LIBERO路径/视频开关，未使用的vla-scripts/finetune.py亦有旧改动。Codex未改、stash或reset该目录；另用本地Git对象创建独立干净副本`external/openvla-oft-task035-e4287e94`，HEAD仍e4287e94541f459edc4feabc4e181f537cd569a8，无网络下载、无Python改动。

只读diff/AST核对：run_libero_eval中仅run_episode/run_task两视频驱动函数变化；模型加载、prepare_observation等实际模型API函数未变，其余三个推理helper文件字节相同。自定义训练器不调用这些上游视频驱动或旧finetune.py。训练仍用同一原SOG10权重、统计、action head/proprio projector和原7:3/1000配方。源文件hash差异据实保留，不伪称与旧目录逐字节相同；后续同adapter评测也应使用该干净副本，不改旧runtime或重跑基线。

这里只做必要的命令路径/源码绑定准备，防止首次训练立刻被现有loader拒绝；不解析训练HDF做额外检查、不加载模型、不做GPU smoke/试训或新增仿真。原OFT venv激活路径正确，输出`runs/trajectory035-mix-001`不存在，原recipe不变。

原始recovery_report SHA `1ef486a9e6fda9337bfb28c3d18922d3fc5eef3f35e200a4a665df3ef751ced7`；export/report SHA `eb5ceb2b937a22d942d2103263f93ab50e4cdc4cf1aa2462a5024946d0aa2da4`，已取回本地并与服务器一致。表中生成合格率不是基线/新模型SR。

**下一执行者用户：按[完整混训命令](../../docs/experiment_plans/2026-11-04_task035_mixed_training_commands.md)直接启动1000更新**。模型只见RGB/proprio/完整原指令；四池/数据身份和原normalization仍由既有训练入口绑定，不改训练代码。训练后固定末1000权重评原10/00各90，10比较24.44%、00比较86.67%；不以正式测试挑权重，不重跑原始模型。

X可并行既有[评测实时SR/去重复读取小增量](../tasks/035_evaluation_live_reporting_followup.md)，非训练前置；不要返修训练器或启动真实作业。研究open，无自动merge/清理，待删=[]。
