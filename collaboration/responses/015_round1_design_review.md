# 015 Round 1：EGRS 完整设计的集中可实施性审阅

审阅者：X。日期：2026-10-21。交付仓库：`No1dry/Learning-Not-to-Act`。

## 1. 结论、证据与完成范围

**结论：主架构可保留；将下述有限接口修正纳入下一份完整实现工单即可，不需要先跑 MVP，也不建议换更大骨干。**目前不能按示意 JSON 原样实现持物保持与完整目标记忆；不能把现有进程 `reset` 当作目标切换；官方 SFT 也没有设计要求的逐字段弱标签屏蔽。这三类问题直接影响行为或训练标签，应在工单中明确。数据清单、标注人工与运行资源是预算决定，不能写成已经就绪。

本轮按 README → STATUS → 015 的顺序阅读，再审阅完整设计、基线及既有 Round 2 来源。审阅基准为方法库 `772af150992273681a994364760b9b7ed3d045a3`；[完整设计 v1](https://github.com/No1dry/Learning-Not-to-Act/blob/772af150992273681a994364760b9b7ed3d045a3/docs/research/2026-10-21_remaining_goal_selector_full_design.md) 的 blob 为 `70de639d352cb0476f741060512ab314b00163f8`。原两份方法稿不修改。

**静态审查边界：**新方法库已可公开访问；本轮匿名访问 `LIBERO-Remain-Eval` 仍失败，未直接核验其 `515e87d9b93ab838428791273a0f3020d6f56e9c`。以下适配器表使用 [014 指明的导出来源](https://github.com/No1dry/LIBERO-Remain/blob/5b6b8386d2d6e971b914316ea2fd2019e96fd116/collaboration/tasks/014_generic_mask10_eval_driver.md) `LIBERO-Remain@c6dc98de0c54517c976057598b60f4cedf7fa3e5`，并核对相应官方上游文件。这是有来源的实现参考，不冒充新评测库逐文件一致性认证，也不把 014 写成已经实现。

只读了文档、源码与数据目录元信息；未下载演示 HDF5 或模型权重，未创建环境、恢复状态、调用教师、抽特征、训练、模型推理或运行测试。本文中的预算和接口均为设计建议，不是新实验结果。

进度：015 审阅内容 **100%**；本轮方法实现 **0%**、新增真实数据准备 **0%**、证据标注 **0%**、训练 **0%**、方法评测 **0%**。这不是整个研究完成 100%，也不改变既有基线分数。

## 2. 可直接保留的设计

- **文本桥接：**当前五类 adapter、六个 model ID 都有语言输入路径。保持底座相机输入、归一化与动作解码，仅替换任务文本，在接口层可行。物体框只服务选择器，不硬约束手；底座抓错仍按原规则记分。
- **独立选择器：**采用 Qwen2.5-VL-3B、语言注意力 LoRA、冻结 VLA，具有明确官方实现路径；不需要读取 OFT 内部特征。
- **历史与调度分离：**规则保留有来源的证据，选择器读取历史，调度消费状态；预测 unknown 与历史未完成不是同一个事实。
- **查询边界重规划：**OFT 的八步 cap 与现有 runner 相容。只在查询前重规划，不承诺 chunk 中途感知，更不做隐藏物理动作。
- **正常回退与硬错误分离：**合法 UNKNOWN 可回退原指令；加载、通信和 schema 错误保留 technical/partial。原指令回退并不安全，也不免除违规、回退或超时。
- **原评价语义：**继续按原完整任务、H520、20 Hz、K4 五观测、评价端终止、sticky 事件和实际 TCP 路径评分。预测 SAT 不是物理认证，不引入 STOP、开爪补丁或保持段。
- **比较结构：**完整 EGRS、同骨干无任务 LoRA、去历史/角色监督等可与完整实现一起交付开关；普通动作微调保持可选，不设为开工门槛。

基线 21/80 成功、A 回退 1/80、确认错抓 24/80 支持优先研究目标/实体判断，但不能证明高层文本足以修复控制错误。架构通过设计审阅也不等于方法有效。

## 3. 必须明确的接口缺口与单一修正建议

这里的“必须”指避免明确的错误实现，不要求先做新实验。除这些内容外，不把命名、可替代架构或更多测试逐轮升格为前置。

### R1：固定目标引用，并把持物证据绑定到目标和实体

**位置：设计 §4.3、§5.2—5.3。影响：**示例每次生成 `g0/g1` 和自由 `goal_text`，没有规定跨查询身份稳定；全局 `interaction_hint` 又不能说明正在搬运哪一个目标。重排、漏掉一个 goal 或把“持有别的物体”误配当前目标，会把完成记忆与保持动作用错对象。

**具体替代：采用 episode 内固定的 goal registry，加逐目标交互证据。**registry 只从原指令生成，不读取 task ID、mask 或谓词。首次解析保留原文片段和目标/目的地描述；后续预测引用固定 ID，不重新增删目标。视觉消歧可更新实体证据，但不能更改原目标语义。解析/引用不合法属于 schema 错误；对合法目标看不清则是 UNKNOWN。

建议最小契约包含：

| 字段概念 | 必需语义 |
|---|---|
| 固定 `goal_ref`、原文依据、目标/目的地描述 | 整个 episode 不因输出顺序或措辞改变身份 |
| 图像局部实体引用与关联状态 | 允许未关联；不是 simulator ID，不因 bbox 重叠就宣称同一物体 |
| `relation_evidence` | SAT / UNSAT / UNKNOWN |
| `release_evidence` 与适用性 | 对搬运目标判断释放；机构操作明确 NOT_APPLICABLE，不能把它当 UNKNOWN 或要求松手 |
| `interaction_evidence` 与绑定引用 | 对哪个目标/实体有 HELD / NOT_HELD / UNKNOWN 证据；夹爪闭合本身不证明持物 |
| 证据定位 | 查询快照 ID、相机、区域、证据时间；必须来自当前或已获得的过去输入 |

框的归一化坐标必须声明相对于哪一幅展示图/预处理坐标系；模型原生像素坐标不可不经定义直接当 `[0,1]`。两相机、历史图不能共享一个含糊的 `current:region`。默认不因此增加向 VLA 传框、crop、点通道或动作修改。

调度使用两个不同概念：**关系成立**与**可认为操作已完成**。搬运目标后者还需可用释放证据；机构目标不套释放要求。携带保持仅在目标—实体关联可信时生效；新身份反证或释放证据立即撤销。短遮挡可沿用已有证据，但不能因“直到释放”为止而无限锁定：沿用设计的证据过期规则，过期后恢复 UNKNOWN，再按第 2/4 项调度。SAT 的两次支持必须含两次查询中新获得的证据，不能把上一条预测复述两遍当新的支持。

两次/三次查询可先保留为固定规则；它们不代表跨底座相同物理时长。UniVLA 单步查询和 OFT 八步查询的历史跨度不同，需要记录查询间隔，不能声称同样的毫秒级记忆或反应速度。此处不要求新增时间归一化实验。

### R2：目标变化必须在 actor worker 内清理缓存，不能走 episode reset

**位置：设计 §6。影响：**参考 `policy_worker` 的 `reset` 分支先执行全局 `_seed(seed)`，随后才执行 adapter reset。因此，即使 UniVLA 的局部 reset 本身不播种，从 `SubprocessPolicy.reset()` 进入仍会重置随机流。当前协议只有 initialize/reset/predict/close，没有公开 goal-change 消息。

**具体替代：在方法库增加一个版本固定的 actor facade，仍由现有模型 worker 加载。**facade 在 `predict(obs, effective_text)` 中比较上次实际执行文本；文本变化时在同一 worker 调用专用 `on_goal_change`，然后执行一次原 adapter predict。不经父进程 `reset`，不重建 policy，不重新加载权重。相同目标使用固定文本，避免每次等价改写都清空 UniVLA 历史；原指令回退与子目标之间的变化也算实际输入切换。

对有缓存的 adapter，仅清除明确与旧目标有关的状态；对已审查无缓存者显式 no-op。未知 adapter 必须声明能力，不能用“没有 hook 就全 reset”的兜底。episode reset 仍走原流程，只在新 episode 播种。

这样无需为方法自行改写 eval core 的通信协议。更通用的 goal-change RPC 可由后续评测工单另行决定，但不是本方法第一版的必需改动。专用 hook 的存在也不等于当前已经实现。

### R3：两个进程不能靠 observation 字典偷传历史；明确一个方法侧组合层

**位置：设计 §3、§6、§9。影响：**现有 `SubprocessPolicy.predict()` 会对白名单观测重新筛选，不能直接把 `history/current_goal/previous_actions` 塞进去给 selector。当前接口也没有 selector 的任意上下文字段。更改白名单会混淆传感输入与方法状态。

**具体替代：一个方法侧 EGRS policy 对接 014，内部组合两个隔离 worker。**actor 使用上述 facade 和现有 SubprocessPolicy；selector 使用方法库自己的窄 RPC，复用现有 framing 工具，消息中明确分开白名单 sensor 与方法 context。context 只含原指令、固定目标引用、历史预测、已发命令摘要等允许信息，不含评价真值。

方法主进程维护规则历史和调度，selector 处理视觉与历史；actor worker 只接原图/本体观测和实际子目标文本。`reset/predict/close/metadata` 是对接概念，不宣称本库已有这些实现。方法包应独立命名并安装到需要加载 factory 的解释器，不覆盖 `benchmark` 包；参考 SubprocessPolicy 会重设 PYTHONPATH，不能依赖父 shell 恰好可导入方法源码。

“先前动作摘要”必须标记为命令/返回片段，不标记为已抓住或物理执行证据。runner 会截断长 chunk，原生返回的全部 50 步不能被写成已经执行 50 步。方法日志与实际执行长度按 query ID 离线关联；不向在线策略回传评分日志。

### R4：弱状态 loss 与多图截断需要真实的数据处理支持

**位置：设计 §4.1—4.2、§7.3、§8。影响：**官方数据处理把 assistant 答案整体设为训练标签，并没有逐 JSON 字段的 provenance mask；其普通 collator 还会直接按最大长度截断 token。沿用默认值可能把未核验状态当硬标签，或截断多图/完整 JSON。

**具体替代：保留官方 Qwen2.5-VL 模型与 LoRA 路径，定制方法数据集/整理器和字段 loss 统计。**采用规范序列化和字段有效性表，在最终 chat-template 与视觉 token 展开后，把未核验字段及依赖它的解释 token 设为 ignore；字段掩码与 input_ids、labels 的边界一起保存/检查。不能按字符数猜 token 数，也不能仅屏蔽数值、却继续监督“因此已经完成”的句子。

人工确认的 UNKNOWN 是有效类别，参与监督；尚未确认可辨性的弱样本是“该字段无监督”，二者不可混同。训练输入、历史和答案解释中也不能夹带隐藏的 physical_truth；屏蔽某个 token 的 loss 不会自动阻止 teacher-forcing 上下文泄漏。未确认值应删除或用不含物理结论的占位表示，并屏蔽对应部分。

为同一完整实现显式设置序列/视觉预算，并在整理器中拒绝无法完整容纳的样本或按预设规则减少最旧历史，绝不默默裁掉当前视图或目标。拒绝/裁减均计数。不需要为此更换骨干。

## 4. 六模型目标切换静态能力表

以下“无缓存”限定为已读的直接 adapter/官方 policy 路径，不推广到任意远程服务或用户自建缓存。所有模型仍需接上方法 facade；本表不是权重运行认证。

| 底座 | 已读实现的状态 | 目标变化处理 | RNG/权重约束 |
|---|---|---|---|
| OpenVLA | 单步输出；本地 adapter reset 仅检查关闭状态 | **无跨查询动作缓存：no-op**，下一次使用新文本 | 不调用 worker reset；不重新构造模型 |
| OpenVLA-OFT | 每次产生 8 步；队列/截断由 runner 管理，本地 reset 无队列 | **无本地跨查询缓存：no-op**；查询边界已消费上一 accepted chunk | 保留原权重与调用流；不能声称中途阻断 step 1—7 |
| UniVLA | `_history` 保存前一 latent 字符串，decoder 有动作聚合 buffer/mask，窗口 12 | **需清缓存**：专用 hook 清 `_history` 并调用 decoder 的局部 reset | decoder reset 清数组而不加载权重；禁止通过外层 episode reset 执行 |
| π0 / OpenPI | adapter 每次返回原生 50 步，内部 NumPy RNG 生成 flow noise；官方 infer 还推进自身 JAX RNG | **当前直接 Policy 路径无旧 chunk 队列：no-op** | adapter reset 会重新创建 NumPy RNG，不能用于换目标；JAX/torch 流同样保留 |
| π0.5 / OpenPI | 同一直接接口，原生 horizon 为 10 | **无旧 chunk 队列：no-op** | 同上；原生 horizon 与 runner cap 分开记录 |
| GR00T N1.7 | 当前 adapter 直接调 Gr00tPolicy；单时刻输入，上游 reset 返回空信息，已读 `_get_action` 无持久动作队列 | **该已读直接路径无目标缓存：no-op** | 保留 torch RNG；不把其他 wrapper/server 的缓存行为套进来 |
| 自定义/不同上游版本、远程服务 | 无静态证据 | **暂不支持动态换目标，直到提供明确能力声明/清理钩子** | 不自动全 reset，不伪造兼容 |

来源：[OpenVLA](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/adapters/openvla.py)、[OFT](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/adapters/openvla_oft.py)、[UniVLA adapter](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/adapters/univla.py)、[OpenPI adapter](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/adapters/openpi.py)、[GR00T adapter](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/adapters/groot.py)。

同时核对：[worker 的 reset 播种](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/policy_worker.py)、[进程代理与白名单](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/isolated_policy.py)、[UniVLA decoder reset](https://github.com/OpenDriveLab/UniVLA/blob/0ab9e9d/experiments/robot/libero/run_libero_eval.py)、[OpenPI Policy](https://github.com/Physical-Intelligence/openpi/blob/215abfb217dbac7d5f1273282331b9b1866c0479/src/openpi/policies/policy.py)、[GR00T Policy](https://github.com/NVIDIA/Isaac-GR00T/blob/51d4c89f72fda44cbf77285c6a8114b52676b8a1/gr00t/policy/gr00t_policy.py)。

独立 selector worker 还能避免 selector 的随机采样消耗 actor 的全局随机数。建议 selector 默认确定性解码并单独记录配置；这不代表 CUDA 位级确定性。保持 RNG 状态也不等于不同方法因查询次数不同仍会消耗完全相同的随机样本，报告时要区分。

## 5. Qwen 训练与依赖的可实施路径

### 5.1 骨干保留，固定真实版本

官方[模型卡](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)提供多图与定位/结构化输出用法；本轮读取模型元数据的 revision 为 `66285546d2b821cf421d4f5eb2576359d3770cd3`。只读了元信息，没有下载或验证权重。

官方训练库本轮源码固定在 `QwenLM/Qwen3-VL@96588727e44c78b25ba03ea03b8e12f7e64fd0da`。其 [train_qwen.py](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/qwenvl/train/train_qwen.py)明确分支加载 `Qwen2_5_VLForConditionalGeneration`，LoRA 分支先冻结参数，再添加 q/k/v/o projection LoRA。因此 r16/alpha32、bf16、全局 batch16、最多 3 epoch 可以保留为候选；学习率 1e-4 没有在这里被验证，也没有证据要求默认升级模型。

需要注意：代码按 model path 名称选择架构，本地目录改成不含 `qwen2.5` 的通用名字可能走错分支；方法入口应按明确 model type 加载，或固定保留对应路径语义，不能只靠“下载的是对的权重”。训练参数清单必须确认只有 selector 的语言 LoRA 可训练，不能仅凭配置名称宣布视觉/VLA 已冻结。

官方[训练说明](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/README.md)给出了依赖参考，其中 Transformers 使用 dev 版本描述；不能把这个描述或 `latest` 当可复现锁。下一工单需固定实际 Transformers revision/包版本，以及 torch/torchvision、PEFT、processor、训练代码与模型许可文件身份。单独 selector 环境，不在 OFT 环境升级这些包。此处不承诺某个现有服务器已满足硬件或依赖条件。

### 5.2 多图、字段标签与历史

官方[数据处理](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/qwenvl/data/data_processor.py)支持 image 列表与逐一占位符，已有 chat template、图像 grid 和 Qwen2.5 位置编码路径；方法层须保持按时间/相机确定的顺序，例如两个过去时刻各双相机，再到当前双相机，不把六幅图误解释成六个任意样本。

当前 [argument.py](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/qwenvl/train/argument.py)的默认 `model_max_length=512` 不适合作为本设计的默认完整输入承诺。建议显式候选上限：每幅最多 256 个视觉 token、至多六幅；总序列上限 4096，另外明确 prompt/历史/答案预算，按 processor 的实际展开计数。1536 个视觉 token 只是按上限相乘的预算，不是所有图像实际 token 数保证。实际不能容纳时按 R4 处理，不能静默截断。默认先关闭 packing/flatten，避免在约 3600 查询规模中额外混入跨样本位置与字段掩码问题；这是实现简化，不是新增实验门槛。

弱标签 mask、字段 token 统计、dev 数据入口和错误样本清单需要方法层补齐。官方数据模块默认 `eval_dataset=None`，读取错误还有替代其他样本的路径；本研究应使用显式 split 与可追踪的剔除/失败记录，不能让某个坏样本无声变成另一个来源后继续宣称采样预算不变。

历史训练输入应有空历史和过去可观察证据，不能直接把物理真值状态填成“过去选择器已确认”。可用人工审阅的可见证据历史，并包含 UNKNOWN/撤销；若需要模型预测历史，再单列一次离线前缀推理预算，由用户启动。其上下文不得读取当前之后的帧。去历史对照要同时去掉旧图和文字历史，保留当前视图与同样的执行接口；否则只是去掉一种记忆通道。

训练有效全局 batch16 指各设备 micro-batch × 梯度累积 × 设备数。若最终有 3600 query，按来源约 80/20 后粗略为 2880 train/720 dev，则每 epoch 约 180 次更新、3 epoch 约 540 次；实际样本数、组划分与剔除会改变它。这是算术预算，不是 GPU 小时估计。显存和耗时在没有用户硬件、实际 token 分布及训练运行前不能可靠承诺。

## 6. 200 来源预算：可列出的文件与不能承诺的覆盖

### 6.1 具体候选：Goal 10 + Object 10

LIBERO 官方仓库[指向此 Hugging Face 数据入口](https://github.com/Lifelong-Robot-Learning/LIBERO#datasets)。下面文件名来自固定 revision `147fa5eb607bb696dd922c3518084a90954cd2f3` 的目录；这是**20/20 个候选文件名可见，100% 目录级核对**，不是 HDF5 内部 episode/图像完整性验收。每文件抽 10 个有效来源只是草案；本轮实际 episode 内容核验 **0/200，0%**。

| # | suite | 候选文件（均为 `.hdf5`） |
|---:|---|---|
| 1 | libero_goal | `open_the_middle_drawer_of_the_cabinet_demo.hdf5` |
| 2 | libero_goal | `open_the_top_drawer_and_put_the_bowl_inside_demo.hdf5` |
| 3 | libero_goal | `push_the_plate_to_the_front_of_the_stove_demo.hdf5` |
| 4 | libero_goal | `put_the_bowl_on_the_plate_demo.hdf5` |
| 5 | libero_goal | `put_the_bowl_on_the_stove_demo.hdf5` |
| 6 | libero_goal | `put_the_bowl_on_top_of_the_cabinet_demo.hdf5` |
| 7 | libero_goal | `put_the_cream_cheese_in_the_bowl_demo.hdf5` |
| 8 | libero_goal | `put_the_wine_bottle_on_the_rack_demo.hdf5` |
| 9 | libero_goal | `put_the_wine_bottle_on_top_of_the_cabinet_demo.hdf5` |
| 10 | libero_goal | `turn_on_the_stove_demo.hdf5` |
| 11 | libero_object | `pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5` |
| 12 | libero_object | `pick_up_the_bbq_sauce_and_place_it_in_the_basket_demo.hdf5` |
| 13 | libero_object | `pick_up_the_butter_and_place_it_in_the_basket_demo.hdf5` |
| 14 | libero_object | `pick_up_the_chocolate_pudding_and_place_it_in_the_basket_demo.hdf5` |
| 15 | libero_object | `pick_up_the_cream_cheese_and_place_it_in_the_basket_demo.hdf5` |
| 16 | libero_object | `pick_up_the_ketchup_and_place_it_in_the_basket_demo.hdf5` |
| 17 | libero_object | `pick_up_the_milk_and_place_it_in_the_basket_demo.hdf5` |
| 18 | libero_object | `pick_up_the_orange_juice_and_place_it_in_the_basket_demo.hdf5` |
| 19 | libero_object | `pick_up_the_salad_dressing_and_place_it_in_the_basket_demo.hdf5` |
| 20 | libero_object | `pick_up_the_tomato_sauce_and_place_it_in_the_basket_demo.hdf5` |

目录证据：[Goal](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3/libero_goal)、[Object](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3/libero_object)。两个目录展示的整体体积约 13.8 GB；它不是读取 200 个 episode 的必然下载量，也不是恢复/标注耗时。

选择 Goal+Object 是一个具体、可获得的初版来源建议，不是已充分覆盖所有关系。表中单目标入篮和开炉等原子技能允许与评测目标共享；需明确主张是**未训练完整复合目标组合**，不能说未见物体或全部未见场景。文件名核对不替代最终语义/同源排除清单。

明确排除当前六个复合任务：汤罐+番茄酱入篮、开炉+摩卡壶、奶酪+黄油入篮、汤罐+奶酪入篮、双杯左右盘、白杯上盘+布丁在盘右侧，以及它们的语义等价组合。不得从其演示、当前评测 official init 0..9、已知等价状态或其派生窗口补训练/dev 数量。训练文件中的 `demo_0` 不是评测的 `official_init_0`，也不能因为编号不同就认定无同源；已知同源成组，未知祖源保留披露，不新增逐一祖源匹配工程。

### 6.2 明显不足与预算内处理

1. **任务数不等于关系多样性。**十个 Object 任务主要重复入篮，Goal 扩充 On、Open、炉子与若干位置关系，但杯子身份消歧、白杯/黄白杯、指定盘左右的证据不足；不保证相同相对位置语义自动迁移。
2. **成功演示不保证失败历史覆盖。**未抓中、错误物体、长期遮挡、释放边界未必足够。不能从普通成功示范自动造出真实错误尝试标签；不足时保留 UNKNOWN/覆盖缺口，不借用当前 eval 失败轨迹补未见训练集。
3. **没有证明能抽满 600 明确 + 300 歧义窗口。**六个有意义窗口是上限而非每条轨迹的义务；无法找到 300 个自然歧义窗口时，报告实际数量，不把随机帧硬标歧义，也不自动恢复新视角。
4. **训练规则的作用域需清楚。**排除 LIBERO-90 训练，扩展域不足如实保留。官方底座可能已见过这些普通数据；“selector 新训练”不等于整个系统从未接触数据。

预算内的具体备选只给一组：若更重视杯子/机构覆盖，可由 Codex 将三个重复 Object 来源替换为非当前六复合任务的 `KITCHEN_SCENE6_put_the_yellow_and_white_mug_in_the_microwave_and_close_it_demo.hdf5`、`KITCHEN_SCENE4_put_the_black_bowl_in_the_bottom_drawer_of_the_cabinet_and_close_it_demo.hdf5` 和 Spatial 的 `pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate_demo.hdf5`，仍保持约 20×10。前两项来自 [LIBERO-10 目录](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3/libero_10)，后一项来自 [Spatial 目录](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3/libero_spatial)。这是来源替换建议，不是新增顺序议题、不是已决定采集，也不能彻底补齐白杯/右侧放置缺口。本文默认清单仍是上表，最终替换名单由 Codex 固定。

### 6.3 人工与离线成本估算

900 个窗口最多对应 2700 个关系/实体查询；六幅图、多个框、关系、释放、持物关联和来源记录需按窗口联合标注，不把一个窗口一眼判断当作三份独立标注。

| 工作 | 估算假设 | 人工成本 |
|---|---|---:|
| 600 个明确窗口 | 每窗口 2—3 分钟，含实体/关系/证据定位 | 20—30 人时 |
| 300 个歧义窗口 | 每窗口 4—6 分钟，允许 UNKNOWN、核对多视图 | 20—30 人时 |
| 约 20% 双标/分歧复核 | 180 窗口 × 3 分钟 | 约 9 人时 |
| 指南、清单与格式修订 | 已有候选框时的小规模整理估算 | 5—10 人时 |
| **合计** | 不是用户逐条看片，也不是已测时 | **约 54—79 人时，按 55—80 人时立预算更清楚** |

这些是假设驱动的估算，实际多目标框数量、可见性歧义与标注工具会改变它；若从零手画全部多视图框，应另外留出余量。建议由指定标注人员/研究助理执行，Codex制定指南与抽检，用户决定人力资源，不默认用户承担全部工作。

离线 VLM 可对最多 3600 查询生成候选，但它们是伪标签；人工核验成本不会因此变成零。若每查询最多六图，候选处理上限约 21600 个图像输入位置，可复用窗口图；不等于 21600 张独立图或 3600 条独立轨迹。候选推理、训练历史前缀推理和物理状态恢复应分别计调用/时间，由用户另行启动，不能用“没有 VLA rollout”将其当免费。

剩余约 300 个弱窗口可监督已可靠确认的实体/格式字段，未核验状态按 R4 屏蔽；不自动输出 900 个真实状态标签。物理真值与可见证据两列独立，不能用投影面积、分割或成功终点直接认证 RGB 中的 In/On/释放。

按任务分层、来源及已知同源组约 80/20 划分可保留，派生窗口和查询继承组别；200/1200/3600 分别记录。无确认集不影响本轮实现设计，但后续报告只能作与既定评测暴露程度相称的主张。

## 7. 调度、故障与 014 的具体衔接

### 7.1 正常行为与技术错误

| 情况 | 处理 |
|---|---|
| 当前目标有绑定正确的持物证据，短暂遮挡 | 在证据有效期内保持目标；新反证/释放/过期撤销 |
| 有明确 UNSAT，当前无可信在途目标 | 选合法未完成项，当前同目标优先，文本稳定 |
| 全 UNKNOWN、无可靠待完成项，且无可信在途目标 | 原完整指令回退；仍计动作、路径、违规和失败 |
| 全部预测 SAT，但评价端未结束 | 不读取停止原因，不生成 STOP/零动作；按原回退规则继续 |
| 预测状态错误，但输出结构与引用合法 | 正常模型错误，行为与原评分如实保留 |
| 丢失固定目标、非法 enum、未来/不存在证据引用、NaN/越界框等契约错误 | 技术故障并保留 partial，不静默删除目标或变成 baseline 成功 |
| selector/actor 加载失败、超时、worker 退出 | 技术故障，不自动多跑一次、不静默重启/切模型 |

原指令回退可能重做 A，是设计已经承认的能力风险，不是本轮要求插 shield 或 STOP 的理由。持物规则不是安全证明；视觉错认仍可能保持错误目标。初始空历史没有 A 完成事实，goal registry 中出现两个目标也不表示任何一个已完成。

### 7.2 方法身份与跨库依赖

依赖固定 eval core，保留 `headless.runner.run_episode` 与物理评分；参考 runner 的可用接口是 policy 的 reset/predict，返回合法原生动作，内部再按 cap 截断。原 [headless runner](https://github.com/No1dry/LIBERO-Remain/blob/c6dc98de0c54517c976057598b60f4cedf7fa3e5/benchmark/remaining_goals/headless/runner.py)是模型无关核心，但旧批处理有 OFT/SOG10 专属身份校验，不能只换 JSON 就宣布方法入口就绪。

具体衔接约定：

- 014 通用 driver 接受方法自定义 policy factory，外层身份是 EGRS；内层 actor 保留真实 OFT/其他模型身份与归一化，不把 EGRS 伪装成 plain SOG10。对外方法配置与内层 actor 配置分开，不能将整套外层配置送入 OFT 专属 transfer 校验。
- 一次运行记录方法 commit、eval core commit、方法 schema、selector base revision/LoRA 文件 hash/processor、提示模板、goal registry/text builder/历史参数、actor checkpoint/adapter/runtime、cap、seed 作用域。模型路径存在不等于权重字节已校验。
- 014 身份封装需容许方法 provenance 与 actor provenance 嵌套或有明确 sidecar 引用；若当前 driver 尚未提供该接口，由 Codex 在相关工单写清，不在方法库复制一套评分来绕开。
- 方法日志另存 query 对齐的输入快照引用、预测、历史变更、子目标、换目标原因、回退原因、两类调用数、图像数与耗时。日志失败不能静默称完整方法运行成功。原动作、双相机视频、物理证据与 TCP 结果仍由 eval core 保存。
- 路径只统计实际执行；OFT 最多约 65 次查询而单步策略最多 520 次查询，逐查询一次 selector 的计算成本可能相差明显。记录实际次数和控制预算，不能当作免费、相同延迟的模块。
- 包依赖只引用 eval core；方法库不复制任务定义、几何、源状态接受或事件计分实现。首个完整方法代码可直接开发，真实联调/运行再依赖最终固定的 014 接口；不以 014 合并作为本轮设计审阅的门槛。

## 8. 交给 Codex 的范围/预算决定

建议一次集中确认以下事项，然后形成一个完整实现工单，不再展开候选体系：

1. **采纳 R1—R4。**默认使用固定目标引用、逐目标持物/释放证据、actor facade、独立 selector context RPC 与字段 mask；不加入空间动作接口。
2. **冻结数据清单。**接受 Goal10+Object10 的覆盖限制，或采用上述三项预算内替换；确认“排除完整复合任务、允许原子目标复用”的研究定义，清单仍需执行前去除已知等价/同源冲突。
3. **确认标注资源与预算。**约 55—80 人时的人员安排，弱样本的使用范围，是否另行使用离线候选和预测历史；这些均不能默认为已获启动授权。
4. **确认运行资源与依赖锁。**selector 与 actor 的解释器/GPU安排、调用超时、模型与 processor revision、依赖及许可身份。若共用 GPU，权重驻留和峰值显存需正面预算，不能默认 3B 与 7B 可随意共存。
5. **给出 014 最终对接契约与可读版本。**本轮已说明 eval 仓库访问边界；后续按实际依赖核对适配器来源与 factory/provenance 接口，不假定未见代码等同于参考导出。

查询计数阈值、视觉 token 上限、LoRA 超参是明确记录的初始配置，可在 dev 预算内调整，不需要为每种替代值再发一轮设计审查。不能用评测分数反向挑规则。

## 9. 下一份实现工单应包含的入口与定向验收

以下是待建设的模块职责，不是假想已经存在的 CLI；最终目录、factory 名称和命令由工单固定。

| 待建设入口/模块 | 应交付内容 | 防止的具体错误 |
|---|---|---|
| 方法配置与版本清单 | selector/actor/runtime/eval core 独立身份、模型能力声明 | EGRS 伪装 baseline、解释器串用 |
| 原指令解析与稳定目标契约 | goal registry、实体关联、逐目标携带/释放/证据定位 | 目标重排后错用历史、漏目标、保护错物体 |
| 方法数据清单与标注导出/导入 | 来源/同源组/split、物理与可见字段、实际覆盖计数 | 帧级切分泄漏、弱标签冒充真值、补错来源 |
| 选择器训练入口 | 固定 Qwen 分支、LoRA 冻结清单、多图处理、字段 mask、dev 统计 | 非预期训练底座、静默截断、监督未核验状态 |
| selector worker 与 RPC | sensor/context 分离、schema 校验、独立随机流、明确故障 | 真值进入策略、硬错误悄悄回退 |
| 历史与规则调度 | 可撤销、过期、当前证据计数、稳定文本、正常 UNKNOWN 回退 | 自我复述增强信念、永远锁住目标、假 STOP |
| actor facade/goal-change hook | UniVLA 清历史聚合；已读无缓存路径 no-op；未知能力拒绝 | 播种重置、加载权重、旧目标动作残留 |
| 014 factory 与结果 sidecar | 方法/actor provenance、query 对齐、partial 保留、离线读取 | 改评分、遗漏成本、方法日志缺失却称完成 |

后续只需与这些接口直接相关的 CPU/fake 检查：目标引用与 held 绑定、弱/UNKNOWN 掩码区别及多图边界、换目标清缓存但 RNG/权重不变、初始空历史与过期撤销、正常回退和硬错误分流、非 OFT/方法身份经通用 driver 保留、sidecar 与原 query 对齐。它们防止明确的数据/运行错误，不要求全库或多平台测试；本轮未执行这些检查。

**下一步操作和执行者：**Codex 汇总本轮有限修正与上述预算/接口决定，提交下一份明确完整实现工单；X 在该工单下实现并做受影响 CPU/fake 验收；Codex 审查与部署；用户另行确认预算并亲自启动真实数据准备、标注推理、训练和模型评测。015 本轮只完成设计审阅，不代替这些阶段，也不自动合并任何历史 PR。
