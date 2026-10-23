# 016 Round 2：软件范围验收

日期：2026-10-23。对象：[PR #2](https://github.com/No1dry/Learning-Not-to-Act/pull/2)，固定head `5a77f158229442d9a9ee95ba828b371dfc4c995a`；[X回复固定稿](https://github.com/No1dry/Learning-Not-to-Act/blob/5a77f158229442d9a9ee95ba828b371dfc4c995a/collaboration/responses/016_round2.md)。

**accepted；016完整软件实现与定向CPU/fake范围closed。** Round1唯一P2已修复，不要求进一步返修。

- evidence按条目实际叶字段解析继承/覆盖，完整human或reviewed_candidate确认项保留。
- weak/未确认条目在teacher forcing前删除；未删除的同级项不被连坐。
- provenance读原索引，监督pointer写过滤后的索引；最终token labels已覆盖重映射。
- human UNKNOWN与no_role保护不退化。

独立复现受影响组：**30/30 passed，100%，1.86秒**，其中原24项＋新增6项。测试使用Python3.12.7、CPU toy/fake和原固定参考core；没有真实模型或仿真。五份增量文件的本地Git blob SHA与固定head一致，避免用错提交。未重跑无关runtime等组；沿用Round1仍适用的23项通过证据，不把它们写成这次重新运行。

完整方法软件已有数据/标签工具、真实LoRA训练与恢复入口、独立selector/actor、可撤销历史、冻结语言桥接和原core薄接入。验收不等于真实processor/CUDA可用或方法有效。

真实数据准备、标注、processor校验、研究模型forward、训练、新方法eval仍为0。014批处理对接、标签来源与真实资源另行推进，不再作为016返修门槛。两项非阻塞建议仍不要求顺带修改。

PR未自动合并；本轮没有部署、安装环境或启动真实阶段。阶段总结见[软件阶段总结](../../docs/stage_summaries/2026-10-23_egrs_software_acceptance.md)。

下一步操作和执行者：Codex准备固定版本部署与具体数据命令，并就尚未决定的标签/资源给出简短可执行选择；用户确认并亲自启动真实阶段。X本轮无需继续返修。
