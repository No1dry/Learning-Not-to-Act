> 后续裁决：用户改为“你直接完成吧”。Codex已直接实现并部署PR22@bd871dea，X无需重复实现/泛审；3000真实评测仍待用户启动。预算及原官方pipeline约定不变。以047_codex_round1、2026-11-18_task047_codex_implemented_deployed及本轮运行文档为准，下方待X为历史。

# 047 工单：直接复用官方OFT流程，三任务集×50条×两模型

状态：用户已批准完整3000条预算，X直接实现最小接线；不先泛审、MVP或额外真实验证。方法仓库 `No1dry/Learning-Not-to-Act`，不修改benchmark/Eval库。

## 1. 用户决定与研究目标

用户原话：“直接拿openvla-oft源码的那套evalution pipeline代码行吗，反正原版模型是可以的，以及直接测3x10x50x2，一步到位。”

测针对九任务10微调后，原有Spatial/Object/Goal能力的保持或退化。不是新Remain任务或严格zero-shot，也不是原版各套单独训练的checkpoint。仅新增正式评测，不训练或生成数据。

| 任务集 | 任务数 | 每任务初态 | 每模型episode | 官方控制步数上限 |
|---|---:|---:|---:|---:|
| libero_spatial | 10 | 50 | 500 | 220 |
| libero_object | 10 | 50 | 500 | 280 |
| libero_goal | 10 | 50 | 500 | 300 |

两模型各1500，共3000。固定seed7、官方task order0、每任务默认初态index0..49、env.seed(0)、先等待10步、chunk8、center_crop=True、两视角/proprio、原始任务语言；其他配置沿固定官方源码。默认初态在各模型之间必须对应，不换状态、不筛选、不用我们的九任务bank。

## 2. 固定模型和源码

- base：官方四套联合 `moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10`，revision `638918f3d1c2e43a39a8a20772bdb8b91835e4b7`，**无我们的adapter**。
- h1：同一官方底座＋045 H1@3000，adapter SHA256 `78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d`。不是042/044原版或其他H1快照，不重训、不合并改写旧权重。
- OFT固定 `e4287e94541f459edc4feabc4e181f537cd569a8`。runner为 `experiments/robot/libero/run_libero_eval.py`，SHA `701a20b6ca2942aa36e0e7d567b25647268b936a23af79c5893534f10bec7802`；libero_utils SHA `489c16dc8220845b2936ddb81aafd7469061d2009b0edddb2f85703bc51a204f`。官方源码链接见方案与reference_bindings。
- 方法实现建议基于已接受PR20固定 `10531b626998d02f6168d23df02501ce64d36969`（含原043＋045完整读权重路径）。PR21@a1179099只加046提示实验，不是必须依赖。都不自动merge。

## 3. 真正复用官方pipeline，不重写另一套

新建很薄的版本化047入口，调用固定官方 `eval_libero`（或其装饰前主体）、`run_task`、`run_episode`。可以在本进程对 `initialize_model` 做可恢复包装：先调用原函数，h1时再且仅再加载一次研究LoRA；base直接返回原初始化结果。入口/装饰器调用方式由CPU/fake测试确认，不用真实首条来试接口。

以下都用原函数：环境建立、官方初态、图像方向和resize/crop、语言包装/tokenizer、proprio、get_action、动作队列/夹爪后处理、env.step及done成功判断、原视频生成。不得接Remain评分器、headless reader、FINISH、状态谓词保护、错抓规则、P1/P2提示、VLM/selector、任务控制/注意力firewall或训练辅助分支。不重写物理、成功判据或另立合规标准。

允许的额外代码仅为：读入047配置、固定身份与LoRA加载、六进程串行启动/输出隔离、旁路观测日志与机器可读汇总。观察包装必须调用原函数并原样返回，不能改轨迹/成功bool；原文件保持字节不变。临时替换在finally恢复，不能热改全局安装包。

### 3.1 H1加载的关键：训练身份与推理归一化分开

H1是我们自己的 `LoRALinear` checkpoint，不是可随便用PEFT加载的标准adapter。按既有实现保持每层q/k/v/o、rank16/alpha32/dropout0、float32 A/B、原增量公式；官方cfg.lora_rank仍32，不因研究adapter的rank16改成16。底座官方LoRA已合并，不能再重复加载官方adapter。原action_head/proprio_projector保持不变。

旧 `hint043.adapter.restore` 要求完整 `_lineage(policy)` 与训练记录相等，其中包含 `libero_10_no_noops` 与其统计摘要。新三套正确的推理统计不同，**不应直接删掉旧断言、伪造metadata，或用10归一化绕过**。

实现047独立且显式的跨套加载：

1. 原identity仍用既有结构校验，固定h1/update3000/final3000和adapter字节SHA；旧identity/PT文件不改。
2. 同底座repo/revision、原OFT源码、原action/proprio组件、完整dataset_statistics字节SHA `6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3`严格匹配。原7B大文件沿已验收缓存来源，不要求重复全量哈希作为新门槛。
3. 从实际原模型统计表中，另核验训练用10统计与identity里的摘要一致；训练norm key/digest仍原样保存为训练来源。
4. 当前推理norm key由官方 `check_unnorm_key` 按当前suite选择，并实际记录该key和统计摘要；优先/回退规则完全跟随原函数，不能固定10、不把推理记录伪装为训练记录。
5. 再安装原LoRALinear并按既有严格语义复制原tensor：目标完整、名字/shape/dtype/有限性、逐tensor摘要及整文件SHA均匹配。新代码可复用既有纯校验/安装助手，但不要调用一个必因suite差异拒绝的旧restore后再吞异常；也不要放宽旧043/045验证器。
6. 只加载模型与adapter，不读取完整training_state/optimizer/教师；模型eval/no_grad。注入临时随机初始化不应改变后续评测的RNG状态，两模型使用同一seed设置。

### 3.2 本地权重保护与独立输出

官方get_vla会同步本地config/code，原视频目录也相对cwd。部署时沿已接受的小元数据隔离视图思路保护原checkpoint，权重只读；正确装配源码搜索cwd/PYTHONPATH，不改官方源码或旧目录。六个cell分别隔离cwd/log/rollouts，视频不覆盖、不仅靠秒级时间戳避免撞名。允许路径层输出适配，不改像素、帧率、success或任务名语义。

## 4. 一条串行命令与正式产物

固定六个独立进程，建议顺序 base-spatial→h1-spatial→base-object→h1-object→base-goal→h1-goal；每个进程只加载一次模型跑500条。单GPU不并行抢显存，不新增诊断前向。原版流程与H1同样调用官方入口，不拿论文数字代替现场对照。

用户只运行一次新脚本，正常完成一个cell后自动下一个；不要求手工每套切命令或等待额外批准。不以SR高低决定是否继续。独占新输出/持久marker；遇技术异常保留并停止后续，不自动重试、删失败、换初态或退款重开。普通模型失败正常计False。官方run_episode会捕获部分异常，需旁路记录它的Episode error，不能仅看shell退出0就冒称500条有效模型结果；技术故障须单列软件错误/不完整，不伪造正式满额SR。不要改变有效任务的done评分。

保留官方原日志和全3000段视频；新增轻量 `episodes.jsonl`（suite、原task id/name/instruction、init index、model/adapter身份、官方success bool、技术状态、视频定位）及各cell `summary.json`。不要求另存海量逐动作raw/图像或新标签。

实时控制台需简洁显示：当前cell、当前task、cell与总3000进度百分比、已完成样本的实时SR；注明live。最后只在六cell完整且无技术问题后给 `comparison.md/json`：30任务、三suite、三suite总体的base/H1 SR和差值；可以保留同初态配对得失作诊断，不新立主metric。各模型总体分母1500，三suite等大所以macro=micro。

不把旧九任务00/10混入这里形成“官方四套AVG”；它们人群/条数/评分不同。048或其他模型、其他seed、LIBERO-90/10、提示词试验均不在本预算。

## 5. 预算、分工与验收

用户已明确批准3000正式episode：每cell500、每模型1500。由原horizon/chunk推导自然预测上限：spatial每cell14000、object17500、goal19000，两模型合计101000次动作块请求；这是执行边界，不要求引入新预算平台。模型加载/状态等待不额外做真实MVP；新增训练、数据/标签/index、参考教师和首条资格重跑均0。

X只新047薄接线＋受影响CPU/fake＋PR与 `collaboration/responses/047_round1.md`，不SSH/真实模型/仿真。CPU/fake覆盖：官方函数委托/base路径不注入、H1恰好一次/固定字节tensor、跨suite正确统计且训练identity不变、同50初态与原成功bool/视频路径、六cell顺序/500×6/错误停及不覆盖、汇总与实时百分比。使用AST或stub原模块，不能复刻一套runner当fake再宣称官方路径验证。不要跑全库/重复历史测试或以偏好重构拖延。

交付六个实际配置模板（base/h1×三suite）、一条串行脚本/常用conda+python示例、必要的软件依赖说明。服务器私有路径由Codex部署填入，不能为找路径让X上SSH；真实资产/效果通过用户的正常正式作业确认，不额外GPU预检。

Codex按明确错误/泄漏/关键功能缺失审查，验收后隔离部署与给完整命令；用户亲自启动全部真实作业。X无需先泛审或修改benchmark/旧模型/分数，未授权Codex代启实验。实现/部署/真实评测当前0，规格交接100%。
