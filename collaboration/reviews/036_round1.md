# 036 R1：软件accepted，独立部署及观测索引完成

2026-11-05，Codex。审查[PR11](https://github.com/No1dry/Learning-Not-to-Act/pull/11)固定head `205d6530e1ba389f74166a2e9520a3db7ae0edbf`，实现`8b9399a940b45db7e3089aaad9f25c6509fd7c5a`；依赖035已验收ac2ec431。**accepted/closed限036软件、文件绑定和部署，无需返修；真实训练效果仍open。** 未合并PR、未修改benchmark或旧运行树。

## 关键审查结论

三池来源/原split与same-row普通观测绑定；raw不带fresh资格假证书，不读普通actions/states作为目标。12ten/4fresh/4raw及prefix分箱、按有效动作标量归一化的.50/.25/.25损失符合工单。原SOG10新LoRA，普通目标为同底座禁用新增native LoRA的连续归一化8×7输出；逐模块finally恢复状态，所有参考先于学生图，不污染checkpoint反传。原组件冻结、参考无梯度，不加载第二7B；9024预算计数/恢复保持，新036身份/加载默认启用LoRA。

新模型180不继承旧分数，复用原035双bridge/proxy/固定core034与官方00；只有最终一次完整reader扫描，执行/核验进度分开。close/ledger/主错误分别保留，坏证据不冒充模型失败。共享旧035默认validator未被替换，新增显式参数保留旧路径。未发现明确实现错误/泄漏/关键缺失，不因风格要求返工。

## 实际CPU/fake证据，不冒称全绿

Codex独立运行：新036 **52/52通过（100%）**，含data16、reference12、training16、evaluation7、保存→加载→新180 fake链1。另49项受影响旧训练/原reader用例通过；合计实际通过101，无失败断言。

首次联合evaluation运行为31通过、19个fixture setup error：旧bridge/proxy测试需在固定core内`git show ac130177:...`，本地该依赖是归档快照而非Git checkout。不是19项通过，不是新实现断言失败；XML及错误完整保留。该19项依赖/实现本轮未改变，复用R11已验收证据，不为恢复Git历史追加重复检查门槛或要求X返修。新036链另独立进程通过。data/training69项2.60秒，evaluation31通过部分/fixture错误13.80秒，链1项1.97秒；未运行全库或任何真实模型/仿真。

## 文件准备与隔离部署

已部署新`code/task036-205d6530`、`configs/retention036-205d6530/data.json`。归档SHA `a1c9c16ca578ff00a4bfa55a47dd3e5ac4f796852c624364ba9d0ab102fcf1e9`，8个必要源码/配方文件与PR快照SHA一致。没有升级依赖或改变旧环境editable映射；命令从新代码目录执行。

按用户已批准文件准备范围，Codex执行**仅元数据**的index绑定：既有JSON/文件SHA、HDF观测shape/语言，不读RGB像素行、不调用模型/教师或环境。新`data/retention036/index-001`已完成，非新仿真数据生成或优化器训练。

| 池 | train/dev来源 | train/dev父组 | train/dev观测行 |
|---|---:|---:|---:|
| ten | 161/60 | 54/20 | 22640/8044 |
| fresh | 55/20 | 55/20 | 14625/5352 |
| raw | 136/44 | 136/44 | 38908/12111 |

总101680行，原180唯一父组；raw九任务，ten/fresh六任务。普通池比035窗口数多每轨迹最后一个当前观测，是策略函数蒸馏可用观测，不是新增专家尾动作。sources identity `c3cc0d23d48ff724bfcb7f74b867d47c0e9c14592d04b2495f8342e2b8288bba`，rows SHA `1107999ddb1da75d703c355edb4b51e2c456617fe83977938585f4b5d6f33cf2`，report identity `3a084ac747f4830808eaee63f20912be01951013be63c2a5ddc9151abd1833cf`。

本地证据：`reports/task036_review_2026-11-05/`的三份CPU XML、index036.console.log/report与deployment_receipt.json。模型加载/教师前向/优化器更新/新模型episode/仿真实例全部0；软件/部署/索引准备100%，真实训练/评测0%。

## 下一步操作和执行者

用户按[036完整训练命令](../../docs/experiment_plans/2026-11-05_task036_training_commands.md)直接启动已批准的一组1000更新，不需再index、plan、pip或MVP。Codex待训练结果给固定末1000的原180新评测命令。X本轮无需返修，保留PR11及来源，等待真实结果；不自动启动/监督作业。原035权重/结果另已本地完整保留最终checkpoint和18段原视频，详见[归档总结](../../docs/stage_summaries/2026-11-05_task035_results_weights_videos_preserved.md)。无删除/自动merge，待删=[]。
