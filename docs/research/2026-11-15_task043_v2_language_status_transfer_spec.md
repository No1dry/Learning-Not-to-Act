# Task043-v2：训练期语言状态提示迁移，无提示VLA部署

2026-11-15 · Codex · 详细规格与完整预算草案。

**状态：用户已同意方法方向及进入下一步；本稿所列数值预算已提交确认，尚未收到确认。X暂不实现，真实阶段暂不启动。** 本稿是旧043 REGA候选的后继方向，不批准旧G0/G1或从042续训到4000步。原方案、署名、数据与结果全部保留。

## 1. 唯一研究问题

在同样训练观测、真实动作监督和更新次数下，训练期用语言显式说明当前任务目标关系，能否改善**没有状态提示时**的10合规成功率，同时尽量保持00官方成功率？

这是训练期特权信息迁移，不是推理时给答案、外挂规划器、FINISH头或长CoT生成。动作蒸馏改善不自动等于“已学会思考”；语言提示/蒸馏本身也不宣称首次或足够ICML新颖性。

## 2. 两组、同一原始起点

| 项目 | H0：无状态提示对照 | H1：状态语言迁移 |
|---|---|---|
| 原始底座 | 官方SOG10固定revision，加载后第0个研究微调更新 | 完全相同 |
| 原始动作/视觉/proprio接口 | 原OFT native；双RGB＋完整L＋8维proprio→8×7动作 | 完全相同 |
| 训练参数 | 原语言q/k/v/o LoRA，r16、alpha32、dropout0.0 | 完全相同 |
| 原能力保持 | 原SOG10旁路LoRA产生fresh/raw参考动作 | 完全相同 |
| 无提示主分支 | 当前观测＋完整原指令 | 完全相同 |
| 辅助训练视图 | 同一观测＋完整原指令，不加状态文字 | 同一观测＋完整原指令＋当前状态文字 |
| 训练与开发样本/前向安排 | 与H1匹配 | 与H0匹配 |
| 正式部署 | 只运行无提示主分支 | 完全相同 |

底座：`moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10`，revision `638918f3d1c2e43a39a8a20772bdb8b91835e4b7`，沿现有OFT/runtime及`libero_10_no_noops`统计。不是随机初始化7B。

**不加载035–042的研究adapter或optimizer，不安装旧z/count/residual、pair swap/align、041旧10教师或042 TCIF。** 保留增强数据和036普通能力保持作为共同底配方；这次不把历史所有组件累加。视觉骨干、原基础参数、动作head和proprio projector冻结，LoRA可反向穿过冻结head。

软件可依赖accepted PR17固定head `7d28d515be610f33f959f36d25623e86796671ce` 中已验收的数据/运行接口，但不自动合并PR17，不把方法main纯文档当成完整可执行实现。

## 3. 数据与一次CPU状态文字整理

复用040固定索引 `8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe`。保持289/81 ten、97训练父组、78/27 fresh、136/44 raw；主行143960。保留370条10/pair，但本轮不使用pair训练流，不取22个pair-only键。

准备入口只读现有主行、source/lineage/audit JSON和已绑定语义，生成独立sidecar，**最多143960个现有(source_id, observation_index)键的一次生产**。不重建原索引，不读RGB像素或新抽帧，不反序列化权重，不启动物理/教师/模型。原索引及大HDF字节不改。

sidecar至少记录：格式版本、原索引identity、原source/audit/语义绑定hash、source键、帧t、split、两个当前目标事实及其证据、提示模板版本、自然语言r、hint_eligible及缺失原因。原始L单独保留；不把改写后的文字冒充原始指令。prepare不实例化会扫描真实HDF内容的Dataset，不另做全量旧轨迹资格/文件payload复查；原训练入口必要的既有输入绑定仍保留。

状态按当前t帧事实生成，不使用t+1或未来、最终成功、专家未来动作或正式测试结果。当前r可以训练预测后续8步动作，但不把未来事实写入r。

### 3.1 文字契约

- 文字说明**当前目标关系是否满足**，不是“永远不要碰它”“只执行B”或动作指令。
- True只表示当前原生目标谓词成立；不额外声称已稳定、已释放或任务结束。False不推出物体一定在桌上。原释放证书未知不写成“仍在手里”。
- 复用按谓词绑定的active-goal语义映射；不得假设official数组位置就是A/B，特别是抽屉和微波炉。
- 提示不出现A/B、mask10、task_id、source_id、demo编号、隐藏实例ID、坐标、未来或文件路径。
- 两个目标事实均为可信布尔值且语义绑定通过，才hint_eligible；缺失/冲突不转False，也不编造完成状态。未知只作离线缺失诊断，不改变正式二元评分。
- 文本用于训练期教师，属于特权监督；不能冒称单帧一定可见。正式学生不接收这些事实。

冻结九任务模板：

| 任务 | 可渲染的当前目标关系（分别附satisfied / not satisfied） |
|---|---|
| basket | alphabet soup in basket；tomato sauce in basket |
| basket_cheese_butter | cream cheese box in basket；butter in basket |
| stove | stove switched on；moka pot on stove |
| bowl_drawer_close | black bowl in bottom drawer；bottom drawer closed |
| dual_mugs | white mug on left plate；yellow-and-white mug on right plate |
| mug_pudding | white mug on plate；chocolate pudding to right of plate |
| basket_soup_cheese | alphabet soup in basket；cream cheese box in basket |
| two_pots | `n of 2 moka pots are currently on the stove`，n由两目标当前事实求和，不区分隐藏1/2实例 |
| mug_microwave_close | yellow-and-white mug in microwave；microwave door closed |

模板表达满足的是对应任务目标区域的关系，不另造几何判据。双壶用集合数量避免身份泄漏，其他任务保留实体语义，不能全部退化成全局完成数量。

每个主行均保留条目；raw无事实可标缺失，本轮不为它补建仿真。训练提示只施加于已有真实专家动作的ten窗口。fresh/raw仍用于普通能力保持，不新增其专家BC或改变目标来源。

### 3.2 缺失处理与数据隔离

主训练人口、同一指令在00普通参考与10中的不同状态、父组train/dev和开发选择保持。不可使用正式评测raw/视频生成训练提示。CPU生产输出逐任务、split、目标状态组合和缺失原因计数，不要求为凑N再生成；某任务缺提示仍可保留其原无提示BC。全train零eligible则一次明确拒训，不能偷偷退成无提示方案后仍叫H1。

## 4. 单个更新的固定计算

主采样沿036：每更新12ten＋4fresh＋4raw，后两池各2个prefix/2个all；任务→父组→变体→窗口采样、seed7。两臂用相同原索引、独立但同seed的采样器。

在已采样的12ten中，按原采样顺序取最先出现的**最多4个eligible draw slot**作为辅助集S。两臂用同S；不重采样、不改变主流、不额外读取新的观测；重复抽中按draw slot计前向。若S为空则辅助项为0，并明确记录，主监督继续。

同一个带LoRA模型运行两种视图：

\[
a_i^-=\pi_\theta(o_i,L_i),\qquad
a_i^+=\pi_\theta(o_i,L_i,r_i)\quad (H1).
\]

H0的a⁺也只用(o,L)，无空提示行或占位文字。H1提示只进入辅助视图，原始无提示prompt字节保持：`In: What action should the robot take to {L.lower()}?\nOut:`。辅助prompt可在Out前增加固定`Current task-goal facts: ...`行；不得改原任务L或把r留到student/eval。

共享模型参数，不启动第二个7B教师。辅助输出的detach副本给无提示分支作目标；它本身仍通过真实专家动作训练。

\[
\mathcal L_{main}=.50\,BC_{ten}^-+.25\,Ref_{fresh}^-+.25\,Ref_{raw}^-;
\]
\[
D_S=7\sum_{i\in S}\sum_{k=0}^{7}m_{ik},\quad
\mathcal L_{aux}=D_S^{-1}\sum_{i\in S}\|a_i^+-a_i^*\|_{1,m_i},\quad
\mathcal L_{transfer}=D_S^{-1}\sum_{i\in S}\|a_i^- -sg(a_i^+)\|_{1,m_i};
\]
\[
\mathcal L=\mathcal L_{main}+.25\mathcal L_{aux}+\lambda_d(u)\mathcal L_{transfer},\quad
\lambda_d(u)=.10\,clip((u-100)/100,0,1).
\]

这里带mask的范数为有效标量绝对值之和；辅助项分母是**S中有效动作标量总数**（有效步×7），不是直接除样本数；S为空返回0。main仍按各池有效标量归一化，不能改成所有24视图等权平均。两臂同系数与warmup；前100步不迁移、101–200线性升至0.10，属于一次正式训练内部日程，不是另跑教师/MVP。

**执行顺序**：先完成8个原底座reference且恢复LoRA/mode/RNG；再逐个辅助前向、保存detach预测并反向aux loss，释放图；再逐个20主前向/主loss及选中ten的transfer反向；最后一次optimizer更新。不能在本更新主图完成前step，不能将辅助图全留内存，也不能让reference临时旁路状态污染checkpoint反向。单观测microbatch1，按上述权重累计，不硬套旧22样本累积设置。

不默认教师更强；学生真实专家BC保持，蒸馏是待检验附加约束。不存在把最终成功样本、测试结果或未来状态用来在线挑教师的门控。

## 5. 训练、开发、保存

- 两组各1000更新，从原始底座新初始化，独立run/optimizer/RNG/账本；AdamW、lr2e-5、warmup50、bf16、既有non-reentrant checkpoint，沿原无依赖升级环境。
- 固定seed7，LoRA初始参数相同；只存当前run配置与权重身份，不复用旧训练状态。不搜索seed、系数、模板或训练长度。
- 在250/500/750/1000保存并做既有固定开发主选择：最多256ten＋128fresh＋128raw=512。只在其中eligible的原ten上额外运行辅助视图，最多256次/次开发；主输出复用，不再调用一次学生。
- 开发不反向；两臂同主选择/eligible辅助键。记录无提示BC、辅助BC、transfer、各池reference loss、提示可用量和已消耗前向数；loss不是闭环SR。
- 唯一正式checkpoint是末1000，不按开发loss/视频/测试挑中间权重。
- 保存LoRA、完整optimizer/scheduler/RNG、采样状态、reference与模型前向账本/配置身份及当前update；CPU prepare另记录已处理键数，正式eval保留原执行账本。恢复同run不得重置已消耗预算；失败保留，不自动退款或重开。

## 6. 完整数值预算：提交用户批准，尚未执行

| 项目 | 每臂上限 | 两臂总上限 |
|---|---:|---:|
| 优化器更新 | 1000 | 2000 |
| 原策略训练参考 | 8×1000=8000 | 16000 |
| 原策略开发参考 | 256×4=1024 | 2048 |
| **原策略参考合计** | **9024** | **18048** |
| 无提示训练模型前向 | 20×1000=20000 | 40000 |
| 辅助训练模型前向 | ≤4×1000=4000 | ≤8000 |
| 无提示开发模型前向 | ≤512×4=2048 | ≤4096 |
| 辅助开发模型前向 | ≤256×4=1024 | ≤2048 |
| **带LoRA训练模型前向合计** | **≤27072** | **≤54144** |
| 正式10 / 00模型轨迹 | 90 / 90 | **共360条** |

另有一次CPU sidecar生产≤143960键；新增仿真/演示、外部VLM/新教师权重、额外MVP/基线重跑/搜索为0。训练前向是按观测视图计，不能把同模型提示视图漏记，也不能与正式eval策略调用混成同一账本。失败调用在前向前扣账；超过上限明确拒绝。

正式评测沿九任务、原bank/人口、H520、chunk8、seed7、双bridge、10二元合规/00官方和全视频。只增加新adapter/factory接线，不改core/reporting或判据；各臂180正常完成后接下一臂，失败不自动重开或越过失败启动后续。

按042两臂训练6h55m、360评测6h16m的历史量级，本轮主流程粗估13–17小时，受共享GPU/磁盘影响；不是实测保证。不另开速度MVP。CPU文字整理耗时取决于既有audit体量，不宣称数据已经ready。

## 7. 因果解释与失败归因边界

主比H1−H0；两臂相同训练更新、样本与辅助动作监督，唯一有意差异是辅助视图是否给真实状态文字。提示视图长度不同，不能冒称精确FLOP相同，只承诺模型前向次数与动作监督曝光匹配。本轮测的是增加真实状态提示的整体作用，不能另声称已分离文字语义与长度/格式因素；不为此未经批准增加第三组。

历史042 F1 70%/80%是性能参考，不代替新匹配对照。若H1高于H0，直接支持的是这套训练期状态语言迁移的作用；不能据此推出学会一般推理、未见任务zero-shot或无碰撞。若仅训练提示分支更好而无提示主分支/正式SR不改善，则迁移假设未获支持，不包装成成功。

双壶s000为正确目标接触但未有效抓持；奶酪黄油s000为错抓后碰撞/恢复失败；白杯s003已有开爪和无接触时刻，后续再接触弹飞。不能把这些都当语言语义失败，也不凭证书未知断言没松手、凭弹飞断言物理引擎bug。所有旧分数保留。

数学上只有标准条件性误差分解：E‖a⁻−a*‖≤E‖a⁻−a⁺‖＋E‖a⁺−a*‖，它要求教师有效和迁移有效，不保证闭环SR，亦非新定理。近邻包括[PI Distillation](https://proceedings.mlr.press/v306/penaloza26a.html)、[ECoT](https://arxiv.org/abs/2407.08693)、[LSS](https://arxiv.org/abs/2609.04893)。

## 8. 实现与授权交接

预算确认后，X直接按配套工单实现和受影响CPU/fake测试，交新PR与043-v2回复；不先泛审、SSH、跑真实标签生产/模型/仿真或要求用户再跑MVP。Codex建议式验收、隔离部署，给常用conda/python命令和简洁实时进度。全部真实生产、训练和正式评测由用户亲启。

当前只有方法方向同意，不冒称本表上限已获批。未开始软件、生产、训练或评测；旧dirty checkout不改，不自动merge、清理、覆盖旧权重/失败或改服务器默认。
