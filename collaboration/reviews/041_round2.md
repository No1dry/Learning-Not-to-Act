# Task041 R2：两组训练完成，用户直接正式360评测

2026-11-12，Codex。接受用户已完成的R0/R1固定末1000训练文件交付；原PR16@e8dcf879软件R1及configfix1部署修复保持。**X无需返修，不自动merge；训练closed，真实评测与研究效果open。** [证据](../evidence/041_training_complete.json)。

两组均连续新增1..1000、原C1、同040完整初始化/同040 index和原配方，分别全新优化器；祖代1000＋新增1000如实记录。R0/R1实际末adapter SHA为d4e726a8/45680122，各自完整training_state与保存SHA一致；选择文件固定末1000，不换权重。仅R1使用039教师，实际3999≤4000，不为凑上限补前向；原参考各9024，合计所有参考22047≤22048，学生49120等于上限。run config除实验臂/teacher/stage/output的预期差异一致，1000条已记录batch摘要/采样计数相同；不冒称独立逐步因果/完整tensor-RNG审计。

启动器R0于11-12 01:43:05、R1于05:28:12进入COMPLETE成功分支且总COMPLETE，原进程结束，无本次训练异常；未另采独立数字shell退出码文件。11-11 22:12:34至11-12 05:28:12共7h15m38，包含读取已有文件和两组训练。旧首次Codex配置失败记录保留，不能混当本次训练错误。dev10 L1为0.119043632/0.118295638，R1略低但不是SR/闭环效果证据。

34个原文件/514830066字节已从服务器取回并SHA一致，含两末adapter/身份/完整optimizer-RNG续训状态、metrics/run config/三账本/console、实际eval配置与原index小记录；manifest80db2c4e。所有服务器中间checkpoint/原数据/旧分数失败不动、不假称全训练数据已下载。[阶段](../../docs/stage_summaries/2026-11-12_task041_training_complete_evaluation_handoff.md)。

**训练100%，正式eval0%；下一用户直接按[运行命令](../../docs/experiment_plans/2026-11-12_task041_dual_model_evaluation_commands.md)一条启动已部署eval_both_sequential.sh。** 两模型各九任务10/00各90，共360；R0完整summary/正常退出后再R1，独立新run、原H520/chunk8/seed7/全视频/来源/core/reporting/双bridge/评分保持。配置实际绑定各自末1000，启动器与原部署SHA相同且仅语法核对，没有执行，未来两个eval/marker不存在。正式入口自己绑定plan，不另跑plan/MVP、数据生成/index/资格扫描、GPU预检或基线，不重训/加seed/选checkpoint，不继承039040分数。

本轮Codex只读比较/复制保存原文件，不加载模型或执行新标签/index/仿真/训练/eval。所有真实作业用户启动。主比较R1−R0，R1−040混有新增训练与优化器重启；六关键文档精确commit读回SHA本地manifest备份，无merge/删除。原数据权重/失败/历史署名保留。

转发X：**041两组训练文件R2已接受，原实现无需修改或额外泛审；保留PR16，等待用户正式360评测反馈，不启动任何真实作业。**
