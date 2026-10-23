# Learning Not to Act

独立的方法研究仓库：研究外部过程提前完成部分任务后，如何让冻结VLA基于当前观测确定剩余目标，并在保留已有成果的同时完成任务。

当前候选方法：**独立实体/关系选择器＋可撤销证据历史＋冻结VLA语言执行接口**。工作名EGRS仅作设计描述，不表示方法效果或新颖性已经验证。

2026-10-23：[016完整软件实现](collaboration/tasks/016_egrs_full_implementation.md)已验收，固定实现为[PR #2 / 5a77f158](https://github.com/No1dry/Learning-Not-to-Act/tree/5a77f158229442d9a9ee95ba828b371dfc4c995a)，代码和独立selector环境已部署。当前实现分支在其基础上增加[017离线批量候选和人工审核管线](docs/offline_pipeline.md)，入口为 `python -m egrs.offline --help`。017请使用Codex审阅交付的增量PR提交；旧5a77f158不含017，PR未自动合并到main。真实数据处理、教师调用、人工确认、训练和新方法评测本轮均为0。

## 从这里开始

- [完整方法设计v1](docs/research/2026-10-21_remaining_goal_selector_full_design.md)
- [016：已验收的完整实现](collaboration/tasks/016_egrs_full_implementation.md)
- [016最终验收](collaboration/reviews/016_round2.md)
- [017完整离线入口、文件和逐阶段命令](docs/offline_pipeline.md)
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

017软件与定向CPU/fake测试由X交付，下一步由X／控制器交付原PR #2增量，外部协作Codex审阅并准备隔离部署；不自动合并PR或运行真实阶段。用户随后分别启动真实数据准备、候选推理、人工确认、训练和模型评测。工具记录实际确认/修正数与UI观察时间，不承诺55—80人时或候选节省时长；软件通过不代表真实标签覆盖或研究效果已经验证。
