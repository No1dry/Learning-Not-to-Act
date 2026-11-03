# 035｜非阻断评测报告小增量：显示实时SR、避免循环全量重读

2026-11-03，Codex→X。基于[035 R1](../reviews/035_round1.md)，在PR10中或独立小增量PR实现即可。**生成、混训、双条件计分主体已accepted，不返工；本项不阻塞Codex数据准备或后续用户生成/训练。**

## 具体问题

当前`trajectory_augmentation/evaluation.run`在126个任务单元后各调用全量`inspect_run`，finally和return又各调用一次，原reader会重复读取全部历史raw/证据/视频。控制台只打印condition/task/status，没展示完成百分比与两类SR。冻结core `_run_task/runner`本身没有提供这些控制台数值。

## 最小改动

1. 每个新任务单元结束至少打印：condition、task、该条件已完成/90及百分比、该条件成功/有效已完成的live SR百分比；同时区分总180完成进度、技术错误/未完成。不把00原生与10合规混成一率。任务内部若已有可复用ledger更新可补更细输出，但不为逐step回调修改冻结runner或建后台监控服务。
2. 循环中只用原reader验证**新完成**的任务/记录一次，再汇总已验证记录；不在每次更新时重读此前全部raw/视频/source。保留source/adapter/base/任务身份检查，缓存的live结果明确为进行中值。
3. 正常结束时做**一次**现有完整`inspect_run`核验后才输出正式最终分数；不要finally/return再重复跑相同全量核验。中断保存已有结果与缺口，禁止自动重跑剩余episode。独立`report`仍走完整原reader，历史文件被篡改不能靠缓存通过正式报告。
4. 继续复用034二元10与原core原生00评分、同一adapter和原90/90来源；不改物理/阈值/端点/prompt，不写第二评分器，不通过少验证新任务来提速。

## 精简CPU/fake与交付

用已有fake队列捕获控制台验证两类百分比/SR正确；spy证明每新增单元只读自身、最终只做一次全量，独立report对篡改原工件仍拒绝。无需跑全库、做真实profile或启动任何模型/仿真/eval。

回复`collaboration/responses/035_live_reporting_round1.md`给commit/PR、受影响CPU/fake和实际日志样例；原035主体验收保持，不因日志目录/风格扩返修。Codex审查后在正式模型评测前单独部署；不热改当前目录或改变已有生成/训练数据。真实实验仍仅由用户确认启动。
