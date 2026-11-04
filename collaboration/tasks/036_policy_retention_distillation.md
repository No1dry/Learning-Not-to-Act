# 036：原策略动作蒸馏约束的10增强微调——直接实现

2026-11-04，Codex决策；用户已批准本文预算及文件准备。X改实现/定向CPU-fake，Codex建议式审查/隔离部署/文件准备/完整命令，用户启动全部真实作业。本工单在方法库`No1dry/Learning-Not-to-Act`，不改benchmark库。**直接实现，不再先交方案，也不增加MVP/GPU预检。**

## 1. 目标、基点和边界

035已有10 54.44%（原24.44%），00 73.33%（原86.67%）；新一轮保留10增强训练曝光量，加入普通观测上的原策略约束。研究依据见[方案](../../docs/research/2026-11-04_task036_retention_plan.md)。第一优先级仍10，00其次，泛化第三；不保证效果。

实现基点为已验收035 PR10@`ac2ec431aa7e1c3c7096baf978878d20ef458e9b`（最后实现`918db35bd67c3b6a9e2cfb189528eff6352cb028`）。main中035可能仍未合并，不得只从main新建而丢失该实现。保留上述依赖及最新main文档，**新建036分支/PR**，说明包含未合并依赖，不自动merge或重写035 PR。

推荐薄入口`egrs.retention`；命名可自定，不为通用框架重构035。复用原数据/OFT helper/严格adapter加载/方法侧双环境分派/原报告reader。原030/035仍可读，旧运行目录、权重、评分、技术失败和003/004全部保留。不能热改部署树，不修改固定eval core，不补做035基线。

固定：原SOG10，原完整instruction＋双RGB＋8维本体，8×7动作，seed7/chunk8/H520。策略输入不带mask、任务状态标签、物体真值、官方谓词、接触真值、未来帧或评测成败；训练采样池标签仅用于取样/损失，不能流入processor/policy。评测一个适配VLA，无FINISH、外置规划器、VLM、条件路由或参考模型。

## 2. 数据池及元数据准备

以下路径均相对已确认的`$EGRS_ROOT`，Codex在交付后固化配置/来源SHA；代码不可写死服务器个人根路径。

- 复用`data/trajectory035/generated-003/export`现有10/fresh普通合格数据及资格/分组，不重新生成或物理检查。
- 原始九HDF位于`data/trajectory035/raw/147fa5eb/libero_10/`；源清单为`configs/trajectory035-564c91c9/seeds.json`。数据集`yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`，每任务原前20，共180父示范，原136train/44dev划分保持。
- 参考底座与学生初值同原固定SOG10：`moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7`；统计键`libero_10_no_noops`，stats SHA `6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3`。继续原干净OFT `e4287e94541f459edc4feabc4e181f537cd569a8`、原依赖，无新增下载/升级。

新036数据索引只做JSON/HDF观测元数据绑定与惰性读取，不调用环境、render/reset/step、真实VLA或教师，不强制导出整库图片。CPU/fake以合成HDF测试；X不得为验收自行读取真实轨迹执行模型。

### 2.1 10专家池

- train161轨迹/54父组，dev60/20，覆盖原六任务。复用原035任务→父组→variant→window采样，排除audit-only hold尾段。
- 原归一化专家动作及valid-tail mask保持；不用旧评测轨迹或其动作。每次更新12条，1000轮共12000次曝光。

### 2.2 fresh普通观测池

- train55轨迹/父组，dev20，覆盖六任务；用已有fresh RGB/本体的同一时刻、原完整指令。
- 每更新4条：2条prefix时间箱、2条全轨迹均匀。任务→父组均衡，在对应时间箱内均匀取当前观测。普通专家动作不作036监督目标。

### 2.3 raw普通观测池

- 固定原180父组全部进入索引，使用原136/44；不按035 replay合格/模型成败挑选，旧失败不改写为通过。其作用是普通**观测**上的函数保持，不声称raw轨迹已获fresh资格。
- 每更新4条：2条prefix、2条全轨迹；九任务→原父组均衡，再取当前观测。
- `obs/agentview_rgb`与`obs/eye_in_hand_rgb`各旋转180°一次；本体为同一行`obs/ee_states`＋`obs/gripper_states`（8维），按原统计归一化一次。预处理/JPEG/缩放/双图顺序复用现有helper；不重复旋转/归一化。
- raw来源种类须另标`official_recorded_observation`等。036只需同一行图像/本体对应，不读`states`、`actions`或未来观测作为模型条件/目标。禁止把035种子清单中“fresh T+1/T”的alignment_basis照搬成raw动作时序证书；原始图像与fresh分辨率/渲染域不同如实记录。
- instruction沿用清单/官方任务语言，不换成B子指令；来源图像/本体长度不一致须明确报数据错误，不能静默偏移/猜对齐。无须再证明raw专家动作对齐，因为036不使用它们。

两普通池prefix定义为前`max(1, ceil(T_obs/3))`个当前观测，**不是用谓词筛选A未完成**。全轨迹箱可自然包含prefix；重复取样是有放回训练，不伪称新数据。raw与fresh同父可同时存在，但必须同split；不把它们计成独立父演示。物理祖源未知保留，不宣称与official init物理独立。原评测初态/视频/动作/成功标签不进训练索引。

## 3. 同底座参考动作：无需双7B

`egrs/augmentation/oft.py::training_prediction`现输出归一化动作，依赖当前图像/本体/指令，不依赖专家动作；优先复用。参考是原始冻结策略，不是完美专家，保持其错误的可能性必须说明。

当前LoRA为项目native `LoRALinear`，**不是PEFT**。增加受控context，暂时旁路全部新增语言LoRA residual，仅用原`base_layer`。`torch.no_grad()`且eval下得到原策略8×7连续归一化action-head输出并detach，不做unnorm/clip/二值夹爪/文本解码。不要复制第二个7B、用PEFT假API或从035 adapter生成参考。

调用顺序必须为：

1. 在学生计算图建立前进入参考context、参考前向。
2. `finally`完整恢复每个module原`training`标志、每个native LoRA enable状态，再学生前向/反向。
3. 原base/vision/projector/actionhead/proprio始终冻结，只原语言LoRA参数进入优化器；参考不改变requires_grad、权重、优化器或梯度，不共享可污染学生的cache。

不要仅`root.train(True)`恢复：会错误地开启冻结vision/dropout。学生非重入gradient checkpointing的重算发生在参考context外，必须始终启用学生LoRA。禁止把教师输出留有grad_fn，或在学生forward/backward间临时关LoRA。loader默认必须恢复LoRA启用；导出不能把“参考旁路”状态带到评测。

metadata记录`reference_view=shared_frozen_base_without_added_lora`及原底座身份；这是训练实现方式，不是额外的推理模型组件。无需新全数据离线teacher缓存阶段；可缓存固定dev参考以减少调用，但缓存须绑定观测/原底座/预处理身份，不能绕过预算或来源分组。

## 4. 固定训练配方与预算

- **从原始SOG10＋新LoRA开始**，不继续035 adapter/优化器。native语言q/k/v/o，r16/alpha32/dropout0；其他冻结。lr2e-5、warmup50、bf16、seed7、非重入checkpointing；不加图像增强/物理扰动。
- 1000 optimizer updates，micro1/accum20、有效batch20：12 ten＋4 fresh-ref＋4 raw-ref。不是简单拼20条取平均。
- `L = .50*L_ten_expert + .25*L_fresh_reference + .25*L_raw_reference`；每池先按本更新有效动作标量数归一化。ten沿原tail mask；普通reference的8×7全部有效（是当前观测的策略函数输出，不截成专家尾部）。不加普通专家action loss，不暗加KL/额外损失。
- 累积实现须与三池分别concat后上式的梯度一致，尤其ten尾长不同；可预取本更新mask分母，不能固定按12均值代替有效标量归一化。参考梯度为0，冻结参数不更新。
- train参考最多8000次（每轮8）；dev在250/500/750/1000各至多256个参考观测，fresh128/raw128，各固定64prefix/64全轨迹。ten dev每次最多256条，固定抽样。参考总预算**≤9024单观测策略前向**，batch合并不能掩盖计数；cache可减少，不另加真实warmup/探测调用。
- 固定保存250/500/750/1000，最终评测必须update1000，不以dev/正式SR挑权重。日志分别给三池loss及加权total、update/1000百分比、实际参考调用/预算、耗时/ETA；不把loss叫SR。
- 无新仿真/重放/10生成；一组1000更新；同一新模型10/00各90（180条）正式评测，不重跑原模型、035模型或先跑小样。学生训练样本20k，对03516k为+25%，不能声称相同计算量/用时。

## 5. 工件加载和正式评测

- 增加明确版本化036 schema/identity，绑定三池来源/划分/预处理、参考底座、采样/损失/LoRA、原统计、权重SHA、update1000等；不伪装035元数据或全局改035 GROUP/validator。原035/030严格读取保持可用，仅为新identity增加必要分支。
- 复用已修方法侧旧/新bridge严格分派、proxy双向协调、原core034二元10和00官方report；沿用旧来源各自端点与状态。不得再安装升级runtime、解引用venv解释器软链，或绕过真实环境锁/把技术错误计模型失败。
- 新模型全部180需新执行，**不能继承035的成功/失败分数或轨迹**（权重不同）。可复用准备工件/来源证据，不能复用模型结果。新目录建议`runs/retention036-train-001`、`runs/retention036-eval-001`，文件准备目录另建`configs/retention036-*`；不覆盖003/004或035训练。
- 原版每完成episode/unit全量重扫旧raw导致最终报告慢；036采用已验证单元缓存/轻量完成ledger或仅进度计数，**不能每次重扫全部历史raw**。最终仍一次原reader正式完整核验，两类合并summary/report；不改几何/事件/成功判据。
- 运行日志至少显示模型完成`n/180`和百分比、10/00各进度；如用真实已验证缓存可报临时SR，否则明确待正式计分，不能用缺证据填失败。最终核验按任务/episode显示处理百分比，最终打印两类正式SR百分比并把progress标`completed`，不再遗留pending假提示。避免额外二次全量report扫描。
- 035最后`policy.close`的worker-15事实保留，不需真机复现。若清理异常发生在全部结果已写后，用方法层finally确保原报告仍写出；明确记录`cleanup_warning`与正式完成/软件退出分别是什么。不得吞掉推理、物理、证据缺失或未完成episode错误，不为得到exit0伪造成功，不改冻结core。轻量错误路径测试即可。

## 6. 必要的定向CPU/fake验收（禁止转成真实预跑）

只覆盖本次受影响路径，以下每项针对具体错误；不全库/多平台/发布级测试，不真实模型/仿真。

1. 合成HDF/JSON：三池计数/父组及split、raw/fresh同父约束、raw同一观测行、旋转/归一化恰一次、prefix边界（短轨迹含1）、输入不带状态/mask/未来/评测值。防泄漏、train/dev污染和观测误配。
2. tiny CPU模型：注入前原base输出＝旁路LoRA参考，改变LoRA不改变参考但改变学生；参考无梯度、学生LoRA有梯度、冻结base无梯度；异常路径逐module flags恢复；参考后学生checkpointing梯度正确；保存加载后默认启用LoRA。防错teacher、反传模式污染和评测实际上跑原模型。
3. 三池12/4/4、2prefix/2全轨迹、有不同ten尾长的池归一化梯度、固定seed与dev及9024调用硬上限。防loss权重失真、超预算；无需耗时全训练。
4. fake训练几步→036保存→严格加载→fake正式队列180个新单元/最终正式报告/百分比日志；混合旧/新bridge双向切换，旧035工件仍可读，新模型不得复用035模型结果。防已发生的部署/schema/代理/继承错误。
5. spy原reader调用次数：逐单元不全量重扫、最终一次完整检查（内部两条件各自reader允许）；故意损坏/缺失证据仍报技术错误。假close警告保留且不掩盖完整结果，未完成不能标completed。防长时间无日志和假分数。

依赖已有fake fixtures，能证明同一故障的测试不重复；不为偏好提出新门槛。CPU/fake通过仅说明软件，不声称9024真实参考已算、1000训练或180评测成功。

## 7. 交付清单及下一步操作和执行者

X提交新036 PR，在`collaboration/responses/036_round1.md`给出固定commit、改动/CLI与配置样例、三池/损失/参考上下文/新adapter加载/评测reader次数的实现位置和定向测试结果、未覆盖限制。列清035依赖；不把旧日志open事项伪称已闭环。不先再交长方案，不发真实作业命令替用户启动。

Codex随后只审明确错误/关键缺失/泄漏/危险控制/证据失配，其余建议不阻断；将新代码、来源索引和配置部署独立目录，给用户常见`source`/`conda activate`/`python`完整训练命令。真实训练参考与评测均用户启动；训练结果回来后给固定末1000的正式180命令。当前训练/新模型评测0%，新增仿真0，未授权Codex/X代跑。
