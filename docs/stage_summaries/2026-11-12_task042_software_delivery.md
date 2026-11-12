# Task042软件交付：统一SDPA的F0/F1

2026-11-12，X。实现`03e0efcd5a999c77549ed8d7b549a29feb731c13`，基于accepted PR16@`e8dcf87979d14d081666629a2de3483629a4f59c`，同步main042工单及源审计。新042分支保留未合并生产代码链，不合并旧PR。

F0/F1均为完整041 R0初始化的原C1，各新1000更新（祖代2000→累计3000）。相同实例级显式SDPA，F0原native padding-only双向，F1只禁T query读C key；每层最终primitive和每条样本checkpoint使用完整独立mask，原Parameter/动作选择保持，原SOG10参考旁路。数据/原C1配方/采样/dev/正式评分保持，严格新schema/实际runtime/完整保存续跑及两独立预算已接入。

定向CPU/fake109通过，0失败/错误/skip；独立集中审查未发现阻断缺陷。包含真实tiny SDPA/autograd/checkpoint、原参考顺序、完整初始化/恢复及各臂fake180。没有真实模型/数据生产/仿真/GPU/训练/eval，没有部署或旧基线重跑；CPU证据不证明SR/物理保护/生产性能。

[交付回复](../../collaboration/responses/042_round1.md)、[完整命令](../task042_usage.md)、[机器证据](../../collaboration/evidence/042_cpu_fake.json)、[独立审查](../../collaboration/evidence/042_independent_review.md)。实现/定向测试100%，部署/真实训练/评测0%，待Codex验收。下一Codex审查、隔离部署和填配置，用户启动两训练及正式360；主比F1−F0，无自动merge/重试/追加预算/清理。
