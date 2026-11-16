# Task044软件交付：原版官方SOG10提示词诊断

2026-11-16，X。方法库`No1dry/Learning-Not-to-Act`，实现`8259a1040b0a83551678db5cbb7849c836bac090`，依赖accepted PR17@`7d28d515`及main@`5e48028`批准工单；分支`x/task044`、新PR base=`x/task042`，旧PR未自动合并。

软件/定向CPU-fake交付100%，待Codex验收；部署、真实模型/仿真/训练/评测0%。只新增隔离`egrs.prompt044`、两模板、串行脚本、测试与文档；原模型/训练/评分/bridge及全部旧证据不改。

冻结18句只在原生predict语言边界使用，原九任务同90个10初态、完整A+B二元评分及A保护保持。native SOG10不用H0/H1等研究权重，原RGB/proprio/native封装、H520/chunk8/seed7/全视频不变。每组新worker/90次reset/≤5850predict，持久审计记录真实输入串及SHA；P1正常完整报告后才P2，失败停、现场留、新输出/marker拒重复。P0仅历史22/90 aggregate-only，无基线重跑。

主组80项CPU/fake通过（新policy21/eval20/entry19＋原bridge/proxy20），另4项原reader与A/炉子约束通过；完整fake90→90和首组失败不启动第二组已覆盖。历史fixture/TDD红灯保留，未放宽源或物理评分。详细命令、测试数量、失败经过、限制、源码与证据链接见[044回复](../../collaboration/responses/044_round1.md)、[机器证据](../../collaboration/evidence/044_cpu_fake.json)和[完整运行命令](../task044_usage.md)。

批准投影未给字段定义，使用完整原plan文件SHA＋expected10＋逐源exact compare严格绑定，不编造未知投影匹配。CPU/fake不证明真实收益或生产运行成功。下一Codex验收、隔离文件部署/填路径，用户一条串行P1→P2正式180；不额外prepare/plan/MVP/标签/00/新seed/基线。本轮无SSH、部署或真实作业，无删除待删`[]`。源码、关键文档/证据、远端PR精确head另作本地SHA备份，旧阶段原样保留。
