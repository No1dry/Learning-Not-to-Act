# Task042：任务—控制信息隔离（TCIF），F0/F1正式对照

2026-11-12，Codex正式下达。用户在042方案和两组数值预算后明确回复**“按推荐的来吧”**，批准按推荐方案交X实现；[批准记录](../evidence/042_budget_approval_and_dispatch.json)。**X直接实现＋定向CPU/fake＋新PR/回复，不先泛审。所有真实数据/模型/训练/eval仍只用户启动。**

## 1. 范围与固定依赖

- 已批[042方案](../../docs/research/2026-11-12_task042_task_control_attention_firewall_proposal.md)为研究规格，本工单为交付合同。复用accepted PR16固定head `e8dcf87979d14d081666629a2de3483629a4f59c`（实现 `c51df70e597021d2c33a5bca013feabf723d879f`，包含PR15/039/038依赖）。main没有全部已验收生产实现，不能只克隆main另写一套。
- 新branch/新PR继承该代码链并同步最新main文档，清楚列未合并依赖；不自动merge旧PR、不改PR16历史交付。建议独立042命名空间，允许必要的显式可选扩展，旧030/036/038/039/040/041默认/reader保持。
- 只改attention信息路由及其严格训练/保存/推理接线。网络参数量、数据、原C1 loss/抽样/dev、动作接口和正式评分不变，无新头/新标签/index/物理重建/外部VLM/FINISH、系数搜索、额外seed/基线或MVP。
- X不SSH、部署、加载真实底座/教师、读取真实轨迹生产、仿真或训练/eval；Codex验收后隔离部署和完整命令，用户亲启。预算批准不扩代跑权限。

## 2. 两臂与初始化：不可误作旧C0/C1

| 项目 | F0（experiment_arm=f0） | F1（experiment_arm=f1） |
|---|---|---|
| base algorithm | c1 | c1 |
| 完整学生初始化 | 041 R0固定末1000全部参数 | 相同 |
| attention execution backend | 同一显式SDPA包装 | 同一包装 |
| 最终有效路由 | 原OFT padding-only双向 | 同规则，仅T query不能读C key |
| 原C1 loss/数据/顺序/dev | 保持 | 相同 |
| 本阶段更新 | 新增1000 | 新增1000 |
| 039旧10蒸馏/新模块参数 | 均无 | 均无 |

初始化adapter SHA：
`d4e726a867531f655d28e11f358ce0af597d4ada0f4928f4597aeadb28d38397`。

这是041的R0（不是R1、不是040或原SOG10），stage-local update=1000但**已累计2000祖代更新**。新两臂各再加1000后累计3000，run/identity/log必须如实区分。初始化包括全部native LoRA/context z/动作残差/count参数，不只LoRA；冻结原SOG10/vision/projector/action head/proprio projector沿原来源不改。

新run、新optimizer/scheduler、seed7 sampler/RNG和独立预算，不载入旧R0 optimizer/RNG/账本作假resume、不复用余额。原lr2e-5/warmup50/bf16、r16/alpha32/dropout0、微批1/原22观测归一化保持，250/500/750/1000保存和原固定dev，只评本阶段末1000。

主比较F1−F0。对旧R0分数的差值还混有新增训练/显式backend因素，不能取旧R0替代本轮匹配F0，也不能把F1全部提升归给mask。

## 3. 必须复现实际OFT native路由，不能假设标准causal

[审计附件](../evidence/042_audited_sdpa_source_excerpt.md)含已存在worker中LlamaSdpaAttention的完整forward片段和版权信息，完整源SHA：
`3aac24cec583a6ef5f60b6ec634a8bd3c8377784c5c63c8cc14cb6790554c52e`。
环境静态元信息：Transformers4.40.1、Torch2.4.1+cu121。只读来源未加载7B确认历史实例，不能把文件存在冒称所有历史实际分支追踪。

该SDPA分支在最终primitive前把上游mask最后一行复制到所有query，且is_causal=False，保留的是padding-only双向图。**F0保留这个有效图，F1只加禁边；禁止暗中把F0或F1全局改成自回归causal。**

在042方法命名空间封装/显式适配attention，保留同一q/k/v/o、LoRA Parameter对象和键名、RoPE/位置、GQA repeat/缩放、dropout/输出投影及并行动作计算。两臂同SDPA调用路径、同尺寸显式mask，不把F0优化为另一套None/causal快捷路径而F1用dense mask。允许受控实现方式，不指定无关风格；**不修改site-packages、原OFT源码/权重或core，不全局monkey-patch所有模型的torch primitive**。

真实用户作业正常初始化时记录实际attention类/版本/合同（不做额外前向），如实判断是否可按该合同适配。若不支持、布局不符或output_attentions/eager fallback会改变数学图，明确报具体错误，不静默换方法/升级依赖或加一轮GPU预跑。历史036–041模型不自动装042包装，base lineage保留原值并另记042执行合同，不伪装“完全没有计算路径改变”。

## 4. T/C区域与唯一研究变量

### 4.1 使用实际插入/shifted标签结构

当前policy仍只输入原双RGB、完整原指令、8维proprio，输出原8×7动作；不移动token，不更改位置编码、图像处理、归一化或原action hidden选择。

- P：真实proprio token，按原projector插入布局确认，不猜固定常数。
- A：原占位标签结构经_process_action_masks得到的**56个shifted动作隐藏全局位置**，保留原前移监督对齐，不能直接取最后56个token。
- a0=min(A)；T为a0之前的有效位置排除P，包含用于z的全部H_v/H_l及此前scaffold。
- C为其余有效位置，包含P、全部A及其后控制/stop/scaffold。
- 每个观测核对H_v/H_l均属T、全部A属C、T非空；padding不作有效证据。首个A可能是最后一个prefix/scaffold位置，它必须归C，**不能误挡首个动作隐藏读proprio**。

区域边界可从原准备后的ids、占位标签结构和实际vision patch/image数量在本次前向中取得，并在原输出projector_features/长度上核对；不为找边界额外做vision/VLA前向。不得读取专家动作值、active-goal真值、mask10/00、task_key、未来帧或评测状态来决定路由。

### 4.2 最终有效mask

M_native为原OFT双向padding-only有效mask，两臂沿同一SDPA包装：

~~~
F0: M = M_native
F1: M = M_native, except M[q,k] = -infinity if q in T and k in C
~~~

**行是query，列是key，禁的是T←C，不是C←T。** C query继续按native读T和C（包括P和其他动作槽）；T内部仍按native双向交互，不改成三角形。padding屏蔽保留，每个有效query至少有合法key，不产生NaN或偷偷把非法整行解禁。

所有层的最终SDPA都应用同一权限关系。不能只挡P直连、只改最后一层，或在上游造mask却被last-row expand抹掉；也不能在最终SDPA把完整mask再叠is_causal=True。additive mask或等价严格实现均可，但不得混淆torch bool-mask True的含义。

F1的H_v/H_l不再从控制区回读数值状态，z仍由原MLP形成并送原count头/残差；W_p p和动作区proprio路径保留。**不把动作H整个做不变约束，不令pair两端专家动作相等，不把count预测硬转成停止/路由。**

### 4.3 checkpoint必须使用每条观测自己的mask

每个前向的有效mask/必要边界是不可变显式参数，进入每层/其checkpoint保存的参数。禁止依赖“全局最近一次样本”的S/T/C或在forward结束后恢复成另一模式，导致重算走错图。

尤其pair u/v可能有不同指令长度、各自mask且两个图同时存活：u反向必须用u的原mask，v用v的。全局臂合同可固定于policy，但不能拿其一个可变字段充当当前样本mask。训练/dev/eval共用同一路径、use_cache=False，不让KV/cache藏控制信息。

固定像素/文字/布局时T-only读取可逐层给z的数值proprio非干涉；图像本身仍含机器人，不能说物理rewind后z严格不变/目标身份已识别/SR有保证。当前研究变量是信息路由包，H也受prefix变化影响，不声称只识别了z的单节点因果作用。

## 5. 数据、loss、原策略参考：保持而非再生产

固定现成040 index：
`8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe`。

370ten/370pair（train289/dev81）、105fresh（78/27）、180raw（136/44）、143960主行。原父split、全部dev source/observation/pair键与选择顺序、task→parent→variant→window抽样不变；新normal仍pair-only不混fresh。不建立新标签/index、不重放/重建资格、不要为本方法加入逐物体A/B标注或解析任务ID。

两臂均保留原C1（同22学生观测/更新）：
~~~
L = .50 BC_ten + .25 base_ref_fresh + .25 base_ref_raw
  + .10 count + .05 self + .05 swap + .01 align
~~~
每更新12ten＋4fresh＋4raw＋1pair两端；两个接收端各保留自己的H/proprio/真实动作/mask，交换仅z。无041 old10保持项、无039模型/teacher加载、无新loss系数或可训练网络参数。原count及不确定标签mask按现成索引保持，不能借新方法改评分。

**原SOG10参考必须旁路防火墙以及所有新增LoRA/z/残差。** F0/F1 fresh/raw与原dev参考均走native双向图，不把F1目标偷改成被firewall改过的教师。所有8参考在本更新任何学生图前完成，no-grad/eval；模式/hook/RNG/cache/requires_grad和042路由恢复后才建学生图。reference输入仍原白名单，不用教师/GT替代策略。复用现成参考保护，但要实际测试其也禁用042边界。

## 6. 新schema、保存恢复、两臂真实预算

新042 adapter/stage schema同时记录base arm=c1、experiment_arm=f0/f1、R0完整source身份/字节SHA、固定index、祖代2000/新增update/累计update、042 attention合同及其版本/后端/有效图。原041 reader仍拒042根，不全局放宽旧reader；新reader全量加载所有学生训练参数，mask规则另记而不是漏存执行差异。

- 新初始化与同一042 run resume分开：新阶段只载R0完整学生参数，新optimizer/账本；resume恢复本run全部optimizer/scheduler/sampler/RNG/更新/持久账本和相同attention合同。
- 不换F0/F1、source/index/config/backend/路由版本续跑；已完成run/已有输出拒覆盖。checkpoint落后于已花预算按原规则拒绝精确恢复，不删除退款。
- wrapper不应给原Parameter路径私加前缀或悄悄漏载参数；不把f0误当旧c0、f1误当旧c1，base c1两者相同。
- 配置完整继承原preset及数值类型，保留photometric_probability的**浮点0.0**，不要因JSON转写变整数0。X测实际生成的配置文件，Codex部署也只做同一严格纯配置读取/上传SHA，不新增GPU测试。

| 已批新工作 | F0 | F1 | 合计 |
|---|---:|---:|---:|
| 新增update | 1000 | 1000 | 2000 |
| 原SOG10参考train/dev | 8000＋1024 | 8000＋1024 | ≤18048 |
| 学生train/dev | 22000＋2560 | 22000＋2560 | ≤49120 |
| 新模型正式10/00 | 90＋90 | 90＋90 | 360 |
| 039教师/新数据仿真/标签/index生产 | 0 | 0 | 0 |
| 额外seed/系数扫描/MVP/基线重测 | 0 | 0 | 0 |

每臂独立reference/student账本、前向前持久扣账，失败/中断不退。不得复用旧041剩余1次参考或在初始化/诊断偷偷加真实“p与p'”双前向；这种非干涉验证只做小型CPU/fake。原dev每250及全部选择保持，只用预算内已有前向的原计数/配对诊断，不再加一轮真实模型分析。

正式每臂九任务10二元合规90、00官方90，原H520/chunk8/seed7/全视频/raw/来源/core/reporting/双bridge与metric不变。各本臂固定末1000新执行，不继承旧R0/040/041分数。训练100%后才由用户另启eval，不自动训练后接评测。

## 7. 定向CPU/fake交付，不新增真实验证门槛

只对受影响路径，禁止全库/多平台、真实7B/教师/特征、MuJoCo、性能MVP或服务器操作。至少覆盖：

1. **最终图/反例**：小型两层以上SDPA复现native双向与P→C→T回流；只挡P的错误实现会漏，F1全部T←C禁边才在固定I/L下使z对p不变，控制可读取p。断言的是实际primitive入参/输出，不能只检查配置flag。
2. **布局与padding**：实际shifted56选择、首个A归C、所有z位置属T，变长/额外scaffold/stop、不齐padding及合法非空行；不能用task_id或目标真值造mask。
3. **原数学计算与状态**：F0与该审计native SDPA公式的小张量结果/梯度一致（合理dtype容差），保留qkv/RoPE/GQA/缩放/原并行图、无新参数/漏载/冻结底座更新。记录dtype/backend差异，不拿CPU证明真实GPU速度/SR。
4. **真实tiny autograd/checkpoint**：不同长度u/v同时有图后反向/重算仍各自mask，不使用最近样本全局变量；原reference切换后学生模式正确、无in-place或路由污染，所有参考先于学生图。
5. **初始化/保存/resume**：完整R0参数载入、祖代2000如实、F0/F1/合同/source/index/config错误拒绝，所有学生模块与完整训练状态可重载，账本前扣/失败计数/恢复不退款和旧041 reader拒042。
6. **入口/进度/原评测**：两臂实际配置严格读取、0.0保留，简洁逐更新百分比/ETA与reference/student计数；fake180/臂单学生路径/原10与00报告/来源和全视频合同保持，推理无reference/GT/partner。

复用已存在固定core/reporting CPU fixture，不把本机缺映射误报方法失败或改断言伪过；无需再跑旧166全套来凑数。明确错误/泄漏/危险/关键约定缺失才阻塞，不因实现风格反复返修。

## 8. X一次交付内容与下一操作

提交新PR、`collaboration/responses/042_round1.md`、受影响实现/配置/定向测试及脱敏常用conda＋python说明。原始attention审计附件是只读参考，不要作为生产模块直接import。回复必须列：

- 固定实现head/accepted PR16依赖，改动文件与F0/F1唯一差别；
- 实际最终mask的构建与落点、首个A、每层/每样本checkpoint、原reference旁路；
- 明确SDPA类/backend、执行合同/原Parameter键保持及不编辑全局包；
- 完整R0初始化/祖代记账、保存恢复/预算，CPU/fake命令与真实passed/failed/skip，已知限制；
- 可直接接线的两臂训练/eval配置与普通命令、后台/简洁进度、两训练串行接力（失败即停、不自动重试/退款/eval）；不写用户服务器私有路径/凭证，不升级依赖或另建真实环境。

**现在执行者X：直接实现＋受影响CPU/fake＋新PR。** Codex验收后隔离部署、填实际配置并给完整命令；用户亲自启动全部真实训练/正式360。原041已closed，不再跑任何旧命令。042结构命题/路由机制不等于ICML创新、A硬保护或zero-shot保证；主比F1−F0，结果不佳不自动加步数/改评分。

保留原039/040/041全部数据/权重/中间状态/分数/视频/失败/历史署名，不merge/删除，不热改运行包；精确待删=[]。如有真正阻塞只报最小具体不兼容与等价选择，不重新泛审设计或自主扩大预算。
