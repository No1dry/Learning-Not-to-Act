# 037-v2收敛与038实现交接

2026-11-06，Codex。本轮仅研究决策/文档交接和两个现有JSON配对的只读数值检查，无实现改动/模型/仿真/新标签sidecar/训练/eval。

## 决策

接受X037审阅的裁决不变，原任务review closed，原037不直接实施、PR12不自动合并。新候选[037-v2](../research/2026-11-06_task037_v2_task_control_factorization.md)将“任务上下文在机器人重置下保持”与“动作按接收端机器人状态重算”分开；保留003数据增强与036原策略保持，删除必须先建完整NEED/PRESERVE实例头/静态D-K规格的前提。

连续z接单VLA动作hidden残差，计数0/1/2只作弱语义锚，不作stop/动作硬gate。训练交换同世界pair的z、保留各端H/proprio/真实动作；不强制动作一致。不是严格可识别分解、完整成果保护器或zero-shot保证。MIR/Invariance Co-training/ReViP等近邻已明确引用，不把不变性/换名字/基础引理当新颖性证明。

## 新取得的证据

[记录状态检查](../../collaboration/evidence/037_recorded_pair_state_inspection.json)：basket demo2的normal158/ten0、drawer demo0的normal187/ten0，排除time/实际机器人索引后，记录非机器人坐标最大差均0；robot坐标实际不同，active目标均true,false。来源五JSON的SHA记录。仅两个现有样本，没有图像像素/全量配对统计/新监督，不从样本宣称全数据通过。全量有效pair由新索引入口一次统计，不重放旧资格。

## 交接与预算状态

[038工单](../../collaboration/tasks/038_task_control_factorization.md)已交X直接实现/定向CPU-fake，不再一轮泛审。网络/损失/数据标签与pair/原策略旁路/共享predict/保存恢复/两组对照/最少测试均给出；X不得真实作业或生成真实标签sidecar。Codex收到代码后建议式审查、隔离部署，用户亲启真实作业。

建议C0/C1同网络、标签、全部图像、顺序与每组1000：总2000更新，reference≤18048，student≤49120，两模型10/00各90，共360新模型episode，零新仿真生成。**这不是已获批准的预算，用户尚待确认**；原三组3000/81216/540及036续训依旧未批。两组测整包约束，不拆分宣称align/swap各自收益，旧035/036不是匹配对照替代品。

研究规格与GitHub交接100%；038代码/实际标签准备/训练/eval0%。新颖性与效果open；下阶段执行者X实现，用户此刻无须启动。035为10最高54.44%/00 73.33%，036为50.00%/82.22%，原24.44%/86.67%，所有证据不改。

关键文档/证据按精确发布commit读回、SHA本地备份及manifest登记；本地收据保存commit，不自引用未知hash。旧资料/开放任务、PR、源码/原始数据全部保留。待删文件=[]；无自动merge/部署/真实作业。
