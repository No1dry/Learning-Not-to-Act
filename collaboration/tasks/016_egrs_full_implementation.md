# 016：EGRS完整软件实现

日期：2026-10-22。执行者：X。状态：accepted/closed（2026-10-23，完整软件与定向CPU/fake范围；§9已修复）。用户已同意推进实现；**只授权代码与定向CPU/fake测试，不授权真实数据恢复、标注推理、训练或eval。**

## 1. 本次交付是什么

一次交付完整③＋④软件：**独立实体/关系选择器＋可撤销证据历史＋冻结VLA语言执行桥接**。

- 只训练选择器LoRA，不更新VLA、动作头或proprio projector。
- 完成实际数据处理、训练/保存/加载、推理worker、调度、actor桥接及日志路径；不是TODO骨架或用假训练替代真实训练入口。
- 不先跑MVP，不扩benchmark，不加FINISH、空间动作接口或新主metric。
- 此次没有批准55—80人时人工投入；代码支持外部标签导入与弱监督，数据不足不影响实现/fake验收，也不能冒充已经可训练。
- 后续真实预算与命令由Codex准备、用户确认并亲自启动。

实现仓库：`No1dry/Learning-Not-to-Act`。建议独立Python包 `egrs`，不得覆盖 `benchmark` 包。

## 2. 规范来源与优先级

1. 本工单是本轮实现范围。
2. [015的Codex裁决](../reviews/015_round1.md)采纳R1—R4。
3. [X的015审阅固定原文](https://github.com/No1dry/Learning-Not-to-Act/blob/bdb63187680315673e40ed73fc52ac0aeddfcf7d/collaboration/responses/015_round1_design_review.md)中R1—R4的字段、缓存、RPC与loss边界是必须满足的契约。
4. [完整设计v1](../../docs/research/2026-10-21_remaining_goal_selector_full_design.md)的主架构/物理预算不变；其中示意JSON与旧“仅设计审阅”状态由本工单补充，不照抄有缺口的示例。

命名与等价实现可合理调整；只有明确错误、泄漏、危险控制、证据失配或本工单关键功能缺失阻塞，不追加风格性返修。

## 3. 数据与预算决定

默认候选目录保持015 §6.1的Goal10＋Object10，不自动采用三项替换：
- 固定公开数据revision `147fa5eb607bb696dd922c3518084a90954cd2f3`，提供20文件的候选catalog模板。
- 200来源/最多1,200窗口/约3,600查询只是预算草案；所有实际数由数据清单统计，不默认已齐备。
- 排除当前六个复合评测任务/语义等价组合，不用冻结eval来源或其派生帧补train/dev。
- 整轨迹、已知同源、改写/配对/增强成组，约80/20 train/dev；未知祖源披露，不重启逐一来源匹配工程。
- 官方数据是普通演示，不要求正确恢复动作，不做VLA动作微调。
- 55—80人时只是900窗口全字段人工方案的估算，**未批准采购、分配人员或启动该方案**。

必须实现标注包导出/导入：支持人工确认、候选/弱标签、UNKNOWN和字段provenance，报告来源、窗口、query三个独立计数。保留物理真值作为离线审计列，但绝不能进入模型输入或未确认答案。该列允许缺失/unknown；人工可见证据训练不以先恢复全量物理真值为前置，不得造真值。

没有标注文件时，准备工具明确返回缺口与实际覆盖；不要制造标签、随机补来源、无声替换坏样本或宣称ready。数据导出可以准备静态清单；物理恢复、render/教师推理等真实入口只供用户后续启动。

## 4. 完整方法必须实现的功能

### 4.1 稳定目标与实体证据（R1）

- 每episode只从原完整指令初始化一次goal registry；固定引用、目标语义、原文依据和稳定actor文本。后续必须引用同一目标集合，不根据task_id或mask取答案。
- 实体关联允许UNKNOWN/未匹配；所有关系、持物、释放证据绑定goal_ref、实体引用、query/snapshot、相机和区域，声明框坐标系。
- 搬运目标的“操作完成信念”需关系与释放证据；机构目标释放明确NOT_APPLICABLE。
- 新反证/释放撤销携带保持，3次新查询不可见后过期；SAT累计2次需2个新查询的观测支持，历史复述不算新证据。
- 两/三次阈值是可记录的初始策略规则，不等于评分K4，也不声称跨底座对应相同物理时间。
- 初始历史为空；命令、夹爪闭合、bbox重叠或一次空抓不自动证明成功、持物或完成。

### 4.2 历史、调度与语义桥接

- 可信当前目标在携带/搬运中优先保持；否则优先当前观测支持的UNSAT目标。UNKNOWN不被永久删除。
- 无可靠待执行目标且无可信在途目标时，回退原完整指令；不返回STOP、零动作或虚构“观察”技能。
- 同目标文本稳定，切换/回退原因可审计。原指令回退也可能失败，评价不豁免。
- 默认不改底座原图、裁剪、归一化或动作解码；不发bbox/坐标给VLA、不插shield或动作残差。
- 对象证据用于选择与反馈，不声称约束机械臂空间。目标选择正确但抓错仍按原规则失败。
- 只使用query边界已得到的图像，最多2个历史双相机时刻＋当前双相机、12条短记录；不额外render或读取逐步评价日志。

### 4.3 独立组合层与worker（R2、R3）

方法policy对外提供现有 `reset/predict/close/metadata` 概念接口；内部组合独立selector worker与actor worker：
- selector窄RPC分开sensor/context；每份当前/过去sensor仍过原白名单，context只含原指令、registry、历史预测和命令摘要。
- 不扩观测白名单，不塞入目标谓词、mask、物体坐标、真实接触、未来帧或评分结果。
- actor facade在actor worker内比较实际文本，专用goal-change hook只清旧目标缓存、保留RNG/权重，不走SubprocessPolicy.reset。
- OFT/OpenVLA及已静态核对无缓存路径显式no-op；UniVLA清latent与decoder聚合；OpenPI不得调用重建_rng的reset；未知能力须明确声明，不能自动全reset。
- 每suite actor解释器、checkpoint与归一化独立保留。**facade外层配置不带原SOG10 transfer并替换factory**；完整原actor配置嵌套，内部仍按原factory及原transfer验证。
- episode开始才按原流程播种；selector的计算不消耗actor随机流。不同查询数造成RNG消耗不同应如实记录，不宣称位级相同。
- 方法包须安装到实际加载factory的解释器，不能依赖父shell的临时PYTHONPATH。
- 合法但错误的预测按方法行为保留；非法引用/缺目标/未来证据/越界框/schema错误、加载/通信故障保留technical/partial，不静默退回baseline或自动重跑。

### 4.4 真正可运行的选择器训练与推理（R4）

- 默认base `Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`；Qwen训练参考源码 `96588727e44c78b25ba03ea03b8e12f7e64fd0da`。
- 显式加载Qwen2.5模型类型，不按本地目录名猜架构。固定processor/依赖；独立selector环境，不能升级OFT环境来满足它。
- 默认r16/alpha32、bf16、全局batch16、lr1e-4、最多3epoch；它们是未验证初值，不要求调参实验。可有依据地统一替代，不以更大模型为默认。
- 实现实际LoRA训练/保存/恢复/推理；列出实际可训练参数，只允许selector语言LoRA。训练不加载/调用VLA产生动作标签。
- 规范序列化＋最终chat template/视觉token展开后的字段mask；对齐input_ids/labels，不按字符估算。
- 人工确认UNKNOWN参与监督；未核验字段是“无监督”，不能把它当UNKNOWN硬标签。物理结论及依赖解释须删除/中性占位并mask，不能只mask loss却留在teacher-forcing上下文。
- 候选预算：每图最多256视觉token、最多6图、总长度4096，显式分配prompt/历史/完整答案预算。超长按预定规则去最旧历史或拒绝计数，不裁当前图/目标/答案，不无声换样本。
- 默认关闭packing/flatten；显式train/dev与字段级统计、无监督字段/丢弃数；训练历史不得含未来帧或oracle完成历史。
- 可用本地tokenizer/processor作纯CPU校验及toy网络验证梯度/save-load；不得加载真实研究模型做forward、训练或特征抽取。缺少真实processor校验时披露，不假称已跑。

## 5. 与benchmark的边界：不等014才能写方法

直接依赖固定eval core：`LIBERO-Remain-Eval@515e87d9b93ab838428791273a0f3020d6f56e9c`，通过其白名单、headless runner/environment/schema/evidence/metrics API调用；不复制任务、状态构造、几何、事件或计分实现。

本次交付方法factory、嵌套method/selector/actor provenance、query对齐sidecar与fake契约贯穿：
- 014未交付或eval私有仓库暂不可读，不阻塞方法本体、训练/推理与fake验收。使用明确本地依赖路径；可读参考来源应记录，不能宣称核验了未读新库。
- 实际batch需要014接受自定义factory、每suite runtime和嵌套身份。缺口列清交Codex对接，不能在方法库另造一套评分或把旧H+W协议当替代。
- 可以提供薄的core API调用/接入示例；真实批处理尚未联通则明确待联调，不编造运行命令或称全部端到端就绪。
- H520、20Hz、K4确认、sticky事件、完整视频、逐控制步实际路径不变；主指标仍合规成功率和成功条件路径。
- 方法日志记录registry/预测/历史/输入文本/换目标/回退、两类调用、图像数和耗时。返回动作是命令；长chunk不能当全部实际执行，按query ID离线与core证据关联。
- schema/方法日志写入失败不可静默称完整成功；不覆盖已有结果目录。

## 6. 必须提供的入口与配置

提供实际可用CLI及完整参数说明，至少覆盖：
1. 静态配置/依赖清单检查与数据catalog、标注导出/导入、分组构建/统计。
2. selector训练、保存/恢复与独立推理worker。
3. EGRS policy factory、actor facade、规则历史与调度。
4. 方法运行配置与eval core对接、sidecar离线检查/汇总；未有的014功能明确标记。

CLI help和文件级plan不得自动初始化native或加载模型。真正训练、教师/selector推理与eval命令只供后续用户启动；带dry-run的路径必须确实不运行模型或仿真。

配置提供原VLA、同base不加载LoRA、完整EGRS、去历史、去角色监督的开关。去历史同时去旧图/文字；去角色监督不能靠日志声明代替数据/loss开关。无LoRA对照不冒充已训练选择器。

README给安装与解释器隔离、数据格式、真实命令、需要的文件和明确缺口。公共库不提交权重、状态包、私人路径/凭证；采用上游代码时保留必要许可与归属，不自动为整个项目发新许可。

## 7. 定向CPU/fake验收

只检查直接影响本次实现正确性的路径，不跑全库/多平台或真实实验：
- registry身份/完整性、实体—持物关联、证据来源/坐标与机构释放适用性。
- 两次新证据/过期撤销、初始空历史、在途保持、正常UNKNOWN回退及不产生STOP。
- sensor/context隔离、未来/GT字段拒绝、命令与执行长度不混淆。
- 目标变化清缓存，稳定文本不重复清；RNG/权重不变；嵌套OFT transfer配置不被facade误改。
- 最终token字段mask、UNKNOWN与弱标签、teacher-forcing隐含结论删除、多图不静默截断、来源组split。
- train入口/LoRA梯度与save-load用toy/fake贯穿；真实Qwen权重未运行须声明。
- 一个fake集成用真实core API或明确pinned contract贯穿policy→core runner→证据/原指标，并验证sidecar与partial。
- 与014不能联通的部分精确列出，不以此省略方法本体交付。

这些分别防止错误目标记忆、RNG改变、泄漏、错监督、评分漂移和假完整结果，不新增耗时物理检查。

## 8. 交付与完成口径

从最新main独立分支交PR；代码/模板/定向CPU-fake结果、实际入口与完整命令一起交付。回复 `collaboration/responses/016_round1.md`，列明：
- 实现模块/commit与测试结果；
- 是否真实使用过processor（不含模型）及尚未运行的研究模型路径；
- 真实数据、标注、训练、eval的实际完成数（本轮应为0，不拿fake充数）；
- 014、数据与硬件尚未解决的真实依赖。

不自动merge、不热改服务器。Codex集中审查后部署，用户另行确认标签与资源并启动真实阶段。此工单可在没有55—80人时人工承诺时完成完整软件；不能据此宣称方法有效。

## 9. Round1最小修正（2026-10-22）

Codex已审查PR #2固定head `116818ca27577387551b74ee661fbe1288aa7d80`：[裁决与复现](../reviews/016_round1.md)。47项定向CPU/fake独立通过；主体实现不返工，仅处理以下P2。

- **错误**：`egrs/selector/supervision.py:35–38`以evidence父列表是否确认提前清空整列，静默丢掉只在`/goals/0/evidence/0`标human的完整确认项。导入允许、训练却丢监督，与逐字段/继承契约不符。
- **推荐最小实现**：按evidence条目及实际继承/覆盖后的provenance判断确认完整性；保留完整确认条目及其监督，弱/未确认物理证据仍在teacher forcing前删除，不得用放松泄漏保护解决。
- **可接受的更窄替代**：若坚持父列表确认作为格式约束，在导入/构建显式拒绝此格式并指明需补标的父pointer，同时同步文档；不能接受后静默丢标。不要扩大改造范围。
- **受影响CPU/fake回归**：逐项完整human确认但父列表无标注时，能保留监督或在导入/构建明确报错；父human但子weak仍不泄漏；既有human UNKNOWN及no_role行为不退化。复用既有fixture/fake processor即可。
- 原PR增量提交，新增`collaboration/responses/016_round2.md`列修正commit、实际回归结果及真实运行仍为0。只复跑受影响数据/训练组；不要求重跑物理证据、全库/多平台或真实模型。
- 审查中的compose/runtime及独立predict依赖是非阻塞建议，本轮不要求顺带返修。014也不连坐本体验收。

此任务仍只授权代码与CPU/fake；不自动merge、部署或启动真实阶段。

## 10. 软件验收（2026-10-23）

固定交付head `5a77f158229442d9a9ee95ba828b371dfc4c995a`的§9修正已接受，受影响30/30项CPU/fake独立通过（100%）。016完整软件范围closed，见[最终裁决](../reviews/016_round2.md)与[阶段总结](../../docs/stage_summaries/2026-10-23_egrs_software_acceptance.md)。不再要求X返修；真实数据、训练、评测仍为0，PR未自动合并，部署/资源与真实命令由Codex后续准备、用户确认启动。上文原始范围与历史审查保留。
