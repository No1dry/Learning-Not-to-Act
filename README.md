# Learning Not to Act

独立的方法研究仓库：研究外部过程提前完成部分任务后，如何让冻结VLA基于当前观测确定剩余目标，并在保留已有成果的同时完成任务。

当前候选方法：**独立实体/关系选择器＋可撤销证据历史＋冻结VLA语言执行接口**。工作名EGRS仅作设计描述，不表示方法效果或新颖性已经验证。

2026-10-22：015设计审阅已接受；本分支交付[016完整软件实现](collaboration/tasks/016_egrs_full_implementation.md)，等待Codex集中审查。包含独立`egrs`包、数据/标注工具、LoRA训练与恢复、推理worker、证据历史、actor桥接及日志。仅完成定向CPU/fake验证，真实数据、标注、训练、模型评测均为0。

## 从这里开始

- [完整方法设计v1](docs/research/2026-10-21_remaining_goal_selector_full_design.md)
- [016：X当前需要完成的完整实现](collaboration/tasks/016_egrs_full_implementation.md)
- [015设计审阅裁决](collaboration/reviews/015_round1.md)
- [当前协作状态](collaboration/STATUS.md)
- [协作规则](collaboration/README.md)
- [安装、方法配置、core接入与日志审计](docs/runtime.md)
- [数据格式、标注、训练/恢复与推理命令](docs/data_training.md)
- [016交付回复与验证范围](collaboration/responses/016_round1.md)

## 软件入口

```sh
python -m pip install -e .
python -m egrs --help
python -m egrs.datacli catalog
python -m egrs.selector.train --config configs/selector.json --dry-run
```

以上仅安装轻量方法包、查看静态目录/计划，不运行真实模型。selector使用[独立依赖](requirements-selector.txt)；所有actor保留各自原环境，并安装本方法包。数据不齐会报告缺口，公开库不含权重/状态包/已确认标签。完整参数、五种方法消融和各actor适配见运行文档。

方法依赖原core的传感器白名单、worker、runner、证据和指标，没有复制评分器。本次核验的是明确标注的旧库固定参考导出；新eval私有库pin及014通用批处理仍需联调。因此，软件可安装并运行CPU/fake路径，不能宣称git clone后已具备真实全模型批量评测条件。

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

Codex审查本分支的016实现并对接014、部署及真实阶段命令；用户确认标签与资源后亲自启动。X负责后续有依据的实现修正。本PR不自动合并，不以MVP或55—80人时人力承诺作为软件交付门槛。
