# 035｜已批准：教师资格v2＋73来源恢复，直接实现

2026-11-03，Codex→X。用户已明确同意本修订与新增上限**73次普通重放＋438次10尝试**，仍由用户启动。**请直接实现＋受影响CPU/fake，无需先交一轮方案。** 这是002真实结果后的版本化研究需求，不重开R3已验收的解释器修复；以PR10@`eecd25f59c43757509b639ef0c8a995547499a16`为基础，保留venv路径修复，不改变旧v1解释。

## 0. 固定输入与目标

- [完整002分析](../../docs/research/2026-11-03_task035_generated002_filter_analysis.md)：180来源技术错误0，normal仅2条、10共6条，均dual_mugs/train，dev为空。
- 120条来源受table_drop未知影响，73条**仅此一项失败**，其末态完整任务/释放连续确认已通过、无已确认违规；73为53train/20dev，跨五任务。只恢复这73，不重新挑来源，不重跑全部180或基线。
- [精确候选与复用文件引用](035_teacher_v2_recovery_refs.json)：73个parent ID、原资格/metadata路径与SHA，旧8条合格数据及其HDF/audit/qualification/lineage/journal SHA均已绑定。引用是文件准备，不是新成功标签。
- 用户只批准新73普通重放＋438次10尝试；原一组1000更新7:3混训、同adapter10/00各90评测预算不变。Codex/X不能启动真实作业。

## 1. 教师资格v2：只改一个未知通道

1. 原v1行为保持，新增显式教师资格策略`table-drop-unknown-diagnostic-v2`（配置格式/字段可等价命名，需明确版本，不能全局悄改）。新策略把**table_drop未知**保留在diagnostics，不单独硬拒；不把原None写成False。
2. 所有**已确认违规仍拒绝，包括已确认table_drop**；wrong_grasp/wrong_placement未知仍拒绝。原完整任务终态、释放＋五观测连续确认、10的A保持/禁重抓/invariant/初态约束、H520、动作投影与桥接规则保持。
3. 不改benchmark core、正式计分器/阈值/原90状态/两基线；不增加释放尾动作、改变示范截断点、放松其他条件或新增模型。教师标签版本不作为策略输入。
4. v2输出资格/lineage/report显式记录策略版本及诊断事件；旧002资格、core事实与原失败不改。动作张量schema可沿用v1，**教师策略独立版本化并进入export身份**；无需复制训练器或改训练配方/LoRA/评测。

## 2. 恢复入口：原180清单验证后只执行73

提供一个具体可运行的file-only `plan`与用户启动`generate/recover`路径，API可自行安排；与旧v1入口兼容，给完整配置示例。

1. 读取原180 seed manifest并按原逻辑验证/分组，**然后**按附JSON的73个ID执行恢复。保留原parent_demo_id/source_group/split、原完整语言、控制器/统计/相机/目标绑定。不得把带缺口demo集合塞进natural-firstN校验，也不基于子集重新split。
2. 对候选核对原资格/metadata与已交摘要引用：legacy rejected、唯一失败core_violation_evidence_unknown、未知事件全为table_drop、无confirmed事件、确认streak≥5。引用不一致直接报告，不另选来源、降低门槛或从评测数据补充。
3. 73条未保存完整RGB HDF，必须新执行记录：沿用035正常重放→安全handoff→3起点/每起点最多2桥接→B控制目标跟踪。新RGB/动作对应T+1/T；实际资格由v2现场证据决定，不能把旧候选直接标作新成功。
4. 每个候选normal最多一次、每变体最多两次，失败照常记分母，未启动的尝试不冒充失败。所有实际控制步仍计H520，确认hold仍只证据、不进监督；保持原初始化/来源超时和解释器路径修复。
5. `plan`只读JSON/文件身份，不构造NativeSession、恢复/渲染或加载模型；`generate`只在用户调用时执行。不得在import、plan、安装或测试时偷跑真实预检。

## 3. 旧8条合格数据复用，不再模拟

1. 从绑定的002 `export/sources.json`精确读取8个source（2normal、6个10），及原180 parents。它们来自两个train父来源，与73候选不相交；不要重放它们，也不要声称它们是新73的产出。
2. 在新run中复制或硬链HDF及必要原资格/audit/lineage/journal文件，核对附引用SHA。引用均留在新run可归档范围内，不依靠逃逸data_root的symlink；重定位相对路径时原source ID、父组/划分、实际动作长度、映射/统计、资格事实和HDF bytes不变。
3. 保留原v1资格事实，显式记录reused_from_generated002，不能给这8条伪造“重新执行/v2新判”的来源。两条normal已严格v1合格，可与v2新合格样本合并；原数据集格式/whitelist与训练器尽量复用。
4. 合并导出只索引真实qualified样本；不因dev/任务不足改变split、复制train到dev、填造动作、回退原普通RAW或加入正式测试数据。新合格量不保证。

## 4. 保留新失败观测，避免再次因筛选调整重采

当前只为qualified写HDF，使73条不能纯文件恢复。v2对**已实际完成并保存的对齐前缀**也保留RGB/proprio/actions/states（T+1/T），即使rejected；资格仍false，导出不收录。未完成的末动作、初始化无帧等只留真实审计，不伪造完整转换或观察。失败文件不能进入训练池。旧002不改、不为补旧图像自主重放。

## 5. 报告、进度和预算分开

- 新物理预算固定：max_normal_replays=73、max_robot_starts=219、max_10_attempts=438，最多265720控制步（7×73×520），原初始化时间另计。旧8条是reused，不计新增物理attempts。
- 每个新来源处理结束至少输出完成/73和百分比、技术错误、新normal/10合格数；复用数量单列。最后明确输出train/dev两个域窗口/父来源统计与`training_ready`（只判断原四池非空，不加载模型）。处理100%不是成功率。
- 独立报告：原180来源数量；固定恢复73来源/53train20dev；旧复用8轨迹/2父来源；新实际尝试与合格/失败原因；各task/split/domain数据覆盖；最终混合池。不要用1080/438上限当实际分母，不把6变体当6独立示范。
- `training_ready=false`不触发自动补跑、重分组或训练。旧训练1000更新/7:3损失与正式评分不改；模型仍只接RGB/proprio/完整指令，所有真值/恢复列表/策略版本为离线元数据。

## 6. 精简CPU/fake和交付

只覆盖受影响路径，复用R1/R3既有证据：

1. v1/v2资格分流；仅table_drop未知可留诊断，确认事件/其他关键未知/完成释放/A保护失败仍拒；原None不变。
2. 原180先分组再子集，73精确ID和旧8复用不可扩大/重叠/改split；引用错误拒绝，不回退。
3. fake生成＋复用导出，新增/复用预算与计数正确；rejected HDF保存对齐前缀但不进入训练，init无帧/末动作未完成不造T+1。
4. 保留R3的8项受影响CLI回归（含真实symlink支持机器），无需重跑全库、训练/评测大组，不运行真实仿真、渲染、模型或GPU。

交PR10增量或独立PR，回复`collaboration/responses/035_teacher_v2_round1.md`，列HEAD、字段/API、配置/完整普通命令、上述精简测试和示例新/复用报告。Codex一次建议式审查、隔离部署、准备真实refs/config后给用户新输出`generated-003`命令；**由用户启动**。不自动merge，不热改当前目录，不覆盖001/002、不重下9个HDF、不追加来源/训练/评测或真实probe。原评测实时SR小增量非阻断，不必等它。
