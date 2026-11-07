# 039 R1：软件验收通过，用户直接启动数据生产

2026-11-07，Codex。审查[PR14](https://github.com/No1dry/Learning-Not-to-Act/pull/14)固定head`113ded21434a06e2cdc156e5d6283a11c3f15488`，实现`8a733d039aef69df1323bb34c896ed40895cff12`；以accepted038 PR13 `5a6452ab`为增量基线，未重审或自动merge旧依赖。

**裁决：accepted/closed限本轮实现、受影响CPU/fake与文件部署，X无需返修。** Task039真实生产/训练/效果尚未完成，不假称三任务已恢复或SR提高。用户已批准60普通＋360次10上限、C0/C1各1000、参考合计≤18048/student≤49120、新模型360；所有真实作业仍由用户启动。

## 关键实现核对

- 收尾只在原生全目标已经为真且真实五帧释放未确认时追加实际OSC张手/≤0.10m竖直撤离/保持；≤40新增控制step且总≤520。每步实际动作、控制目标与新T+1观测入HDF，不用audit-only尾帧补监督。V2准入/未知拒绝/保护和事件规则未改，没有FINISH或推理真值控制。
- 双壶仅新normal初始化按实际对象注册表及freejoint地址互换两指定对象qpos7/qvel6。核对同类尺寸/实际关节布局与有效quat，其余状态保持；真正restore后拍新RGB，原A/B、语言、K、正式bank不动。新10与新normal真实交接配对，不把01换标签成10。
- 固定三任务原first20全部60父源；normal一次与最多3×2个10槽，初始化/中断在实际调用前持久计数。缺失metadata只补失败，不退款或自动重试；新输出拒覆盖。
- 旧六任务221ten/75normal及原180raw/split按原身份和引用复用，两个生成root显式绑定，不复制巨大HDF/可写hardlink、不重新物理准入旧资格。新来源绑定实际收尾/置换版本，三池及新索引用真实计数；旧入口默认严格合同不放宽。
- 同进程HashContext以canonical路径/稳定stat去重，源变化拒绝、不持久化免检；父源/attempt/哈希/索引有阶段日志。039训练入口实际消费新index identity，新增合格train10为0在模型加载前拒绝。
- 038网络、loss、三池权重/采样、原策略完整旁路、adapter与正式eval未换算法；少量共享改动为显式dataset/index contract、可选哈希上下文和紧凑日志，旧默认保留。微型CPU两组共享新数据/顺序、保存身份与fake eval路径已接通，训练tensor不因日志变化而改变。

## 独立CPU/fake与边界

本地**279个独立用例最终通过，0遗留失败/错误、0skip**：文件/记录器组222个，微型模型/入口组57个。包含X在Windows跳过的两项真实symlink回归。不是全库/多平台或真实模型/仿真MVP。

初次文件组221 passed/1 failed，失败原因为本地缺历史`Learning-Not-to-Act-task016`测试源码快照；随后一次补测仍因Codex创建链接时cwd拼写错误失败。复用已有固定fc1b4990快照建立测试专用链接后，只重跑该1项通过。四份原始JUnit保留，不改生产代码/锁、不把前两次失败抹掉。模型组57一次全部通过。

X原回复的277 passed/2 Windows skip、OpenMP分进程隔离解释保留原文署名并按固定PR head备份。本轮没有读取真实图像像素/创建物理环境/新标签或索引生产/加载VLA或教师/真实训练/eval；不拿软件证据替代真实恢复效果。

## 部署和下一步

新代码`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task039-113ded21`，配置`configs/task039-113ded21`。源与配置逐字节SHA核对，原runtime逐字节复制、旧九任务eval输入/core/reporting/双bridge保持。worker和simulation两个原venv的editable方法包映射指向新副本，从core cwd核对模块来源；这是明确的部署变更，没有依赖升级、旧代码或数据改写。

generation JSON只引用原035完整配置/原003 export/原036 index。新eval配置指向各未来末1000，目前adapter不存在，未构造或假称真实权重绑定plan。新production/train/eval目录未创建、真实作业未启动。

**准备/部署100%，真实039数据生产/训练/评测0%。** 用户按[完整常用命令](../../docs/experiment_plans/2026-11-07_task039_generation_training_evaluation_commands.md)直接启动一次generate；有新增合格train10后直接C0、完成后C1，不再等额外人工预检。各末1000产生后按同文档依次正式评测。出现错误保留输出/账本反馈，不自主重开生产/挑来源/改判据/加预算。

Codex负责仅读取用户产物、结果/权重/视频归档及分析；X本轮无需返修，不新增功能/泛审。原035/036/038权重、失败、分数、原数据均保留，不自动merge/清理，待删=[]。本R1/机器证据/阶段总结精确commit读回与SHA本地备份、manifest登记。
