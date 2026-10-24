# 方法研究当前状态

更新：2026-10-24。

## 当前决定

主路线已定：③独立实体/目标关系选择器＋④可撤销证据历史，冻结VLA，仅训练selector LoRA。通过稳定子目标语言驱动，不把bbox当空间动作约束。

## 任务

| 任务 | 状态 | 下一执行者 |
|---|---|---|
| [015设计审阅](tasks/015_remaining_goal_selector_design_review.md) | accepted/closed，仅设计审阅范围；[裁决](reviews/015_round1.md)；X原文见PR #1固定提交，PR未自动合并 | — |
| [016完整软件实现](tasks/016_egrs_full_implementation.md) | accepted/closed，软件范围；[最终裁决](reviews/016_round2.md)，PR #2未合并 | — |
| [017离线数据与人工确认](tasks/017_selector_data_pipeline.md) | accepted/closed，软件范围；[裁决](reviews/017_round1.md)；新版本已部署 | Codex权重搬运；用户启动真实阶段 |

设计与016软件验收均100%；本轮受影响30/30项CPU/fake通过（100%），其余23项复用首轮证据，不冒称全部重跑。固定代码上传与独立selector环境安装均100%，类导入/命令/core身份静态核对通过；不代表真实processor/CUDA/模型效果已验证。原始20文件搬运100%，017的59/59项CPU/fake通过且已隔离部署；真实来源/图像/标签构建、训练、新方法eval仍0%。[阶段总结](../docs/stage_summaries/2026-10-23_egrs_software_acceptance.md)。

## 授权边界

016/017软件范围已关闭，X当前无需返修。下一阶段是用户启动真实数据与候选流程，不新增MVP或无关软件检查。

未批准真实数据恢复、物理/教师标注、特征抽取、真实Qwen/VLA forward、训练或eval；这些仍由用户另行确认并启动。用户已接受VLM候选＋人工确认方式；55—80人时或900窗口全审不默认生效。固定20文件目录元信息约13.82 GB，不冒充200条来源已ready。无数据可完成软件，真实训练前必须另确认标签与资源。

## 后续

016无需继续返修；017已验收并部署；原始20文件搬运已全部完成，不再重复启动服务器下载脚本。Codex审查/部署后分别提供抽帧、候选、审核、训练命令。隔离部署已完成，旧VLA环境未修改；未启动真实作业。014在评测侧单列，不能在此复制评分；其尚未交付不阻塞方法本体与fake契约实现。

不自动merge、扩benchmark、加01/11模型评测或FINISH。原稿/失败/数据保留，不清理开放或未闭环事项。

## 原始文件搬运范围补充

2026-10-23网络例外：用户明确授权Codex本地下载固定20个原始文件，再经SSH传到服务器；仅做字节搬运和完整性校验，不含HDF5轨迹读取、抽帧、候选推理、训练或eval。 原始文件传输及SHA校验已100%完成；不据此宣称200来源或训练集已准备完成，其他真实阶段仍由用户启动。

## 017后续实际状态

017不再返修。20文件已于2026-10-23 12:17北京时间全部上传并校验（100%），但不等于200来源/训练集ready。用户已新增授权固定7B教师快照的本地下载与上传，仅文件搬运；本地下载已启动；SSH曾短暂拒绝连接，复查后已恢复认证，现逐文件校验上传中；不以文件数冒称模型缓存全量ready。真实inventory/候选/人工审核/训练仍由用户分别启动。见[017阶段总结](../docs/stage_summaries/2026-10-23_offline_pipeline_acceptance.md)。

## 2026-10-23文本规格标注更新（覆盖上文旧准备进度）

固定7B的16文件已全量传输/校验100%；用户已完成200来源inventory（160/40、无gap）与20次registry候选推理。原候选仅40%格式通过，原错误保留。用户随后取消本次20条文本规格的形式化逐条/整体确认，由Codex完成标注；20条/21目标已定稿并部署（100%），来源记录保留，不声称独立人工复核。此更新不改变视觉状态标签的核验要求。

当前下一步：**用户启动抽帧**；抽帧、视觉标签、训练及新方法eval尚未启动。Codex没有代启任何真实阶段，017无需返修。见[文本规格交接总结](../docs/stage_summaries/2026-10-23_registry_annotations_and_frame_handoff.md)与[定稿标注](../docs/annotations/2026-10-23_registry_annotations_v2.json)。旧候选、旧审核草稿均不删除或改写。

## 018实际阻塞：教师输出包装与schema（2026-10-23）

用户已完成抽帧（100%）：200来源、1200窗口、3200查询、无gap，原160/40来源分组不变。随后由用户启动视觉候选。一次已有输出快照为处理33.03%（1057条），实际调用397、跳过660，原解析有效候选0；CPU只读诊断去最外层代码块后JSON均可解析，但严格schema仍0通过。不能把处理百分比或格式包装问题当作任务成功率。

[018修复任务](tasks/018_teacher_wire_format_and_schema_alignment.md)现为open，X负责包装解析与字段提示对齐及受影响CPU/fake回归；只修代码块不够。016/017验收不重开，原图像/规格/分组不重建，旧输出和错误保留。Codex建议用户停止当前无有效产出的任务，但没有代停或重启。停止/继续及修复后真实推理仍由用户决定和启动；不自动进入训练，不伪造后续历史，不把全UNKNOWN或schema通过冒称标注质量正确。

## 2026-10-24：018已验收并部署（覆盖上文旧open状态）

[018](tasks/018_teacher_wire_format_and_schema_alignment.md)软件范围accepted/closed；[裁决](reviews/018_round1.md)，固定交付`119cd50bde04a53f41ddac47871d0f688276b146`。Codex独立55/55受影响CPU/fake通过（100%），新目录部署100%，未放宽契约、修改student prompt、环境依赖或旧数据，PR #2未自动merge。X当前无返修项。

用户下一步直接复用3200条已有查询启动新版视觉候选，不重抽帧、不重标文本规格、不另设GPU预检或CPU诊断门槛。新提示真实有效率尚未验证，不把UNKNOWN/格式成功当标注准确率。旧PID已不在运行，未由Codex停止；新推理/训练/eval仍未启动。见[阶段总结](../docs/stage_summaries/2026-10-24_teacher_wire_repair_acceptance.md)。

## 2026-10-24：新版视觉候选已结束，用户已确认仿真监督标注

用户启动的018候选生成已结束（100%处理）：3200条中1072通过schema（33.50%）、822失败（25.69%）、1306跳过（40.81%）；实际调用1894次，schema通过率56.60%。17/20任务有通过记录，但不等于视觉准确或训练监督已ready。12条针对性双视角抽查发现起始状态错判SAT、证据框落机械臂等明确问题，不能只修release后直接训练。

018软件验收保持accepted，暂不要求继续修解析。用户已确认改用已有仿真轨迹生成离线监督，来源、帧对应和可观察性有明确边界。正式[019工单](tasks/019_sim_supervised_annotations.md)已交接X；**尚未启动真实状态恢复、渲染、新教师、训练或eval**。原图/窗口/规格/分组和旧结果保留。见[本轮结果、图像核查与决策依据](../docs/stage_summaries/2026-10-24_teacher_candidate_quality_review.md)。

下一执行者：X实现019并CPU/fake验证；Codex审查部署；用户启动真实标注。018软件已闭环，不继续因模型标注质量反修解析；RGB、窗口、文本规格和160/40分组不重建。

## 2026-10-24：019软件已验收、配置部署完成

[019](tasks/019_sim_supervised_annotations.md)软件范围accepted/closed，固定实现`b38526d5`；[裁决](reviews/019_round1.md)。Codex独立156/156受影响CPU/fake通过（100%，5.66秒），28变更文件blob吻合；新目录源码/配置部署100%，X当前无需返修。复用原环境、core515e87d及原3200查询，不新增GPU预检或重建数据。

用户下一步启动真实label-sim。Codex/X尚未读取真实HDF、恢复状态、渲染、调用模型或训练；实际对应/覆盖待该作业验证。partial/UNKNOWN诚实保留，看processed与supervised比例；有可靠子集可导出，不以完美ready阻塞。见[阶段总结](../docs/stage_summaries/2026-10-24_sim_annotation_software_acceptance.md)。不自动merge或串行启动后续阶段。


## 2026-10-24：019真实标注已结束，元信息入口失败（最新状态）

用户已启动并完成首次019真实作业，但200/200来源均在读取缺失的 `bddl_file_content` 属性时失败；3200查询processed=0、supervised=0（均0%），最终ready=false、usable=false。尚未进入状态恢复或图像对齐，不将UNKNOWN占位误称对应失败或模型失败。manifest identity：`2cd2df5f78b7148b1f490f31c56ce5b55df6bad15c6131dc88172b756bc7b82d`。

019既有软件测试证据保留，但不能代表本批真实元信息兼容成功。[020明确兼容性修复](tasks/020_sim_source_metadata_compatibility.md)已交X，状态open：支持明确来源标识解析固定本地BDDL，诚实区分内嵌原件与安装版本解析，不伪造历史字节一致性，不放宽任务/原图对应核验。旧失败数据不覆盖；X只修改与CPU/fake验证，Codex审查部署，用户再启动真实标注。当前没有可训练的仿真监督标签，训练和新方法评测仍0%。

## 2026-10-24：020软件修复已验收部署（覆盖上文020 open状态）

[020](tasks/020_sim_source_metadata_compatibility.md)软件范围accepted/closed；[裁决](reviews/020_round1.md)，固定PR实现 `dc4dfa97d131fcdf8c1cc116e18d529a9d4d0efb`，未自动merge。Codex独立148/148受影响CPU/fake通过（100%，4.55秒），16变更blob吻合；新目录部署、代码字节一致及配置准备均100%。固定官方LIBERO的20个BDDL文件逐一SHA-256核对并配置，未读取原始HDF、恢复/渲染或启动作业。

用户下一步直接在020新目录启动label-sim；不重建RGB/窗口/规格、不另加真实元信息预读或GPU预检。X当前无需返修。019旧失败保留（200来源全失败，3200查询processed/supervised均0%）；本次真实标注、训练与新方法eval仍0%。见[阶段总结](../docs/stage_summaries/2026-10-24_source_metadata_compatibility_acceptance.md)。完成后Codex再审coverage并提供独立导出命令。

## 2026-10-24：020真实作业结束，标注core部署错误已另行纠正（最新状态）

用户启动020后，200/200来源（100%）通过元信息入口，但均因 `benchmark.remaining_goals.finish.xml_assets` 缺失而在core_activation失败；3200查询processed/supervised均0%，无可用监督。最终manifest `766fcd5a13a1f05bb56ffde90222f369b0a4d3f98df3277d1a030bac6d6439d9`，作业已自行结束，Codex未停止。上文将部署准备等同可运行的判断不成立；515e87d裁剪core不包含该标注助手，属Codex配置核对遗漏。

已隔离部署配置原本支持的完整annotation reference core c6dc98d，020r2新配置/新输出就绪（100%）；方法代码仍dc4dfa97，不改旧环境/原eval core及任何旧输出。实际worker解释器8个辅助函数可导入，固定Git身份/干净状态及3项传输SHA通过，无原始HDF读取或仿真/模型工作。X无需因部署失配返修。

用户下一步亲自启动020r2真实标注；Codex不代启或追加。真实native/XML/图像对应、可监督比例仍未证实，训练与方法eval仍0%。详见[更正记录](reviews/020_deployment_correction.md)和[阶段总结](../docs/stage_summaries/2026-10-24_annotation_core_deployment_correction.md)。019与020旧失败均保留。

## 2026-10-24：020r2已运行，历史命名/资源前缀兼容阻塞（最新）

用户启动020r2后，缺模块已解决；已观察82/200来源返回失败（41%尝试快照），42条为BDDL历史名称差异、40条为Mac历史XML资产根未识别；processed/supervised均0%，不属于物理对应或模型结果。快照不是全量完成率。Codex仅建议用户停止，未代停/重启，不假定已停止。

[021工单](tasks/021_historical_source_names_and_xml_assets.md)已交X，附已有events提取的真实字段/路径样例：5对准确历史名称映射采用版本化来源适配，未知/跨任务冲突继续拒绝；方法侧支持精确历史Mac前缀的有界asset解析，不改固定core、原数据、谓词或对应阈值。只做相关CPU/fake，不新增GPU预检。X实现；Codex审查部署；用户启动后续真实标注。旧019/020/020r2失败与分母保持。

## 2026-10-24：021按原工单范围验收部署；022补充Object名称（最新）

[021裁决](reviews/021_round1.md)：固定PR HEAD3444ec74，独立247/247受影响CPU/fake通过（100%，无skip）；20变更blob吻合，代码/配置隔离部署100%，未自动merge。只读旧audit/request的CPU解析中，10类Goal名称通过、5份已有XML的495引用全部解析成功，无HDF/图像读取或仿真/模型工作；真实对应/标签仍未证实。

旧020r2后续4类Object历史名称尚未被原工单列入，当前仍gap，范围遗漏由Codex负责。021原软件范围accepted/closed，不倒改旧失败；新[022补表任务](tasks/022_object_historical_name_coverage.md)交X，4个已观测及6个预期条目分开标明，不扩任务/预算、不放宽目标/对应规则。不是要求所有未知字段完美才使用可靠子集；为避免已知来源错误/重复渲染，建议完成小补表后再由用户启动全量。新版真实标注、训练和方法eval仍0%。见[阶段总结](../docs/stage_summaries/2026-10-24_historical_source_compatibility_acceptance.md)。

## 2026-10-24：022补表已验收部署，可直接由用户启动标注（最新）

[022裁决](reviews/022_round1.md)：固定PR HEAD `fb7399b434a74fb66796d709fbd88d9b44c4cfa9`，独立238/238定向CPU/fake通过（100%，无skip），13变更blob吻合；新目录部署100%，X无需返修。旧audit/request文本中的14/14类已见任务名称均可解析，此前4个Object冲突已清除；另6种Object明确预期兼容，尚非真实字段验证。

实际worker的8个助手、源码字节及3项传输hash核验通过；复用完整c6标注reference、旧XML证据及原200来源/3200查询，不新增MVP/真实元信息预读/GPU预检。没有启动HDF处理、恢复/渲染、模型、训练或eval。旧结果与缺manifest状态保持，PR #2未自动merge。

下一步直接**用户启动022新版label-sim**；真实标注覆盖、训练和新方法eval仍0%。Codex审查实际输出后再给独立导出/训练命令，可靠子集不要求完美ready。见[阶段总结](../docs/stage_summaries/2026-10-24_object_name_coverage_acceptance.md)。

## 2026-10-24：022真实标注100%完成，023对齐失败取证（最新）

用户022作业已结束：200来源/3200查询100%处理、无运行错误；可监督165（5.16%），train165（6.45%）、dev0。ready=false、usable=true不能冒称原训练/验证方案ready。原165条、3200全部分母与原160/40划分保持。

只读旧audit分析：2990查询（93.44%）因对齐未解；14来源获唯一next_state接受，81为双候选probe通过但等价认证失败（其中21还在额外帧有RGB失败）、3三候选歧义、102无候选通过（含全部100 Object）。不能直接调阈值或认定全是图像错误。

[023工单](tasks/023_bounded_alignment_diagnostics.md)已交X，固定2条旧train来源、各3个既有probe做原图/重建图与状态分量诊断；不做全量重跑、VLA、标签/阈值变更或训练。X实现/CPU-fake，Codex审查部署，用户启动实际恢复/渲染。诊断结果出来后才作修正规则决定。见[阶段总结](../docs/stage_summaries/2026-10-24_sim_annotation_result_and_alignment_diagnosis.md)。本次Codex没有启动真实作业，旧失败与资料不清理。

## 2026-10-24：023首轮交付已审，生产入口两处小修（最新）

固定PR HEAD `9c0429d590f40bcef83570c85ced1ee0fc10b8dc`，Codex独立53/53定向CPU/fake通过（100%，无skip），17变更blob吻合。但封存生产JSON明确证明两个误拒绝：固定Git版本被额外要求特定目录basename；planned与已验证sources的不同schema被强制全字典相等。[023首轮审查](reviews/023_round1.md)needs-fix，仅这两项；具体实现要求已追加[023工单](tasks/023_bounded_alignment_diagnostics.md)，不扩范围或重跑全库。

尚未验收部署或启动真实诊断；53项通过不冒称生产入口通过。原2来源/probe/预算、标签/阈值/160:40划分及旧结果保持。X小修/CPU；Codex复核只读输入后部署给命令；用户亲自启动。用户当前无需实验或训练。

## 2026-10-24：023第二轮验收部署，等待用户启动两来源诊断（最新）

[023第二轮裁决](reviews/023_round2.md)accepted/closed（软件范围），固定HEAD `fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391`，X无需返修；独立89/89定向CPU/fake通过（100%，无skip），8变更blob一致。目录名误拒绝和planned/source schema误拒绝已解，其他身份/绑定/预算不变。

代码/会话隔离部署100%，实际封存生产输入只读解析通过（2来源/6 probe/12 PNG），没有创建诊断输出、读取原始HDF、worker或仿真启动、恢复/渲染、模型/标签生成。旧输入identity与新诊断实现identity分别保留。PR未自动merge。

用户下一步启动独立diagnose-alignment；真实诊断0%，训练/方法eval0%。上限18恢复/6旧动作/36比较/72直接render（内部初始化/restore渲染另计受原预算），不重跑200来源/改阈值标签/自动训练。见[阶段总结](../docs/stage_summaries/2026-10-24_alignment_diagnostic_software_acceptance.md)。旧165条监督、dev0、资料和失败均保留。

## 2026-10-24：023诊断100%完成；用户确认024共识标注修订（最新）

用户运行023已complete：2来源/6probe/36比较无错，manifest `6f60f37329f1c4f4d0ab1926ca8022e71d48b11a2d534daadb40493dbdd841e7`。Codex核验产物并看4张面板：6/6 probe的三候选目标原子一致；重放误差以qvel为主但qpos也不同，不能说纯噪声。篮子agentview的前景0.03154—0.03223超门槛，wrist0.00620—0.01198通过，不能简单归咎背景或全局错位。仅两条train案例，不外推全量正确。

用户已确认保留0.03/原谓词、改为逐帧逐视角逐字段共识。[024需求](tasks/024_frame_view_field_consensus_labels.md)已交X：匹配共同视角+全部可信候选字段一致+原可见/物理证书，否则UNKNOWN；不伪造物理唯一对齐/不改RGB或输入，不用relation广播grasp/release。验证后复用旧165及旧唯一对齐来源，未知来源才补算，新旧结果/代码身份分别记录。

024实现和真实补标尚未开始，训练/eval未启动；原165/5.16%和dev0保留。X实施/CPU-fake，Codex审查部署，用户启动补标，不额外GPU预检或模型MVP。见[诊断结果与决策总结](../docs/stage_summaries/2026-10-24_alignment_diagnostic_results_and_labeling_revision.md)。未启动后续作业或清理资料。

## 2026-10-24：024由Codex接管，补标与训练准备已完成（最新）

用户明确授权本次Codex自己修改并运行排障直到可训练，覆盖旧X实现/用户独占启动限制。Codex实现[PR #3](https://github.com/No1dry/Learning-Not-to-Act/pull/3)@ed779093，71项定向CPU/fake通过；PR #2/#3未自动合并。024本次实现、补标、导出及训练就绪范围accepted/closed，不再要求X返修。

200来源/3200查询处理100%、0运行错误；2429可监督（75.91%），train1958（76.48%）、dev471（73.59%）。原160/40划分、阈值0.03、原生谓词保持；复用旧14来源/165监督，余186来源按逐帧/视角/字段共识补标；旧结果不覆盖。原报告ready=false仍保留其全字段完备语义，不阻止可靠非空训练/验证子集。

3B固定快照上传校验100%；60种真实processor组合和一次CUDA前向/反向通过，288有限LoRA梯度、7372800可训练参数、峰值显存17.72GB；优化器更新0、诊断权重未保存。训练准备100%；正式训练、改进后方法评测0%，下一步直接用户启动正式selector训练，无新增MVP或检查门槛。见[阶段总结](../docs/stage_summaries/2026-10-24_consensus_labels_and_training_readiness.md)。原始证据与失败均保留，本轮无删除/清理。

## 2026-10-24：正式selector训练完成，025评测入口交X（最新）

用户024训练100%完成：3 epochs/369 optimizer steps，每轮train1958/dev471，三个checkpoint均完整。Dev token-mean loss为0.2074258→0.1753629→0.1675368，按dev选择checkpoint-3；三项adapter文件hash与保存声明一致。训练下降不等于任务成功率提升，方法评测仍0%。

Codex训练期间尚未完成评测对接准备，遗漏已明确记录；固定core批处理当前只接受顶层OFT，并非改一条配置就可直接执行完整方法。[025详细任务](tasks/025_oft_selector_batch_evaluation.md)已实际交X：只补方法侧OFT＋selector所需100条编排，复用冻结core、旧10状态与原指标/视频/底座，不先做全模型014框架、不重做状态、不增加MVP或rollout。X实现/定向CPU-fake，Codex审查部署及conda/python命令，用户启动正式评测。没有启动新模型推理、仿真或eval；旧训练、checkpoint和失败记录全部保留。

[训练阶段总结](../docs/stage_summaries/2026-10-24_selector_training_results.md)。024准备范围关闭保持，025开放；本轮无清理/删除。

## 2026-10-24：025由Codex直接实现并部署；纠正旧基线覆盖（最新）

用户新授权不再等X。Codex已完成[PR #4](https://github.com/No1dry/Learning-Not-to-Act/pull/4)，v2实现79fdcf34、后续仅文档提交80b70c0；28/28定向CPU/fake通过（214.37秒），原core/测量/计分不变。controller/OFT/selector三环境只更新方法包并补原LIBERO路径，源码身份和传输SHA一致，未改依赖或自动merge。

必须纠正：原100是计划，旧baseline实际只有80条执行；frypan_stove9、cabinet_close_top_bowl共20条缺旧回放文件。新文件计划同为80/100，models_loaded=false、simulation_created=false。严格默认不放行缺来源；用户显式--allow-missing-sources后可直接比较相同80条，100分母保留，20缺失不算失败、不换初态、不自动补状态。完成会显示completed_with_missing_sources和80%，不是跑满100。

025软件/部署范围accepted，X无需实现或返修；20条来源缺口仍开放，整体100实际执行目标未完成。训练100%、方法评测0%；用户下一步按本地完整conda/venv/python命令启动同80来源的正式比较，控制台实时显示百分比/task/episode/query。若要求实际100，另需恢复原证据或明确授权准备。见[部署与覆盖总结](../docs/stage_summaries/2026-10-24_method_evaluation_entry_deployment.md)。旧日志、来源、训练checkpoint、初版80计划与失败记录均保留，无删除。

## 2026-10-24：025真实首条在registry解析暂停，026已部署原文审计（最新）

用户已启动025，并非未启动：首条basket_s000_10在文本registry生成159 tokens后json.loads失败；visual input0，n_steps0、executed_actions=[]，完成0%。OFT加载/原资产核验及环境初始化已通过，前置TF/cuDNN消息不是这次暂停的异常链；技术错误不能当作任务失败或方法效果。原进程已退出、生成原文未保存，无法断言仅Markdown围栏。

Codex直接实现[PR #5](https://github.com/No1dry/Learning-Not-to-Act/pull/5)@51c69d3b，共享已有严格完整外层JSON解码，保留原schema/prompt/权重/计分；新增raw_output与wrapper/json/schema审计，失败RPC及独立infer --audit-output也能保存。不语义修复、不自动重试、不用任务真值替代。47项定向CPU/fake通过、39未选；三环境部署和文件级dry-run通过，没有新增真实模型/仿真调用。

026代码/审计部署已完成，但真实故障原因仍开放，不宣称已彻底解决。用户下一步启动单次同指令/checkpoint-3的3B文本调用，取新raw/schema；不加载OFT、不创建仿真、不执行策略动作。Codex读取后再决定后续，X无需修改；PR未自动merge。旧失败目录、原100计划/80可用及20缺证据范围保持，不覆盖或删除。

[故障与026记录](../docs/stage_summaries/2026-10-24_selector_registry_parse_failure.md)。

## 2026-10-24：026真实schema错误已定位，027字段提示已部署（最新）

用户026单次同checkpoint-3文本调用已保存原文：image_count=0、prompt132/generated159 tokens。完整JSON围栏正常解析；instruction和source_text被大写/加句号改写，两个actor_text错误地为the person。并非只需忽略大小写；不把文本拆解失败视为视觉SFT或动作失败。

Codex实现[PR #6](https://github.com/No1dry/Learning-Not-to-Act/pull/6)@a236454a，仅明确registry原字段并加两个通用非benchmark示例；原validator、视觉prompt、权重、checkpoint、评分保持，无自动重试/语义回填。55项定向CPU/fake通过（100%，37未选），新027目录及三环境方法包部署100%，不改依赖/core。固定processor文本预算检查与CLI dry-run不包含模型生成或仿真。

真实修订效果仍开放，未宣称解决：下一步用户启动027独立文本调用，Codex读取新audit后决定恢复正式eval。X无需返修；训练100%、方法eval完成0%，旧100计划/80可用/20缺来源保持，原025/026失败均保留。见[阶段记录](../docs/stage_summaries/2026-10-24_registry_field_prompt_revision.md)。未自动merge或清理。

## 2026-10-24：027用户真实文本拆解通过，直接交接正式评测（最新）

用户027调用已成功，Codex读取registry与audit确认：同3B/checkpoint-3真实加载，image_count=0、prompt609/generated95 tokens、bare_json，wrapper/JSON/schema全部passed、error=null。原指令/原文片段逐字保留，两个actor_text正确为分别放alphabet soup和tomato sauce入basket；026已见文本故障在此调用中解决，不外推其他任务或视觉/执行成功率。

代码仍PR #6@a236454a，原测试与部署证据复用，不再增加模型预检/重训/状态回放，X无需返修。027正式配置已上传、新输出路径隔离，完整conda/venv/python命令已交用户。下一步用户启动正式方法eval；Codex读取交回结果。准备/训练100%，方法评测完成0%；同旧基线80可用/100计划/20缺来源保持，双视角视频和原指标不变。未代启实验/自动merge/清理。见[真实通过及评测交接](../docs/stage_summaries/2026-10-24_registry_verified_evaluation_handoff.md)。

## 2026-10-25：027视觉失败已处理；028由Codex真实验证并部署（最新）

027正式尝试在首个视觉查询因两个evidence缺失暂停，0动作/0%完成。用户明确要求Codex直接修复并亲自运行必要验证，本次覆盖旧用户独占启动限制，但不授权完整评测或重训。

[PR #7](https://github.com/No1dry/Learning-Not-to-Act/pull/7)最终db74ad40，34项CPU/fake通过；v3四类输入/六次真实视觉调用100%通过原严格契约，最终v4同失败输入665 tokens逐字等于v3。640步等价贪心快路径、25步原掩码，筛选3.60秒，不据冷启动185.31/187.60秒宣称端到端加速。原prompt/权重/计分不改，但推理协议明确版本化为证据先行、无支持只能UNKNOWN、最多3区域/8位小数/自生成ID绑定；不是后改JSON或模型内在置信度证明。

真实OFT已在完整调度中返回并通过core校验的8×7动作，selector复用刚实测记录；没有仿真/执行。诊断脚本随后NumPy断言报错的failed报告仍保留，独立sidecar复核确认动作返回边界通过，不冒称整个脚本exit0或保存动作逐值。所有001—006诊断及旧失败保留，未清理/自动merge。

代码/三环境部署和正式配置准备100%；软件接口范围验收，不再交用户诊断。必须保留负面观察：首个mask10中g0已满足仍被判UNSAT，策略选择g0，不能称方法有效。正式方法评测完成0%，未代启；下一步用户直接按已交完整命令启动同80可用/100计划/20缺来源的评测，Codex分析结果。完整运行与识别准确率仍未证明，见[详细阶段记录](../docs/stage_summaries/2026-10-25_visual_wire_verification_and_handoff.md)。
