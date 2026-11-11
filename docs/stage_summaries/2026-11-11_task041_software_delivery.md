# Task041：匹配C1阶段与039旧10保持软件交付

2026-11-11，X。实现`c51df70e597021d2c33a5bca013feabf723d879f`，基于acceptedPR15@428c13585cebac1d6c90fd86a205e914caa2bb8f，同步main工单be43704（本地merge6fe4bb9）；新PR保留未合并依赖，不自动merge。

`egrs/retention041/`新增严格配置/现成040数据及旧003队列、独立039参考分支、040完整参数初始化、R0/R1新stage C1训练、三前扣账本、完整保存恢复和单学生原180评测。两臂都是C1、新optimizer各新增1000；仅R1对原12ten中前最多4个明确旧003 train位置加.10 masked保持，22student/8base-reference不变。全部参考先于学生图，冻结骨干共享、039完整新增分支独立，模式/hook/cache/checkpoint/requiresgrad/RNG精确恢复。`task_control/oft.py`仅可选显式modules扩展且默认保持；旧reader/原数据/采样/dev/评分和全部权重/失败/历史署名不改。

最终root定向CPU/fake166通过，0失败/错误/skip，四组65/32/43/26，未跑全库/多平台/真实MVP。tiny真实checkpoint autograd、基础R0/R1匹配、0选择R1=R0、少于4实际均值、同一图旧10梯度、教师不进优化器、失败前扣、完整中断恢复/复制run拒绝与新schema原180合同覆盖。独立whole-diff只读审查0 Critical/Important/Minor，读到实际JUnit但未重复测试。初始temp setup、TDD红灯与fixture/EOF格式修正保留，不伪装通过；CUDA数值/显存/速度、真实生成/训练/效果未验证。

- [041回复与常用命令](../../collaboration/responses/041_round1.md)。
- [完整用法](../task041_usage.md)：环境与固定输入、R0/R1单独/串行训练、新stage和resume区别、原040配置派生新eval、nohup与进度。
- [CPU JSON与完整命令](../../collaboration/evidence/041_cpu_fake.json)，[数据](../../collaboration/evidence/041_cpu_data.junit.xml)/[参考](../../collaboration/evidence/041_cpu_reference.junit.xml)/[身份评测](../../collaboration/evidence/041_cpu_identity.junit.xml)/[stage](../../collaboration/evidence/041_cpu_stage.junit.xml)JUnit。

实现/定向测试交付100%，Codex验收pending；部署、真实数据/标签/索引生产、模型/仿真/训练/eval均0%。预算已批准：两臂各新增1000、参考共≤22048/student≤49120、新模型360，仍仅用户亲启；原04058.89/86.67与03958.89/85.56及所有已完成run保持。祖代1000与本轮新增1000分记，不旧040resume；主比较R1−R0，R1−040混有额外训练/优化器重启。无跨版本保持等于A硬保护/ICML创新或SR保证。

下一Codex审查、隔离部署/填写实际路径，用户启动已批真实作业，Codex审阅产物；X本轮不部署/SSH/启停作业/自动merge/删除。发布后精确head/tree及关键blob读回，源码ZIP、回复/用法/阶段/CPU证据、发布/读回/审查报告与SHA256 manifest本地保存在`research_archive/Learning-Not-to-Act/task041_delivery_2026-11-11/`；范围仅软件/文档/CPU证据，不冒称备份服务器真实数据或权重。
