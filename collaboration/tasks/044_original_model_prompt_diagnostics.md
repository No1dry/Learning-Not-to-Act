# 044：原版OFT在10条件下的提示词诊断对照

状态：用户已批准180条正式预算，直接交X实现；不先泛审/交方案/MVP。日期2026-11-16。仓库为**No1dry/Learning-Not-to-Act**，不是benchmark/Eval库。本轮X负责代码与受影响CPU/fake；Codex审查部署给完整命令；全部真实评测仍由用户亲自启动。043由Codex实现的例外不延伸为044由Codex代实现/代跑。

## 1. 研究问题及范围

原版SOG10在固定九任务10上历史SR24.44%（22/90）。补两个无需训练的诊断：
- P1：原完整指令＋固定的“初始A已完成”事实文字。
- P2：仅给剩余目标B的单任务指令。

检验“获得完成信息后能否执行剩余目标”和“显式剩余指令是否更有效”。P1/P2提供了额外初始语义信息，必须明确是informed diagnostic，不是自主RGB识别结果/公平无提示主方法，也不是理论性能上界。P1添加事实，不再附“跳过A/只做B/保护A”等额外行动指令；P2是单独的语义干预，不混入P1。

P0复用现成原模型90条历史对照，不重测、不计入新180、不用H0冒充P0。043 H0也经过1000训练，严禁加载H0/H1、042或其他研究adapter。P0只作原历史引用；已有逐episode证据能绑定则报告配对，只有总分则明确aggregate-only，不伪造配对、不为补证重跑基线或阻塞新两组。

## 2. 唯一有效的语言表

以[044_prompt_manifest.json](../evidence/044_prompt_manifest.json)逐字节冻结的九任务表为准，模型入口原指令须精确命中，不模糊匹配/LLM改写/按效果选模板。P1构造为原instruction＋句号空格＋p1_added_initial_fact，P2只p2_instruction。

| ID / task | P1附加句 | P2模型所见指令 |
|---|---|---|
| 0 / basket | the alphabet soup has already been placed in the basket. | put the tomato sauce in the basket |
| 1 / basket_cheese_butter | the cream cheese box has already been placed in the basket. | put the butter in the basket |
| 2 / stove | the stove has already been turned on. | put the moka pot on the stove |
| 3 / bowl_drawer_close | the black bowl has already been placed in the bottom drawer of the cabinet. | close the bottom drawer of the cabinet |
| 4 / dual_mugs | the white mug has already been placed on the left plate. | put the yellow and white mug on the right plate |
| 6 / mug_pudding | the white mug has already been placed on the plate. | put the chocolate pudding to the right of the plate |
| 7 / basket_soup_cheese | the alphabet soup has already been placed in the basket. | put the cream cheese box in the basket |
| 8 / two_pots | one of the two moka pots has already been placed on the stove. | put the remaining moka pot on the stove |
| 9 / mug_microwave_close | the yellow and white mug has already been placed in the microwave. | close the microwave door |

完整原指令已从现成043 plan的9种10任务metadata摘录核对，所有90条initial_mask=[true,false]。双壶不使用隐藏实例编号/物体ID或“第一/第二壶”；P1说已放一壶，P2说remaining moka pot。

提示代表**episode初始**信息，整条轨迹固定；A后续被破坏也不更新文字/用GT纠正。不得读取逐帧sim predicates、状态sidecar、训练audit/标签、测试未来或VLM预测来生成提示。它不是新数据整理任务，零新标签/索引/仿真准备。

## 3. 冻结模型、输入与评分

模型：官方moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7；原OFT e4287e94541f459edc4feabc4e181f537cd569a8，libero_10_no_noops。沿现有base-runtime，原中心裁剪、两RGB、proprio8、chunk8、seed7、H520和非量化/native动作头不改。官方发行底座中已有的训练组件保持；禁止新增任何研究LoRA/训练权重/FINISH。

原043 plan仅作为**同一90来源/任务/环境协议的元数据参考**，不是043策略或评分复用入口。只选10：六旧批任务＋新三各10单episode=36执行单元/90episode，每变体同一组ID与初态。不要带入90个00，不能新建初态、重做资格/回放/训练数据或新mask。实际core/reporting revision以参考plan记录为准，不能根据旧目录名猜版本；现成投影hash见批准证据。

**只在模型调用边界换字符串**：保留原source instruction、goal_specs、全任务原生目标、A保护/释放/错抓/放置判据、步数和端点。即使P2只写B，原完整任务A+B仍用于正式评分，A破坏/错抓按旧规则失败。不要改source instruction再让评分器误以为任务只剩B。

10继续既定binary-compliant-success-v1及其原底层证据规则，正式仅成功/不成功；底层UNKNOWN诊断留原始证据，按现有二元规则计不成功，不删分母、不另改阈值。技术错误/工件缺失应明确不完整而非伪造模型完成/成功。

## 4. 实现边界与建议接线

推荐以accepted PR17固定7d28d515be610f33f959f36d25623e86796671ce为代码依赖，读取最新main本工单。main主要为文档，不自动合并PR17/18；新开044分支/PR。可以复用已接受方法层bridge/proxy、原36个10来源规划、原reader/二元报告/子进程native policy，**不改冻结core/reporting/全局安装包**，不重写仿真与评分算法。

推荐独立egrs.prompt044或等价隔离包、schema task044-prompt-eval-v1：
- prompt mapping/contract纯CPU/stdlib；策略wrapper消耗044配置后，以原FACTORY与原配置创建OpenVLAOFTPolicy，不安装任何研究adapter。
- wrapper.predict(observation,original_instruction)只将原允许的RGB/proprio传给底座，将语言精确替换为P1或P2。重用官方native prompt封装/分词/forward，不借用043训练prompt_override或引入chat/system/CoT格式。
- 原egrs.retention.evaluation固定要求研究adapter及10+00总180，**不能直接冒用其旧schema、塞假adapter或补空00来过验证**。可复用内部已有组件，044须显式ten-only/native-original合同与真实90预算，原旧入口行为不变。不强制做通用平台/全库改造。
- 建议正式CLI：python -u -m egrs.prompt044 evaluate --config CONFIG --output NEW_RUN；config含variant p1/p2、固定prompt manifest、原来源/runtime依赖。正式入口自己做原必要绑定和plan，不让用户额外先跑plan/预检。
- 每变体独立新输出与fresh model worker，沿原种子规则，不跨P1/P2继承策略状态或分数；原始模型不保存“新训练adapter”。
- outer044 runtime可以有专用factory，native底座收到的factory/options必须满足原OFT验证。metadata如实区分原底座身份、prompt_variant、prompt_manifest SHA、deployment_initial_semantic_information=true，不称无提示043/hint043_arm。原actual loaded model/组件/归一化身份必须可追溯，不伪造同一model identity。
- 保留两份语言：source_instruction（原）与model_instruction（干预后）；至少在每episode/首次模型调用处记录实际传入base.predict/API的字符串和SHA，后续query绑定同一固定语言。记录原生封装来源，不假装手写字符串等于实际tokenizer输出。
- 诊断raw保留原RGB/proprio/actions/video和prompt元信息；source/skipped目标oracle字段不得混进视觉输入。
- 跨旧/新bridge时保留现有严格分派/proxy协调与实际环境身份验证。所有原工件保持，不修改043 run/权重或复用其策略结果。

## 5. 已批预算与直接顺序运行

P1 90＋P2 90=**180条新模型episode**，九任务各10/组；P0/00新执行0。训练0，新物理训练数据生成0，新标签/索引0，提示搜索/额外seed/MVP/基线0。原H520/chunk8导出的模型predict调用上限180×ceil(520/8)=11700，无额外观察probe/预检前向。既有正式计分所需的原证据核验保留，不另加耗时验证层。

交付两配置模板和一个用户显式启动的run_both_sequential.sh：P1正式90正常报告/退出后P2正式90；首次失败即停，保留输出/预算/marker，不自动重试或进入下一组，拒绝覆盖/并发重复。准备完成不等额外MVP，Codex验收后隔离部署，用户直接一条命令跑180。脚本不得顺便训练/00/新baseline/额外prompt，X不得SSH或自己启动它。

保留每组逐episode进度、每任务SR与总体正式SR，百分比优先；正式核验未完时不冒称formal100%。沿现有live定义能合理给出已完成SR可保留，不为实时SR另外跑评分。最终summary/report区分P1/P2、固定90分母/完整性、P0历史引用，所有episode全视频。已有失败/中间产物不删，恢复/重跑需明确交回决定。

## 6. 定向CPU/fake验收（不跑真实数据/模型/仿真）

只覆盖受影响路径，不全库/泛审：
1. 九任务两变体精确映射、P1保留完整原串、P2纯B、双壶无实例ID；未知/冲突instruction或缺变体拒绝，manifest身份可核对。
2. fake底座捕获实际语言/RGB/proprio，变更fake观测truth/目标字段不会更新提示、也不传入底座；原评分source instruction/目标保持。
3. native-original loader未调用任何adapter.attach/训练/043 head；metadata写出真实variant和实际语言。
4. 同一90来源每组一次、无00、无旧模型结果继承；新输出/预算/重复marker保护。
5. 使用原兼容fixture覆盖两bridge/proxy切换；原二元判断P2中A破坏/错抓仍失败，技术错误不伪成功。
6. fake完整串行90→90和首臂失败不启动次臂，报告分母/进度/全视频路径/预算真实一致；不把fake称真实180。
7. 新实际配置模板语法/严格类型（0.0如有仍是float）及输出位置不与现有保护输入根重叠，不再把新增输出放宽data根内。

现成fixture缺本地路径时复用之前accepted快照，不削弱断言，不把全库恢复/平台改造变成前置。禁止7B下载/加载、GPU前向、真实reset/step/回放或重新采集数据。

## 7. X交付清单与下一执行者

新PR＋collaboration/responses/044_round1.md，写固定head、依赖、源文件清单、真实CPU/fake命令/数量/失败及最终结果、模型语言与评分语言分离说明、预算/输出/进度与串行入口；附新配置/脚本/测试。参考本轮批准与prompt JSON，不自行变体搜索/追加阶段。不要只给研究建议而不改代码，不部署或运行真实任务。

Codex按明确错误/关键缺失做建议式审查，不因偏好反复返修；接受后只文件部署与完整conda/python命令，用户亲启。043全部旧运行已closed，本044实现前准备/真实执行均0%。不自动merge或删除。
