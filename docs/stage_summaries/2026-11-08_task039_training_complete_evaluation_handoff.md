# 039两组训练完成：末权重保留，进入正式360评测

2026-11-08，Codex。[R3](../../collaboration/reviews/039_round3.md)接受两组真实1000更新与固定末1000产物；软件R1/数据R2保持，X无需返修，PR14@113ded21不自动merge。C0/C1各100%、正常exit0，无残留训练进程。用户亲启并行从11-07 22:42:59到11-08 03:50:46（北京时间），总5h7m47s，训练主体各约4h53；Codex没有启动或停止训练。

两组adapter SHA e9d481030c35/6d340e991860，与identity字节hash匹配；完整training_state与各SHA匹配，末权重不同。selected均update-001000，同config（除arm）/新index b8587565/base_lineage/recipe；最终采样计数相同，不声称独立证明逐步时序因果。reference各9024/student各24560，共18048/49120，等于预算未超。C0/C1新dev10 L1为.129999882/.130077180，约.06%差非常接近，不是SR或C1有效结论；新旧dev人口不同，不跨数据比loss。

九任务305有效pair/130017行沿R2，新增三个任务监督已恢复，但白杯训练仅1父源3变体的限制保持。网络/loss/原基座/完整指令、双RGB/proprio与正式评分不改。本轮只读现有文件与保存29个末adapter/完整续训状态/metrics/配置/预算/实际eval配置/索引小记录，服务器与本地SHA一致；归档task039_training_complete_2026-11-08，manifest06bafa44。旧039中间checkpoint/生产大文件及035/036/038所有权重、分数、视频、失败保留，未下载全部原始数据。

评测文件准备100%，真实新模型eval0。原eval配置已经对应实际存在的各末1000，九任务来源/core/reporting/双bridge与038保持；不重建状态/基线、不重新训练或挑权重。新增[串行接力shell](../experiment_plans/scripts/task039_eval_both_sequential.sh)只bash语法/上传SHA核对，未执行。用户按[完整命令](../experiment_plans/2026-11-08_task039_dual_model_evaluation_commands.md)一条启动，C0正式summary/正常退出后自动C1，两组10/00各90共360、全视频、原H520/chunk8/seed7/评分，不自动重试/report或额外MVP。

后续比较以正式10/00 SR、九任务变化、同episode配对增失为准。训练阶段closed，真实效果/研究仍open；所有真实评测用户启动，Codex只文件/结果分析，X无实现任务。阶段关键文档/证据精确GitHub commit读回SHA本地备份与manifest；无清理/自动merge，待删=[]。
