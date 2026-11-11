# Task040：train-only父源覆盖与pair-only normal软件交付

2026-11-10，X。基于acceptedPR14@113ded21434a06e2cdc156e5d6283a11c3f15488，合入main040工单3d92223（本地merge fef4a95），独立新040PR保留未merge代码依赖。首实现ea3c48b95ed538abdd0e2c5c5beabac32fc86657，最终实现/修复0f24e9d46bfbc33edd001facf19d2c1c40ffc166。

`egrs/coverage040/`实现三任务demo_20..39候选元数据、seed7/旧锚点alias分组、仅新train代表的有界039生成、040来源/账本/sidecar版本绑定、引用旧039并仅追加新ten/pair的索引及同038算法C1训练/评测。新normal只作生成与pair来源，不混主池；旧fresh/raw及全部dev记录和确定性选择键/顺序不变。原算法、准入、H520、正式来源与评分、全部旧035/036/038/039数据/权重/失败/视频/历史署名保持。

最终定向CPU/fake162通过、0失败/错误/skip。实际合成动作记录→040export/index→原038微型C1，真实seed7抽到新pair，22student/8reference计数、保存/恢复tensor等值及严格adapter/index和固定末1000合同通过。独立whole-diff审查0 Critical/1 Important，父进程中断时子worker可能继续写证据的问题已用040本地安全launcher修复，6项fakePopen回归覆盖；清理未确认则拒封存，scoped复查无遗留问题。root另加未解析输出占位符回归。数据77项代码未改故保留已通过组，来源43和模型42在修复后重跑；不再全库/平台或真实MVP。

- [一次040回复与常用命令](../../collaboration/responses/040_round1.md)。
- [详细使用](../task040_usage.md)：3字段配置/环境展开、部署者填值、单次生产、单C1训练/完整恢复、原配置复制的正式180、nohup与进度。
- [测试JSON与三组命令](../../collaboration/evidence/040_cpu_fake.json)，对应[来源](../../collaboration/evidence/040_cpu_sources.junit.xml)/[数据](../../collaboration/evidence/040_cpu_data.junit.xml)/[模型](../../collaboration/evidence/040_cpu_model.junit.xml)JUnit。

实现/定向测试交付100%、Codex软件验收pending；部署、真实元数据/标签/索引、生成/模型/仿真/训练/eval0%。普通≤60/ten≤360、单C1原SOG10新初始化1000、reference≤9024/student≤24560、新模型180预算已批准，仍只有用户亲自启动。没有新合格train父组ten则模型加载前拒训，有新增按实际量继续、不设每任务N/新pair最低数或追加预算，无S/C0/新seed/基线/039续训。

父进程稳定stat缓存不豁免独立native子进程首次身份复验。早期TDD红灯、temp-parent setup、测试oracle字段及首次新JSON换行检查失败均保留，最终证据未伪装这些开发失败。无不安全OpenMP忽略、依赖升级、服务器启停、删除或自动merge。

下一Codex审查并隔离部署、填写实际普通命令，用户启动已批准作业，Codex分析产物；本轮不声称真实覆盖或SR提高。发布后按精确head/tree/关键文件blob读回，再将源码ZIP、回复/用法/阶段/CPU证据、发布与读回回执保留到本地`research_archive/Learning-Not-to-Act/task040_delivery_2026-11-10/`并生成SHA256 manifest。备份范围只为源码/文档/CPU证据，不冒称服务器数据/权重已备份。
