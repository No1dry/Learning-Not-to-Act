# 017：完整离线数据、候选标注与人工确认管线

日期：2026-10-23。执行者：X。状态：accepted/closed（仅软件与CPU/fake范围，2026-10-23）。用户已接受“VLM候选＋人工确认”；**本工单只授权实现与定向CPU/fake测试，不授权X/Codex运行真实数据、模型或训练。**

## 1. 本轮交付与边界

016已验收并部署，不返工在线方法、训练器、评分或冻结VLA。本轮补齐现有单样本CLI没有的批量来源/窗口、一次加载的离线候选、可用的字段审核工具与完整命令。一次完整交付，不先做MVP，不加数据库/多人平台/全浏览器工程。

从已验收 `5a77f158229442d9a9ee95ba828b371dfc4c995a`继续开发，可在原PR #2增量交017，并同步main最新协作文档；不要从尚不含实现的纯main写出断链文件。比较范围明确为5a77f158之后的017增量，不自动merge或热改服务器。

现成可复用：`extract_existing_images`、registry/prediction契约、prompt/encoding、EvidenceMemory、annotations export/import、grouped_split/build。不得复制修改一套标签/评分规则。

## 2. 固定来源与用户先行下载

- `yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`；用已交付`data/catalog.json`的Goal10＋Object10，20文件不换。
- 目录API元信息20/20核对，合计13,817,196,909 bytes（约13.82 GB）；仅文件元信息，实际HDF5内部已核验来源数仍为0。
- 每文件固定数字顺序`demo_0..demo_9`，目标200来源。缺失/坏来源明确记gap，不自动换成demo_10，也不按教师判断或VLA成败挑来源。
- 读原文件`data.attrs.problem_info.language_instruction`，原文不改。缺失时需要显式人工指令映射，不能用任务编号查在线答案或悄悄猜文本。
- 读取已有双相机uint8 HWC RGB及其长度/来源元信息；不恢复state/render，不调用VLA，不拿动作、reward、done、谓词、坐标等生成答案。
- 记录`macros_image_convention`（可unknown）。官方存图与当前core都保留raw RGB，不盲目翻转/裁剪/替换OFT处理后图。样本meta保存相机/方向/原frame索引；不塞进模型context。
- 原始下载因服务器网络失败，2026-10-23用户授权Codex本地下载这20文件再SSH搬运，仍与本工单实现并行。这只是原始字节与完整性校验；X/工具不把download自动串成抽帧、教师或训练。

## 3. 来源分组、窗口与query（固定规则，不看成败）

先按整来源episode＋已知alias，用现有grouped_split/seed0固定约80/20；不得按帧分。未知祖源如实记录，不重启物理来源逐一匹配工程。与之后现有build的归属一致；不因候选/人工标签改split。

每来源双相机共同长度T，6个anchor=`floor(i*(T-1)/5), i=0..5`。每窗口取`[anchor-16, anchor-8, anchor]`，截到合法范围后去重递增；相同窗口再次去重。两相机长度不符、空图或非法格式明确失败，不默默取较短长度/补帧。

- 每窗口query_id从1开始密集递增；原frame索引留在数据清单，不冒充query_id。每个query只提供窗口内此前至当前的1—3双相机快照。
- “3 query”是3个时刻，不是为凑数量制造新增目标、角色问句或“A已完成”的提示。
- registry只从该原指令生成并人工确认一次，按精确指令复用，符合原validate_registry。不可用task_id/mask/几何真值补答案。
- 窗口开始memory为空，`commands=[]`（没有实际调用VLA，不能伪造命令）。候选按过去→当前生成；后续history仅来自此前合法候选经原EvidenceMemory得到的记录，`history_provenance=model_prediction`，不读未来人工标签或演示成功。
- 候选结束冻结用于审核的payload。人工修当前answer不能回填已确认真标签到过去history或悄改输入；如需改payload，另生成版本。
- 最多200来源/1,200窗口/3,600 query；实际更少正常，分开报告独立来源/窗口/query及train/dev数量，不补造。
- 均匀采样不保证600明确/300歧义等比例，也不保证DISTRACTOR/双目标覆盖。报告实际分布/缺口，不按SAT筛帧凑配额，不扩任务阻塞。

## 4. 离线候选：一次加载、与学生身份分开

默认候选教师：`Qwen/Qwen2.5-VL-7B-Instruct@cc594898137f460bfe9f0759e9844b3ce807cfb5`，processor同pin，显式Qwen2.5类、bf16、batch1、do_sample=false。仅离线候选，无LoRA、不调用收费API/外传图像。16,584,414,560 bytes只是五个权重文件体积；显存峰值和耗时未经运行，不保证4090一定够。OOM/错误保留，不自动量化、换模型或重跑。

- 独立离线配置/loader；**不得放宽016学生3B的resolve_config pin，不把7B变成在线选择器/训练底座。**
- registry从原指令生成；视觉候选严格只用同一sensor/context envelope、共同prompt/schema与预算（最多6图、每图256视觉token、总4096、答案1024）。无GT/文件名/帧阶段/剩余任务暗示进入prompt。
- 整次命令只加载一次教师，按窗口顺序处理，保存模型/processor/prompt配置身份、实际输入、原输出/解析错误、耗时与调用数。
- 不合法JSON/schema/越界/超时等保留answer=null与错误记录，不伪造UNKNOWN，不悄悄修复/重试后冒充一次调用。人工可以明确补写；独立后续窗口可继续。
- 所有机器候选的标签provenance初始weak；模型置信/一致/质量评分都不能自动升级。
- 最多约20个registry候选调用＋3,600视觉调用（实际指令/去重/缺口改变数量）；不得拿它当实际调用数或GPU小时。

## 5. 人工确认工具：能完成审核，不要求手改几千行JSON

提供最简离线HTML审核包（无需数据库/服务平台）：双相机当前与合法历史图、固定指令/registry、当前候选字段和证据框，可改值/框、按字段或完整evidence item确认、跳过未确认、导出annotations与审核记录。真实人工由用户指定；X/Codex的AI输出不能署为human。

- 所见为模型实际允许的当前/过去视图，不展示未来完成帧/物理状态/模型最终成败提示。显示框用于审核，不写回训练图或VLA图。
- 确认实体/关系/释放/持物时同步核对goal/entity/query/camera/bbox/supports；完整evidence item明确确认后才标reviewed_candidate。未确认字段保留weak，不能整份自动升级。
- 人确认“确实看不清”才是受监督UNKNOWN；机器失败/null与尚未审核不是human UNKNOWN。
- 审核界面不改immutable payload/source/split。便携图像映射用于显示；不得为本地看图改训练payload中的规范路径/身份。审核审计另存sidecar，不塞额外字段进训练schema。
- 支持保存/导入已有审核JSON，避免必须一次审核完。无付费API、无遥测/外部图片上传。
- 先提供按任务/来源轮转的审核队列，避免只挑教师高置信或简单样本。建议对已确认窗口约10%做分层复核；这是工作组织建议，不保证质量、不新增模型试验门槛。
- 1200窗口/3600query不要求全部逐字段审核才允许构建。全候选清单保留；明确输出人工已确认训练子集及未审/无监督/gap清单，复用现有import/build。不得把缺标签标为“全量ready”，实际监督来源覆盖单报，不能按eval成败取子集。
- 55—80人时旧估计未获批；VLM候选能节省多少时间未知，不承诺几小时。工具记录实际确认数/修正数/审核时间供资源决策，不能伪造人时。

## 6. 入口、输出与交付

入口命名可等价调整，必须分别可启动：
1. 静态plan（不读HDF5/模型）；实际inventory/来源与split清单。
2. registry候选→人工确认→批量图像/窗口/合法source payload。
3. 一次加载教师的候选推理；不自动串到训练。
4. 审核包导出/导入；已确认子集与未审全量并列；调用现有build得到train.jsonl/dev.jsonl/report.json。

给出全部必需文件、顺序、真实参数与分别命令，不只伪代码。物理真值列允许null，不导出oracle表当视觉答案。外部排除声明默认不能预填true；报告候选名单对六复合任务/语义等价/已知eval同源的排除依据，未知物理祖源保留披露，不要求证明从未见过的场景。

所有输出使用新目录；故障保留partial，不覆盖旧数据。真实入口仅供用户启动，CLI help/static plan不初始化native/模型或偷偷读真实样本。

CPU/fake只覆盖本次路径：数字episode选择/gap不替换；固定采样去重与来源split；无未来/伪命令/GT且历史冻结；教师只加载一次、学生pin不改；null与weak不伪升UNKNOWN/human；字段确认/证据索引回写可被既有import/build/最终mask正确消费。用合成小HDF5/fake模型和审核事件，不跑真实数据/模型、全库/多平台或旧物理证据。

交付`collaboration/responses/017_round1.md`＋增量PR/commit、实际CPU/fake结果、完整入口/命令与缺口。真实来源、候选调用、人工确认、训练、eval本轮应为0。Codex集中审查部署后，由用户分别启动。

## 7. 来源

- [固定Goal目录](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3/libero_goal)、[Object目录](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3/libero_object)；2026-10-23仅查询文件元信息。
- [LIBERO官方create_dataset](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/scripts/create_dataset.py)读取problem_info语言并直接保存已有相机RGB；本工单不执行其中重放代码。
- [7B教师固定模型目录](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/tree/cc594898137f460bfe9f0759e9844b3ce807cfb5)；只是候选，不声明其LIBERO标签准确率。

## 8. 最终软件验收

固定c6840ae6已通过[Codex验收](../reviews/017_round1.md)，59/59项定向CPU/fake独立通过（100%），并已隔离部署。017软件范围closed，无需X返修；真实数据处理与模型运行仍由用户另行启动。见[阶段总结](../../docs/stage_summaries/2026-10-23_offline_pipeline_acceptance.md)。
