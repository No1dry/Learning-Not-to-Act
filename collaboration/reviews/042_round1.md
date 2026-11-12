# Task042 R1：accepted，已隔离部署，用户直接训练

2026-11-12，Codex。接受PR17固定head `7d28d515be610f33f959f36d25623e86796671ce`（实现03e0efcd、依赖accepted PR16@e8dcf879）的软件/受影响CPU-fake/文件部署交付。**X无需返修，不自动merge。** [机器证据](../evidence/042_codex_acceptance.json)、[固定X原回复](https://github.com/No1dry/Learning-Not-to-Act/blob/7d28d515be610f33f959f36d25623e86796671ce/collaboration/responses/042_round1.md)。

## 核对与独立复测

- F0/F1同base C1、同041 R0全部参数初始化，祖代2000＋新增1000如实记账，原C1 loss/数据/采样/dev/参数量不变；仅F1禁任务T query读控制C key，F0保留原OFT双向padding-only，而非causal。
- 最终每层SDPA接收完整mask、首个shifted动作隐藏归C、真实P与插入长度核对，控制区proprio路径保留；逐样本不可变mask进入checkpoint，变长u/v不串线。无目标真值/task_id或专家动作内容参与路由。
- 原SOG10参考走原2D padding→native双向，旁路布局hook/LoRA/z/count/残差；8参考先于22学生图，模式/hook/RNG/cache/梯度保护恢复。新身份/完整保存与同run恢复、先扣账/失败不退款、严格配置0.0和单学生原180/臂评测接线保持。
- 原80部署源/依赖中79逐字节不变，唯一旧文件task_control/oft.py增加显式可选forward seam，默认不变；新12模块独立tcif042命名空间。原安装包/OFT/core未修改。

独立**109个不同用例最终全部通过，0遗留失败/错误/skip**。首次103通过＋6setup错误，是Codex在错误cwd放fixture链接造成原固定core/reporting缺映射；修正为原现成fixture后仅补6通过，初始红灯保留，未改X代码/断言、未重跑全库/旧166。

因X本机没有Transformers，另在服务器**现有**HF4.40.1/Torch2.4.1库上做随机2层/hidden16的CPU软件接口检查，未mock生产inspector：native与F0数值一致，F1任务区对数值proprio非干涉且控制可读p，实际HF变长非reentrant checkpoint反向通过，源SHA3aac24ce匹配。它不计入109、不加载预训练VLA/轨迹、不占GPU、无optimizer update；原CPU amp FutureWarning保留，不为warning升级依赖。不能据此声称真实7B准入/数值/速度/显存或SR已验证。

## 部署与下一步

新code/config目录task042-7d28d515，92源码/依赖＋8配置/脚本服务器SHA一致，两实际训练JSON在本地及服务器原worker严格读取通过，float0.0保留。原runtime字节相同，eval只改schema/group/experiment_arm/未来adapter；原来源/人口/core/reporting/双bridge/评分/H520/chunk8/seed7/视频不变，R0原adapter字节SHA正确。两个原venv仅no-deps editable映射，core cwd静态模块来源正确，无依赖升级。启动器仅bash -n、未执行；未来两train/two eval/marker均不存在，没有新index/标签或真实VLA/GPU/数据/仿真/训练/eval。

**准备100%，真实训练和正式评测0%。下一用户直接按[命令](../../docs/experiment_plans/2026-11-12_task042_user_training_evaluation_commands.md)及本地042完整命令，一条启动器F0→F1各新增1000，正常后用户另启正式360。** 不再generate/index/plan/旧资格/MVP、GPU预检、基线或重开旧041。失败保留不退款/自动重试/接eval；原子marker防重复。原已批reference≤18048/student≤49120/正式360保持。

软件与文件交付closed、训练/SR/研究open。六关键文档及固定X六原稿精确commit读回SHA本地备份manifest，源tar/独立JUnit/随机CPU结果/私有部署收据保留；旧dirty checkout及全部权重/原数据/分数/失败/署名不改删，待删=[]。主比F1−F0，不承诺目标识别/A保护/ICML创新或zero-shot。

转发X：**042 R1已accepted并部署，无需返修或新泛审；保留PR17/原交付，等待用户真实训练/评测反馈，不启动任何真实作业。**
