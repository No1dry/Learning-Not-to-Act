# Task038：实现037-v2语义保持/控制重算（直接代码，不再泛审）

2026-11-06，Codex→X。037首轮审阅已accepted/closed，保留PR12原文/署名，不要求返修；**本工单是新功能实现，不是再次写研究综述。**

## 决定与交付

按[037-v2完整规格](../../docs/research/2026-11-06_task037_v2_task_control_factorization.md)实现C0/C1两组；[实际记录配对证据](../evidence/037_recorded_pair_state_inspection.json)及[字段样本](../evidence/037_existing_metadata_samples.json)已在库。先读本页与规格，遇到明确数学/接线矛盾一次集中指出，通常实现选择可自主处理并披露，不为偏好反复返修。

**允许：改方法库代码、定向CPU/fake、GitHub新PR与一次responses/038_round1.md。禁止：加载真实模型/教师、读取图像做特征/推理、生成真实新标签sidecar、真实仿真/数据生成/训练/eval、服务器作业、自动merge。** 两组各1000/参考18048/模型360只是预算提案，待用户批准；实现不自动授予运行权限。纯现成JSON只读定位字段可做，不重做物理资格。

当前main为文档主线；实现接在已验收036 PR11固定`205d6530e1ba389f74166a2e9520a3db7ae0edbf`（实现`8b9399a940b45db7e3089aaad9f25c6509fd7c5a`）之上，main尚未合入时显式声明依赖，不丢弃那套双bridge/proxy与原报告，不自动merge依赖PR。

## A. 代码路径和合同

建议新包`egrs/task_control/`，新schema/recipe，不热改已部署035/036目录。共享OFT特征/动作函数的必要提取允许，但旧分支行为/身份合同不变，不为新功能把所有旧严格校验放宽。新CLI至少含`index`、`train --arm c0|c1`、`eval --arm c0|c1`，不必复制整个旧引擎。

**输入白名单**只有`images[2], instruction, proprio[8]`；动作、事实、完成计数、mask名、task_id/source_id、配对信息和时间不进入模型/提示词。不能靠task_id决定跳A/执行B。完整原指令、不换子指令；无外部VLM、FINISH、GT gate、第二VLA。

共享实现一次前向返回`H_a[1,56,d]`、prefix-derived `z[1,128]`及动作。z输入为实际图像prefix和原指令prefix的均值拼接，MLP隐藏256；动作残差瓶颈256，公式/初始化按规格第2节。计数head仅辅助标签0/1/2，推理不作路由；同类双壶不分配隐含sim实体槽。原固定action head读残差后H，8×7归一化、原resize/相机方向/proprio/反归一化/夹爪转换全部保持。

**明确修复旧接线风险**：旧`training_prediction`可参考，但不能只改它、eval继续`base.predict`绕过新模块。训练与eval的当前帧forward/hidden选择必须共享；BOS→图像/proprio插入→原文本→动作占位的实际映射必须精确。排除padding/占位，future action不进特征。prefix隐藏已受proprio影响，文档不宣称架构层严格独立。

注册所有新增模块、optimizer收齐新LoRA和新模块；base/vision/projector/head冻结但不切断输入梯度。只zero `W_out`，不能把整条F全zero。identity列新全部tensor及SHA、arm/配方、base/原统计、数据/pair索引与固定末1000；strict恢复缺/多/错形都报错，不能静默忽略新模块。保存新模块与LoRA、完整优化器/RNG/调度器/三个池与pair sampler/预算计数，恢复不换arm或重置计数。

## B. 一次文件索引，不再生成仿真数据

复用服务器原路径（部署根相对配置，不写口令）：

- `$ROOT/data/trajectory035/generated-003/export`及其source所指audit/lineage/HDF。
- `$ROOT/data/retention036/index-001`三池、行与原180父组split；train ten161/fresh55/raw136，dev60/20/44；原10增强只覆盖六任务。

新`index`输出不可覆盖旧003/036：`labels.jsonl`、`pairs.jsonl`、`report.json`＋来源身份。只读取现成文件；不导入/实例化环境、不读eval run/正式测试状态。HDF原动作/观测只按原loader使用，T+1/T和pad mask保持，confirmation_frames不导出。

标签从active goals计数，不套official前两项；raw不补谓词、不重放。缺失标签mask并计数；这是训练监督缺失，不是把benchmark的二元结果改成UNKNOWN。两组共用同标签/源、图像和采样清单。每条pair保留两个row/source引用、handoff/0索引、两端独立有效动作mask、split与原audit/lineage摘要。

有效pair规则按规格第3节：**实际记录**非机器人状态（原rewind modified_indices、排除time0）差≤1e-8；构造hash/goal相同不足以代替。检查同父/split/语义/原合格来源、hand-open/free/release及至少一个robot坐标变化。不要用“所有任务的前九关节”猜layout。该检查防错误交叉监督，不重新物理回放/改旧资格。无效pair不移除原动作源，不加真值输入。全量pair数尚未知，报告真实覆盖；零有效pair报明确不可用，不自动降级标准/补数据。

## C. 两组固定训练，避免隐含额外预算

保持036主损失/三池12+4+4、.50/.25/.25、普通前1/3与all各半、原策略参考旁路方式；每更新额外1pair的2观测，task→parent→variant分层。固定同seed7、同索引与抽样清单；两组从原SOG10新LoRA开始，不加载035/036成品继续。

按规格第4节准确实现：C0为`main+.1 count+.1 self`；C1为`main+.1 count+.1(.5 self+.5 swap)+.01 align`。每端动作监督用自身真实动作，不对齐两端动作；swap只换z，接收端H/p/target/mask不变。两组相同22学生观测/更新，不偷偷C1加数据；cross只复用缓存前向，不多跑7B。pair两个图需要共同计算再backward，不能把一侧z无意detach；可分开编码/梯度检查点，不能为省显存偷变成teacher-student方法。

计数CE对有标签的已有观测（包括pair）按出现类均值，不能用future completion/frame index充标签。L_align按128维归一化后均方，epsilon1e-6，不混用L1理论界。

所有原策略参考先于学生图计算，必须同时旁路新LoRA、z/残差及其hook，模式/检查点/逐模块training状态恢复正确；不能引用改造后的学生当原策略。参考每组train8000/dev≤1024，共≤9024；两组≤18048。新model仍单个7B，eval无reference。

固定每组1000、lr2e-5/warmup50、bf16、250保存/验证、末1000，不增加续训/挑checkpoint。dev复用≤512普通观测/次＋确定性≤64pairs/次；学生总≤24560/组，两组≤49120，reference单列。日志逐update百分比、各pool/count/self/swap/align、已有dev计数分组/paired诊断、耗时和ETA、显存；SR只在真正eval产生，不把loss打印成SR。允许缓存H/z做z置零的head-only诊断，无新VLA前向；诊断不改变模型控制动作。

## D. eval与定向CPU/fake验收

继续九任务原10二元合规/00官方各90，原H520/chunk8/seed7/原初态及评分/双bridge-dispatch/proxy/原reader，全视频；两arm各新180，不能继承旧模型分数。共享同新predict路径，当前帧自己算z，没有pair/标签输入。不把037研究代码放纯Eval benchmark库。

只做能防这次真实错误的受影响测试：

1. T+1/T与handoff动作、padding/confirmation排除、active/official顺序、跨父split拒绝——防监督错位/泄漏。
2. 记录非robot状态确实相等/变化的正反例及实际layout——防伪配对，不做新物理预检。
3. BOS/图像/proprio/文本/动作prefix布局、输出8×7、无GT输入——防输入错误。
4. 同一合成当前帧训练/eval共享路径结果、单backbone调用、swap只换z——防eval绕过和动作错标。
5. 零初始化等价、非zero初始化支路；backward能到全部期望新模块/LoRA、冻结模块无梯度——防假训练。允许首步W_out之外梯度为零，另用非零W_out验证完整路径。
6. 原策略reference旁路**全部**新增模块且逐模块模式恢复、计数含resume不超——防学生伪装teacher/超预算。
7. 新模块/LoRA保存strict恢复、C0/C1同采样及预算、恢复不中断顺序——防评错权重/不公平比较。
8. fake九任务180/两arm360计划、二元/官方指标和新adapter路径、保留旧run——防错分数/覆盖。

不要求全库、多平台、发布级校验、真实GPU/模型/仿真/MVP；未经运行项写清未运行，不冒称通过。

## E. 一次交付

新PR包含代码/配置/这些CPU-fake结果、README式完整`source conda.sh; conda activate; python -m ...`命令模板。`responses/038_round1.md`简明写实现commit、与规格必要偏差、测试结果、部署需用文件及未执行真实作业。原037新颖性仍待研究，不需又写长综述；本轮若遇明确不可实施错误集中反馈，不擅自换算法/扩预算。

Codex审查、隔离部署与文件准备；用户确认预算并启动真实index/两组训练及360评测。未经预算批准不给已可启动的实际实验指令，不自动启动/停止作业。所有035/036原分数/权重/视频与旧037文档/PR12保留，无删除清单。
