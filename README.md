# Learning Not to Act

研究外部过程提前完成部分任务后，VLA能否根据当前观测重新确定剩余目标，在保留已有成果的同时完成任务。

Task042软件已交付、待验收：[回复](collaboration/responses/042_round1.md)与[完整命令](docs/task042_usage.md)。基于accepted PR16，F0/F1均为041 R0完整初始化的原C1，各新1000；同显式SDPA，F0保留native双向，F1仅增加T读C禁边。109项定向CPU/fake通过，未部署或启动真实实验；最新状态见[STATUS](collaboration/STATUS.md)，下方旧交付/结果保留。

Task041软件已交付、待验收：[回复](collaboration/responses/041_round1.md)与[完整命令](docs/task041_usage.md)。R0/R1均从040完整权重初始化、基础均C1，各新增1000；仅R1增加039旧10行为保持，原数据/采样/评分保持。本轮未部署或启动真实作业，旧039/040结果与工件保留。

Task040软件已交付、待验收：[回复](collaboration/responses/040_round1.md)与[完整命令](docs/task040_usage.md)。新增三任务demo_20..39的train父源覆盖，新normal只用于生成/pair；复用原039数据与dev/参考池，单C1固定1000。原算法与评分保持；本轮未部署或启动真实作业，以下039已完成结果保留。

## 新接手从这里开始

**[项目主交接文档：截至039，含目标、方法、数据、结果、代码/服务器位置和下一步](docs/handoffs/2026-11-08_project_handoff_after_task039.md)**

配合[最新STATUS](collaboration/STATUS.md)和[AGENTS](AGENTS.md)阅读。主交接文档第0节是一页状态，第11节是下一步只读失败分析，第14节有可转发给新agent的prompt；不需要从旧聊天或早期计划重新推断当前路线。

## 当前状态：039正式评测已完成

正式benchmark为9个LIBERO-10复合任务，10/00各90条/模型。039的数据准备、C0/C1各1000更新和两模型共360条正式评测已全部完成，两个eval正常退出。

| 模型 | 10合规SR | 00官方SR |
|---|---:|---:|
| 原始SOG10 | 24.44% | 86.67% |
| 038 C1 | 55.56% | 84.44% |
| 039 C1 | 58.89% | 85.56% |

[039阶段总结/九任务表](docs/stage_summaries/2026-11-08_task039_final_results_coverage_recovery.md)、[机器结果](collaboration/evidence/039_final_results.json)、[R4](collaboration/reviews/039_round4.md)。当前下一步是分析已有白杯/双壶等10失败证据，再确定针对性方法；没有已批准的新一轮实验，不能重复039或自动续训。

## 当前方法和实现位置

当前路线是在OpenVLA-OFT SOG10上进行10真实轨迹增强、普通观测原策略保持，以及单VLA内部任务上下文z/动作残差的C0/C1对照；没有在线外部VLM/选择器或FINISH头。旧EGRS选择器方案是历史，不是现在的默认入口。

**main目前主要承载决策/协作文档，不能只克隆main就假称已拿到运行实现。** 最新已验收代码是未自动合并的[PR14固定head113ded21434a06e2cdc156e5d6283a11c3f15488](https://github.com/No1dry/Learning-Not-to-Act/tree/113ded21434a06e2cdc156e5d6283a11c3f15488)，含accepted038/036等依赖。运行/源码位置及固定core、权重SHA见主交接文档；不要自动merge依赖PR。

## 分工与仓库边界

- 用户亲自启动、运行、监督所有真实模型/仿真/标注/训练/eval。
- Codex负责研究决策、详细需求、建议式审查、文件准备部署、完整命令和结果归档。
- X负责实现和受影响CPU/fake测试，经GitHub交付；DeepSeek已退出，历史署名保留。
- 实际实现需求必须进入`collaboration/tasks/`并给用户短prompt；不以泛审/全库检查/真实MVP拖延研究，不覆盖旧数据或重写旧分数。

| 仓库 | 职责 |
|---|---|
| [Learning-Not-to-Act](https://github.com/No1dry/Learning-Not-to-Act) | 当前方法、训练/评测接线、研究与X协作 |
| [LIBERO-Remain](https://github.com/No1dry/LIBERO-Remain) | benchmark定义、冻结core/协议及历史研究记录 |
| [LIBERO-Remain-Eval](https://github.com/No1dry/LIBERO-Remain-Eval) | 给外部VLA评测的精简分发库；不是无条件通用全90 driver |

## 历史材料

早期016/017选择器/离线管线、015设计、四路线讨论与迁库记录均保留，见[迁移来源](MIGRATION.json)、[早期README事实快照](https://github.com/No1dry/Learning-Not-to-Act/blob/f6e9b8b7668ab1c20505a2b162ccb7d1b8e93aa2/README.md)和各阶段总结。其“当前方法/0%/待启动”属于当时阶段，不覆盖新的STATUS/主交接文档，也不授权重新运行旧命令。X原稿与Git历史不改，不因路线变化抹掉历史证据。

本库不提交服务器密码/token、模型权重或原实验大文件。039结果/权重/少量配对原视频已在用户本地归档，精确路径与备份manifest在主交接文档内。
