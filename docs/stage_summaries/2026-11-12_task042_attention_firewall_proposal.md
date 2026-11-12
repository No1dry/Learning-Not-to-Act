# 042任务—控制注意力信息隔离提案与静态审计

2026-11-12，Codex。用户要求下一步后发布[042方案](../research/2026-11-12_task042_task_control_attention_firewall_proposal.md)及[审计/预算草案](../../collaboration/evidence/042_existing_attention_audit_and_proposal.json)。**只有研究提案，数值预算未批准、没有X实施工单或新实验。** 041本轮closed，全部旧分数/数据/权重/失败不变。

041旧10蒸馏未超R0，当前z仍从融合后视觉/指令隐藏形成。只读已验收OFT实现与现存LlamaSDPA源码发现：不取proprio槽不代表无proprio信息；该分支会把最后mask行扩成双向padding-only，简单上游mask可能被覆盖，且仅禁直接P边会留下控制隐状态回流。服务器源SHA3aac24ce、Transformers4.40.1/Torch2.4.1+cu121，本地复制SHA匹配；没有构造7B对象追踪历史各run实际类，不能把静态源当全部执行证据。

推荐TCIF：F0保留原生OFT双向路由，F1逐层禁止任务前缀T读取控制区C，控制区仍读T/C，不改token顺序/位置/原并行动作或全局package。按实际首个shifted动作隐藏划界，避免把首个控制位置错挡；任务z/count与C1损失、原rewind-pair保持，原策略参考必须旁路新边界。mask随每个样本作为显式参数走checkpoint，不能用全局最近样本状态；CPU/fake只覆盖这些明确失真风险，不另GPU预跑。

两臂均以041 R0完整末权重d4e726a8初始化、新run优化器/账本，各新增1000，祖代2000＋新增1000累计3000；同370ten/370pair、105fresh/180raw、143960行及原split/dev，不生成新标签/index。提议新增2000更新、原参考≤18048、student≤49120、新模型10/00各90×2共360；旧10教师/新数据仿真/外部VLM/MVP/seed/系数搜索/基线均0。主比F1−F0，不把对旧R0差值全归信息边界；attention合同统一SDPA，不承诺时间/显存或SR。

固定像素/文字时T只能读T，逐层归纳可得z对数值proprio不变；只是结构性质，不是新数学定理、物理rewind视觉不变、完整目标识别或成果硬保护。ReViP已有模态重平衡及prefix/suffix近邻，ProgressVLA/CycleVLA已有进度引导/回溯，不将单mask包装成ICML首创。结合外部预完成设置与原pair的具体受控效用仍待正式实验。

提案交接100%，042实现/部署/真实阶段0%。用户确认预算后Codex一次详细工单＋prompt交X直接实现/定向CPU-fake，不先泛审；之后Codex验收隔离部署/常用完整命令，用户亲启全部真实作业。X当前等待，原PR16不自动merge；不因本提案自动续训/生成/热改包/重开041，待删=[]。五关键文档精确GitHub commit读回SHA本地阶段备份/manifest，现存runtime源文件只读副本另存；脏checkout保留，无删除。
