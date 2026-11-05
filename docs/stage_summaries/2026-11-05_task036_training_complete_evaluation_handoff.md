# Task036：1000更新训练完成，正式180评测交接

2026-11-05，Codex。用户启动训练后交回完成消息；Codex只读已生成日志/身份/文件SHA、准备评测配置和方法包，不做额外模型前向/仿真。训练1000/1000=100%，真实新模型评测0%。软件仍PR11@205d6530（实现8b9399a9），未改代码/合并PR或新增预算。

## 实际训练及核对

`runs/retention036-train-001`有连续1…1000条update、250/500/750/1000四checkpoint和固定末1000选择记录。参考账本/最终日志/identity一致：8000train＋1024dev＝9024/9024，未超预算；最终adapter/source index/统计/base lineage一致，training_state字节与其SHA一致。训练进程已结束，控制台无Traceback/RuntimeError/ValueError/OOM错误标记。未重新加载7B或反序列化执行训练状态作验证。

最终adapter SHA **`b110901c2e0f85c2e012647d9fb6994da5d71d0e4ddf728b559d8d016ce36050`**，与035权重不同。索引仍同一036三池/180父split，不重建数据。日志末次更新记录elapsed12776.88秒（约3小时33分，未含末次dev/保存尾时），不宣称精确端到端用时。

| 离线损失 | 初始参照 | 末期 | 解释 |
|---|---:|---:|---|
| train weighted L1，前/后50均值 | 0.089659 | 0.041612 | 下降53.59%，不是SR |
| train ten专家L1，前/后50均值 | 0.177820 | 0.067151 | 专家动作拟合改善 |
| dev ten，250→1000 | 0.156958 | 0.130358 | 下降16.95%，不是任务成功 |
| dev fresh参考偏差，250→1000 | 0.010563 | 0.014806 | 相对原策略仍有漂移 |
| dev raw参考偏差，250→1000 | 0.011127 | 0.013748 | 不能据此声称00已保持 |

普通参考初期近零符合从原模型起步；后来非零只表示动作函数偏离。是否提高/保住10及恢复00必须正式评测，不以loss替代SR，也不改选250/500权重。

## 权重/结果保留

最终adapter、identity、完整training_state及SHA、metrics、run_config、reference_budget、selected_checkpoint和console共9文件已从服务器复制到本地`research_archive/Learning-Not-to-Act/task036_checkpoint1000_2026-11-05/`并逐文件SHA匹配。保留manifest SHA `ba48c1b7b205679f782adbe8517e9988f03a174af2f424ed9072f937bf23ca0f`。服务器四checkpoint/索引和035全部结果/权重/003/004仍保留，不覆盖或清理。原7B未重复下载。

本地审查`reports/task036_training_results_2026-11-05/training_review.json`明确检查和备份范围；源码/初态/模型执行并未重跑。无需X返修或新增CPU全库/GPU预检。

## 正式评测准备与下一步操作和执行者

配置`configs/retention036-eval-001/evaluation.json`绑定新036末1000，原035的全部源配置/旧新环境分派/端点/评分保持，base-runtime只复制原内容。新schema为task036-retention-eval-v1，新输出runs/retention036-eval-001，不继承035模型结果。

模型worker会剥离父PYTHONPATH并换cwd，因此将原两个venv中的**方法包无依赖editable映射**指向已验收036代码；没有升级任何依赖、修改冻结core或热改源码。分别在与真实worker相同的core cwd核对模块来源，新036/identity reader均指向task036-205d6530，防止旧035 reader拒绝新权重。仅包/模块来源核对，无模型加载。

Codex执行一次新配置的纯文件plan验证180/180、126单元、同一新adapter、无continuation/继承；simulation_created/weights_loaded均false，输出run尚不存在。证据在evaluation_preparation_receipt.json及plan.json；不新增物理/模型预跑、不让用户另跑plan/pip。GPU读取为空闲约81GB，仅时点状态，不承诺之后共享资源仍空闲。

**用户按[完整常见命令](../experiment_plans/2026-11-05_task036_dual_condition_evaluation_commands.md)直接启动原批准的10/00各90正式评测**；Codex待结果统计/视频比较。两类各对原24.44%/86.67%和03554.44%/73.33%，10第一/00第二/泛化第三保持，真实效果open。所有视频保存，无FINISH/教师/规划器推理。无自动真实实验、merge或删除，待删=[]。文档按实际新commit精确读回SHA本地备份，manifest更新。
