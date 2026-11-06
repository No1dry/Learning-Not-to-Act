# 037 R1：外部完成干预一致性学习——集中设计审阅

2026-11-06，X。结论：**有明确冲突需调整**。建议保留研究问题与有效增强，收紧候选方法和理论主张；当前不支持把“剩余目标更新”、小型角色头或零初始化残差单独作为主创新。

审阅基准：最新main `15f826c91f5e77518726e0cc77cbc95a60bbfb6f`的[037工单](../tasks/037_intervention_learning_design_review.md)、[主设计](../../docs/research/2026-11-05_icml_intervention_residual_learning_design.md)、[理论草稿](../../docs/research/2026-11-05_goal_completion_intervention_theory.md)、[036正式结果](../../docs/stage_summaries/2026-11-05_task036_final_results_retention_tradeoff.md)；接口静态核对已验收PR11 `205d6530e1ba389f74166a2e9520a3db7ae0edbf`及固定上游OFT源码。已阅读上述方案，本稿不是盲法独立提案。以下区分原文事实、代码契约与审阅推断，不将服务器工件的设计字段当作已经逐条核验的实际内容。

## 一页结论

研究问题值得继续。035/036分别得到10合规54.44%/50.00%、00官方73.33%/82.22%，显示增强有效且存在保持取舍；没有证明模型已经学会目标残差化，也没有证明新增结构优于同数据普通微调。

| 优先问题 | 集中结论 | 最小修订 |
|---|---|---|
| 1. 与近邻重合及pair必要性 | 进度调制动作、反事实学习任务结构、完成后更新剩余指令均有先例；完整角色标签下拟议pair关系在零误差时冗余 | 将候选收窄为“目标义务/保持义务的视觉学习与有限样本配对正则”；保留C2−C1，失败时放弃pair主创新归因 |
| 2. 潜态不等于观测信念 | 潜在完成算子合法，不代表当前双RGB/本体后验满足点态等变；遮挡下pair甚至可能推动错误确定性 | 为点态理论明确可辨识域；实践逐项目mask缺失/失配关系，承认残余不可观测偏差，不承诺校准或SR保证 |
| 3. OFT实际接线 | 同次前向提取prefix和56个action hidden可行，但现eval、参考旁路、optimizer和保存器均不会自动包含新模块 | 共用学生预测路径；显式新模块参数/身份/strict加载；原参考旁路全部新增模块；成对组织反向 |
| 4. 角色语义与实际数据 | 有fresh真值trace与父关联的生产契约，尚无037角色标签、强配对清单或对称目标实例绑定证据 | 复用原数据，新增版本化离线角色/关系sidecar；只请求小metadata样本核对；不重做035资格或状态 |
| 5. 科学对照与报价 | C0/C1/C2可检验此实现的增量价值，不能证明全面优于近邻或普遍因果机制 | 三组同初始化/采样/长度；固定最终更新；披露模块容量、显存与标签成本；不自动启动候选预算 |

**推荐收敛**：保留原完整指令、同一VLA、预测角色接动作、036参考保持与现有增强；把`L_pair`定位为待验证正则。先由Codex一次确定目标规格、监督可用范围和预算，再交实现。若坚持“新可识别原理/组合保证”为主创新，现设计和现有数据尚不足。没有查到完全相同方法不等于已证明首次。

## 1. 近邻工作：哪些已做，差异还能放在哪里

以下是原文方法节查核，不是穷尽查新；“尚未见”仅指所读内容。建议直接借鉴定义、约束和对照，当前无需复现另一整套基础模型或重跑基线。

| 原始来源与位置 | 已有机制及最强重合 | 本候选可保留的区别／借鉴判断 |
|---|---|---|
| [MimicGen](https://arxiv.org/html/2310.17596v1)，§3假设2–3、§4.1–4.2 | 物体中心子任务分解、完成检测、片段适配与执行生成示范，再训练模仿策略 | 桥接、后缀适配、增强＋BC均不能独占。值得借鉴子任务假设与失败记录；不需要为037重新生成MimicGen数据 |
| [RoCoDA](https://arxiv.org/html/2411.16959v2)，§III-A、§IV-A–B | 用局部因果阶段保持依赖变量联合采样；无关变化保持动作，几何变化相应变换动作；包括仿真状态采样/渲染 | “未受影响目标保持”与其因果不变性思想重合。完成A会改变动作义务，不能套动作不变；也不能只用“语义而非几何”略过重合。优先借鉴配对有效域说明 |
| [ReViP](https://arxiv.org/html/2601.16667v3)，§4.1式(4)、§4.2式(5)–(6)、§4.3式(9)、附录A.1 | 冻结外部VLM观察器形成状态/阶段信息，经MLP和残差FiLM调制VLA，影响动作；已有接近恒等的初始化 | 它调制的是视觉—语言prefix，不是直接action hidden。移入同一VLA、替换调制位置、不再加载Qwen是接口差异；不能据此称新学习原理。应借鉴其因果链与mask处理，目标级完成/保持关系仍需独立证明价值 |
| [ProgressVLA](https://arxiv.org/html/2603.27670v1)，§IV-A式(1)–(2)、§IV-B–D式(3)–(11) | 标量进度估计（含`t/T`标签）、动作条件世界模型、以预测进度引导扩散动作 | 目标身份和保持义务比单标量丰富，但“进度头真正影响动作”已有。值得借鉴进度与行为分开的评估，不应为OFT引入另一套扩散/世界模型 |
| [NEEDLEWORK](https://arxiv.org/html/2610.02339v1)，§3.2式(1)、§3.3式(2)–(3)、§3.4 | 轨迹内shortcut、跨轨迹成功续接、失败到成功连接，验证短桥后纳入策略训练 | 绕过冗余轨迹与复用成功后缀不是新颖性。借鉴连接资格和覆盖保留；不改变本项目已验收的生成、初态和评分 |
| [GLiDE](https://arxiv.org/html/2403.17124v1)，§2.1–2.4、式(1)–(3) | 扰动示范回放产生成功/失败反事实，以任务模式可行性约束学习语义模式，再驱动反应式策略 | 比普通增强更接近“干预揭示任务结构并影响决策”。所读方法未见本候选NEED→PRESERVE完成配对，但不能因其不是VLA而忽略。值得借鉴监督究竟新增了什么信息的分析 |
| [LTL2Action（ICML 2021）](https://proceedings.mlr.press/v139/vaezipoor21a.html)，[§3.3定义3.1–3.2、§4、§6](https://arxiv.org/html/2102.06858v3) | 依据当前事件真值做formula progression，将指令更新为剩余指令，并据此决策；覆盖顺序/安全约束；假设无噪声事件标注函数 | “完成后删除义务／剩余目标作为决策状态”有清晰先例。可研究的区别是无在线真谓词时如何视觉学习，而不是剩余化概念首创。最值得借鉴语义与可观测性边界，无需移植RL训练体系 |
| [PRTS](https://arxiv.org/html/2604.27472v1)，§3.2式(10)–(12)、§3.3式(15)、§6.5 | 同一VLA联合行为与目标可达性表示学习；展示干预后重估未完成阶段 | 单前向、内置目标意识与人类干预恢复均非空白。其role-aware mask指token种类，并非NEED/PRESERVE；§6.5约每任务五次的定性压力测试，不能当本问题的正式合规SR。值得对照其主张范围，当前不增加大型预训练复现 |

**新颖性边界判断**：去掉完成配对后，C1仍比`t/T`标量更有目标语义，但属于目标级角色/进度条件化策略；小头和残差不足以单独支撑主创新。即使保留pair，也必须说明相较完整角色标签新增的是关系信息、归纳偏置还是仅优化正则。现稿最稳妥的是后两者，不能先写成已经成立的因果识别贡献。

## 2. 理论逐项审阅与最小勘误

### A：存在性构造成立，不能推出pair必要

草稿A中`(c,r)=(0,0),(1,1)`上两种零风险策略、在`(1,0)`上分歧的构造正确。补明：c可供策略辨认，A/B是高层动作类别。它既不证明RGB可识别，也不证明连续控制正确；若c不可观察，`π_scene`甚至不属于部署策略类。增加`(1,0)→B`样本同时有利于普通BC，故该构造支持C0，而非直接支持`L_pair`。

### B：硬保护下等价；软角色训练没有该保证

草稿B在同动力学/时域/K、可行策略几乎必然全程保持P、且`G=P⊔R`时正确。主设计写`R=G\C`，尚未明确`P=C`，因而与上述分解条件未对齐：若`P⊊C`，被删除却不保护的目标可能失效。当前可保持的10定义域最小写明`P=C`；其他已真但可暂时破坏/需再达成的谓词不能永久从R删除。

软概率、soft gate或有限保护惩罚不满足硬约束前提。即便允许最多5%破坏：安全策略`Pr(R)=Pr(G)=.98`，风险策略`Pr(R)=1、Pr(G)=.95`，优化R和G可选不同策略。因此该命题只能解释任务定义，不能替代现有合规评价或证明新网络保成果。

### C：潜态完成算子不能直接升级成观测信念等变

集合更新的幂等性与可交换性无代数错误；依赖限制的是物理部分映射的合法域和序列，不应宣称物理操作可交换。`φ(I_i(s),G)=C_iφ(s,G)`是合法语义配对要满足的条件，尚不是035生成器已满足的事实。若φ还依赖完成事件历史，s须包含相应任务监视状态，不能默认当前物理姿态足够。

具体反例：A未完成/已完成的两个隐藏状态给出完全相同可用观测o，等概率时正确后验是`q_i(o)=(1/2,1/2)`；pair却要求`q(o)=C_iq(o)`，对应L1项`2(1−p_P)`，推动`p_P→1`。输出概率不能自动消除这种冲突。

最小修订：点态等变和后述组合引理限定到角色可由允许输入辨识、语义关系有效的域；潜态标签仍可用于学习概率预测，缺失/错位项mask。若在未证明可辨识的配对上使用一致性，应明确是可能有偏的结构正则；不能宣称信念校准保证，也不能用模型自己低置信度为由删除困难评价案例。此处不要求新增全库可视性认证、渲染或人工视频审查。

### `L_pair`：零role误差时冗余，单独还有塌缩

对当前L1候选可展开为：

```text
L_pair = ||q¹_i − e_P||₁ + Σ(j≠i) ||q¹_j − q⁰_j||₁
若 y¹=C_i y⁰，则
||q¹ − C_i q⁰||₁ ≤ ||q¹−y¹||₁ + ||q⁰−y⁰||₁。
```

因此两端完整正确的角色监督在零误差时已满足该关系；全PRESERVE常量也能使pair为零。并且完成目标的源端被投影抹去，pair本身并未要求源端NEED，须由合法源标签/角色监督锚定。有限样本正则仍可能有益，但不能称它凭空增加可识别信息。若未来只有关系标签而无完整两端标签，才可另说明其新增监督量；当前不猜这些数据已经存在。

### D：L1累加界成立，表示误差不等于SR

草稿D的三角不等式和非扩张递推成立。补明` s_j=I_ij(s_{j−1})`，o_j来自真实允许的部署观测机制，各步真语义关系成立；“存在某个有利观测”不足。引用这个界时固定使用L1，不能将JS训练损失直接代入同一个累加界。保留已写的平均训练loss不推出未见中间态点态误差的限制。

即便角色完全正确，`F≡0`、F忽略角色或残差落在head不敏感方向，动作仍可不变。接入计算图只证明**能够影响**动作；不证明实际依赖、更不保证SR。无需添一个牵强SR定理，继续由正式10/00结果检验。

## 3. OFT接口：可做，但不是只改training helper

静态位置均指PR11固定提交，而非main中尚未合并的实现：

| 接口 | 已确认事实 | 下一实现工单必须明确 |
|---|---|---|
| [oft.py:144–178](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/augmentation/oft.py#L144) | 原图像预处理、完整prompt、29871、官方label/mask helper、8维本体、单forward；shift后取`1×56×d`送原action head | 原56-token选择保持；在同一次output上另外切prefix，不插goal token、不改shift或crop |
| [固定上游modeling_prismatic.py](https://github.com/moojink/openvla-oft/blob/e4287e94541f459edc4feabc4e181f537cd569a8/prismatic/extern/hf/modeling_prismatic.py#L396) | 布局为BOS→双视觉patch→proprio→其余文本；前向返回hidden | `patches=N_patch+1`计入proprio，未计BOS，不能直接当整段prefix边界；prompt span与action mask使用各自正确索引 |
| [固定上游action_heads.py:75–97](https://github.com/moojink/openvla-oft/blob/e4287e94541f459edc4feabc4e181f537cd569a8/prismatic/models/action_heads.py#L75) | 56个hidden按8个动作、每步7个hidden重排后经MLP得到`1×8×7`；没有detach | 冻结head参数仍可向输入传梯度；训练时不能用no_grad把head或prefix整段包住 |
| [evaluation.py:43–66](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/augmentation/evaluation.py#L43) | attach LoRA后，predict直接调用`self.base.predict` | 只给训练helper加F，正式eval不会自动用F；须共用学生动作路径，保留原反归一化、夹爪处理、chunk/reset和传感白名单 |
| [reference.py:13–44](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/retention/reference.py#L13) | 参考只旁路`LoRALinear.enabled`，no_grad/eval不等于旁路新模块 | 参考须显式跳过所有037角色/残差模块，仍为原底座动作；保持模式恢复和先参考后学生的顺序 |
| [training.py:189–227](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/retention/training.py#L189)、[oft.py:71](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/augmentation/oft.py#L71) | optimizer收集model可训练参数；保存器只收LoRA；现逐item forward→backward | 新模块正确注册/纳入optimizer、保存和strict恢复；pair两端须联合组织loss或保留所需图，不能先释放再假装双向求导 |

最小实现草图（仅设计，未写入生产代码）：

```text
原输入预处理与官方placeholder/labels → 一次OFT forward → H
H_a = 原shift/mask选择(H)                       # [1,56,d]
Z   = 按真实布局选视觉、proprio与原prompt特征(H)
q_i = 共享角色头(目标query_i与Z交互的表示)
U_R,U_P = 用预测q_i聚合，保留目标/实例身份
H'_a = H_a + W_up F(H_a,U_R,U_P)               # 仅W_up零初始化
动作 = 原冻结head(H'_a)                        # [1,8,7]
```

GT只进入离线loss，不进入Z/query/q聚合；00/10都走同一路径。不要让F通过无角色的自由旁路直接读取全部Z，否则角色监督可能只成为装饰。即便限定了入口，也仍需承认F可以忽略U。C2−C1检验pair效果，C1−C0检验整套角色结构，不能仅凭角色accuracy宣称因果中介已识别。

单次前向和梯度路径成立：`L_action→head→F/q→prefix→语言LoRA`，以及原`H_a→LoRA`路径。注意零初始化的是最后输出投影；若整个多层F都置零，可造成不必要的梯度停滞。即便只置零W_up，首步动作loss对F前段/角色的梯度也可能为零，之后才打开；`L_role`可先提供角色梯度。这不构成设计失败，但不能声称从首步所有路径均非零。

### 目标query与依赖知识不能省略

原tokenizer和[冻结输入embedding接口](https://github.com/moojink/openvla-oft/blob/e4287e94541f459edc4feabc4e181f537cd569a8/prismatic/extern/hf/modeling_prismatic.py#L321)可以从原指令跨度形成query，无须额外LLM前向。但“both”“it”“close it”的消歧、关系/依赖D及合法成果定义并未由取embedding自动解决。

尤其两个同类壶：若两个query来自完全相同文本跨度，且共享同一确定性交互/头，则输出相同，无法表示“一壶NEED、一壶PRESERVE”。至少要明确实例绑定：可采用共享的图像实例slot＋集合匹配监督，或有来源记录的可区分文本指代；不能偷偷用task_id→A/B槽位。实例slot/匹配的额外参数、标签和对称性须进入方法描述，当前尚不是已经实现的接口。

`data_scope.json`有active_goals/invariants，未提供完整token span/D/义务语义编译。双壶开炉是K，不是两个放壶目标之一；其原指令未完整表述该额外约束，不能说G/D/K全部从原文本自动推导。应承认离线任务规格来源、区分模型实际可见部分与监督/审计专用部分，并使三组拥有相同静态知识条件；原指令不改写为B。

## 4. 现有数据：能复用什么，尚缺什么

[003训练就绪记录](../../docs/stage_summaries/2026-11-04_task035_generated003_training_ready.md)与[036索引交接](../../docs/stage_summaries/2026-11-05_task036_software_accepted_training_ready.md)已记录：normal75/10共221条；train ten161条、54父组，fresh55条、raw136条，fresh/ten覆盖六任务、raw九任务。三个池并不独立；总索引101680行不是101680条独立示范。本轮不重新判定这些数据的035资格。

下表是**生产代码契约**，不代表本轮已读取服务器每个文件：

| 证据/标签 | 实际字段与位置（PR11固定版） | 支持程度与限制 |
|---|---|---|
| 原父与划分 | [data.py:137–183](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/trajectory_augmentation/data.py#L137)：export `sources.json`的parents/sources；`parent_demo_id/source_group/split/task_key/parent_file_sha256`，windows中start/stop/action_mask | 可绑定同父、同划分与动作窗口；不是强配对ID或因果证书 |
| 名义起点变体 | [control.py:123–145](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/trajectory_augmentation/control.py#L123)、[generation.py:243–263](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/trajectory_augmentation/generation.py#L243)：variant0名义机器人、另两组小关节扰动；rewind记录modified_indices/layout、非机器人前后hash、perturbation_rad | 非机器人不变是相对normal的handoff，不是相对normal初态；variant0也不自动是“只改变A” |
| normal/10关联 | `audit.json.handoff.normal_state_index/selection`；同父normal与10的source_id/domain/variant/attempt | 初态normal vs 初态10可能有伴随物体/速度变化；handoff normal vs 初态10则A通常两端都已完成，不能套NEED→PRESERVE |
| 当前native事实 | [generation.py:167–189](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/trajectory_augmentation/generation.py#L167)：`lineage.json.actual_initial_state/actual_initial_facts`；`audit.json.frames[t].facts/state`、rewind/handoff；qualification及diagnostic_events | 可作为离线潜态监督来源；未知保留，已真谓词还需义务/依赖解释；不是现成NEED/PRESERVE标签 |
| 当前观测与动作 | [generation.py:191–208](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/trajectory_augmentation/generation.py#L191)：HDF `data/demo_0/actions`为T，states及`mapping.images/proprio`对应数据集为T+1；完整instruction绑定保留 | fresh可复用BC动作与当前输入；具体图像/本体键必须按mapping读取，不能假定有名叫proprio的单一dataset |
| 控制与trace | [generation.py:95–114](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/trajectory_augmentation/generation.py#L95)：steps含phase/projection/reference_target/controller_target/audit_only；HDF controller_goal_pos/ori为T | 可追溯桥接与续接目标；续接还有桥接/保持，不存在已经证明的normal/10逐步时间对齐，不应强制连续动作相等 |
| 额外确认与失败 | audit.confirmation_frames和steps.audit_only；v2 rejected也可保留完整已观察transition前缀，export只选qualified | 确认帧不自动在HDF中，不能给HDF尾部补伪观测/动作；失败/raw不改成通过，也不自动纳入新训练 |
| 目标/K语义 | [data_scope.json](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/augmentation/data_scope.json)的active_goals/invariant_predicates；固定core `d8541ef4`的`benchmark/remaining_goals/nine_catalog.py:18–30,62–72`另有required_open_predicates | 抽屉/微波炉10为物已入、门开；双壶须保留开炉K。上述是监督/审计规格，不能作为在线真值mask |
| raw/参考观测 | [retention/data.py:116–142](https://github.com/No1dry/Learning-Not-to-Act/blob/205d6530e1ba389f74166a2e9520a3db7ae0edbf/egrs/retention/data.py#L116)：sources observation_mapping/basis，rows observation_index/prefix/pool；fresh source在036轻量索引中不完整保留035元数据，ten另含original_source | raw只读同一行传感，继续作原策略参考；fresh role应回链原035manifest/audit，不能从036 rows凭空恢复标签 |

### 三档监督不要混称

1. **普通BC/参考保持**：继续使用原合格fresh-ten动作与普通观测参考。缺pair不影响这部分，也不触发重生成。
2. **role监督**：已有初始事实和逐帧native trace具备生产基础，但须有版本化的`goal_id/instance_binding/obligation/label_valid/reason/source_frame`映射。初始关门为真不代表“关门义务已完成”；只用A/B truth或`t/T`不足。缺标签mask，不回写原024/035标签。
3. **语义关系配对／强单因素配对**：前者只要求对应目标的角色关系有证据，允许图像和合法运动不同，可作为结构正则；后者还需限定伴随变化、匹配机器人与决策相关状态，才能支撑“解耦阶段捷径”的因果解释。现契约没有给出全量强pair证书，161条10不能直接报成161对。不能为了保持候选预算把未知pair全部算有效，也不要求两张RGB或动作逐点相等。

建议最少新增**离线sidecar设计**：绑定原manifest/HDF/audit SHA；记录每端`source_id+observation_index`、goal/实例对应、角色与valid/reason、intervened_goal、relation_type和逐目标pair_valid；保留语义配对/受控因果配对的区别。该sidecar是待实现产物，当前没有宣称已存在。

### 只需Codex提供的小metadata证据

无需用户重跑或逐条看视频。下一工单前由Codex从**已有文件**摘取并脱敏：

- 003 export sources/report中各一份normal/10同父记录和一个旧复用来源记录，连同原始mapping/路径相对关系及SHA；036对应三池sources/rows各一行。
- 同父normal与10的lineage初始facts、audit首帧/hand-off/首个continuation的索引、rewind摘要；仅文本/数值小片段，不搬完整state/RGB。
- 一个依赖任务（抽屉或微波炉）的初始与完成前后facts，及已保留UNKNOWN的例子；若没有，明确缺失，不补写。
- 一份现有native facts的准确键/语义说明，以及九任务文本规格：goal引用/实例绑定、D、P准入、K与required-open来源。双同类目标要给实例对应规则。

这些样本只核对契约和字段，不足以统计全部有效pair。**强pair数、role可监督覆盖率、旧复用来源audit完整性目前未知**。若现成trace足够，新成本主要为离线join/sidecar与存储；若缺事实只能重放/渲染，或需要新实例/可视性人工标注，须单列新增预算，不能记为本轮零成本已具备。样本缺失不撤销旧BC资格，也不增加全库物理认证门槛。

## 5. 实验收敛、能回答什么与成本

| 组 | 固定相同部分 | 差异 | 可以归因的结论 |
|---|---|---|---|
| C0 | 同底座/LoRA初始化、原父split、观测顺序、expert/reference、统计、loss池权重、更新数和最终checkpoint | 动作BC＋保持，无角色模块 | 同数据增强/曝光本身是否足够 |
| C1 | 与C0/C2相同观测、动作/参考曝光；与C2相同角色监督、小模块容量和实例处理 | 预测角色接动作＋L_role，无pair | 整套角色结构相较C0的增益；不能把额外容量效应完全排除 |
| C2 | 与C1同结构/参数、与三组同采样 | 增加有证据的L_pair | 当前实现/数据/权重下pair正则的增量价值 |

三组必要且足以作这次局部方法分解；**不足以证明**优于所有近邻、角色因果中介、未见组合保证或普遍优越。移除pair若效果不降，就不主张pair必要；C1有效但C2不增益时，回到角色结构/增强的贡献定位。当前不额外要求复现ReViP或新增第四组；论文要声称优于其机制时再另定公平比较预算。

batch仍20：12 ten、4 fresh-ref、4 raw-ref及原池归一化权重可保留；但“2个fresh-prefix恰好对应2个ten”不是现sampler保证，prefix也不必是初态。应预先生成三组共用采样日程，显式选有效语义关系端点；若只在初态成立，就只在该处施加pair。其余样本保持BC/参考，缺关系就mask并记录有效量。按父组采样，避免三种机器人变体被当独立父样本；不因测试成败选pair。

C0不用标签不代表可以换一批更容易的观测。配对重采样必然改变相对036的曝光，三组同步改变并披露。C1/C2比C0多参数/运算；C2可能需要同时保留两端图，峰值显存可能增加。目标query可缓存冻结embedding，不需要额外VLM前向；“都是20观测/一个OFT forward每观测”不等于墙钟、激活或总FLOPs完全相等。现有checkpointing还含重计算，不能把逻辑前向计数当物理kernel次数。

### 候选成本表：全部待确认，当前执行为零

假设三组均每更新20学生观测、8参考；每250更新验证512学生观测（ten256＋两普通池各128），其中参考256。以下参考包含dev，均按未缓存上限计，**不是GPU小时承诺**。

| 项目 | 主设计三组各3000 | 可选节省版：三组各1000 |
|---|---:|---:|
| 优化更新总量 | 9000 | 3000 |
| 学生训练观测请求 | 180000 | 60000 |
| dev轮次／学生观测请求 | 36轮／18432 | 12轮／6144 |
| 参考请求train＋dev | 72000＋9216＝**81216** | 24000＋3072＝**27072** |
| 新模型正式评测 | 3×(90条10＋90条00)＝**540** | 同为**540** |
| 新仿真生成／旧基线重跑 | 0／0（仅在现证据可用前提下） | 0／0（同前提） |
| 新role/pair标签 | 覆盖与可用pair数未知；离线sidecar另报 | 相同证据需求，不因少训练就假定标签齐全 |
| 额外计算/存储 | C1/C2目标交互、残差、role loss，C2关系与图保留；sidecar/模块checkpoint；量级待模块宽度确定 | 同类额外开销，次数减少 |

只提出这一种节省替代：共同1000、固定末步、不自动续到3000；它与既有运行长度接近且对照内部公平，但若训练未收敛，只能说该预算下无收益，不能断言方法普遍无效。若优先排除训练长度不足，选择原三组共同3000即可；不能先看测试SR再决定谁加训。不要把035/036旧1000与新C2的3000作唯一方法对照。

主结果仍10二元合规SR、00官方SR，全部九任务/原来源/评分/视频保留。每条件90条、每任务10条，单条总体约1.11pp；一次训练seed的微小涨跌不足以宣称稳健普遍改善。可从既有同episode结果报告配对得失与不确定性，不新增真实episode或主观评分。role/pair诊断只用原dev，不能据正式SR挑λ/检查点。

未有10增强的stove/mug_pudding/two_pots三个任务完整报告“已知任务、未见该任务10增强的外部完成迁移”；普通池已见这些任务，且划分源于既有可用数据/已知历史结果，因此是探索性迁移。不是未见任务zero-shot；九个两目标10也不能验证D的多完成组合。更强组合协议单列预算，不作为当前补建要求。

## 6. 本轮交付与下一步执行者

本轮设计审阅与回复文档完成100%；新增方法实现、数据导出/标注、训练、模型评测均0%。只进行了文档/源码静态阅读、原文检索与人工推导；未运行CPU/fake测试、数值脚本、模型、仿真或真实作业。没有修改冻结部署、原数据/失败/raw、旧独立稿、评分或代码，没有自动合并/清理。

下一步由**Codex**一次取舍：接受“结构正则”的收窄定位，明确P/D/K与实例绑定，提供上述现成小metadata样本并据此确定监督/关系范围，选择共同长度及最终预算。随后由**用户**确认新增资源；获新实现工单后再由X实现与定向CPU/fake、Codex审查部署，全部真实作业仍由用户启动。本回复本身不是实现或实验许可。
