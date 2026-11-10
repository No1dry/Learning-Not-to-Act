# Task039：教师收尾、双壶置换与合并索引软件交付

2026-11-07，X。按已获批工单直接实现，新功能在`egrs/coverage039/`。实现commit`8a733d039aef69df1323bb34c896ed40895cff12`，依赖accepted038 PR13@`5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`，合入main工单`d919233`的本地merge为`e5ff4aa`。新PR保留未merge依赖，不自动合并旧PR或本PR。

实现真实、有界且全记录的释放收尾、仅新双壶训练episode初态的实际freejoint置换、固定60父源和durable60/360尝试账本、旧221ten/75normal及180 raw的引用复用、动态三池/标签pair索引、单次准备哈希去重与进度、同038算法的新索引训练和评测入口。原V2准入、物理判据、正式初态/评分及038网络/loss保持。所有旧035/036/038权重、报告、失败、raw、视频和续训状态保留。

最终受影响CPU/fake277通过、0失败/错误、2跳过（本机Windows真实文件symlink权限不足，模拟路径测试已通过）。合成新生成→export/merge→两索引→同038微型训练和严格adapter/fake-eval合同接通；原038受影响130用例保留。独立审查0 Critical、2 Important均修复并定向复查；没有把真实覆盖或收益当软件结论。初次同进程NumPy MKL/Torch OpenMP冲突及早期红灯保留，最终fake记录器按实际worker隔离，未放宽校验/忽略重复库/改依赖。

- [一次回复与常用命令](../../collaboration/responses/039_round1.md)。
- [详细运行文档](../task039_usage.md)：配置、环境映射、单次生产/索引、新C0/C1训练与显式恢复、原双条件正式评测。
- [测试JSON](../../collaboration/evidence/039_cpu_fake.json)、[文件组JUnit](../../collaboration/evidence/039_cpu_files.junit.xml)、[模型组JUnit](../../collaboration/evidence/039_cpu_model.junit.xml)。

实现与受影响测试交付100%，Codex软件验收待完成；真实数据生产/标签/索引、模型、仿真、训练/eval及部署均0%。预算已经批准，不再请求重复授权：最多60普通/360次10、各1000训练、reference18048/student49120、模型360，仍只由用户亲自启动。生成没有新增合格train10时训练在模型加载前拒绝，有新增按实际量继续，不另加每任务N/MVP。不保证三任务真实全部恢复。

下一Codex审查、隔离部署并给出实际路径命令，用户亲启已批作业，Codex审查产物。发布后用精确head读回关键文件SHA及PR状态，并在本地`research_archive/Learning-Not-to-Act/task039_delivery_2026-11-07/`保留源码archive、回复/文档/测试证据、发布回执和SHA manifest；此备份范围仅源码/文档/CPU证据，不冒称备份服务器真实数据或权重。无自动merge、删除或服务器作业启停。
