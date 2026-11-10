# Task 040：新增训练父源的10续接覆盖扩充

2026-11-10，Codex交X。**用户已明确批准推荐方案、预算及提交工单。现在直接实现＋定向CPU/fake，不再先交方案或泛审。真实作业仍只由用户启动。**

依据：[040方案](../../docs/research/2026-11-10_task040_parent_coverage_proposal.md)、[039分析纠错](../../docs/research/2026-11-10_task039_analysis_review_corrections.md)、[批准记录](../evidence/040_budget_approval_and_dispatch.json)。用户原话：“按你推荐的吧，提交工单吧”，随后要求继续。

## 0. 一页任务与验收范围

沿039已验收的生成方法，为`stove`、`mug_pudding`、`two_pots`各新增`demo_20..39`候选，固定分组后仅对新增train父组做有界生成。**旧039全部数据复用，新合格train10＋新train pair追加；原fresh/raw及全部dev完全保持。** 从原SOG10新初始化一组C1训练1000更新，固定末1000评原九任务10/00各90；不是续训039，不先跑S，不增加C0/额外seed或改变方法与评分。

交付包含：一个用户生产入口（元数据→train-only生成→增量导出/索引）、一组C1训练/保存恢复、正式180评测接线、百分比进度、配置示例及常用conda/python命令。只在新040入口/契约中支持增量，不能全局放宽旧035/036/038/039严格断言。

### 固定依赖

| 依赖 | 固定身份 |
|---|---|
| 已验收实现 | PR14 head `113ded21434a06e2cdc156e5d6283a11c3f15488`（含038依赖）；不是只克隆main |
| 当前文档基线 | main `a9e3f291b1f5d1f0bc545a9de73954c6a2935118`之后的本工单；同步最新main文档但不自动合并旧PR |
| 原039 task-control索引 | `b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c` |
| 原039 report identity | `64a2d4923dda271ffeb2a67f080c81c40bbdb277bae6351328a779791e1abdaf` |
| 原普通演示 | `yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3` |
| 原SOG10 | `moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7` |
| 统计 | `libero_10_no_noops`，dataset_statistics SHA `6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3` |
| 正式core / reporting | core `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`；reporting目录来源`cb8aca6aca0864bb9a304bdf2471b5025b371479`，沿原内部字节锁及双bridge |

旧039已结束且结果有效，C1 10/00=58.89%/85.56%。本轮是新数据功能，不是因旧软件效果返修；旧实现、原始数据、权重和失败一律保留。代码地图见[主交接](../../docs/handoffs/2026-11-08_project_handoff_after_task039.md)第10节。

## A. 输入契约和新候选，不改旧split

新增配置显式绑定原039 task-control/retention索引、其原merged及旧根引用、原035完整180父清单/原生成环境配置，以及新输出目录；复用已有固定配置，不让用户手抄整套数据字段。示例用`$LNA_ROOT`等占位，实际路径由Codex部署时填，不提交凭据或服务器私有工件。

1. 新候选**恰为**上述三任务各`data/demo_20`至`data/demo_39`，共60个；不能把旧`first20`重标为新源，不能缺一个就从40以后补、不改其他六任务。三个既有HDF各50个demo与候选键存在已由Codex只读元信息确认；实际完整输入由用户生产入口绑定，不重下官方数据。
2. 在真实生成前，由同一生产命令构造新版本040元数据清单。复用原相对文件名、完整原指令、task语义、HDF mapping、OSC_POSE和图像方向/归一化声明。canonical原父ID为`<官方相对HDF路径>#demo_N`，episode为`data/demo_N`；阶段路径前缀不能成为新的父身份。元数据命令不需要模型/仿真，真实轨迹与标注步骤不可伪称只是文件准备。
3. 保留原180父组136train/44dev的ID、group、split及全部记录。新候选按原seed7/已知重复组件规则分组：没有旧锚点时用完整新组件的canonical source IDs排序、`sha256('7|'+ '|'.join(ids))`，模5为0分dev，否则train；沿原alias组件规则，不另造按任务抽签或改seed。
4. 与旧父源已知重复者继承旧split，不能伪称新独立父组；不重复生成已知旧父组，同一新重复组件只取自然序最小代表生成，其余alias留清单。若新组件连接旧train与dev，拒绝受影响的新候选、记录冲突，不能移动旧来源或破坏原数据可用性。
5. **仅新增train父组进入生成计划。** 新候选dev保留元数据但不生成、不加入训练/pair或本轮dev。记录60候选、每组实际代表、train/dev/重复/冲突/缺字段及选择原因，计划在读任何正式测试轨迹前固定。原HDF的物理祖源未知继续标unknown，不能声称对原模型未见或对正式init已物理独立。
6. 不需要新做全库重复检测或恢复所有旧轨迹。只核对本次新范围与已有明确重复证据；缺失来源真实性信息照实失败，不能靠造hash/断言通过。官方测试init/rollout不进入生成、训练、标签或teacher选择。

## B. 真正生成：复用039，不新增控制算法

1. 对每个已固定的新增train父组，normal最多1次；合格后最多3个原机器人起点，每起点最多2个原桥接尝试。正常沿原“成功后不再试替代桥”的行为，不为消耗预算凑满次数。
2. 复用`physical_release_clearance_v3`：原生全任务成立后真实张手≤10步、竖直退离≤20步/0.10m、保持≤10步，最多40额外控制步且**全episode≤520**；原真实释放连续5观测，不用张手指令/几何退离代替证书。收尾完整进入T动作/T+1观测，不放进audit-only尾巴。
3. 仅`two_pots`沿039在normal初始化之前交换两个同类壶freejoint的qpos7/qvel6，非目标状态不动，A/B谓词及实例名不换。其他两任务初态保持原样，不增加场景编辑、目标重标或中途teleport。
4. 从新normal记录中的安全canonical `[A=True,B=False]` handoff只重置原机器人索引，按原真实桥接/控制目标续接重新执行B。监督标签必须是实际投影/执行动作；禁止直接拿normal后半段动作给回初态机器人，禁止旧RGB配新状态。
5. 原V2准入、A/K保护、已确认违规/穿透及释放规则全不变；原table_drop未知仅诊断政策不扩大。失败前缀/原因/来源/尝试计数全部保存，不能unknown→True、改5帧或过滤掉正式失败来提分。
6. 新040 recipe/provenance绑定source range、fixed split、train-only、原039算法版本及此次账本；旧来源保留其原identity/签名/资格。可以复用原helper，但新输出不得伪装原039生产。

## C. 最容易出错的索引要求：新增normal不等于新增fresh

采用独立的新040增量索引/视图，引用旧039已合格数据，不覆盖或重写旧文件，不做可写hardlink。固定期望来自旧039真实索引，不全局删掉旧数据验证。

| 数据部分 | 必须怎样处理 |
|---|---|
| 原ten | 305条（224train/81dev），原行/动作mask/计数标签/来源保留；追加仅新合格train10 |
| 原fresh参考 | **完全原105条（78train/27dev）**、原观察行/前1/3与all划分/标签保持；新normal不得进入此池 |
| 原raw参考 | **完全原180条（136train/44dev）**、原观察行、无count标签保持；新原始demo不得进入此池 |
| 原pair | 305对（224train/81dev）及其成员、来源和证据复用，不因入口变化重做旧物理资格 |
| 新pair | 新normal的handoff端＋同父新ten的初始端，只在train；各端取自己真实出站动作，不是normal初态，也不交换动作 |
| 新normal | 存在生成导出与pair专用来源表中，**不出现在20个主池样本集合**；不以`fresh`采样来代替pair-only能力 |
| dev | 所有旧dev主池行、pair及确定性选择顺序保持，新dev为空增量；不能仅保持条数却换了样本 |

1. 新pair按038原规则核验**记录的**非机器人状态、活动目标/保持事实、释放及实际机器人变化；排除索引沿lineage，不猜坐标。仍为1e-8原比较规则，各端都要有有效动作。缺标签mask，不用official谓词数组前两项猜A/B。新pair缺失单列原因，不把有资格的ten BC轨迹因缺pair自动踢掉，已有旧train pair可继续训练。
2. 新normal可供`get_pair()`解析，但不能混进主采样rows。可扩独立`pair_sources`等，只要求显式、可验证、保存恢复能消费，不能用伪pool绕过、零权重假样本或伪造现有source字段凑契约。
3. 原dev数据及新索引的`dev_indices`/`dev_pair_indices`所选**稳定source+observation/pair键与顺序**要等于旧039，不只比较行号。训练/dev视图共享同一新的外层index identity。内部算法schema可兼容原038，外层040清楚绑定旧identity、新delta、train-only与实际计数，不因阶段名重写网络。
4. 旧来源及新HDF按稳定路径/实际stat在单次生产进程共用hash上下文，同文件只读hash一次；旧已核验物理资格/sidecar不再重放。不要重演每父重复hash同一大文件，也不要引入跨进程“永久免验缓存”。变动文件拒绝，不能把skip写成验证通过。
5. 报告旧/新增/合计的每任务train父组数、ten条数/窗口、pair数/缺口；fresh/raw/dev未变证据、候选dev封存数和预算。若有已记录初态坐标可汇总新分布范围，不额外仿真/模型做覆盖测量，不把parent数量当已证明的独立物理布局。
6. **没有来自新增合格train父组的ten时，训练入口在加载模型前拒绝浪费相同覆盖训练。** 有新增按实际合格量继续，无每任务N条/新pair最低数门槛，不自动追加来源或预算凑N。

## D. 同一C1算法，一组1000，不续训

1. 从原SOG10新初始化新增LoRA/z/动作残差，arm只能本轮C1；不加载039 adapter当初始化，不跑C0/S/3000步或额外seed。沿原seed7、lr2e-5、warmup50、bf16、gradient checkpointing、save250/500/750/1000、固定末1000。
2. 每更新12ten＋4fresh-ref＋4raw-ref、主loss .50/.25/.25，另1pair两端；task→parent→variant→window均匀层级不改。仍为`L_main+.10 L_count+.05 L_self+.05 L_swap+.01 L_align`；原网络、count/z/LoRA/rank和原参考完整旁路全部新增模块保持，不加progress/FINISH/额外保护loss。
3. 固定原dev及选择，参考上限9024=8000训练＋≤1024dev；学生上限24560=22000训练＋≤2560dev。新normal用于pair两端，已经包含在22个学生观测/更新内，不增加隐藏VLA或参考调用。
4. 保存原checkpoint/optimizer/scheduler/RNG/sampler/两账本及新index identity，恢复只允许原run/账本/同配置同index，不把新run续旧039。eval reload共用真实train forward，所有新增模块恢复，模型元数据绑定实际040index而非伪旧b8587565。
5. 不改变底座、动作head、proprio/图像白名单/归一化/原完整指令；mask、task ID、source ID、GT、目标事实、未来帧不进入策略输入或推理路由。eval仍单VLA无教师/外部VLM。

## E. 正式180、日志和用户命令

- 复用039 C1原正式来源/九任务人口、core/reporting、双bridge/proxy、H520/chunk8/seed7、10二元合规与00官方端点、全视频；仅绑定本轮实际末1000新权重与新run，不重建状态或重跑原模型/039。不继承039分数，不改评分或另跑一个report进程。
- 生产建议一个显式`python -m egrs.coverage040 generate --config ... --output ...`入口，完成候选元数据→真实有界生成→增量索引，**不自动开训练/eval**。train/eval为独立用户命令，提供普通conda/既有venv激活＋python、nohup日志及精简进度查看模板，不要求用户使用uv等新工具或反复手工plan/pip/MVP。
- 每≤30秒显示当前阶段、已处理父组/计划父组及百分比、normal/ten已花槽与上限、当前来源/variant/桥/控制步和耗时；不要用“已花尝试/360”冒称生产完成比例。训练显示update/1000、百分比、loss、耗时/估计；不刷巨大sampler字典。eval复用已有进度及最终正式SR百分比/每任务表/视频路径，不为实时SR另造评分。
- 输出命名建议data/coverage040/production-001、runs/task040-c1-train-001与task040-c1-eval-001；配置通过`$LNA_ROOT`等实际部署变量解析，不能把字符串占位当已经展开的路径。旧输出存在拒覆盖，非实验参数必需时明确报错，不能悄悄退回默认假路径。

## F. 批准的总上限与记账

| 类别 | 上限 | 记账 |
|---|---:|---|
| 普通重放 | 60 | 新train代表父组每个最多1次；新dev/已知旧重复0次 |
| 10尝试 | 360 | 每新train父组3×2；每episode≤520，包含全部收尾/确认动作 |
| 训练 | 一组C1 1000 | reference≤9024，student≤24560；含所有dev调用 |
| 正式eval | 180 | 九任务10/00各90，不包括任何额外MVP/基线 |

新生产的持久attempt ledger在物理初始化前占槽；失败/初始化异常/用户中断都保留花费，不退款、隐式重试或删除重开同槽。新run拒覆盖；如支持显式同run恢复，仅核对同计划并跳过已花槽，不再次执行中断槽，不引入额外normal重放。预算是上限不是必跑次数/成功数保证。总最大控制218400步；原H内含确认，不另加无账本物理诊断。

## G. 定向CPU/fake，一次交付

只做受影响路径，复用已有039验收；以下每类直接防本轮解释或运行错误，不要求全库279/真模型试训或真实MVP：

1. 20..39范围/三任务/固定分组及alias：旧180 split不变、dev绝不生成、新重复代表不多花槽、冲突不移动旧数据；旧first20入口仍拒新范围。
2. fake生成验证normal1、3×2、全局60/360/H520及真实收尾/双壶初始化旧规则；在初始化前崩溃/中断仍记已花，新run拒覆盖/不退款；无GT策略输入。
3. 合成旧039＋delta（一个新train、一个封存dev足够）：旧fresh/raw/dev及选择键/顺序严格相等，新normal只进pair来源、新ten只train；真实T+1/T、归一化往返/来源地址与mask错误会拒。没有新合格父组时加载模型前拒训。
4. fake/tiny policy走generate/export/index→22学生/8参考与原C1 loss→save/resume/reload→fake eval合同，证明实际消费新index及新pair来源而非旧039或新normal被主池抽到；不加载7B、不跑真实任务。新pair失败不连坐合格BC数据。
5. 同进程同文件hash一次、文件变化失效与≤30秒可见进度；共用不变底座/动作推理、旧双bridge eval接线只做受影响fake，不升级依赖/恢复无关完整Git历史。

## H. GitHub交付与角色

新PR包含实现/版本化配置、常用命令模板、上述定向测试结果及`collaboration/responses/040_round1.md`。基于accepted PR14实现依赖并同步当前文档；注明新head、主要文件/契约和必要偏差、真实未运行事项及参数由Codex部署填充的位置。无需再写长综述/重新论证S是否先做；有明确矛盾集中报告，不擅自扩大预算或换方法。

**X只改代码及CPU/fake，不SSH部署/启动真实HDF数据生产、仿真/模型/索引/训练/eval；预算获批不扩代跑权限。** Codex建议式审查，仅明确错误/泄漏/危险/证据失配/关键缺项阻断；验收后隔离部署、提供完整普通命令，用户亲启真实作业。不得自动merge、删除、覆盖旧数据或将040软件完成称为SR提升。
