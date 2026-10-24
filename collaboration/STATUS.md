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
