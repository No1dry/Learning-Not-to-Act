# 030 v2 R2｜真实proprio白名单＋可执行PROGRESS生产入口

2026-11-03。状态open。X在PR9上增量交付；无需重交训练/adapter/评测主体或另开纯方案审阅。依据[首轮裁决](../reviews/030_v2_round1.md)。只针对会阻止本轮真实数据与开训的两个缺口，不扩大科研范围。

## 1. 修真实字段误拒绝（P1，必须）

当前`data._field`对子串`state`一律拒绝，但实际官方HDF有：`obs/ee_pos [T,3]`、`obs/ee_ori [T,3]`、`obs/ee_states [T,6]`、`obs/gripper_states [T,2]`。8维proprio的3+3+2或6+2都需要合法的`gripper_states`。

按角色精确允许真正机器人传感字段或等价规则；继续拒绝世界`states`、`robot_states`/物体状态、predicate/contact/reward/success/future等被当作策略输入。不要因为名字包含state误拒合法传感值，也不要反向放开所有state。保留显式proprio顺序、dim8、动作dim7/normalization/偏移与输入白名单；不修改真实HDF来绕校验。

合成测试使用真实命名与shape，验证两种合法proprio组合可导出/读取，隐藏全状态与物体字段仍拒绝，模型item仍只有原RGB/proprio/指令/动作目标/mask。

## 2. 补实际PROGRESS证据路径，不把空接口当成已交生产能力

当前可填外部插件但无已交可运行producer，旧200 base来源也不能生成增强。交付一个真实可调用、仍由用户启动的普通演示离线进度producer/适配器；优先复用已验收恢复、历史XML/名称、图像对应及原native谓词组件，依赖固定版本/路径明确，不自动merge旧PR。

最小完整行为：

1. 接受已绑定普通demo manifest、原状态字段/明确状态—观测时序依据、固定九任务目标、显式局部锚点/窗口与依赖配置。CLI/同次export配置必须有实际实现，不留`<your_recover.py>`作为唯一生产路径。
2. 锚点选择与成败无关，可用事先固定的稀疏步幅和候选局部窗口；输出计划锚点/预计恢复数，不自动执行真实恢复。不要遍历全量200/380来源的全部帧、重做旧全景视觉标注或准备新benchmark状态。
3. 仅在用户启动时执行必要的局部恢复/原图对应核验/原生目标读取；复用现成对齐证据。只有对应可靠的当前锚点才输出pending-goals；不通过/歧义继续记录诊断且不生成该增强锚点，不清零状态/放宽对应规则凑量。不把终局作为FINISH/停车监督。
4. 可新增`progress_anchors`或等价索引：当前`t`与可信pending-goals。一个锚点只证明该时刻，不凭两端一致插值整阶段。PROGRESS输入完整指令，目标仍是该时刻起原专家chunk8（episode尾mask）；chunk允许跨后续阶段，因为完整指令请求全部目标。不要把单锚点复制为未经核验的一长段阶段标签。
5. 保存source/file SHA、原state/obs/action时序绑定、锚点、native事实/对应证据及排除原因；这些都只用于离线监督/采样，不能进入训练item/策略prompt或eval停止决策。
6. **不要求此轮自动生产ATOMIC**。没有经核验的整段动作归属，就保持该池空，按030既定RAW回退并报告实际比例；也不要求九项都有完美覆盖才开训。保留现有可信人工/程序原子段输入支持，不能用一次目标变化伪造exclusive_goal_actions。
7. 新增fake backend/已绑定可信锚点的CPU路径，证明同一个export能产生非空训练PROGRESS索引、保持旧split、端点/动作mask/字段不泄漏。X不运行真实仿真、读真实轨迹做标注、下载新增数据或加载7B。

若现有已交付组件就能完成第2项，提供固定依赖、可运行适配代码/完整配置及fake集成即可；不强制某种文件组织或另建标签框架。缺实际数据不是这项软件能力的替代，也不能仅添加更多provenance布尔值。

## 交付与边界

在PR9提交增量，回复`collaboration/responses/030_v2_round2.md`给commit、两项受影响CPU/fake结果、真实入口配置和普通conda/python命令。只跑相关测试，不复跑全库/旧物理回放，不改物理评分、原模型/归一化、旧数据或033状态。

新增数据/下载、真实局部恢复、两次1000-update训练与A90+C36预算仍待用户确认。Codex负责绑定实际文件/路径与部署，不让用户手填200条记录或反复跑预检。034单独验收，不因本任务返修；其余已交主体保持。
