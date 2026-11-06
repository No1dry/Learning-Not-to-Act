# 038：C0/C1训练完成，交付正式360条评测

2026-11-07，Codex。用户完成两组1000，Codex读取现成JSON/权重与续训状态字节hash、既有进程并备份文件；没有新标签/模型/教师/物理/训练/eval作业，也不另加plan/MVP或重复旧状态资格。

## 已完成与保留

两组训练100%，固定末1000，原策略参考各9024、学生各24528，合计18048/49056未超18048/49120上限。数据index/原base/除arm外配方一致，最终sampling记录一致、arm身份正确、两个权重不同，字节hash与原训练状态SHA核对。C0 `f3f4c876f29cca0478e0d37148a0d3f60bbf265cbe1fb91ea0452cd417f3120b`；C1 `3f3873a435623af0d374e2ea5f5153429f6619ff06b0ec7062eea4cf23cef6c2`。

已完成的一次索引：101680行，计数标签50661，raw缺失51019，221pairs全部有效（161train/60dev），六任务有10增强，原九任务普通观测/正式来源保持。没有为另三个任务自动补数据或改变评价人口。

两末1000adapter/identity/完整续训状态、metrics/训练配置/选择/预算、实际eval配置/runtime/session及索引小记录共24文件本地SHA保留，原服务器所有中间checkpoint/原console及035/036/003/旧失败保持。归档`research_archive/Learning-Not-to-Act/task038_training_complete_2026-11-07`，收据摘要见[机器证据](../../collaboration/evidence/038_training_complete.json)。

## 离线结果不代替SR

末1000 dev10 L1：C0 .129851，C1 .128834（相对低约.78%）；计数准确率96.43%/96.03%，paired align .001414/.001311。结果混合且差距小，不宣称C1的实际合规SR或泛化已提高，也不按该结果换checkpoint。该实验仍是同网络/数据/标签/时长比较swap/align整包，不能单独拆分归因每一项。

## 下一正式阶段

[R2](../../collaboration/reviews/038_round2.md)接受训练完成产物/范围closed，效果/新颖性仍open。用户直接按[两组正式评测命令](../experiment_plans/2026-11-07_task038_dual_model_evaluation_commands.md)依次C0、C1，各10二元合规90/00官方90，共360新episode，所有原视频/raw/query/action保存；原H520/chunk8/seed7/完整指令/双相机proprio/双bridge-proxy/评分不变。

R1的两个eval配置本次只核对实际末权重身份与arm，不额外扫旧来源或另跑plan；正式入口自己绑定plan并执行，未伪造已经实际评测。模型执行100%后，同进程完成原结果核验/正式summary，再启动第二组；不同时占同GPU，不重跑原始/035/036基线、不新生成/重训或改判据。参考教师仅训练，eval单VLA，无FINISH/外部VLM。

训练/评测文件准备100%，新模型评测0%。Codex未代启动任何真实作业；用户启动，完成交回后Codex统计百分比/配对差异及取视频，X当前无需改代码。方法主张尚待SR，不把文件验收当科研成功。

关键文档/收据按发布commit精确GitHub读回、SHA本地阶段备份与manifest登记，旧文档/开放任务/源码/原始数据均不删除，PR13未自动merge，待删=[]。
