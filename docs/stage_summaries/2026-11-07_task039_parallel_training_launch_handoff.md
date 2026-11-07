# 039训练启动方式：用户授权一键并行，尚未启动

2026-11-07，Codex。用户要求一次训练C0/C1，允许自动接力或并行，选择更快方式并估时。仅读A10080GB空闲和038原metrics，C0/C1单跑12574.55/12963.76秒（3h29/3h36），各PyTorch已分配显存峰值约16.4GB（不含全部缓存/上下文）。据显存余量选择两个独立进程在GPU0并行，可能利用CPU/I/O空档；未测并行吞吐，不能保证比串行更快/减半。串行主体合计7h6，并行按5–8h预留只是估计，不启动性能MVP。

按Codex文件准备/命令职责新增[启动脚本](../experiment_plans/scripts/task039_train_both_parallel.sh)，上传服务器configs/task039-113ded21/train_both_parallel.sh，与GitHub源SHA一致；只bash语法检查，没有执行。自行激活原Conda/OFT venv/session，training_ready/已有输出拒绝、原子launch marker防重复，独立两日志/权重/预算，等待双方并记录退出状态。失败不重试/退款、不中止另一组，不自动eval。

原模型/损失/索引/seed/每组1000/末1000/reference≤18048/student≤49120/正式360不变，未新增实验预算。用户在[完整命令顶端](../experiment_plans/2026-11-07_task039_generation_training_evaluation_commands.md)只运行一条nohup，不再叠加旧逐组命令；两组完成才评测。039准备100%，当前训练/eval0，Codex未启动/停止真实实验，X无实现任务。

STATUS/AGENTS/脚本/命令与机器证据精确commit读回SHA本地备份、manifest登记；旧所有数据/权重/失败保留，无自动merge/清理。该启动便利不是模型创新或真实并行性能验证。
