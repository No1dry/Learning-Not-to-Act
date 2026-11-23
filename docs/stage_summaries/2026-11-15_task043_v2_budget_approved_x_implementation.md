# 2026-11-15：043-v2完整预算已批准，正式交X实现

用户在明确包含CPU≤143960键、零新仿真、两臂原始OFT各1000、reference≤18048、训练模型前向≤54144、正式10/00各90×两模型共360的问题下，明确选择“批准预算并交X实现（推荐）”。预算与软件实施范围获批，不扩展Codex/X真实作业权限。

正式入口：[工单](../../collaboration/tasks/043_v2_language_status_transfer.md)、[完整规格](../research/2026-11-15_task043_v2_language_status_transfer_spec.md)、[批准证据](../../collaboration/evidence/043_v2_budget_and_authorization.json)。此前同日待批稿保留并已加后继指针；旧043 REGA不执行，不从042累计3000接到4000。

H0/H1从原始官方SOG10固定revision新初始化语言LoRA r16/alpha32，共同复用040原数据和036普通能力保持，不安装旧z/count/pair/TCIF。每更新20主观测，最多复用4个eligible ten作辅助视图；仅H1辅助有当前目标状态文字，两臂部署都无提示。相同样本/优化/辅助BC和固定蒸馏日程，不默认教师更好、不把文字蒸馏本身当ICML新颖性或已证明推理。

X现在直接版本化实现＋定向CPU/fake，新PR与responses/043_v2_round1.md，不先泛审/SSH或真实生产。实现依赖accepted PR17固定7d28d515的软件接口，非从纯文档main直接运行，也不自动合并旧PR。Codex建议式验收后隔离部署并给完整常用conda/python命令；用户亲启CPU真实文字生产、两组训练及正式评测。软件/生产/部署/训练eval在派发时均0，规格与授权交接100%。

CPU sidecar仅当前主键/既有JSON事实与原生语义映射，无像素/未来/测试真值或隐藏实例ID；未知不改False、释放未知不说未松手，双壶集合化。主数据289/81 ten、原fresh/raw/split/正式bank保持，不重建旧索引或凑N。H520/chunk8/seed7/全视频与10合规/00官方评分不变。

042 F1 70%/80%、全部历史权重、数据、原始失败和署名保留。新工单/规格/授权/状态/本阶段按精确commit读回并SHA本地归档、manifest更新；旧dirty checkout未改，无新标签/模型/仿真/训练eval、无自动merge/删除，待删=[]。

可转发X：

> 043-v2预算已批准，请按collaboration/tasks/043_v2_language_status_transfer.md及完整规格直接实现，不先泛审。原始OFT起步、H0/H1双视图训练、部署无提示；实现CPU sidecar、loss/预算/完整恢复和正式360接线，做受影响CPU/fake，新PR并回复043_v2_round1.md。不要执行旧043 REGA，不SSH或跑真实作业，不自动merge；真实阶段均由用户启动。
