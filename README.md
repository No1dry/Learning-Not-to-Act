# Learning Not to Act

2026-11-06：Task038实现037-v2的单VLA任务上下文/控制重算，新增文件索引、C0/C1训练恢复和共享预测评测入口。见[使用与完整命令模板](docs/task038_usage.md)及[实现工单](collaboration/tasks/038_task_control_factorization.md)。基于已验收036 PR11，真实索引/训练/360条评测预算仍待批准；下方EGRS内容保留作历史，最新范围以[STATUS](collaboration/STATUS.md)为准。

2026-11-04 当前候选实现：036三池原策略保持，复用035数据，以同底座旁路新增LoRA产生普通观测参考动作；新模型10/00各90全新评测。见[配置与完整命令](docs/retention036.md)及[036交付](collaboration/responses/036_round1.md)。当前仅软件与CPU/fake，真实训练/新模型评测未启动。

2026-11-03 教师v2恢复入口：按批准引用复用旧8条，仅重建固定73来源，见[配置与完整命令](docs/trajectory_teacher_v2_recovery.md)。正式评分、原分组与训练配方保持；当前交付仅软件和CPU/fake。

2026-11-03 当前候选实现：035 机器人起点变换的完整10轨迹生成、7:3混训，以及同一adapter的固定10/00各90条评测。
见[生成与混训完整命令](docs/trajectory_augmentation.md)、[双条件评测](docs/trajectory_augmentation_evaluation.md)
和[035交付回复](collaboration/responses/035_round1.md)。复用已验收030主体，独立035分支/PR；当前仅交软件与CPU/fake结果，真实生成、训练与评测尚未启动。

2026-11-02 当前实现：030 v2 进度感知数据增强与 OFT 语言 attention LoRA 续训，
含数据索引导出、普通/增强两组训练和 A90/C36 普通 adapter 评测入口。
见[完整命令与依赖](docs/augmentation_commands.md)、[数据映射与证据](docs/augmentation_data.md)
及[030 v2 回复](collaboration/responses/030_v2_round1.md)。
本轮仅 CPU/fake 软件交付，未启动真实导出/训练/评测；034 二元报告独立复用。
以下 selector 内容保留为历史路线，不是030的前置依赖。


独立的方法研究仓库：研究外部过程提前完成部分任务后，如何让冻结VLA基于当前观测确定剩余目标，并在保留已有成果的同时完成任务。

当前候选方法：**独立实体/关系选择器＋可撤销证据历史＋冻结VLA语言执行接口**。工作名EGRS仅作设计描述，不表示方法效果或新颖性已经验证。

2026-10-23：[016完整软件实现](collaboration/tasks/016_egrs_full_implementation.md)已验收，当前含017离线管线的固定实现为[PR #2 / c6840ae6](https://github.com/No1dry/Learning-Not-to-Act/tree/c6840ae6c27429c8a6eb27a4e937927f4f934202)，代码和独立selector环境已部署。PR未自动合并，main暂不含该实现；运行请使用上述固定版本。真实训练、新方法评测均为0。

## 从这里开始

- [完整方法设计v1](docs/research/2026-10-21_remaining_goal_selector_full_design.md)
- [016：已验收的完整实现](collaboration/tasks/016_egrs_full_implementation.md)
- [016最终验收](collaboration/reviews/016_round2.md)
- [017离线管线验收](collaboration/reviews/017_round1.md)
- [017阶段总结](docs/stage_summaries/2026-10-23_offline_pipeline_acceptance.md)
- [软件与部署阶段总结](docs/stage_summaries/2026-10-23_egrs_software_acceptance.md)
- [015设计审阅裁决](collaboration/reviews/015_round1.md)
- [当前协作状态](collaboration/STATUS.md)
- [协作规则](collaboration/README.md)

## 三个仓库的边界

| 仓库 | 职责 |
|---|---|
| [Learning-Not-to-Act](https://github.com/No1dry/Learning-Not-to-Act) | 方法设计、选择器训练、证据历史、方法wrapper、方法配置与研究协作 |
| [LIBERO-Remain-Eval](https://github.com/No1dry/LIBERO-Remain-Eval) | 干净mask10 benchmark：任务、状态工具、评测、指标、视频及模型适配 |
| [LIBERO-Remain](https://github.com/No1dry/LIBERO-Remain) | 原benchmark与历史研究记录；原提交、PR、原始结果仍保留 |

本库依赖固定版本的benchmark，不复制并修改一套成功判据。未来运行记录方法版本、eval core版本、底座checkpoint、selector与配置身份。

初始eval core参考为 `No1dry/LIBERO-Remain-Eval@515e87d9b93ab838428791273a0f3020d6f56e9c`。其通用episode核心可接策略，但现成批处理仍是OFT参考流程；014通用入口由评测侧推进，不把尚未完成的支持写成已就绪。

## 已迁入的研究材料

- [原始模型实验结果](docs/research/2026-10-20_baseline_results.md)：结果副本，不改分数。
- [Codex四路线与组合](docs/research/2026-10-20_codex_method_proposals.md)
- [X独立候选原稿](collaboration/responses/methods_2026-10-20_round1_independent.md)
- [X与Codex方案对比](collaboration/responses/methods_2026-10-20_round2_comparison.md)

X两份原文保持原字节和署名。原PR #11并未因迁入而自动合并；独立稿的顺序/来源证据继续指向原固定提交，不能宣称严格盲法。完整设计和015仅修正仓库归属与链接。

迁移来源见[MIGRATION.json](MIGRATION.json)。本库不包含服务器凭证、旧实验大文件、状态包、模型权重或整套benchmark源码。

## 当前下一步

016/017软件与部署已完成，X无需继续返修。Codex准备实际数据来源、标签/资源选择和完整运行命令；真实标签、人力与预算仍需确认，不默认承诺55—80人时。真实数据准备、标注推理、训练和模型评测均由用户亲自启动，不先扩benchmark或训练FINISH。
