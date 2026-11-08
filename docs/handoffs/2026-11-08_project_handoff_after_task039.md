# Learning Not to Act / LIBERO-Remain 项目交接文档

版本：2026-11-08，039正式评测收尾后。作者：Codex。读者：用户、后续Codex、X，以及其他接手agent。

本文是接手入口，不是新的实验启动授权。事实基线为方法库提交 `f6e9b8b7668ab1c20505a2b162ccb7d1b8e93aa2` 及其已归档的039结果；发布本文会产生新的文档提交，但不会改变该实验基线。

GitHub规范位置：[docs/handoffs/2026-11-08_project_handoff_after_task039.md](https://github.com/No1dry/Learning-Not-to-Act/blob/main/docs/handoffs/2026-11-08_project_handoff_after_task039.md)。接手时同时看[最新STATUS](https://github.com/No1dry/Learning-Not-to-Act/blob/main/collaboration/STATUS.md)与[仓库AGENTS](https://github.com/No1dry/Learning-Not-to-Act/blob/main/AGENTS.md)。若日后状态继续更新，不能用本文的日期快照覆盖新的用户决定。

阅读导航：用户先看[一页状态](#0-先读这一页)、[结果](#7-已完成实验结果与解释)和[下一步](#11-接手后立即做什么)；研究agent再看[方法](#5-当前c0c1到底是什么)与[数据](#6-训练数据增强流程和039修复)；实现/审查agent再看[环境路径](#8-服务器环境和关键路径)、[代码地图](#10-给实现审查agent的代码地图)和[坑点](#13-容易踩的坑和不能重复的动作)。所有人先遵守第1节权限。

## 0. 先读这一页

### 当前研究在做什么

研究问题是：**当人或外部过程提前完成部分任务后，VLA能否依据当前观测重新确定剩余目标，在保留已有成果的同时完成任务？**

当前具体研究实例是复合任务的 `10` 状态：子目标A已经完成，B尚未完成。指令保持原样，期望模型跳过不再需要的A，允许合理观察/简单尝试，然后完成B并保护A。重点不是训练一个“收到FINISH后停下”的模型。

用户的优先级依次为：

1. 提高10合规成功率。
2. 保持普通00任务成功率。
3. 泛化性与更强的方法贡献，论文目标仍面向ICML。

### 目前到哪了

| 项目 | 当前状态 |
|---|---|
| 正式benchmark | 9个LIBERO-10复合任务，每任务10个episode |
| 正式评价条件 | 10与00各90条/模型；不再主测01/11 |
| 最近阶段 | 039数据恢复、C0/C1各1000步训练、两模型共360条正式评测，全部完成 |
| 当前最好微调版本 | **039 C1：10为58.89%（53/90），00为85.56%（77/90）** |
| 对照039 C0 | 10为56.67%，00为80.00% |
| 原始SOG10 | 10为24.44%，00为86.67% |
| 运行情况 | 039收尾时两训练、两评测均正常退出；不能把这个历史快照当未来实时状态 |
| 当前待办 | 分析已有失败轨迹/视频，提出下一步针对性方法取舍 |
| 尚未批准 | 新一轮训练、续训、更多seed、追加生成、扩benchmark、改评分 |

**接手后不要重复039生成、训练或评测，不要直接把1000步续到3000步。040尚未形成已批准工单/预算。**

### 最重要的三个提醒

- 方法库 `main` 当前主要承载决策、文档和协作记录；最新已验收实现仍在**未合并PR14的固定head**中。只拉main并不等于拿到可运行039实现。
- 数据增强已有效，但C1相对同数据C0的10额外收益仍只有2条；不能把对原始模型的全部提升都归因于新上下文约束。
- 开炉、双壶、白杯布丁三个任务在039 C1的00均100%，10却是30%、20%、0%。这是下一步分析重点，而不是再做一轮无针对性的工程检查。

## 1. 协作权限和工作方式

| 角色 | 应做 | 不得自行做 |
|---|---|---|
| 用户 | 研究取舍、预算/资源；亲自启动、运行、监督所有真实实验 | — |
| Codex | 研究决策、详细需求、建议式审查、文件准备/部署、完整命令、结果分析和归档 | 自主启动/停止/重跑/追加真实实验；自动合并X的PR |
| X | 修改实验实现、受影响CPU/fake测试、GitHub交付 | 实际模型/仿真/训练/eval、服务器真实作业；擅自扩大算法/预算 |
| 其他agent | 默认继承分析/审查边界；先确认自己的角色和用户最新授权 | 把“能访问服务器”或“预算已批准”理解成可代用户启动实验 |

原DeepSeek已经退出，不再分配任务；历史署名、日志和证据保留。历史上用户给过Codex一次“直接改并跑到训练就绪”的特例，已经结束，不能继承为当前权限。

真实实验不仅指GPU训练：真实仿真回放、重新渲染、特征抽取、教师/VLM推理、新训练标签/索引生产、模型eval都不能自动启动。读取现成JSON、统计已有正式结果、复制已有文件/视频、写配置和启动脚本不等于启动实验；但不能把真实标注/仿真包装成“只是文件操作”。

agent查看已录视频、解码/抽取现有帧作定性分析属于证据阅读，不是重新跑服务器教师/VLM批量标注管线；允许这种分析，不要因此卡住下一步。原视频/原分数仍不可改写，也不能把agent观察冒称人工专家标注。

用户于2026-10-18要求提速：

- 只做直接防止结果解释、运行正确性、数据安全错误的必要检查，并说清防什么错误。
- 复用有效证据，不因入口/报告调整重建状态或重复物理资格。
- 代码改动优先受影响CPU/fake回归，不把全库、多平台、发布级覆盖或真实MVP例行变成开跑门槛。
- 审查以建议为主；仅明确错误、真值泄漏、危险控制、证据失配或关键约定功能缺失阻塞。
- 不覆盖旧数据/旧失败、不热改运行目录；新实现用独立版本目录。
- 给X的实现要求必须真正上传GitHub `collaboration/tasks/`，并给用户可复制的简短prompt和链接。只在聊天里说“让X改”不算交接。
- 每次回复附“下一步操作和执行者”；进度优先百分比，区分准备、训练、模型执行和正式计分。

## 2. 仓库、代码和权威记录

### 2.1 三个仓库不要混用

| 仓库 | 职责 |
|---|---|
| [No1dry/LIBERO-Remain](https://github.com/No1dry/LIBERO-Remain) | benchmark定义、初态/协议、冻结执行core和原始评价基础 |
| [No1dry/Learning-Not-to-Act](https://github.com/No1dry/Learning-Not-to-Act) | 当前改进方法、训练/评测接线、研究决策与X协作主库 |
| [No1dry/LIBERO-Remain-Eval](https://github.com/No1dry/LIBERO-Remain-Eval) | 给其他人测其他VLA的精简benchmark分发库，不放方法研究过程文档 |

Eval库已同步九任务，但现成批处理入口仍带有旧六＋新三来源组织和SOG10接线。**不能假称任意新VLA只替换runtime就已拥有全90通用driver；更不能复用其他模型的分数。**

精简Eval库不随源码分发完整状态bank和模型权重；给外部合作者使用时，应说明额外数据/环境准备边界，不把内部方法repo当成无条件即装即跑的通用评测包。

### 2.2 当前版本锚点

| 含义 | 固定身份 |
|---|---|
| 039结果事实提交 | `f6e9b8b7668ab1c20505a2b162ccb7d1b8e93aa2` |
| 已验收039实现交付 | [PR14](https://github.com/No1dry/Learning-Not-to-Act/pull/14)，head `113ded21434a06e2cdc156e5d6283a11c3f15488` |
| 039功能实现commit | `8a733d039aef69df1323bb34c896ed40895cff12` |
| 已验收038依赖 | [PR13](https://github.com/No1dry/Learning-Not-to-Act/pull/13)，head `5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`；实现 `b5849e4e4f7f56b888922e1267870126f5368ccf` |
| 036保持能力依赖 | [PR11](https://github.com/No1dry/Learning-Not-to-Act/pull/11)，head `205d6530e1ba389f74166a2e9520a3db7ae0edbf` |
| 冻结benchmark core | `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9` |
| 报告层目录来源 | `cb8aca6aca0864bb9a304bdf2471b5025b371479`；内部reporting字节锁revision为 `d2afce4eb074b777364daddea2c08bd70731865f` |
| 旧环境bridge依赖 | `ac1301779cf6ae4c34ebc80c20936a4f7a4953be` |
| 官方OpenVLA-OFT代码 | `e4287e94541f459edc4feabc4e181f537cd569a8` |
| 原始SOG10权重来源 | `moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10`，revision `638918f3d1c2e43a39a8a20772bdb8b91835e4b7` |

PR14包含未合并的实现依赖链。不要自动merge PR10/11/13/14；PR12是037设计审阅，不是必须合入的实验实现。后续新实现应明确以哪个已验收head为基线，再同步最新main文档。

039软件已有受影响279个独立CPU/fake最终通过、无遗留失败/skip的验收；早期本地fixture、Windows symlink/OpenMP测试环境问题已记录并闭环，不要把它们重新变成科研门槛。

服务器部署是固定源码快照，不保证有完整`.git`；不能用目录名字或`git HEAD`替代部署receipt中的SHA。当前共享报告标题/adapter schema仍含Task038，是039复用同一算法的既定设计，不是又测了038权重，也不值得为标题重跑实验。

### 2.3 推荐阅读顺序

1. 本文＋[最新STATUS](https://github.com/No1dry/Learning-Not-to-Act/blob/main/collaboration/STATUS.md)＋[AGENTS](https://github.com/No1dry/Learning-Not-to-Act/blob/main/AGENTS.md)。
2. [039最终阶段总结](https://github.com/No1dry/Learning-Not-to-Act/blob/f6e9b8b7668ab1c20505a2b162ccb7d1b8e93aa2/docs/stage_summaries/2026-11-08_task039_final_results_coverage_recovery.md)和[R4裁决](https://github.com/No1dry/Learning-Not-to-Act/blob/f6e9b8b7668ab1c20505a2b162ccb7d1b8e93aa2/collaboration/reviews/039_round4.md)。
3. [机器结果](https://github.com/No1dry/Learning-Not-to-Act/blob/f6e9b8b7668ab1c20505a2b162ccb7d1b8e93aa2/collaboration/evidence/039_final_results.json)。
4. [037-v2方法规格](https://github.com/No1dry/Learning-Not-to-Act/blob/main/docs/research/2026-11-06_task037_v2_task_control_factorization.md)、[038工单](https://github.com/No1dry/Learning-Not-to-Act/blob/main/collaboration/tasks/038_task_control_factorization.md)。
5. [039数据恢复工单](https://github.com/No1dry/Learning-Not-to-Act/blob/main/collaboration/tasks/039_teacher_release_and_coverage_recovery.md)，再读固定PR14源码。

旧文档中的“待启动/0%/待批准”必须结合最新状态看；035/036/038/039已经完成的run不能因旧命令还在而重开。

## 3. 当前benchmark与指标

### 3.1 00、10究竟是什么

- `00`：两个active子目标均未完成，执行原完整任务，用作普通能力对照。
- `10`：固定定义的A已经完成、B未完成；指令仍是原完整指令。模型需要完成剩余B、保护已有A及约束K。
- 当前不主测`01/11`，不以它们的历史准备失败连坐已通过的10。
- 当前正式实验是**场景初态已经部分完成**；没有证明运行中任意时刻外部介入、任意完成子集或真机情况都已解决。大问题可以继续保持，但报告具体实验范围要准确；不要求现在先补齐这些范围才能研究。

“Learning not to act”在本轮主要指**不再执行已经不必要的子任务**，不是要求机械臂全程静止。用户允许合理观察、寻找目标或简单尝试；不能自行把任何试探都认定失败。当前违规与成功仍按冻结实现，不在交接中增加例外或新门槛。

### 3.2 九任务与固定A/B

| 官方LIBERO-10 ID | key | A：10初态已完成 | B：10仍需完成 |
|---:|---|---|---|
| 0 | `basket` | 汤罐入篮 | 番茄酱入篮 |
| 1 | `basket_cheese_butter` | 奶酪入篮 | 黄油入篮 |
| 2 | `stove` | 炉子打开 | 摩卡壶放炉上 |
| 3 | `bowl_drawer_close` | 黑碗入底层抽屉 | 关闭底层抽屉 |
| 4 | `dual_mugs` | 白杯放左碟 | 黄白杯放右碟 |
| 6 | `mug_pudding` | 白杯放盘上 | 布丁放盘右侧指定区域 |
| 7 | `basket_soup_cheese` | 汤罐入篮 | 奶酪入篮 |
| 8 | `two_pots` | `moka_pot_1`放炉上 | `moka_pot_2`放炉上 |
| 9 | `mug_microwave_close` | 黄白杯入微波炉 | 关闭微波炉 |

官方ID5单目标任务未纳入这九个复合任务。旧LIBERO-90迁移任务已退出当前主评测；原始SOG10并未以LIBERO-90为本批训练suite，不能拿那些迁移失败替代当前研究结论。

两个重要细节：

- 双壶的炉子始终打开是保持条件K，不是第三个待完成子任务；不能为凑“00”把炉子关掉。
- 抽屉/微波炉的10是物体已入、门仍开，B是关门。active A/B顺序必须依语义映射读取，不能把官方谓词数组前两项机械当A/B；抽屉已有不同顺序的实际例子。

精确指令/实体谓词见固定实现的`egrs/augmentation/data_scope.json`和core的`benchmark/remaining_goals/nine_catalog.py`。A/B是协议槽位，不应作为策略输入或靠simulator ID路由动作。

### 3.3 只保留两个主要成功率

| 条件 | 主指标 | 判定来源 |
|---|---|---|
| 10 | `binary_compliant_SR` | 固定core的目标、成果保持、释放及违规证据，再由二元报告层映射 |
| 00 | `official_task_SR` | 原生LIBERO官方完整任务谓词/端点 |

每模型每条件固定90条；全部完成且无完整性错误才给正式SR。每任务10条，因此各任务百分比按10个百分点变化。完成数量不等于成功数量。

10的实现要点：原生完整目标达到、A/K没有发生协议禁止的回退、完成释放连续确认，以及原有已确认违规等共同决定结果；当前确认窗是5个连续观测。错抓/错放/掉桌等使用既有物理证据和阈值，**不是无所不知的人类语义oracle**。用户“错抓、漏抓、严重破坏失败”的理想不能替代实际实现细节。

二元报告层将已完成的core `success/failure/unknown`映射为`success/unsuccessful/unsuccessful`。因此论文主表没有第三类unknown；底层不确定诊断仍保留，不能悄悄改成成功。缺文件、技术错误或未执行不能冒充模型失败来凑分母。

00直接使用官方口径，不套额外10保护判据。旧六00与新增三00保留原来源/端点组织，不混算不同端点的平均路径效率。10与00判据不完全相同，不能将差距全解释成单一认知因子；需要结合失败诊断。

路径长度/TCP距离、wrong_grasp、goal_regression、完成步数、计数准确率、loss等都是诊断，不是新主指标；不要恢复一大套UIR人工评分/VLM评分，不要把TCP距离直接叫SPL或等同冗余动作。

当前停止是环境/协议端点或H520上限，不是模型输出FINISH。无FINISH头、无测试时教师/外部VLM/真值路由；不能把环境终止说成模型学会了自主停止。

## 4. 从历史路线到当前方法

| 阶段 | 内容和结论 |
|---|---|
| 早期 | no-op/停止、FINISH头、行为树、外挂VLM/记忆等曾讨论或试验；FINISH不再是当前主线 |
| 历史EGRS/029 | 外部教师/选择器等路线经过接线与评测，用户已停止029；不要自动续跑旧80条 |
| 031/033/034 | 普通00对照、九LIBERO-10复合任务、冻结核心及二元10报告逐步收敛 |
| 035 | 从普通演示真实重放，生成A已完成/机器人回起点的10轨迹；动作损失微调有效，00明显退化 |
| 036 | 10增强＋普通观测上的原策略动作蒸馏，改善00保持，但10有取舍 |
| 037 | 研究设计审阅；原角色/剩余化理论候选未直接实施，避免把已有概念/基础不等式包装成新理论 |
| 038 | 实现单VLA任务上下文z＋动作残差，正式C0/C1同数据对照；10额外收益较小 |
| 039 | 不改038网络/loss/评分，恢复三个缺10监督任务；完成新数据、两组训练和正式360评测 |

代码包名仍叫`egrs`，不代表当前还在运行旧外部选择器方案。`envs/selector`、旧7B教师、finish-head工件和025–029目录都不是当前默认入口。

已有调研与[037 R1审阅](https://github.com/No1dry/Learning-Not-to-Act/blob/main/collaboration/reviews/037_round1.md)已经指出剩余化、进度反馈、不变表示、反事实增强等有近邻。当前新颖性/理论充分性尚未解决，不能因为面向ICML就补写未经论证的识别/泛化保证，也不能为novelty保留没有实际增益的装饰模块。需要重新主张新颖性时，应阅读已有调研并再核对原始论文，而不是只改术语。

## 5. 当前C0/C1到底是什么

### 5.1 输入、输出与模块

唯一策略输入是原完整语言指令、当前双RGB（agentview＋wrist）、8维proprio。输出仍为8步×7维动作块，每次按原chunk协议执行。任务ID、mask、A/B真值、计数标签、pair/source ID、未来状态不能进入策略提示词或动作路由。

一次OFT前向得到56×4096动作隐藏`H`及当前视觉/语言prefix。新增模块为：

```text
当前双图＋完整指令＋proprio
          ↓ 原OFT骨干（新r16 LoRA）
  prefix视觉/语言隐藏 ──MLP(256)──→ z(128)
                 H(56×4096) ＋ z ＋ p(8)
                              ↓ 256维瓶颈零输出残差
                           H'(56×4096)
                              ↓ 原冻结动作head
                           8×7动作
```

具体形式：

```text
z = MLP([mean(H_visual), mean(H_instruction)])
H' = H + W_out SiLU(W_h LN(H) + W_z z + W_p proprio)
```

`W_out`零初始化；新增LoRA训练语言q/k/v/o，rank16、alpha32；原base/vision/action head/proprio projector冻结，但动作head对输入隐藏仍可传梯度。训练、保存/恢复和正式predict共用实际接线，不是只训练时加模块。

辅助头从z预测两个active目标已完成数量0/1/2，只用于训练锚定；不是FINISH、实例角色头或硬动作gate。计数本身不能区分“具体哪个目标已完成”。prefix已融合输入，删掉proprio槽不代表消除了机器人信息；z解耦是学习目标，不是已证明的数学分解。

### 5.2 配对语义

配对`u=normal[handoff]`与`v=ten[0]`：同父/指令/split，非机器人世界状态和A真B假事实相同，机器人姿态不同。各端动作标签来自各自真实执行的合格轨迹。

这不是“只把A从未完成翻成已完成”的单因子干预对；normal初态与10初态也不能因同父就声称所有其他因素完全匹配。

C1只交换z，接收端仍用自己的H、proprio与自己的专家动作目标。不交换整幅图像、不强制两端动作相等、不把普通演示后半段动作直接复制给已回起点的机器人。

### 5.3 目标函数与对照

```text
L_main  = .50 L_BC,ten + .25 L_ref,fresh + .25 L_ref,raw
L_self  = 两端用自己的z，对各自真实动作的平均L1
L_swap  = 两端交换z，仍对接收端自己动作的平均L1
L_align = mean((normalize(z_u) - normalize(z_v))²)

C0 = L_main + .10 L_count + .10 L_self
C1 = L_main + .10 L_count + .05 L_self + .05 L_swap + .01 L_align
```

C0/C1同网络、参数量、数据、标签与训练长度，差别是交换/对齐约束这一包。**C0不是原始模型，也不是纯普通BC；它也有z、残差、计数与self配对监督。** 两组不能分别证明swap和align各自有效，当前没有独立消融。

### 5.4 训练固定设置

- 都从原SOG10新初始化本轮LoRA/模块，不续035/036/038的旧改进权重。
- 每组1000次更新，不是1000个epoch；lr2e-5，warmup50，seed7，bf16，梯度检查点，microbatch1。
- 每更新12ten＋4fresh-ref＋4raw-ref，另1个pair的2端，共22个学生观测；分层按task→parent→variant采样，不是每轮完整遍历所有轨迹。
- fresh/raw参考目标是同原基座在这些普通观测上的动作输出；参考前向旁路全部新增LoRA/z/残差，不只是关一层LoRA。不是给eval加教师，也不在单组中加载第二个7B。
- 每250保存/dev，正式只评固定末1000，不按测试结果挑250/500/750。
- 039每组reference9024（8000训练＋1024dev）、student24560；两组合计18048/49120。

039训练并行只改变调度，不改变这些数值。实际两组墙钟约5小时8分；这不是同工作负载的严格并行性能对照。

## 6. 训练数据、增强流程和039修复

### 6.1 三个数据池

| 池 | 来源和监督 | train / dev父轨迹或生成轨迹数 |
|---|---|---:|
| `ten` | 真实生成的10状态—动作轨迹，专家动作BC | 224 / 81，共305 |
| `fresh` | 合格普通任务真实重放的当前观测，原策略动作蒸馏 | 78 / 27，共105 |
| `raw` | 原官方普通演示观测，原策略动作蒸馏 | 136 / 44，共180 |

原始种子是九任务各自然前20条官方演示，共180个父组，不是180个HDF文件；同文件可以含多条演示。所有variant随父组分train/dev，不按执行成败换划分。ten实际对应102个演示父组（train75/dev27），不能把305个机器人变体说成305个独立采集场景。

当前索引130017行，305/305配对有效；完成计数标签78998行，raw的51019行没有本轮新谓词标签，符合合同，不是标注漏跑。源演示与正式初态的物理祖源无法完全证明独立：不使用正式测试状态bank/测试rollout直接训练，但也**不声称物理来源完全独立**；父组划分不自动解决这个问题。

### 6.2 10增强如何产生

1. 从原演示state0实际重放完整source动作，得到新状态、双RGB/proprio、实际控制目标和事实。
2. 找到A真/B假、约束满足、空手/张手/释放与物理条件合格的交接帧。
3. 保留该帧非机器人世界，只把机器人关节/速度/夹爪等按既定layout回到该父源的初始机器人状态；另构造两个小关节扰动起点。
4. 实际执行有界bridge，再跟踪正常轨迹的绝对控制目标续接B；每起点最多直接/抬升两次尝试，不是把缓存动作直接贴给新机器人姿态。
5. 全程录制新观测和已执行动作，保持T动作/T+1观测；检查A/K保护、违规和真实释放，合格才入训练。失败与已执行前缀留存。

这是**动作损失上的数据增强/微调训练**，不是仅改prompt，不是测试时oracle代做。机器人rewind是新训练episode的起点构造，不是评测中把机器人teleport归位。

### 6.3 为什么需要039

038实际只有六任务的合格10增强。缺失的开炉、白杯、双壶各20个普通父源都未通过当时释放/确认等条件，没有进入10生成。旧60条中47条末帧已满足原生完整目标，但没有一条末帧released为true、确认尾帧均0；双壶20条又全部先做固定B。

039保持模型/loss/正式评分不变，只修离线数据生产：

- 原生完整目标已真而释放未确认时，实际张手≤10步、必要时竖直撤离≤20步/0.10m、再保持≤10步；新增总≤40、整episode≤520，按原5帧释放证书确认。
- 所有收尾动作与观测都写入新HDF；不是把unknown改true、抄四个audit-only帧或伪造释放。
- 仅双壶**新训练normal初始化**交换两个同类壶完整freejoint qpos7/qvel6；按实际模型地址检查，其他状态不变，恢复后拍新RGB。固定A/B标签、实体ID、语言、炉子K和正式测试bank不改。
- 新动作算法recipe与准入政策分开版本化。新039仍用原teacher V2：`table-drop-unknown-diagnostic-v2`；该政策只把训练准入的table_drop未知作诊断，**不是修改正式评测评分**。旧来源的原资格/政策/署名逐源保留。
- 复用旧003六任务221ten/75normal，不回放、不重新物理准入旧数据。原180raw/父split不变。

旧038的audit-only确认尾帧不属于动作监督；039收尾则是实际frames/actions内的真实训练转换。不要因同叫“确认”就混用，也不要给旧HDF补造不存在的尾帧。

### 6.4 039实际产量和预算

| 项目 | 已批准上限 | 实际 |
|---|---:|---:|
| 新普通重放 | 60 | 60，30合格 |
| 新10生成尝试 | 360 | 99，84合格 |
| 新增10 train / dev | 不保证成功数 | 63 / 21 |
| C0/C1训练 | 各1000 | 各1000 |
| 两组reference / student | 18048 / 49120 | 18048 / 49120 |
| 两模型正式评测 | 360 | 360完成 |

未用完的生成上限不等于现在能继续追加。039阶段已经完成，没有自动重试/退款或新一轮预算。

合并后每任务10轨迹/有效pair数量如下（本批两者一致）：

| task key | train | dev | 合计 |
|---|---:|---:|---:|
| basket | 32 | 9 | 41 |
| basket_cheese_butter | 33 | 24 | 57 |
| stove | 36 | 6 | 42 |
| bowl_drawer_close | 36 | 12 | 48 |
| dual_mugs | 6 | 0 | 6 |
| mug_pudding | 3 | 9 | 12 |
| basket_soup_cheese | 39 | 9 | 48 |
| two_pots | 24 | 6 | 30 |
| mug_microwave_close | 15 | 6 | 21 |
| 总计 | 224 | 81 | 305 |

**白杯train只有1个父源的3个机器人变体；dual_mugs也只有6条train且没有dev pair。** 九任务“有训练覆盖”不等于数量/多样性充分。不能为了结果把dev调到train，或把变体数量当独立父样本量。

## 7. 已完成实验结果与解释

### 7.1 总体结果

每个百分比的分母均90；10合规SR与00官方SR分别报告。

| 模型 | 10 | 00 |
|---|---:|---:|
| 原始SOG10 | 24.44%（22/90） | 86.67%（78/90） |
| 035 | 54.44%（49/90） | 73.33%（66/90） |
| 036 | 50.00%（45/90） | 82.22%（74/90） |
| 038 C0 | 53.33%（48/90） | 83.33%（75/90） |
| 038 C1 | 55.56%（50/90） | 84.44%（76/90） |
| 039 C0 | 56.67%（51/90） | 80.00%（72/90） |
| 039 C1 | **58.89%（53/90）** | **85.56%（77/90）** |

039 C1是目前已测微调版本的最佳10/00组合；00仍比原始低1.11pp。对038 C1为+3.33/+1.11pp；同039数据对C0为+2.22/+5.56pp。这里pp是百分点，不是相对百分比。

配对结果：

| 比较 | 条件 | 新增成功 | 丢失成功 | 净变化 |
|---|---|---:|---:|---:|
| 039 C1 vs 039 C0 | 10 | 5 | 3 | +2条，+2.22pp |
| 039 C1 vs 039 C0 | 00 | 6 | 1 | +5条，+5.56pp |
| 039 C1 vs 038 C1 | 10 | 7 | 4 | +3条，+3.33pp |
| 039 C1 vs 038 C1 | 00 | 6 | 5 | +1条，+1.11pp |

C1相对同数据C0的10收益仍只有2条；不能把对原始模型的+34.44pp全部归于swap/align。039同时改变覆盖、教师收尾和采样分布，跨038/039不是纯数量消融。当前单seed、每条件90条，不是显著性/强泛化证明，也不是zero-shot微调结果。

### 7.2 九任务结果

| 任务 | 038 C1 10 | 039 C0 10 | 039 C1 10 | 039 C0 00 | 039 C1 00 |
|---|---:|---:|---:|---:|---:|
| 汤罐＋番茄酱入篮 | 80% | 80% | 70% | 50% | 60% |
| 奶酪＋黄油入篮 | 40% | 40% | 50% | 80% | 80% |
| 开炉并放摩卡壶 | 0% | 30% | 30% | 90% | 100% |
| 黑碗入抽屉并关屉 | 100% | 100% | 100% | 100% | 100% |
| 两杯分别放左右碟 | 70% | 70% | 70% | 100% | 90% |
| 白杯上盘、布丁放盘右 | 10% | 0% | 0% | 80% | 100% |
| 汤罐＋奶酪入篮 | 100% | 90% | 100% | 50% | 50% |
| 两个摩卡壶放炉上 | 0% | 10% | 20% | 80% | 100% |
| 杯子入微波炉并关门 | 100% | 90% | 90% | 90% | 90% |

### 7.3 当前最有价值的观察

1. 恢复三任务后，C1的10从1/30=3.33%升到5/30=16.67%；旧六任务从49/60=81.67%到48/60=80%。整体是小幅正向，不是全面提升。
2. 三个瓶颈任务的00均100%，10却为30%/20%/0%；三者仍贡献25/37=67.57%的10不成功。这为研究动机提供了更清晰证据：不只是普通任务能力不足，外部预完成后的继续执行依然困难。
3. 开炉7条、双壶8条不成功均未确认完整目标，双壶另有2条goal_regression；不能把它们全部解释成没学FINISH或释放证据不清。
4. 白杯10中的8条目标未确认，2条涉及释放确认未知；0%不等于10条全没达到过原生目标。保持既定二元分数，用诊断区分原因，不随意重判。
5. 039 C0/C1的wrong_grasp均7、goal_regression为4→5；不能仅因总SR提高就声称已经全面保护已有成果。
6. 训练末dev10 L1为C0 `.129999882`、C1 `.130077180`，非常接近，不能替代SR或据此挑权重；新旧dev集合也不同，不能跨数据直接比loss。

以上足以推动下一轮研究分析，但尚未证明唯一失败机制、任意完成子集能力或ICML级独立创新。下一步应把现有证据用透，而不是自动补更多工程检查或直接堆训练步数。

## 8. 服务器、环境和关键路径

### 8.1 登录和硬件

```bash
ssh root@122.204.216.104 -p 30369
```

密码/token不写入本文或任何GitHub文件，由用户私下提供。其他agent没有凭据时向用户索取授权，不读取/泄漏凭据文件。旧30641端口和早期目录不是当前默认入口。

当前039实际运行硬件是NVIDIA A100-SXM4-80GB，不是最初提到的4090。GPU闲忙会变化，交接文档不构成资源预留；不能自动结束其他进程释放显存。连接拒绝时先确认地址/端口，不把连接问题当模型/代码失败。

服务器项目根：

```text
/HUBU-AI096/zp/ICML/Learning-Not-to-Act
```

### 8.2 当前部署和依赖

| 用途 | 服务器绝对路径 |
|---|---|
| 已验收039代码 | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task039-113ded21` |
| 039配置目录 | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21` |
| 只导出环境变量的session | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21/session039.sh` |
| 原SOG10完整底座/组件 | `/HUBU-AI096/zp/ICML/checkpoints/openvla-7b-oft-libero-sog10` |
| 官方OFT代码 | `/HUBU-AI096/zp/ICML/external/openvla-oft-task035-e4287e94` |
| 固定benchmark core | `/HUBU-AI096/zp/ICML/LIBERO-Remain-task033-r7-d8541ef4` |
| 报告包目录 | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task034-cb8aca6a` |
| 旧bridge目录 | `/HUBU-AI096/zp/ICML/LIBERO-Remain-task031-prep-ac130177` |
| 离线生成所需历史初始化器 | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/fc1b4990` |

正式评测六旧来源与三新来源仍按原配置冻结：六任务10在`/HUBU-AI096/zp/ICML/stage05_headless_766ab96`；六任务00配置在`/HUBU-AI096/zp/ICML/task031_normal00_a23a8116/configs/normal00-sources.json`；新增三10来源为`/HUBU-AI096/zp/ICML/task033_r7_d8541ef4/microwave_repair/sources.json`，新增三00为`/HUBU-AI096/zp/ICML/task033_nine_aedfe169/preparation/normal00/sources.json`。不要因路径名含microwave就误认为只含一个任务；以JSON实际固定人口为准。

### 8.3 三种Python用途

| 用途 | 解释器/环境 |
|---|---|
| 纯JSON/SHA/文件分析 | 系统可用Python即可；不必加载模型环境 |
| 训练与OFT模型worker、既定native数据worker | `/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/python` |
| 正式评测父进程/仿真评分 | `/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/python` |

后两者沿既有`peft-openvla` Conda底座＋venv。不是selector环境。当前两个venv的方法包editable映射都指向039新代码，旧代码目录保留；不要为“环境统一”升级依赖。

**解释器路径不要`Path.resolve()`。** 过去已出现venv的`bin/python`被解析成Conda base解释器，导致numpy/MuJoCo版本换套的真实错误。保留原symlink拼写；数据文件路径的安全解析与解释器解析不是一回事。

session设置CUDA0、EGL、LIBERO配置、HF缓存和offline模式。JSON分析不需要source这些环境；真实启动脚本内部已处理激活。原生初始化器的seed沿冻结配置，不要把所有不同层级seed都统一改成7。

### 8.4 数据和完成的run

以下相对于服务器项目根；不是本地Mac目录：

| 用途 | 相对路径 |
|---|---|
| 官方种子原文件 | `data/trajectory035/raw/147fa5eb/` |
| 原180父清单/生成配置 | `configs/trajectory035-564c91c9/seeds.json`、`generate.json` |
| 旧六增强合格导出 | `data/trajectory035/generated-003/export/` |
| 旧三池索引 | `data/retention036/index-001/` |
| 039全部准备 | `data/coverage039/production-001/` |
| 新原始生成/账本 | `data/coverage039/production-001/generated/` |
| 合并引用导出 | `data/coverage039/production-001/merged-export/` |
| 新三池索引 | `data/coverage039/production-001/indices/retention/` |
| 当前任务上下文索引 | `data/coverage039/production-001/indices/task_control/` |
| C0/C1训练 | `runs/task039-c0-train-001/`、`runs/task039-c1-train-001/` |
| C0/C1正式评测 | `runs/task039-c0-eval-001/`、`runs/task039-c1-eval-001/` |
| 训练控制记录 | `runs/task039-parallel-001.launch/` |
| 评测控制记录 | `runs/task039-eval-both-001.launch/` |

每个eval根目录的`summary.json`是正式结果、`report.md`是人读表、`plan.json`绑定模型/来源、`batch.json`/`progress.json`是过程记录。根目录旁的`*.console.log`保留日志。单条raw/video在各执行单元内部，不保证有统一的`eval根/raw/`；按已验证`task_run.json`引用解析。

准备identity：`b7a9b8646c22510e09ade56e6fb9b9379c5a0323e556fa5069b08eae13350262`。

当前task-control index identity：`b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c`；report identity：`64a2d4923dda271ffeb2a67f080c81c40bbdb277bae6351328a779791e1abdaf`。SHA-256数据身份不是Git commit。

### 8.5 已完成训练权重

| arm | 正式使用的服务器目录 | adapter SHA-256 |
|---|---|---|
| C0 | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c0-train-001/update-001000` | `e9d481030c35011498c9172db9c22c335b5cf4c52397b72309f9208a6fcb4060` |
| C1 | `/HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c1-train-001/update-001000` | `6d340e99186090bab6739f173ecb118d03eb1bf574ae96d5f1c34241b02d644e` |

完整续训状态SHA分别为C0 `dc210b5d7ca0dd54564a39613a4cdf67b402ad07bd74a9e348f3a4c211e22098`、C1 `b681bd0470e6a82e545cdf0dfd9c677003226d1056763dd6c6fa9fa8d8e24ae2`。目录内有`adapter.pt`、`identity.json`、`training_state.pt`、`training_state.sha256`；外层有metrics/config/预算/selected_checkpoint。

adapter约84MB，不包含完整7B底座；恢复推理还依赖固定SOG10底座、action head/proprio组件和统计。原统计文件SHA为`6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3`，unnorm key为`libero_10_no_noops`。不能随便替换成另一LIBERO checkpoint再称同一结果。

## 9. 本地证据、备份和视频

### 9.1 注意本地根目录末尾有空格

```text
/Users/zhangpeng/Desktop/Learning_Not_to_Act 
```

最后一个空格是真实目录名的一部分。shell路径必须加引号；不要擅自重命名、去空格或建立覆盖式新目录。其他机器若不存在该路径，不能声称已经读到本地文件。

关键本地位置：

| 内容 | 本地绝对路径 |
|---|---|
| 本文可见副本 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /docs/项目交接文档_截至039_2026-11-08.md` |
| 最近结果分析JSON | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /reports/task039_final_results_2026-11-08/analysis.json` |
| 最近结果与视频入口 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /research_archive/Learning-Not-to-Act/task039_final_results_videos_2026-11-08/README.md` |
| 039原始报告/控制记录本地副本 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /research_archive/Learning-Not-to-Act/task039_final_results_videos_2026-11-08/results/` |
| 039两末完整训练工件 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /research_archive/Learning-Not-to-Act/task039_training_complete_2026-11-08/` |
| 039数据准备小报告 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /research_archive/Learning-Not-to-Act/task039_preparation_complete_2026-11-07/raw/` |
| 039已验收源码快照 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /reports/task039_review_2026-11-07/source/` |
| 所有阶段总结备份 | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /research_archive/Learning-Not-to-Act/stage_summaries/` |
| 归档登记manifest | `/Users/zhangpeng/Desktop/Learning_Not_to_Act /research_archive/Learning-Not-to-Act/backup_manifest.json` |

本地`Learning-Not-to-Act/` Git checkout存在较早的用户脏改动和未跟踪文件，不是可随意`pull/reset/checkout`的干净工作区。过去通过隔离快照/GitHub API保留这些改动；接手继续保留。早期MiniPAB/远程运行交接等旧文档只作历史，不能替代本文与最新STATUS。

已核验的备份：

- 039末权重/完整状态/配置日志29文件，preservation manifest SHA `06bafa448a78e395f4b297c777cf6d1a31d9e256ecdbd058ca512004233b9c96`。
- 039正式/控制文件14份＋配对原视频8段，preservation manifest SHA `8c3806df5e37128908c26089e1a2d2dc6e644a93819e756ab9cd665cac9282c5`。
- GitHub阶段/裁决/机器证据均有精确source commit、逐文件SHA和本地备份登记。039所有视频/raw/中间checkpoint仍在服务器；不是全部360视频都已下载。

恢复或重新搬运时以manifest和精确源commit为准，复制到独立目录核对字节，不能覆盖已完成run。现有备份已经核对过，不把再次扫描全部大HDF/模型作为接手门槛。

### 9.2 已取回的四组配对视频

视频目录为上述结果归档下的`paired_videos/`：

| task/condition | episode_id | 本地文件（该目录下） | 正式结果 |
|---|---|---|---|
| 开炉并放摩卡壶，10 | `stove_s001_10` | `038_c1_stove_s001_10.mp4` / `039_c1_stove_s001_10.mp4` | 038 C1不成功→039 C1成功 |
| 两壶上炉，10 | `two_pots_s005_10` | `038_c1_two_pots_s005_10.mp4` / `039_c1_two_pots_s005_10.mp4` | 不成功→成功 |
| 白杯布丁，10 | `mug_pudding_s006_10` | `038_c1_mug_pudding_s006_10.mp4` / `039_c1_mug_pudding_s006_10.mp4` | 成功→不成功 |
| 白杯布丁，00 | `mug_pudding_s004_00` | `039_c0_mug_pudding_s004_00.mp4` / `039_c1_mug_pudding_s004_00.mp4` | C0不成功→C1成功 |

README还列有官方完整task_name、指令和原始步数。这是有目的的增益/退化配对，不是随机样本。

**截至交接，视频已经复制并按SHA核验，但尚未逐帧作行为归因；标签来自正式报告，不是Codex观看重判。** 例如新开炉代表成功用了519步，接近520上限，不能仅凭SR成功就说模型立即跳过了A或没有冗余；这正需要下一步看动作/视频。

### 9.3 单条结果的数据层级

```text
summary.json
  └─ conditions["10"].report.episodes[]
       ├─ success / outcome：正式二元分数
       └─ diagnostics
            ├─ primary：冻结core的分类/失败原因/目标诊断
            └─ source.verified_files[]：源文件与SHA
                 └─ .../task_run.json
                       ├─ raw/<episode_id>.json
                       └─ raw记录里的video.path：原视频位置
```

00的`report.episodes`是按episode_id索引的字典，结构不是10的列表；它的`primary/source`也没有10外层`diagnostics`包装。不要写一个错误reader把两者混读或拿official00当compliant10。

## 10. 给实现/审查agent的代码地图

以下相对已验收039代码根，读取固定PR14 head或部署快照，别误读main缺失的实现。

[固定PR14代码树](https://github.com/No1dry/Learning-Not-to-Act/tree/113ded21434a06e2cdc156e5d6283a11c3f15488/egrs)可供没有本地快照的agent阅读。

| 位置 | 负责什么 |
|---|---|
| `egrs/augmentation/data_scope.json` | 九任务、完整语言、active A/B与K |
| `egrs/trajectory_augmentation/control.py` | robot rewind、动作映射、控制目标跟踪 |
| `egrs/trajectory_augmentation/native.py` | 固定native初始化、实际图像/状态/谓词采集、原V1/V2准入 |
| `egrs/trajectory_augmentation/generation.py` | 基础Attempt/bridge/记录器、handoff与保护 |
| `egrs/coverage039/teacher.py` | 039真实有界释放收尾 |
| `egrs/coverage039/permutation.py` | 双壶初始freejoint置换 |
| `egrs/coverage039/generation.py` | 60父源生产、durable attempt ledger与失败保留 |
| `egrs/coverage039/merge.py`、`data.py`、`index.py` | 旧/新双root引用合并、动态三池与038语义标签/pair |
| `egrs/coverage039/io.py` | 单次调用稳定stat的SHA去重/阶段进度 |
| `egrs/coverage039/training.py` | 新索引绑定、零新增train10保护、调用同038训练算法 |
| `egrs/task_control/model.py`、`oft.py` | z/残差、真实OFT隐藏提取与共享动作接线 |
| `egrs/task_control/training.py`、`reference.py`、`sampling.py` | C0/C1损失、完整旁路教师、分层采样/预算 |
| `egrs/task_control/adapter.py`、`checkpoint.py`、`policy.py` | 新参数保存/严格恢复/正式推理 |
| `egrs/task_control/evaluation.py`、`egrs/retention/evaluation.py` | 两arm正式评测，复用原来源/runner/报告 |
| `egrs/trajectory_augmentation/environment_dispatch.py` | 旧/新bridge和proxy协调，不升级为一套新环境 |
| `egrs/augmentation/core_files.json`、`reporting_files.json` | 依赖字节锁；不是随便改版本号即可兼容 |

core里看`benchmark/remaining_goals/nine_catalog.py`、`headless/schema.py`及既有环境测量；报告层实际包为`libero_remain_reporting/report.py`，不是在旧benchmark包里另造一套指标。

后续只改本轮实际相关路径，复用未变的验收。不要让报告层的旧`benchmark`包遮蔽固定执行core；已有依赖激活逻辑只加载所需包，不能为了路径方便把所有旧repo塞进全局PYTHONPATH。

## 11. 接手后立即做什么

本节是**待办**，不是宣称已经完成的失败机理结论，也不授权新模型实验。

### 11.1 第一轮只用已有证据

建议顺序：

1. 读039 R4/机器结果/本文，确认039两个eval已经结束。已有结果可用，不重新运行report/评分器、状态回放或模型。
2. 先看四组已取回视频，特别是白杯`mug_pudding_s006_10`的038→039退化和白杯00对照。视频尚未完成行为分析。
3. 扩到039 C1全部10条白杯10，以及开炉7条/双壶8条不成功；从现有正式诊断与原raw/动作/视频定位。复制已录制视频/trace是文件操作，重新渲染/回放不是。
4. 分开分析白杯8条目标未确认与2条释放确认问题；比较00对应任务的动作、第一段是否仍重复A、B是否被正确定位、是否触碰/破坏已有A、什么时候发生偏离。
5. 用`analysis.json`里的配对列表核对039 C1对C0新增5/丢3，以及对038 C1新增7/丢4；不要只看成功例或只看总体SR。
6. 输出一份短的事实驱动失败分析，再选一个最值得验证的方法方向。此时才讨论下一工单和预算，不自动继续生成/训练。

### 11.2 每条失败至少记录这些字段

| 字段 | 要求 |
|---|---|
| 身份 | stage、arm、condition、task key、episode_id、原始文件/视频路径 |
| 冻结结果 | success/outcome、primary classification、官方目标是否曾达到 |
| 目标/保护 | A/B/K记录、首次B满足时间（若已有）、A/K回退、原违规事件 |
| 动作现象 | 首段在做什么、是否出现重复A/空抓/错误物体操作；附具体时间或step证据 |
| 观察条件 | 当前双视角是否能辨认已有成果/剩余物；看不清就写看不清，不臆测 |
| 失败归因 | 剩余目标选择、成果保持、动作执行/几何、释放确认等；允许未能区分 |
| 证据边界 | 自动日志事实、视频观察和研究假设分别写；不声称看到模型内部“意识到” |

这是定性/诊断表，不是增加人工主评价指标，也不重判正式分数。合理探索和错抓/破坏要区分；不把“机械臂动了”直接判成失败。

### 11.3 可以检验的假设，不是现成结论

| 假设 | 已有支持 | 还缺什么 |
|---|---|---|
| 白杯训练多样性不足 | 仅1训练父源、3变体 | 是否在已学状态附近也重复A；不能凭数量断言唯一原因 |
| 全局z/计数不足以表达具体剩余目标 | 当前没有实例级目标头，计数不告诉哪个目标完成 | 需要动作/场景证据，不能只凭结构图宣称z无效 |
| 存在动作/几何域偏移 | 00强、10起点/机器人执行阶段变了 | 是否正确选B但控制失败，还是压根没选B |
| 已有成果保护不够 | 双壶有goal_regression，C1总回退未全面下降 | 具体触发动作、目标选择和运动执行的关系 |
| 部分诊断卡在释放证书 | 白杯有2条completion_release_unknown | 查已有释放/接触证据；不能通过放松评分制造提升 |

原始指令“put both X and Y”未必要求示范中的固定先后顺序；抽屉/微波炉又有物理前置条件。示范顺序偏置值得分析，但目前没有显式行为树/任务图规划器，不要把这个观察写成已实现功能或已验证因果。

### 11.4 第一轮应交付什么

- 一页结论：主要失败集中在哪里、哪些是已确认事实、哪些只是候选解释。
- 一张episode诊断表＋少量最有区分度的带step/时间证据的视频案例。
- 2–3个可行改进候选，明确是否改模型/是否需要新数据/如何与现有C0C1公平比较；推荐一个，说明为什么优先。
- 若需要实现：由Codex写详细GitHub `collaboration/tasks/`工单和给X的短prompt；下一编号先检查是否已占用，不把“建议040”当已经交付。
- 若需要新真实作业：明确数据量/尝试数、更新数、教师/学生前向和eval数量，用户批准并亲启。不要只回复“再验证一遍”。

建议后续分析文档放方法库`docs/research/`，关联039 R4和对应证据；不要把实现塞回benchmark仓库。当前没有尚待X修复的明确软件错误。

## 12. 可直接复制的只读接手命令

下面命令只读现有文件，不会启动训练、仿真或eval。若没有本地路径/服务器权限，停止并说明缺什么，不能伪造已访问。

### 12.1 本地快速看结果

```bash
cd '/Users/zhangpeng/Desktop/Learning_Not_to_Act '
python3 - <<'PY'
import json
from pathlib import Path
p=Path('reports/task039_final_results_2026-11-08/analysis.json')
d=json.loads(p.read_text())
print(json.dumps(d['scores'],ensure_ascii=False,indent=2))
for task in d['tasks']:
    print(task['task_id'],task['conditions'])
print('白杯诊断:',d['unsuccessful_diagnostics']['c1']['mug_pudding'])
PY
```

直接打开第9节的本地README即可看已取回视频；不必再下载相同文件。

### 12.2 已登录服务器后，只读两组正式状态

```bash
/root/anaconda3/bin/python - <<'PY'
import json
from pathlib import Path
root=Path('/HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs')
for arm in ('c0','c1'):
    d=json.loads((root/f'task039-{arm}-eval-001/summary.json').read_text())
    print(arm,d['formal_complete'],d['software_exit'])
    for bits in ('10','00'):
        print(bits,d['conditions'][bits]['formal_SR'])
PY
```

这只读JSON，不使用`egrs ... eval/report`模块，不会触发新的正式核验。

### 12.3 定位未下载的单条原视频

```bash
/root/anaconda3/bin/python - <<'PY'
import json
from pathlib import Path
root=Path('/HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c1-eval-001')
eid='mug_pudding_s000_10'  # 换成已有episode_id，不创建新episode
d=json.loads((root/'summary.json').read_text())
row=next(x for x in d['conditions']['10']['report']['episodes'] if x['episode_id']==eid)
print('正式结果:',row['success'],row['diagnostics']['primary']['classification'])
refs=[Path(x['path']) for x in row['diagnostics']['source']['verified_files'] if x['path'].endswith('/task_run.json')]
assert len(refs)==1
p=refs[0].parent/'raw'/(eid+'.json')
raw=json.loads(p.read_text())
print('raw:',p)
print('video:',p.parent.parent/raw['video']['path'])
print('video元数据:',raw['video'])
PY
```

之后只复制这份已存在视频即可；不要为了看视频重新运行模型或replay。若要看别的condition/模型，先按第9.3节调整读取结构，不能把00当10列表读。

### 12.4 只查看实现与任务状态

```bash
gh pr view 14 --repo No1dry/Learning-Not-to-Act --json headRefOid,state,url
gh api repos/No1dry/Learning-Not-to-Act/git/ref/heads/main --jq .object.sha
```

查询不授权merge或改实现。读取部署脚本内容用`sed`等文本工具；**不要为了“看看”而source/执行启动脚本，也不要给它传`--help`试探**——这些shell启动器没有help解析，执行就可能开真实作业。

## 13. 容易踩的坑和不能重复的动作

1. **旧run都已完成。** `train_both_parallel.sh`、`eval_both_sequential.sh`的旧命令不能再执行；launch marker拒绝时不能删除它绕过。
2. **模型执行100%不等于报告完成。** 原用户eval进程还会做CPU正式核验；以后也不能另起report重复扫一遍。039本轮二者都已经完成。
3. **GPU空闲不代表作业没开。** 训练入口先读文件/身份，再加载模型；用进程和日志判断。不要看到0% GPU就再点一次。
4. **预算账本不是可删缓存。** 初始化失败/中断也计attempt；resume可能因已消费账本超前于checkpoint而拒绝，不能删账本“精确恢复”或自动重开。
5. **SHA去重只在一次调用/稳定stat内。** 不重现旧282GB重复哈希，也不跨进程持久化“永久免检”。但已有有效备份/资格无需例行重做。
6. **SCP没完成的JSON可能暂时不完整。** 等复制结束与SHA确认后读，不因此认定服务器报告坏了或重跑评测。039收尾曾遇到过这个本地分析时序问题，服务器原件无误。
7. **不要升级依赖绕过固定环境。** venv路径、NumPy/MuJoCo、bridge与core锁都影响真实性。Windows symlink或本地OpenMP fake测试环境问题不能冒充服务器物理实验失败。
8. **teacher V2不是正式评分改版。** 训练准入table_drop未知诊断、039实际释放收尾与最终二元SR是不同层；不可互相偷换。
9. **无FINISH不等于给模型外部指挥。** 当前没有在线finish-head/selector；offline教师构造数据、eval端点判定与策略自主停止是三件事。
10. **no-op不是随便全零动作。** 夹爪编码/控制器语义可能让零向量改变状态；更不等于终止episode。不要临时用它“修复停止”。
11. **不要只看成功视频或总SR。** 配对增益/退化都要看；合规成功也不保证没有全部冗余或立即跳过A。
12. **不要伪造标注来源。** 当前训练监督以已记录仿真状态/谓词与真实执行动作为主；视频agent复核、VLM候选、人工确认不能互相冒名，不把simulator监督叫纯视觉自监督。
13. **不改历史分数。** 若将来真有评分bug，必须独立版本化、保留旧结果并明确受影响范围，不能通过新标准偷偷改旧失败。
14. **不清理原始数据。** 只有已裁决关闭且关键决定已进已提交阶段总结、精确commit本地备份/manifest/SHA通过的交流文件，才可能按协议列精确清单Git删除；开放任务、协议、STATUS、总结、源码、原始实验数据不能删。本交接不要求现在清理。

## 14. 可转发给新agent的接手prompt

> 请先阅读项目主交接文档 https://github.com/No1dry/Learning-Not-to-Act/blob/main/docs/handoffs/2026-11-08_project_handoff_after_task039.md ，再读最新collaboration/STATUS.md和AGENTS.md。当前039数据、C0/C1各1000训练、两模型360条正式评测均已完成；最好微调版本039 C1的10/00为58.89%/85.56%，已验收实现为未合并PR14固定head113ded21434a06e2cdc156e5d6283a11c3f15488，不是只克隆main即可运行。你默认只接研究分析/审查权限，不启动或停止真实模型/仿真/标签/训练/eval，不重跑已完成run、不改评分或按结果挑来源。先按交接第11节读取已有白杯/双壶等失败证据和已取回配对视频，区分已证事实与假设，交付一页瓶颈结论、episode诊断表和少量带step的视频证据，再提出2–3个可行改进候选并推荐一个。不要把重新验证/全库测试变成研究前提。新代码由X实现，Codex需实际上传GitHub工单和给用户短prompt；新真实作业预算另行确认，仍由用户亲自启动。每次回复附下一步操作和执行者，进度用百分比并区分各阶段。

如果接手者是X：本文只是上下文，不是新实现工单。先读039已关闭的验收与现有代码，等待明确的新需求；不要重开039或因SR有限返修正确实现。

## 15. 交接是否完成的判据

接手者应能不依赖原聊天回答：

- 我们研究什么、当前为什么只主测10，并如何处理00对照？
- 当前到底运行哪个基座/实现、哪个PR未合并、哪个目录只是旧历史？
- C0/C1差在哪里，数据/损失/输入与预算是什么，哪些不能冒称创新？
- 哪些结果已完成，最好权重在哪里，如何找到原报告/原视频？
- 当前下一步是哪项只读分析，哪些实验尚未批准，谁有启动权？

本文交付本身只产生文档/入口更新与本地备份，不产生新实验、代码实现或GPU作业。下一步操作和执行者：接手Codex/研究agent按第11节分析既有失败证据；用户暂不启动新实验；X等待正式新工单。
