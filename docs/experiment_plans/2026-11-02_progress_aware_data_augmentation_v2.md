# 030 v2｜九任务进度感知数据增强与OFT动作微调

日期：2026-11-02。决策：Codex。状态：**进入X代码实现与CPU/fake交付；真实数据范围、下载和GPU预算为下列候选，尚未启动或获实验启动授权。**

本文替代030 v1的旧六任务/80条/含LIBERO-90范围与112条新增评测预算。v1保留历史，不倒改。在线方案只有**原完整指令＋当前双视角RGB＋proprio → 微调后的OFT → 动作**；不挂旧selector、规划器、记忆、关系头或FINISH。

## 1. 已完成的基线与固定评价

九个LIBERO-10复合任务，官方0起ID：0、1、2、3、4、6、7、8、9。每项10个mask10 episode，原始模型记录90/90完成，无技术错误/缺失。**二元合规成功率24.44%（22/90）；不成功75.56%（68/90）**。原诊断中的67 failure＋1 release-unknown均为二元不成功，原始记录不修改。

成功记1的必要条件仍是现有core确认的目标/释放/连续确认和合规条件；未全部通过记0。不是删除释放要求，也不把原生目标曾满足等同成功。原诊断可以保留未知证据，论文主结果与正式逐episode结果只有成功/不成功。系统崩溃、未执行和数据损坏另外报运行不完整，不能伪装模型失败。此口径对原始模型、续训对照、增强模型一致。benchmark实现见034任务，方法库不复制评分器。

00原生目标达成86.67%（78/90）、10原生达成40.00%（36/90）仅是同口径能力诊断；不能拿00原生SR减10合规SR。现有90条与视频全部复用，不补跑基线。

## 2. 研究假设和不能冒称的覆盖

采用动作L1微调，并改变训练样本权重和语言—动作绑定，检验VLA本身能否根据当前观测接续剩余目标。三个训练视图：RAW完整指令50%、PROGRESS进度均衡25%、ATOMIC真实技能段原子指令25%；另有保守photometric扰动。

普通BC本来就见过中间帧，单独切后缀不是新状态。正常演示中A完成后的机器人姿态与外部完成A、机器人仍在初始位姿不同。本轮是**同任务正常演示适配→外部进度干预测试**，不是已覆盖编辑初态或未见组合零样本泛化。若覆盖不足导致无效，先用已有结果分析，不自动增采或换方法。

## 3. 候选训练数据：既有200＋最多新增180来源

- D_base：复用已下载Goal10＋Object10的20任务/200条普通演示，原160 train / 40 dev分组保持。旧2429条selector关系query不是动作样本，不能直接作技能段标签。
- D_compound：九个正式任务的**未编辑普通专家演示**，每任务按自然demo序取前20条（不足如实列出，不按成绩挑），最多180来源；已有文件优先复用，不重复下载。总计最多380来源，约304/76仅为分组预期，不是验收数量。
- 固定官方数据源沿用v1：`yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`。真实文件名、demo数、精确instruction、来源hash由manifest绑定，不能只凭下表中文名猜文件。

| ID | key | 普通任务及最终目标 |
|---:|---|---|
| 0 | basket | 汤罐与番茄酱罐都入篮 |
| 1 | basket_cheese_butter | 奶酪与黄油都入篮 |
| 2 | stove | 开炉子；摩卡壶上炉 |
| 3 | bowl_drawer_close | 黑碗入下抽屉；关闭下抽屉 |
| 4 | dual_mugs | 白杯左盘；黄白杯右盘 |
| 6 | mug_pudding | 白杯盘上；布丁在盘右侧（原定义区域，不改参照） |
| 7 | basket_soup_cheese | 汤罐与奶酪都入篮 |
| 8 | two_pots | 两壶上炉；炉子开启是保持约束，不是第三个待完成目标 |
| 9 | mug_microwave_close | 黄白杯入微波炉；关微波炉门 |

精确官方名称/谓词沿用benchmark已冻结的[九任务清单](https://github.com/No1dry/LIBERO-Remain/blob/191eabf1dad8bebc1cf2a39d26a98308ed4d6338/collaboration/tasks/033_nine_task_scope.json)。ID5单最终目标任务与LIBERO-90不加入正式测试。

新增来源先按完整轨迹分train/dev，再派生全部视图；已知同源/重复必须同组，不能以帧切分。不得为凑约16/4拆同源。普通演示和official init继续作为两个来源域，未知物理祖源如实披露，不重开全量demo↔init匹配工程。

**禁止训练/验证内容**：正式90评测初态及其编辑过程、模型评测轨迹/分数、029错误动作、从eval日志回填的完成位。没有VLM编造专家动作，也不把改变物体位置后的旧动作复用为专家。

## 4. 数据导出：一个入口，三类索引，不重建整套标注工程

1. RAW：`o_t, I_full, a[t:t+8]`。保持原图方向、processor/crop、proprio、动作表示、夹爪符号、原normalization stats；显式列出HDF字段和时间对应，不猜t/t+1、不二次归一化。完整指令chunk可以跨两个技能。
2. PROGRESS：输入仍与RAW相同，仅离线按真实阶段均衡采样：两目标待完成、某一目标满足而另一待完成。不预设列表第一个总先做；全目标终局不新增停车监督。单目标来源不伪称复合进度增强。
3. ATOMIC：仅对实际执行某目标的连续技能段换为对应原子指令。段内可含该技能必要前提/退让，但不可混入另一最终目标的操作；不能把整个AB轨迹改成B。目标false→true只能提出候选，不能单独证明整段动作属于该目标。
4. 复用已有可信状态/边界证据，必要时在用户启动的同一次导出中只恢复所需阶段锚点和候选边界局部窗口；不先全量渲染、重跑旧200来源视觉标签或建立通用数据平台。原图—状态—动作对应有歧义，保留RAW合格样本，增强片段不猜。
5. ATOMIC的8步chunk不得跨技能边界；尾部真实动作位mask后参与L1，padding不监督。RAW episode尾部同理；不复制末动作凑8步，不拼不同轨迹。
6. 未有可信增强片段的来源回退RAW并报告实际比例；**不要求九任务每项都有完美段才训练**。若PROGRESS/ATOMIC两池均空，明确该配置不是已实现的进度增强，不静默冒称Aug可用。

导出产物至少包含来源/分组manifest、字段映射、阶段/片段索引及证据来源、可用/排除原因、各task/split/view窗口数和有效动作数。优先索引原HDF，不复制全量RGB。大数据/权重/服务器绝对路径不提交GitHub。

## 5. 两个正式训练配置，同底座同预算

| 配置 | 数据来源 | 训练视图与增强 |
|---|---|---|
| RAW-control | 同一D_base＋D_compound及train/dev | 仅RAW原完整指令/原采样，无新增外观扰动 |
| Progress-Aug | 完全相同来源及train/dev | RAW/PROGRESS/ATOMIC=50/25/25；轻微photometric |

池内先按任务再按来源均衡，避免长轨迹或单任务淹没其他任务。导出和训练均报告实际比例，不伪造50/25/25覆盖。photometric初值p=0.5，亮度/对比度[0.9,1.1]，同一输入双视角共享因子；禁止额外几何crop/翻转/物体换色/换位/强遮挡。

底座身份保持官方`moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7`；固定OFT代码`e4287e94541f459edc4feabc4e181f537cd569a8`。从已合并的SOG10加载原已训练action head与proprio projector，使用原processor/stats，再加本轮新adapter。不能重复套发布原adapter、随机初始化head、借resume step300000假装新run。

冻结视觉编码器、基础VLM、原action head/proprio；只训练**语言transformer attention完整路径匹配**的q/k/v/o LoRA，r16/alpha32/dropout0。冻结head的forward仍保留通往LoRA的梯度，不detach/no_grad整个动作链；宽后缀不能误匹配视觉层。

候选：bf16、microbatch1、accum16、gradient checkpointing、AdamW、lr2e-5、warmup50、seed7、每run1000次optimizer更新，每250保存。L1按有效动作标量归一化。两组均在同一无新增增强、完整指令dev集上按动作L1选checkpoint；测试SR不用于选参或挑checkpoint。

24GB能否原样训练尚未实测，不承诺时长/显存。X实现gradient checkpointing等必要支持并说明静态估计；不另起GPU预检。若用户正式训练OOM，保留失败再决定不改语义的offload；不擅自去视角/proprio、缩chunk或量化。adapter和训练状态保存完整，支持本轮真实恢复而非原发布step的伪恢复。

## 6. 候选预算与比较，不自动扩成全部消融

| 组 | 新训练 | mask10模型评测 |
|---|---|---|
| B0原始OFT | 无 | 复用九任务90条；合规24.44% |
| A增强OFT | 1000 updates | 原九任务/indices0..9，共90条 |
| C普通续训 | 1000 updates | 固定九任务/indices0、3、6、9，共36条 |

**候选新增总量：最多180条普通演示来源＋两个1000-update训练run＋126个模型episode。未获真实实验启动授权。** 索引0/3/6/9提前固定，不按已有成败挑。A/B0全90比较方法总体收益；A/C/B0同36条比较是否超出普通续训。不得把C的36条冒充全90成绩。00不默认重测；若需正常能力保持实验，另报预算，不能声称当前已排除遗忘。

主结果只有**二元合规SR**，逐task与总计给百分比及分母；路径仅作为成功条件下辅助统计，失败N/A，不增加综合效率分数。视频保存全部；控制台实时显示阶段、task、完成百分比、SR、更新步/loss/耗时，默认普通conda/python命令，不让用户反复运行检查命令。

评测复用原90状态、完整指令、seed7/chunk8/H520、双图/proprio/crop、动作接口、原物理终点与判据。只增加适配器身份，不能拿更换后的model hash冒充原模型，也不能把预期adapter差异误判为输入/来源不兼容。A与C都用普通OFT入口，不接selector，不用原子oracle指令或任务真值决定动作/停止。

## 7. 当前交付与分工

用户“下一步”推进**代码实现/准备**，不解释为已经批准上述新增数据/下载/GPU预算。X现在直接实现，不再只交一轮可行性文档；确有硬阻塞时集中说明。主要改动、受影响CPU/fake、实际入口、两组配置、数据需求与普通命令一次交PR。Codex审查部署后，将实际可用数据/覆盖/资源和完整命令交用户确认启动；不自动运行数据恢复/标签、训练或eval。

新任务见[030 v2实现工单](../../collaboration/tasks/030_v2_progress_augmentation_implementation.md)。二元汇总单独由benchmark [034](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/034_binary_compliant_success_reporting.md)实现，是纯报告修改，不阻塞本轮训练代码开发。无需重建状态/重训FINISH/复活旧selector，也不以全库、多平台测试为前置。真实效果未证实，不能把代码交付标作训练成功。
