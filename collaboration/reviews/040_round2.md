# 040 R2：现成数据准备已完成，用户直接训练C1

2026-11-11，Codex。**接受本次production-001完成产物的报告范围，生成/导出/索引100%，training_ready=true；无需额外预检、凑N或返修，用户直接启动已批单组C1。** 软件R1及PR15@428c1358保持，不自动merge。

本轮仅读取、复制现成报告和账本并核对SHA；没有新跑planner/标签、索引生产、物理资格或模型。原进程在最终读取时已结束，无preparation_error；没有采集独立shell退出码，不额外声称有exit0记录。

## 实际数据与预算

- 60候选固定分组为46train代表、14dev封存；实际46普通、69次10尝试，均未超60/360。新增合格train10为65、有效新pair65，无pair gap，source_errors=0。10尝试合格率94.20%，这是生成数据资格率，**不是模型SR**；失败尝试与normal未合格记录均保留。
- 生成到准备完成共6100.924秒，约1小时41分41秒；日志100%轨迹生成先于导出/索引结束，最终以preparation_report为准。

| 任务 | 新增train10 | 合并后train10 | 训练父组（原→现） |
|---|---:|---:|---:|
| stove | 32 | 68 | 12→23 |
| mug_pudding | 9 | 12 | 1→4 |
| two_pots | 24 | 48 | 8→16 |

原其他六任务不变；合计370ten（289train/81dev）、370有效pair、143960行。fresh仍105（78/27）、raw仍180（136/44），原dev稳定选择与参考池未变报告均true；新normal仍只用于生成/pair。

任务索引identity为`8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe`，report为`c87e6eba02fa987024cf57985f1fad4fff180b0132bc615042674ce9138c47c0`；准备identity为`ff0aeb8fd984cf9f7a67bbeb95550f8a10893e2906c2acf021f7feadd6ebf0ed`。[机器证据](../evidence/040_preparation_complete.json)。

## 下一步

获取本快照时训练/eval目录尚无，均0%。用户按[已部署命令第2节](../../docs/experiment_plans/2026-11-10_task040_user_generation_training_commands.md)在原OFT环境启动一组C1：原SOG10新初始化、固定1000/末1000、reference≤9024/student≤24560；不重跑generate/index、基线/旧状态或新增MVP，不续训039。详细私有路径命令已在聊天和本地文档。

现成六份小报告/账本服务器到本地SHA一致，原大HDF/raw/旧数据/权重/失败保留服务器。新父组实际覆盖增加但效果未知，不把数据量或父组数当SR提升/独立物理布局证明。X无需改代码；Codex不启动训练或评测，不改评分、不删除或退款重试。数据准备closed，训练与效果open。
