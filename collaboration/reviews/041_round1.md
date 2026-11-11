# Task041 R1审查：accepted，已隔离部署

2026-11-11，Codex。接受PR16固定head `e8dcf87979d14d081666629a2de3483629a4f59c`（实现 `c51df70e597021d2c33a5bca013feabf723d879f`，继承accepted PR15@428c1358）的软件/定向CPU-fake/隔离文件部署交付。**X无需返修，不自动merge。** [固定X原回复](https://github.com/No1dry/Learning-Not-to-Act/blob/e8dcf87979d14d081666629a2de3483629a4f59c/collaboration/responses/041_round1.md)、[机器证据](../evidence/041_codex_acceptance.json)。

## 已核对

- R0/R1基础都C1，同040全部可训练模块初始化、新优化器/调度及独立预算，各新增1000，祖代更新如实记录；R0不是旧C0，不旧040resume。
- 原C1 loss/专家BC/22student/8普通参考、原dev/采样不改。R1仅从已抽ten中前最多4个明确old003六任务train来源增加0.10的完整039动作保持；少于4按实际个数、0则无调用，mask均值正确，无新观测/重抽或测试来源。
- 039新增LoRA/context/residual/count独立，原冻结大骨干共享；普通/039参考都在学生图前，no_grad/eval并恢复模式/hook/cache/checkpoint/requires_grad/RNG。无活跃图热换参数，teacher不进student optimizer/adapter或推理。
- 041身份/保存/同run完整恢复、三账本前扣/失败不退款、领先checkpoint拒恢复、新run防覆盖及单学生原180/臂评测接线保持，旧reader未全局放宽。
- 对accepted040的70个部署源/依赖文件，69逐字节未变；唯一旧生产扩展是task_control/oft.py显式可选modules，旧默认通过回归。新10模块在retention041下。

独立受影响CPU/fake **166/166通过（100%），0失败/错误/skip**：data65、reference32、identity43、stage26。复用原固定core/reporting CPU fixture，首次即全过，未改X源码/断言；未跑全库/MVP/真模型/MuJoCo或GPU预检。小型真实torch autograd与checkpoint不等于真实VLA/GPU效果保证。

## 部署及下一步

新code/config目录名task041-e8dcf879，80源/依赖＋8配置/启动文件服务器SHA匹配；两原OFT-worker/simulation环境仅no-deps editable映射，无依赖升级，在core cwd静态核对041训练/策略及共享OFT模块来源。原runtime字节保持，eval仅schema/group/experiment_arm/未来adapter改为041，原基础arm=c1和全部源/评分/bridge保持。040/039实际adapter SHA匹配已批输入。只复制文件、语法检查和静态模块定位，没有加载模型或执行真实数据/index/标签/仿真/训练/eval。

**软件/文件准备100%，真实训练/正式评测0%。下一用户直接一条启动器按R0→R1各新增1000；正常完成后另行正式360。** 完整普通conda＋python替代、后台和简洁进度见[运行交接](../../docs/experiment_plans/2026-11-11_task041_user_training_evaluation_commands.md)及聊天/本地私有绝对路径命令。无generate/index/额外Codex预检、MVP、基线、系数搜索、seed或重开旧run。失败保留/不退款、不自动重试/评测；原子marker和已有输出防重复。

本轮软件交付closed、训练与研究效果open；原预算参考≤22048/student≤49120/正式360保持，用户亲启全部真实阶段。R1−R0主比较，不将跨版本行为保持冒称A硬保护/ICML创新；无实际SR新结论。六关键文档及固定X8原稿精确commit读回SHA本地备份/manifest；源tar、四JUnit与私有部署收据保留，原dirty checkout和全部旧工件/失败/署名不改删，待删=[]。

转发X：**041已accepted并部署，当前无需返修或再写泛审；保留PR16与原交付，等待用户真实结果。** 如遇运行报错，Codex再给明确最小修复项，不先追加真实作业。
