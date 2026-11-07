# 038软件验收、部署与正式预算批准

2026-11-06，Codex。前阶段037首审closed保持，本文记录新038实现交付的闭环，不代表方法研究或实验效果闭环。

## 结果

[PR13](https://github.com/No1dry/Learning-Not-to-Act/pull/13)固定head`5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`、实现`b5849e4e4f7f56b888922e1267870126f5368ccf`的软件/部署accepted，X无需返修，不自动merge。详见[Codex R1](../../collaboration/reviews/038_round1.md)。

共享训练/正式eval单VLA前向、实际prefix/56-hidden布局、z128/残差瓶颈256、只交换z且各端自身动作、完整新模块保存与原策略旁路、两组同数据采样/预算均符合规格。新index从旧active facts/实际记录状态建立监督，不取official前两项、不重放/真值输入。130个独立CPU/fake最终通过：首次112＋18缺本地依赖setup error，复用现成固定core/reporting映射后只重跑18通过；旧错误XML保留，没有虚报第一次通过或重跑全库。

新代码独立部署`code/task038-5a6452ab`，实际配置`configs/task038-5a6452ab`，19源文件/4配置SHA核对；两个原venv的editable映射切换到此副本、core cwd模块来源正确，不升级依赖，旧代码目录不改。原base-runtime逐字复制，旧正式九任务来源/双bridge/评分不变。部署收据见[机器证据](../../collaboration/evidence/038_codex_acceptance.json)。没有真实index、图像特征、tokenizer/模型、教师、仿真、训练或eval。

## 用户本轮确认

用户明确答“同意两组正式对照及预算”：零新增仿真生成；一次索引，C0/C1各1000、总2000更新，参考≤18048、学生≤49120，两模型10/00各90、总360新episode。预算和文件准备授权**不授权Codex/X代启动**。旧三组3000与036续训不因此批准。

[完整常用命令](../experiment_plans/2026-11-06_task038_index_training_commands.md)已交用户：原Conda+OFT venv，一次index正常后直接C0，完成后C1，不并行抢同GPU、不再等待额外人工预检/MVP。只评各固定末1000，真实评测命令待其实际产生后给出，未用缺失权重伪造plan。

软件/代码部署100%；本轮真实索引/标签准备、训练、模型评测均0%，真实pair量与方法效果仍未知。下一用户启动index/C0/C1；Codex读取用户交回结果并准备360评测；X等待明确问题，无新改动任务。

## 保留和归档

035的10/00为54.44%/73.33%，036为50.00%/82.22%，原24.44%/86.67%；原权重/所有旧数据/视频/失败、037文档与PR12保持，不重计分、不按成败选训练源。本阶段关键文档/机器证据精确发布commit读回SHA、本地stage副本与manifest，X原回复/原测试证据按固定PR head备份保留署名。原复查XML/部署日志/配置在本地review目录。待删=[]，没有清理、自动merge或启停真实作业。
