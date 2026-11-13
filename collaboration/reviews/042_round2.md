# 042 Round 2：训练完成文件验收

2026-11-13，Codex。裁决：accepted，限已完成训练产物及后续评测文件接线。X无需返修；PR17固定7d28d515be610f33f959f36d25623e86796671ce不自动合并。软件R1裁决保持。

## 训练事实

F0、F1分别连续新增1000/1000=100%，四次保存，固定本阶段末1000；共同完整041 R0初值，祖代2000＋新增1000=累计3000。启动器在北京时间2026-11-12 21:30:07启动F0，11-13 00:57:05接F1，04:25:39两组COMPLETE，共6小时55分32秒；成功标记来自shell成功分支，未另取数值退出文件。无残留训练进程、控制台异常标记。

除臂、attention路由/合同与输出外训练配置相同，原040数据/index/dev/C1 loss不变；1000条日志更新连续，逐条sampling/batch摘要相同。这不是独立逐步tensor/RNG因果审计。实际32层LlamaSdpaAttention、bfloat16、Transformers4.40.1/Torch2.4.1+cu121及源SHA一致；F0 native padding-only，F1逐层禁止任务query读控制key，reference旁路合同保持。

| 项目 | F0 | F1 |
|---|---:|---:|
| 新增更新 | 1000 | 1000 |
| 原参考前向 | 9024 | 9024 |
| 学生前向 | 24560 | 24560 |
| 固定末dev10动作L1 | 0.116909468 | 0.119636011 |
| 固定末dev加权L1 | 0.068372321 | 0.074766576 |

总reference18048/student49120等于批准上限。dev误差不是SR，不因其高低换checkpoint、取消匹配对照或追加训练。

## 权重与备份

- F0 adapter：8afe299e47b0cde3ac9fb21f888a895b4fefaa0a8f64a15ee8f3cc10a8829d88
- F1 adapter：79ad5b7f78fe11ab0721c2b7e38b3f170a768f6dbba70b383ef24dd0f2fe0ac1
- F0完整训练状态：f5ee96efc72dcf93f2a68f978b3534a92c78424c78066b7330334251c1bef596
- F1完整训练状态：94a548e359ba90de6c94332003577051dcac10cff51aa3519d7d160424156ea3

实际权重SHA与identity一致，完整状态SHA与附带文件一致；只验字节，不反序列化训练状态。两末完整状态及metrics/config/账本/控制台/实际eval配置/原index小记录共32文件514407216字节，服务器到本地SHA一致，保存清单SHA ec0667263a5d3bf38998f728cc99e49324c5a6758d210614380e18c68b5aed34。旧数据、中间checkpoint、失败与历史署名保持。

## 下一步

[用户正式评测命令](../../docs/experiment_plans/2026-11-13_task042_dual_model_evaluation_commands.md)：直接使用原已部署启动器，F0正式180及完整报告正常后接F1正式180，共360。两模型分别10合规90＋00官方90，原来源/runtime/core/reporting/双bridge/评分/全视频/预算保持；实际配置绑各自末1000，脚本SHA与原部署相同、仅bash语法核对未执行。快照时eval输出与marker均不存在。

不重prepare/index/plan/MVP、来源重复资格、GPU预检、基线或训练。正式入口自己绑定实际权重建plan；执行100%后仍可能在同进程核验，summary/report与正常结束才算完成。只用户启动，Codex本轮无新模型/物理/标签/索引/训练/eval，未启停作业、未删除或合并。训练交付closed，真实SR与研究结论open。
