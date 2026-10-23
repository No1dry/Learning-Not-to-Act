# 017 Round 1：Codex软件验收

日期：2026-10-23。固定实现：[PR #2 / c6840ae6](https://github.com/No1dry/Learning-Not-to-Act/tree/c6840ae6c27429c8a6eb27a4e937927f4f934202)。比较基线5a77f158；[X交付原文](https://github.com/No1dry/Learning-Not-to-Act/blob/c6840ae6c27429c8a6eb27a4e937927f4f934202/collaboration/responses/017_round1.md)。

**accepted；017完整离线管线软件与定向CPU/fake范围closed，无需X继续返修。**

- 固定来源/来源split、窗口和稠密query正确，不替换gap、不按模型成败选样本。
- 7B教师与3B学生身份分离；候选一次加载、只消费合法过去历史，失败保留null/未尝试，不伪造UNKNOWN或人工标签。
- 字段/完整证据明确确认后才监督；陈旧确认与immutable输入变更被拒绝，部分监督不冒称全量ready。
- Codex独立运行受影响组：**59/59 passed，100%，2.27秒**。只用合成小HDF5、toy/fake，未重复原runtime/物理证据。
- 29份增量文件Git blob SHA均与固定head吻合。最终wheel重新构建并在checkout外隔离安装，static plan/HTML资源可用；不冒用X较早wheel作最终证明。

## 合成浏览器核对的准确边界

已验证字段确认、完整evidence确认、改bbox自动撤销关联确认，以及触发导出后的成功提示。浏览器下载事件超时，未取得该次实际导出JSON，**不声称完成浏览器导出文件→Python导入的端到端证明**；已有CPU测试覆盖后端导入/最终mask。没有可证实的软件故障，不据工具限制增加返修门槛。fixture不是研究标签。

## 部署及研究状态

Codex已将c6840ae6放入独立新代码目录，安装最终wheel到原独立selector环境，服务器offline help/static plan通过；旧代码与VLA环境保留，PR未自动合并。后来SSH端口拒绝连接是新的连接状态，不倒改既有部署成功证据。

20个原始文件本地下载与服务器SHA校验100%；这只是字节搬运，真实inventory/抽帧、教师调用、人工研究标签、训练/eval仍为0。用户另已授权固定7B快照的本地下载/上传，不授权推理。阶段总结见[017总结](../../docs/stage_summaries/2026-10-23_offline_pipeline_acceptance.md)。

下一步操作和执行者：Codex完成权重搬运及具体命令；用户恢复SSH连接后亲自启动各真实阶段。X本轮无需返修。
