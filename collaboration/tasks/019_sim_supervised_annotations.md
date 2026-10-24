# 019：现有轨迹的仿真监督标注与训练数据导出

状态：accepted/closed（019软件范围，2026-10-24），见[裁决](../reviews/019_round1.md)。固定实现b38526d5已隔离部署，156/156独立CPU/fake通过；真实标注由用户启动。2026-10-24用户明确选择“改用仿真监督标注”。X实现及CPU/fake测试；Codex审查、部署、命令与结果核查；用户亲自启动真实状态恢复/必要渲染/标签生成和后续训练。不是重新修018解析，也不改变③选择器＋④可撤销历史、冻结VLA的路线。

## 1. 固定范围与实际动因

复用当前20任务、200来源、160 train / 40 dev、1200窗口/3200查询及20条/21目标文本规格。固定来源HF revision `147fa5eb607bb696dd922c3518084a90954cd2f3`。inventory identity `3f550e7736ba5428dad789a307e2c18b32f25ec51dcc763e1fb8e65db563bb33`；windows identity `bb453b047946179eb1ec68eb4c9ab884f9b2564b5173e849836a5caa56988cdd`；文本规格identity `ec058064453e996175bebfca449d427b240d762a08d33c01f383164dc16a8095`。

018代码`119cd50b`软件已验收。其候选实际调用1894，通过schema1072，但788条合法运输目标里783条SAT；12条针对性图像核查有起始碗仍在桌上却判SAT/HELD、证据框落机械臂等明确错误。不能靠枚举修补将这批结果直接升为真值。旧候选、失败及原输入保留，不覆盖或重新记分。完整依据见[本轮质量总结](../../docs/stage_summaries/2026-10-24_teacher_candidate_quality_review.md)。

不扩benchmark、不增加来源或重抽RGB、不训练FINISH、不改VLA/benchmark指标。标注侧可以读取仿真真值；模型的条件输入、记忆和执行策略不得读取它。

## 2. 入口、依赖与既有产物复用

在方法仓库增加独立离线标注入口（如`egrs.offline label-sim`），读原inventory/windows/文本规格与显式annotation backend配置，写新目录。另提供接入现有训练器的train/dev导出入口，可与标注分开，但不自动训练。原teacher不被调用，不把GPU教师诊断或重新下载模型设为前提。

优先复用现有可工作LIBERO运行环境/固定库版本。若selector环境与LIBERO依赖冲突，用配置指定独立标注worker解释器/库路径，不热改依赖或现有运行树，不把服务器路径/凭证写进仓库。控制器/worker只传操作性记录，不启动VLA/selector forward。真实标注可能需要必要的仿真渲染，不宣称零GPU成本；操作数量和配置启动前说明，由用户启动。

先读取本批HDF实际字段/attrs，明确states、actions、model XML、env/BDDL是否具备。不得依据当前官方master直接假定本批完全同格式；缺失字段明确报告，不换demo_10、不用official init文件猜配演示。

## 3. 状态—图像对齐是唯一必要的新增物理对应核对

严格使用本window记录的source/episode/frame和原方向约定，不改采样点、RGB、顺序或分组。官方生成脚本存在“执行action后保存RGB、再按valid_index切states”的顺序，可能存在前/后动作索引差异；**不能默认states[i]对应RGB[i]，也不能无依据统一移一帧**。

按实际producer/元信息与恢复后的可见对照确定对齐规则；必要时使用已有action得到对应后状态，记录采用的规则、依据、版本和边界帧处理。可在实际标注作业内用少量固定帧检查对应关系后继续，不新增独立GPU最小验证/全库物理检查。若无法确定对应关系，该来源/字段记gap，不伪造通过或按模型成败选规则。不要通过改变原图去“对齐”；必要渲染只供标签/对应检查，不能替代模型原RGB输入。

参考：[官方生成脚本](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/scripts/create_dataset.py)。该页面是实现线索，不是本批已验证的producer声明。

## 4. 逐子目标真值与可观察标注

用原任务BDDL/实际环境的原生原子谓词及对象状态映射，建立20指令→21个固定goal_ref的显式映射，记录依据。尤其：
- 复合开抽屉/放碗分别评估Open与放入谓词，不能把全任务success/done广播到两个goal。
- 运输SAT指目标确在要求的区域/容器/支撑物；仅识别物体、靠近或抓起不算SAT。push plate to front of stove必须用实际目标区域，不猜成plate on stove。
- 不把最后帧置1的rewards/dones作为各子目标标注，也不按“演示结尾必成功”造标签。
- 身份由标注侧实例对应确定；输出使用稳定、合法的传感实体引用，不能把MuJoCo名字/数值ID喂进条件输入。目标/目的地与goal_ref不混用。

真值正确不等于可观察。使用必要的目标/目的地/机构活动部件可见性或分割证据；目标不可见、关系缺乏观测支撑或抓持不确定时，输出UNKNOWN并按明确规则mask，不用隐藏SAT/UNSAT强行监督。只有看见固定柜体不自动证明抽屉开合可观察；有接触或指爪合拢也不自动等于持有。抓持可复用可靠已有检查，规则/阈值和不确定情况明确记录，不以新增复杂物理认证体系拖延。

沿用现有wire语义/校验，至少：
| 字段 | 标注要求 |
|---|---|
| relation | 对应本goal原子谓词；可观察才监督SAT/UNSAT，否则UNKNOWN/不监督 |
| interaction | 可观察且有可靠抓持依据才HELD/NOT_HELD，不确定UNKNOWN |
| release | 运输不得NOT_APPLICABLE；HELD不得同时标当前已释放。明确保守释放定义与依据，无证据UNKNOWN；机构为NOT_APPLICABLE |
| role/association | 与本goal目标和可见实例匹配，未知不硬绑定；不能凭文字意图作可见证据 |
| evidence | 原RGB坐标中的真实目标/关系区域，normalized_xyxy；source/query/camera绑定准确，supports只写该区域真支持的字段 |

GT分割/投影框必须与**存储RGB的像素方向**对应；别将opengl惯例盲目翻转。可见bbox而非遮挡物体的完整几何投影框。关系证据需覆盖相关目标/目的地；不能用空桌面/机械臂框统一声称entity/role/relation/release/interaction都被证明。GT mask、深度、框画线和额外相机仅留标注侧，不画进模型输入，不新增模型视角。

[原生谓词参考](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/libero/libero/envs/predicates/base_predicates.py)。不修改benchmark的谓词或评分。

## 5. 监督来源、历史与训练接入必须真的可用

新增独立标注协议与来源（如`sim_supervised`），在answer字段级/evidence项级来源及训练mask中明确支持。现有`CONFIRMED={human,reviewed_candidate}`不能让新来源全部被静默mask，也不能为了兼容冒写human或捏造UI确认/耗时。保留旧来源语义；未知、未核验和不支持字段不自动升为可监督真值。

必须接通现有build_dataset/prepare_answer/encoder，输出可被现有训练器读取的train.jsonl/dev.jsonl、来源/字段覆盖报告。使用原fixed_source_splits、group_ids、ancestry_known与既有排除依据，不重新随机划分或宣称物理来源完全独立。原始窗口只读，新增答案/来源在新产物内。

**训练标签与输入严格分离**：真值只在answer/字段监督及独立审计侧使用；不能进入payload.sensor/context、prompt、条件历史、执行器或评测策略。不要为支持新标签来源而把oracle历史加入合法history_provenance。只能复用真实存在且合法的过去预测/可见证据历史；没有则留空并报告，不用前面GT答案伪造“模型历史”。物理真值侧车与模型样本分开，不把state数组/接触真值/实例表伪装成proprio或文本元数据。

保持学生训练/推理共享提示、原图像/长度预算与现有字段过滤/掩码规则；不借机更换模型或改方法架构。允许新增支持所需源类型，但不放宽输入白名单。

## 6. 输出、可监督性与进度

写新版本manifest/annotation JSONL及独立audit，记录原source/frame、state对齐规则、环境/模型XML/BDDL版本或hash、goal映射、可见性、来源与不能监督的原因。无需复制全部state数组。旧结果不改写，已有目录拒绝覆盖。

给出整体/逐任务、train/dev的“计划查询/有监督字段查询/gap/UNKNOWN及字段覆盖”，用于数据质量而非新benchmark metric；不能把全UNKNOWN或只创建文件称标注成功。保留自然类别分布，不按基线成败或为做出均衡/提升而挑来源。

长作业逐条保存，定期输出处理百分比与可监督记录数，确保用户能监督；阶段只生成/导出标签，不自动串行模型抽取/训练/评测。

## 7. 仅受影响CPU/fake测试与交付

至少覆盖：前/后动作索引与末帧边界；不确定对齐不假通过；两goal分别判定；隐藏真值不被监督为可观察事实；可见框方向及各引用正确；运输/机构release、持有/释放一致；新来源能产生真实监督token而旧weak仍mask；新来源不能进入oracle历史或prompt；固定划分不变、输出新目录和失败审计。用合成状态/掩码/worker，不实际加载本批HDF、恢复物理场景或启动渲染/模型。无需全库/多平台/发布级测试或额外GPU预检。

在本方法仓库交付019完整实现增量，附固定SHA、受影响CPU/fake结果、可配置运行说明及`collaboration/responses/019_round1.md`。明确真实字段/对齐/标签覆盖仍待用户启动验证，不以fake通过代替。标注worker环境要求与操作预算写清，Code review无明确错误尽量不反修。

下一步操作和执行者：X实现019并CPU/fake验证；Codex审查、隔离部署及完整命令；用户亲自启动实际标注生成。没有授权X/Codex自动恢复状态、渲染、运行模型或训练。
