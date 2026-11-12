# 042预算批准与X直接实现交接

2026-11-12，Codex。用户在已发布042推荐方案/预算后明确回复“按推荐的来吧”，批准两组正式对照及交X实现。[详细工单](../../collaboration/tasks/042_task_control_information_firewall.md)、[批准机器记录](../../collaboration/evidence/042_budget_approval_and_dispatch.json)、[已批方案](../research/2026-11-12_task042_task_control_attention_firewall_proposal.md)。本阶段仅文档/源码审计附件交接，没有实现、部署或新真实作业。

## 固定决策

F0/F1基础都C1、同041 R0全部末参数初始化，新optimizer/scheduler/采样RNG/预算，各新增1000；祖代累计2000＋新增1000=3000如实分记。原040 index8ef04d91及370ten/370pair、105fresh/180raw、143960行/原split与dev选择/原C1 loss/参数量保持，不生成新标签/index、无039旧10教师/外部VLM/FINISH。

两臂同显式SDPA包装。F0保留OFT原生padding-only双向图，F1只逐层禁止任务前缀T读取整个控制区C，控制区仍保留native读取。按实际shifted56隐藏划界，首个动作隐藏即使落在prefix scaffold也归C；mask随每个观测进入checkpoint，不依赖全局最近样本；原策略参考必须同时旁路防火墙与全部新增分支。不能默改为causal，不能让native last-row扩展把研究mask覆盖，也不允许热改site-packages/OFT/core。

已存在worker审计源SHA3aac24ce（Transformers4.40.1/Torch2.4.1+cu121），[附原版权和完整SDPA forward片段](../../collaboration/evidence/042_audited_sdpa_source_excerpt.md)供X不SSH即可复现CPU/fake；这是静态来源，不声称已追踪历史7B真实实例。新用户作业初始化记录实际类/版本合同，不加未计数真实forward。F0/F1各自完整参数/执行合同/optimizer/RNG保存恢复，新042 reader不放宽旧root，0.0配置类型保持。

## 已批准预算与角色

- 新增训练各1000、共2000；原SOG10参考各9024、总≤18048；student各24560、总≤49120。
- 新模型每臂九任务10/00各90，共360，原H520/chunk8/seed7/来源/双bridge/评分/全视频保持。
- 新数据/仿真/标签/index/状态重建、039教师、额外seed/系数扫描/MVP或基线重测均0；账本前扣，失败不退款，不复用041余额或重开完成run。

**规格交接100%，042实现/部署/真实训练及评测0%。现在执行者X，直接版本化实现＋定向CPU/fake＋新PR和responses/042_round1.md，不先泛审。** 依赖accepted PR16固定e8dcf879（含PR15/039/038链），同步最新main文档，不假定main已有全部实现、不自动merge。X不SSH/部署/加载真实模型或实验；Codex验收后隔离部署与完整普通命令；用户亲启所有真实阶段。

主比较F1−F0，旧R0不能替匹配对照。信息非干涉是条件结构性质，不是完整目标识别/A保护/SR/zero-shot或ICML新颖性保证；语义区仍可在图像中看到机械臂。若真实效果不佳，不自动扩大预算/改评分。审查以建议为主，仅明确错误/泄漏/危险/关键约定缺失阻塞，避免偏好返修。

七关键文档（工单、批准、源附件、已批方案、本总结、STATUS、仓库AGENTS）同提交发布，精确commit读回SHA本地归档并更新manifest；现存完整运行源只读副本沿提案归档保留。旧dirty checkout及039/040/041全部权重/数据/分数/原失败/署名保持，不合并/删除/代启停，精确待删=[]。旧提案未批准/无X任务条目仅属历史，不覆盖后续决定。
