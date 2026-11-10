# 039 R3：两组训练完成，接受末1000并交正式评测

2026-11-08，Codex。用户要求下一步，仅读/复制现有训练文件、身份/预算与eval配置，不加载真实模型/仿真、不再生成标签/索引或训练/eval。软件R1与数据R2保持，PR14@113ded21不自动merge，X无需返修。

**接受本轮真实训练产物范围：C0/C1各1000/固定末1000，连续1000条更新、两个exit=0，无残留训练进程。** 训练100%、评测文件准备100%，真实模型eval0。并行从11-07 22:42:59到11-08 03:50:46（北京时间），总5小时7分47秒；主体各约4h53，启动/文件读取/保存另计。与旧038串行耗时只是参考，不当同数据受控性能证明。

| arm | adapter SHA前缀 | reference | student | 新dev10 L1 |
|---|---|---:|---:|---:|
| C0 | e9d481030c35 | 9024 | 24560 | 0.129999882 |
| C1 | 6d340e991860 | 9024 | 24560 | 0.130077180 |

两组合计reference18048/student49120等于已批上限，没有超额。C0/C1同run_config（除arm）、新index b8587565、原base_lineage/训练recipe；最终采样计数一致，未另做逐步GPU时序/因果审计。固定末adapter字节SHA匹配各identity，完整training_state字节SHA匹配各sha文件，二者权重不同；selected_checkpoint均末1000，不按dev/测试挑其他checkpoint。

新dev10 L1差约0.06%，非常接近且C1略高，不是成功率，也不作“C1已有优势”结论。与旧038的dev集合不同，不跨数据直接解释loss升降。305pairs/130017行和三任务训练覆盖沿R2，白杯1父源/3变体不足的限制保留，不加生产/重训门槛。

29个最终adapter/identity/完整续训状态/metrics/配置/预算/两实际eval配置/索引小记录与退出记录已复制到本地research_archive/Learning-Not-to-Act/task039_training_complete_2026-11-08，逐文件服务器到本地SHA一致；manifest SHA 06bafa448a78e395f4b297c777cf6d1a31d9e256ecdbd058ca512004233b9c96。服务器全部中间checkpoint/console、039生产大文件、旧035/036/038权重分数失败保留，不伪称全部视频/原数据已下载。

两eval JSON与038的九任务来源/固定core/reporting/双bridge输入一致，变化仅明确的runtime路径/arm/新末权重。未来eval目录与launch marker未创建。新增的是Codex命令准备职责下的串行接力shell，不改实验实现；已做bash语法和上传SHA检查，未执行。C0正常完成正式summary再启动C1，失败不自动重试/启动后续arm，不另跑report。

用户按[一条完整命令](../../docs/experiment_plans/2026-11-08_task039_dual_model_evaluation_commands.md)直接正式评测，两组各10/00各90共360，沿原H520/chunk8/seed7/全视频/原评分，无FINISH/外部VLM/真值控制。run自行绑定真实权重建plan，本轮不另做plan/MVP/物理/全量来源重扫；未假称新模型plan/eval已通过。

训练交付closed、正式SR/方法机制/研究结论open。Codex只归档/准备命令，真实作业仍用户亲启；X无改动任务。关键文档/机器证据精确commit读回SHA本地阶段备份与manifest登记，无自动merge/删除，待删=[]。
