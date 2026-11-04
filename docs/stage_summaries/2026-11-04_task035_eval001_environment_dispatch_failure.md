# Task035：首轮正式评测初始化失败与双bridge修复交接

2026-11-04。训练100%保持；用户启动eval001后程序自行退出，完成0/180=0%。SOG10与最终LoRA已加载，首任务在环境身份检查处失败，attempts/results空，无策略动作，不记模型失败或SR=0%。Codex未启动新仿真、模型、重跑或停止作业。

根因：`LiberoGoalEnv.__init__`计算实际环境锁后与旧manifest不同。LIBERO源码SHA、资产SHA、robosuite1.4.0/MuJoCo2.3.7、20Hz与compat实现均匹配；唯一差异为bridge_source_sha256。旧六10/00共120条需要fa85ae08...（fingerprint27939e2d...），新三共60需要3a515ddd...（fingerprinte7d58f35...）。当前d8541ef4只有后者，方法评测未对双版本分派。代码差异是新task_semantics支持；不能据此篡改原身份或关闭校验。

这是Codex审查/部署遗漏。R7“训练完成”和“纯文件计划180通过”仍是事实，但“可直接执行180”被此次真实启动否定并撤回。原配置误指00模板的问题此前已修，与本次bridge不兼容是不同问题。

原服务器`runs/trajectory035-eval-001`和.console.log保持；本地`reports/task035_eval001_failure_2026-11-04/evidence/`保存console、batch和首task元数据。最终权重仍update-001000/SHA21b982e5...，不重训，不改变数据/测试来源/评分或重跑基线。

[X精确任务](../../collaboration/tasks/035_legacy_environment_dispatch.md)仅方法侧版本化环境实现分派，严格验证实际旧/新依赖锁，保留真实实现身份，不修改冻结core与原manifest；CPU/fake和只读身份核对后由Codex审查部署，用户启动新输出eval002的原180条，不加MVP或真实诊断。旧001零episode，不需要续跑框架。完整原模型输入、原端点、10二元合规SR/00官方SR与全部视频/证据保持。

训练范围accepted；兼容修复open，新模型效果open，实时SR并行项仍非阻断open。旧命令暂停，下一执行者X。开放任务/原错误/运行refs/原始数据不清理，待删=[]。
