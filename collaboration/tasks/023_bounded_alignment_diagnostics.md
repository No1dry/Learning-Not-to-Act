# 023：两条固定旧来源的对齐失败诊断，不改标签或阈值

状态：accepted/closed（软件范围），见[023第二轮裁决](../reviews/023_round2.md)；下一步由用户启动两来源诊断。2026-10-24，Codex交X。仅实现定位本轮已暴露错误所必需的诊断入口与定向CPU/fake测试；真实恢复/渲染仍由用户启动。

## 问题已定位到什么程度

022原200来源/3200查询均处理完，无来源运行错误；仅165查询有状态监督（5.16%），全部在train，dev为0。2990查询（93.44%）因alignment_unresolved屏蔽，另144查询因可见/原生证书不足产生gap。**不是VLA/selector效果，也不是现有低覆盖率可支持的模型结论。**

200来源的原对齐裁决分布：

| 类别 | 来源数 | 占全部来源 |
|---|---:|---:|
| 唯一next_state通过，获接受 | 14 | 7.0% |
| next_state和replay_action在固定probe均通过，但完整等价认证失败 | 81 | 40.5% |
| same_state/next_state/replay_action三个都通过，歧义 | 3 | 1.5% |
| 当前阈值下无候选通过 | 102 | 51.0% |

81条中均有完整状态残差超过1e-6；其中21条在额外帧还有RGB检查失败，所以不能笼统说“只因状态误差”或直接全部放行。全部100条Object来源属于无候选通过；其agentview的next_state残差明显高于wrist，且部分是稳定偏差。尚不知是渲染/资产光度差异、几何不匹配还是其他原因。不能提高0.03阈值凑覆盖率，也不能直接钦定next_state。

[已有测量与固定案例](023_alignment_evidence.json)来自完成作业audit，只读分析，没有新恢复/渲染。旧manifest identity：`318c572532ac3f489d6da59e51039466579664501c69bed1fa113be3345549b4`；实现fb7399b4，代码字节identity见JSON。原标注结果完整保留。

## 交付一个独立、可直接运行的诊断入口

最简脚本或CLI均可；不要求新增通用框架/前端/完整报告工具。输入为**已完成作业manifest**及新输出目录，复用其inventory、requests、backend-config、image bindings和原有状态/动作。允许ready=false作为诊断输入，不能要求先export或训练。

本次配置严格固定两来源、各三个**已经测过且已请求的probe**，不按任务成功与否换来源：

| 来源 | 原probe帧 |
|---|---|
| `libero_goal/open_the_middle_drawer_of_the_cabinet_demo.hdf5#demo_0` | 0,66,129 |
| `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5#demo_0` | 0,72,139 |

这两条都是原train来源。只为分别解释“两个候选画面均通过但状态不等价”和“Object无候选通过”两类失败；不能据两条案例宣称全部200来源已修复。

每个既有probe，对same_state、next_state、replay_action分别执行既有明确操作，保存以下**独立诊断侧车**：

1. 原RGB、按既有orientation对应的候选渲染RGB、差异图和前景mask，以及带source/frame/rule/camera标识的PNG对照。两原相机，无新视角；原图不得改写。差异图若放大需标明倍率。优先简单PNG，勿为此实现新网页。
2. 将现有合成残差拆开记录：whole-image MAE、现有object/hand foreground MAE、background MAE及像素数；保留旧max度量，按camera/rule/frame保存。可另记每通道平均偏差用于区分颜色偏移与几何错位，但**不得据此校正源RGB或自动换验收指标**。
3. next_state与replay的状态误差按真实API布局分组，至少区分time、qpos、qvel、act（实际不存在则明确说明），不能猜扁平数组分段。保留原完整max和状态hash。诊断需要知道差异是否落在位置、速度或其他量，而不是把混合单位的1e-6当作唯一解释。
4. 记录同一候选下的既有native目标原子布尔值/异常；仅供判断“物理状态不同是否导致监督语义不同”，**不生成训练标签/answer或导出数据**。未知不能用false或0替代，不把目标真值用于选择对齐候选。
5. 记录源/原始XML、实际重写XML、安装资产和camera/运行库身份的已有审计依据；不改相机/材质/灯光/控制器来拟合原图。重用现有身份/资产工具，不能改固定c6或原环境。

不调用完整label-sim的200来源循环，不自动接train/export/eval。原图/状态/动作的对应和下标必须仍是原绑定；next_state无下一帧时不得clamp，本次固定probe本来有下一帧。保持原metadata/BDDL/资产/模块锁和有界reset逻辑。只校验实际消费的绑定，不重扫3200图片或重建来源。

## 运行边界与可复核输出

- 最多2来源 × 3probe × 3候选 = 18次候选恢复，2相机=36组图像比较；动作重放最多6条已有动作，仍受原substep预算。RGB/segmentation直接渲染最多72次，初始化及原restore/refresh内部渲染另计并受原source timeout约束。无settle/hold、新动作、新episode或模型forward；无自动换样、重试扩容、阈值搜索。
- 使用固定完整c6参考core及现有worker环境；方法代码与诊断脚本隔离部署。实际诊断实现identity必须记录；输入旧manifest/code identity与当前诊断实现identity分开，不能为了读取旧证据把其hash改成新代码。
- 输出新目录，保留每步已完成记录、配置/输入身份、预算、成功或异常以及PNG索引。失败不能写成完整成功；不覆盖原audit/manifest/165条标注。native数组、谓词、mask和诊断图不进入selector样本、history、prompt或actor。
- 这是失败后的具体取证，作用是防止将真实几何不匹配误标为真值，或因无关完整状态差异丢掉本来可确定的监督；不是新的模型MVP，也不是例行GPU预检。当前不授权全量重跑或阈值/标签协议变化。

## 受影响CPU/fake与交付

只验证固定案例/帧/候选预算、下标和相机绑定、真实布局分组接口、残差拆分、产物身份/异常保留、无标签或后续任务、旧结果不改写。用合成RGB/临时文件/fake native，不跑全库或多平台，不自主读真实HDF或渲染。

X在 `collaboration/responses/023_round1.md` 交付最终remote SHA、定向测试、诊断入口与运行参数/保守预算、尚未验证项。不要提前实现“提高阈值、直接取next_state、放宽等价证书、整轨放行、重划dev或多候选共识标签”；这些要看诊断图和分组误差后由Codex再作版本化研究决策。

下一步操作和执行者：X实现/CPU-fake；Codex审查并部署、提供一次完整命令；用户启动两来源诊断；Codex看原图/重建图与结构化误差，再决定具体修正，随后才考虑全量补标或训练。


## 2026-10-24首轮审查补充：只修两处确定的生产入口错误

[023首轮审查](../reviews/023_round1.md)针对固定HEAD `9c0429d590f40bcef83570c85ced1ee0fc10b8dc` 提出两项needs-fix，53/53定向CPU/fake通过不代表生产输入通过；详细封存JSON证据见[这里](023_production_input_compatibility.json)。

1. `sim_diagnostics._historical_inputs` 不得锁死core目录basename为LIBERO-core-c6-reference。封存配置使用另一目录名，但同一固定c6 revision、allow_reference=true、文件hash正确。删掉目录名字面要求，保留版本及身份保护；勿改旧manifest、重命名/复制旧目录来绕过，也勿改成另一硬编码名字。补一个实际进入production分支的合法异名fixture，错误版本/标志仍拒绝。
2. `planned == sources` 不符合本批inventory：planned只有sample_id/source_id/file/episode/group_ids/task_group/ancestry_known七项计划身份；sources还有instruction/T/orientation/split等验证扩展。要求各自唯一，按这7项计划schema投影匹配，保留source与旧request/registry/PNG/T/split的完整其他绑定。把测试中planned_sources=deepcopy(sources)改为真实基础/扩展两种结构，补正确扩展通过及错file/episode/group/缺失重复计划拒绝的CPU负例。

这两项是直接导致原获准manifest无法开诊断的明确错误，不是偏好返修。其他范围不扩大：固定2来源3probe、18次恢复/6旧动作/36比较/72直接render、原数据/阈值/标签/划分、无模型都不变。X只小修和定向CPU/fake；Codex修后只读核对现有生产文本/选中绑定，再部署给用户命令；不得自行读真实HDF/恢复/渲染或启动实验。请在023_round2回复最终remote SHA及受影响测试，无须重新全库验证。
