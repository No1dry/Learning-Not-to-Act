# Task038：037-v2软件与CPU/fake交付

2026-11-06，X。直接执行038；新包实现一次文件索引、共享OFT任务上下文/控制重算、C0/C1固定训练/恢复与原双条件评测。实现commit`b5849e4e4f7f56b888922e1267870126f5368ccf`，依赖accepted036 PR11@205d6530；保留所有旧证据，未自动merge。

最终受影响CPU/fake130通过、0失败/错误/skip。独立审查0 Critical/1 Important，抽屉/微波炉空required-open证据漏检已集中修复，scoped复查通过。没有把真实pair覆盖、方法收益或软件交付当研究结论；Windows原子JSON写的早期fixture失败与后续边界隔离有完整记录。

- [一次038回复](../../collaboration/responses/038_round1.md)：接口、必要选择、测试和后续。
- [使用及完整命令模板](../task038_usage.md)：新环境/worker方法包部署、index/train/resume/eval/report。
- [CPU/fake JSON](../../collaboration/evidence/038_cpu_fake.json)、[JUnit](../../collaboration/evidence/038_cpu_fake.junit.xml)。

实现/受影响测试交付100%；Codex审查待完成。真实数据准备/标签sidecar、模型、仿真、训练/eval及部署均0%，所有035/036结果/权重/视频/失败/raw和PR12保持。无删除或自动merge。下一Codex审查、隔离配置/部署和预算说明，用户批准后亲自启动真实作业；当前模板不是实验许可。提交后精确commit读回校验并本地备份，记录SHA。
