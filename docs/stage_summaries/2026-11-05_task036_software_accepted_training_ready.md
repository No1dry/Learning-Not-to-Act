# Task036：软件验收与训练文件准备完成

2026-11-05。用户批准036预算后的实际交付与决策闭环，不代表真实效果完成。

[PR11](https://github.com/No1dry/Learning-Not-to-Act/pull/11)@205d6530（实现8b9399a9，依赖035 ac2ec431）经[R1](../../collaboration/reviews/036_round1.md)accepted/closed限软件/隔离部署/元数据索引。新036测试52/52=100%通过；另49旧受影响用例通过。首联合测试的19项旧bridge/proxy fixture需Git历史、归档依赖无.git而setup error，非通过；记录保留，并复用同版本R11证据，不添加恢复Git历史门槛或要求X返修。保存→严格加载→新180 fake链独立通过；没有真实GPU/物理预跑、全库或平台发布门槛。

同底座参考按逐模块状态恢复、先参考后学生的方式暂时旁路native LoRA，原组件冻结；三池12/4/4、prefix/full、有效标量损失.50/.25/.25、新036 identity和9024预算计数符合任务。评测一个适配VLA，新180不能继承旧分数，原核心评分/端点/双bridge保持；执行只读新单元ledger，最终一次完整reader、进度分明，清理警告不掩盖推理或证据错误。X无本轮返修任务，不自动合并。

## 部署/文件准备100%，真实训练/评测0%

新`code/task036-205d6530`及`configs/retention036-205d6530/data.json`已部署；归档SHA `a1c9c16ca578ff00a4bfa55a47dd3e5ac4f796852c624364ba9d0ab102fcf1e9`，8个必要源码/配方本地与服务器匹配。没有改旧运行树、依赖包或环境editable映射，用户从新代码目录运行即可。

Codex按已批准文件准备范围完成只读既有观测元数据的索引绑定，没有读取RGB像素行、生成/渲染/重放环境、加载VLA或调用教师。`data/retention036/index-001`：ten train161/dev60（54/20父组）、fresh55/20、raw136/44，原180唯一父组；观测行train76173/dev25507、总101680。ten/fresh覆盖六任务，raw九任务，不伪称新增独立示范/物理资格。

sources identity `c3cc0d23d48ff724bfcb7f74b867d47c0e9c14592d04b2495f8342e2b8288bba`，rows SHA `1107999ddb1da75d703c355edb4b51e2c456617fe83977938585f4b5d6f33cf2`，report identity `3a084ac747f4830808eaee63f20912be01951013be63c2a5ddc9151abd1833cf`。本地证据`reports/task036_review_2026-11-05/`的deployment_receipt.json、index报告/日志及三份CPU XML。教师前向/更新/模型episode/仿真实例全部0，未自动监督或启动真实作业。

## 下一步操作和执行者

用户按[普通完整训练命令](../experiment_plans/2026-11-05_task036_training_commands.md)直接启动已批准的一组1000更新，无需再index/plan/pip/MVP；参考前向最多9024含dev、固定末1000、之后新模型10/00各90预算不变。Codex待结果核对、准备评测命令，X当前无需返修。10提高第一、00保持第二、泛化第三，效果仍open，不以软件通过承诺SR改善。

035完整结果及最终权重/续训状态/18段原视频已另行本地SHA归档，原服务器035所有checkpoint和003/004父子工件保留，见[保留总结](2026-11-05_task035_results_weights_videos_preserved.md)。旧close-15事实不改，不因小日志/清理问题重跑或重新计分。

本阶段文档提交GitHub后按实际来源commit精确读回、SHA核对并本地备份，收据和backup_manifest记录实际新commit，未把父commit当文档来源。无删除/自动merge，待删=[]；035运行refs及全部原始数据不可清理。
