# 039软件阶段：有界教师收尾与数据覆盖恢复入口已就绪

2026-11-07，Codex。[PR14](https://github.com/No1dry/Learning-Not-to-Act/pull/14)固定head113ded21434a06e2cdc156e5d6283a11c3f15488、实现8a733d039aef69df1323bb34c896ed40895cff12，依赖accepted038 PR13@5a6452ab；本轮[R1](../../collaboration/reviews/039_round1.md)限软件/CPU-fake/隔离文件部署accepted，X无需返修，不自动merge。研究数据恢复与效果仍open。

本轮保留038网络/损失/评分，针对旧三任务无10监督缺口，增加真正张手/有界竖直撤离/原5帧释放确认，动作与T+1观测全部导出；双壶仅新训练episode初态互换同类对象freejoint位姿/速度，固定A/B与正式bank不变。保持V2准入/保护/未知拒绝，不改标签或引入FINISH/推理真值。

60个原first20父源固定、normal≤60/ten≤360账本先计数/不退款；旧六221ten/75normal和180raw/父split引用复用。新索引真实计数和双root/收尾置换身份绑定、共享稳定文件hash上下文与可见日志。新增合格train10为零则拒绝重复训练旧数据，否则按实际量继续、不凑N/真实MVP。

独立受影响279个CPU/fake最终全通过/0遗留失败/0skip，含新039全链和原038回归；初次221/1缺历史fixture与一次Codex链接cwd错误保留，复用现成fc1b4990后仅补测1项通过，模型57一次通过。没有用真实模型/仿真/新标签检查替代CPU，X277通过/2skip和OpenMP解释原文按固定head备份。

新code/task039-113ded21与configs/task039-113ded21文件SHA核对；原runtime/035生成配置/九任务评测人口、固定core/reporting/双bridge保持，两原venv方法editable映射切新副本并核对来源，无依赖升级/旧代码数据修改。[完整conda/python命令](../experiment_plans/2026-11-07_task039_generation_training_evaluation_commands.md)已填，下一用户直接generate→C0→C1、之后两模型正式评测，不增加验收往返。

用户已批准上限60普通＋360次10、原SOG10两组各1000/末1000、reference≤18048/student≤49120、两模型10/00各90共360。预算不扩大代跑权限。本次仅文件部署/CPU-fake，无真实生成、标签或索引生产、模型/教师加载、训练/eval；准备100%，实验0%。实际数量/SR待用户运行。

038的55.56%/84.44%和全部旧权重/数据/分数/视频/失败保持。新eval配置对应未来039末1000，不继承旧分数，不重建初态/基线。关键软件文档/证据精确GitHub commit读回SHA并本地备份登记manifest，X原稿保留署名；无清理/自动merge，待删=[]。
