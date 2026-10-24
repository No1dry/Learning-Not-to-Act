# Selector首次训练完成：结果与评测交接

2026-10-24。用户启动的024正式selector训练已100%完成，status=complete；3 epochs、369次optimizer更新，每轮1958训练查询和471验证查询全部执行。3个checkpoint均有COMPLETE。Codex只读取训练产物，没有代跑、追加或重启训练/评测。

| Epoch | Train mean loss | Dev token-mean loss |
|---|---:|---:|
| 1 | 0.2821453 | 0.2074258 |
| 2 | 0.1808220 | 0.1753629 |
| 3 | 0.1545209 | 0.1675368 |

按最低dev loss选择checkpoint-3，未使用测试集成绩选择。训练与验证loss均连续下降；两列聚合权重不同，不直接当作generalization gap。没有任务成功率结果，loss下降不能替代系统有效性结论。

固定Qwen2.5-VL-3B基座和processor revision 66285546d2b821cf421d4f5eb2576359d3770cd3，语言LoRA r16/alpha32、lr1e-4、累计batch16、history与role均开启；VLA没有训练。输入文件SHA与024已验收导出一致：train c696a50e1c56a783cd1829d681b491f8a362f2b24be71d78859f164bf8a3fe64，dev 29178e19fbfa9514dec378e1efce71ea594ab5c4edcfa0958211c82dd3d84d26。

选中adapter SHA-256：e8ea45be6d466c6d3eacfe290eda14dd41f464a92aa13b2f09676c7d35aa82c8。选中state SHA-256：9ee11b8c28e9dbecd2f48b81762ea46bbe1eb38310ea0f0878b13ff241632867。Codex只读核对adapter三文件hash均与state声明一致。控制台PEFT词表提示为warning，未导致保存失败；不能把无报错或低loss当成模型效果。

## 评测状态与实际缺口

训练100%，新方法评测0%。下一阶段直接同一100条mask10正式评测，不新增数据、重训、MVP、FINISH或额外rollout；旧基线复用，指标及视频口径不变。

固定eval core的批处理仍假设顶层原OFT runtime，现有方法只有compose与单episode薄桥，不能仅换factory字符串就称批处理已就绪。评测对接没有在训练期间落实，是Codex准备遗漏；现在已将范围收窄为[025方法侧OFT批量接入](../../collaboration/tasks/025_oft_selector_batch_evaluation.md)，不要求先完成全模型通用框架。X补必要编排并做定向CPU/fake；不改冻结core或计分，不重新准备/回放原状态。Codex审查部署后给完整conda/python命令，真实评测由用户启动。

原logs、三个checkpoint、024标签和失败历史均保留，本轮不清理。训练原始status/epochs已复制到本地reports/selector_training024_result_2026-10-24/evidence/，本总结提交GitHub并本地归档。

下一步操作和执行者：X交付025评测入口；Codex审查部署；用户启动正式100条模型评测。
