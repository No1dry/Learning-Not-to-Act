# Learning Not to Act

独立的方法研究仓库：研究外部过程提前完成部分任务后，如何让冻结VLA基于当前观测确定剩余目标，并在保留已有成果的同时完成任务。

当前候选方法：**独立实体/关系选择器＋可撤销证据历史＋冻结VLA语言执行接口**。工作名EGRS仅作设计描述，不表示方法效果或新颖性已经验证。

目前是完整方法设计与集中可实施性审阅阶段：还没有新增方法实现、已训练选择器或新方法评测成绩。不是运行软件包或一条命令可启动的新系统。

## 从这里开始

- [完整方法设计v1](docs/research/2026-10-21_remaining_goal_selector_full_design.md)
- [015：X当前需要完成的设计审阅](collaboration/tasks/015_remaining_goal_selector_design_review.md)
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

X在**本仓库**回复015的一轮集中可实施性审阅，Codex形成后续实现工单。完整实现不以先跑MVP为门槛。真实数据恢复、标注推理、训练和模型评测仍由用户亲自启动。
