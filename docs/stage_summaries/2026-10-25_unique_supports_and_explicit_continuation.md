# 029：重复支持标签修复与保留已完成结果的续跑

## 事实与责任

028正式运行于2026-10-25 01:16北京时间技术暂停。已完整完成basket的s000/s001两条，均为模型失败，完成子集SR=0%；合计2/80=2.5%（固定100计划为2%）。s002在q3生成重复支持标签`["entity","entity"]`，原validator正确拒绝，不能计为模型任务失败。此前有限验证没有覆盖这个约束遗漏，属Codex实现遗漏；旧失败、原3个attempt和已完成2条不改。

用户要求下一步并延续Codex直接修复/必要真实复核的授权；整批评测仍由用户启动，X无需返修。

## 修复与实测

生成语法改为无放回的支持标签集合，保留全部325种非空有序子集，schema同步uniqueItems。不是在输出后删除重复、添加证据或放宽校验。grammar版本`egrs.visual-evidence-first.v4`；原贪心快路径、证据先行、权重/视觉prompt/原判据和评分均保持。

Codex复用原s002的q1/q2/q3无损观测及先前模型预测/命令重建失败请求：6张图逐一hash对应；原/新均2766输入tokens，新生成666 tokens，原wrapper/JSON/schema全部通过，supports无重复，进程正常退出，含冷加载168.65秒。没有仿真、动作或训练，不声称已证明视觉判断正确。

36项受影响CPU/fake通过（100%，42.50秒），包括全部合法标签排列、重复/未知/空标签拒绝、贪心掩码等价、原默认100编排、技术暂停、续跑及数据绑定。325种组合和fake环境均不是GPU/真实仿真实验。

## 显式续跑和SR显示

新增`--continue-from CLOSED_RUN`，新目录只运行未完成episode，已完成的success/failure/unknown全部保留，不按效果挑选。检查固定来源/状态、底座、checkpoint、memory/selector配置和原raw/sidecar/video。原技术失败尝试留在旧目录和lineage；s002由用户显式从原初态重试，不伪造中段恢复。原2条视频/数据不复制覆盖，也不重新调用模型。

续跑按原core汇总父结果+新增结果，保持100计划分母、80可用来源和20缺来源；每条父结果记录原method SHA及文件hash，新增结果记录029 SHA，不声称80条都由029重新运行。历史技术尝试单列，旧失败报告不倒改。后续再续跑可递归引用已关闭lineage，所有已完成时不创建模型/环境；旧数据改动或状态不一致会在模型创建前拒绝。

CPU复核包括：2条失败仍继承、仅跑剩余8条fake、sidecar编号正确、合计8成功/2失败不丢失败；全部已继承时无模型/环境；篡改父文件与改状态拒绝。新增控制台`[SR/live completed]`按已完成有效episode显示实时SR、inherited/new数，最终同时打印完成子集和固定100分母SR，不改原summary主指标，不向policy提供真值。

## 部署及交接

实现[PR #8](https://github.com/No1dry/Learning-Not-to-Act/pull/8)，固定commit `5af83dcba2c834689d0fd17a61bc93574c0a0b83`，未自动merge。release源码hash `3c6a48abd2b8580536b2e8f7119112e4e690418ca98cd1d167d8468fb4228fc2`；诊断完整hash `a90d11e7cc2b3df38835576e87089cbb1f676bf99e761ae3a4b3d2dc8138af2a`。二者仅评测编排等不同；实际使用的structured、selector init、encoding、model、prompt五文件SHA逐一完全一致，因此复用真实模型证据，不为入口修改再跑GPU。

隔离部署029-codex-v1；三解释器方法源码hash一致，仅更新方法包，不升级依赖或改原代码目录/权重。源码归档SHA `7ec3af7edd7374d4823a5b79ba3a725e116d728f689e1e79ce4dd1203742c6ed`；wheel SHA `f3e20f3bfb363cb744c267546c940abea7aa9ed1c86fce5231926e4680224907`。

真实服务器文件级续跑预检passed：models_loaded=false、simulation_created=false，100计划/80可用/2继承/78剩余，下一条basket_s002_10；原2条已核验，未创建正式新输出或代启续跑。完整conda/venv/python命令已准备。

修复/部署准备100%；总评测已完成2.5%（2/80），新78条执行0%。下一步用户启动新命令，Codex分析交回结果。模型仍可能判断错误，不宣称方法有效或整批后续必不出错。旧结果及诊断全部保留，本轮无删除/清理。
