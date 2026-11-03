# 方法研究当前状态

## 2026-11-03：X提交教师v2与精确73恢复实现，等待审查

[PR10](https://github.com/No1dry/Learning-Not-to-Act/pull/10)增量实现 `20647cce386dfe2a3f768a029f909fa32350aa60`，见[教师v2 Round1](responses/035_teacher_v2_round1.md)及[完整配置/命令](../docs/trajectory_teacher_v2_recovery.md)。已合入最新main `5448e8a`。软件实现100%；v2仅table_drop未知诊断，原v1/正式评分/版本锁/划分/训练配方保持。

入口先验证原180及父分组，再按批准refs固定73（53train/20dev）；旧8条原字节复制复用、零重放，与新attempt分列。新失败保存已完成对齐前缀但不进训练。导出身份含策略/恢复版本，逐来源进度与四池training_ready已接通；不足不自动补跑。

受影响CPU/fake66 passed、2 skipped（15.29秒，0failure/error），两skip为Windows缺少权限的原symlink用例；不算通过。精确180→73＋旧8的合成端到端已通过，独立窄审查无剩余已证实阻断；真实新生成/训练/模型eval本轮0%。002原数据仍2normal/6个10，不宣称003已产出。

下一步Codex集中审查/隔离部署/准备实际refs与generated-003完整命令，用户亲自启动已批准73普通＋最多438次10；原1000更新/90+90预算保持。旧001/002失败、原数据和所有历史保留，无自动merge/清理，待删=[]。

---

## 2026-11-03：用户已批准教师v2与73来源恢复，直接交X实现

用户明确同意：table_drop未知仅诊断，已确认违规/完成释放等原条件不变；旧002已有2normal/6个10共8条合格HDF零重放复用，只重建73候选（53train/20dev），新增上限73普通重放＋438次10尝试。原一组1000更新/7:3混训和同adapter10/00各90预算保持，仍由用户启动全部真实作业。

**下一执行者X：按[完整直接实现任务](tasks/035_teacher_v2_recovery.md)实现＋精简CPU/fake，不必再先交方案。** [精确候选/复用引用](tasks/035_teacher_v2_recovery_refs.json)已备好：73个ID和原资格/metadata SHA；旧8条HDF/资格/审计等引用SHA。原180先验证/分组再选73，不重分组、不把候选改成成功，不复制train到dev；失败观测保留但不进训练。

版本化策略不改正式benchmark/原90状态/评分，也不改原native版本锁/动作投影/桥接/A保护/释放/H520；不增加释放尾动作、截断示范或新来源。R3解释器修复验收保持，原001/002失败/原始数据保留，不重下数据或重跑所有180/基线。[批准阶段总结](../docs/stage_summaries/2026-11-03_task035_teacher_v2_approved.md)；原分析已标明本次批准，旧“待用户确认”仅历史。

实际可用数据仍2normal/6个10、仅dual_mugs/train，dev空；v2尚未实现，新增真实生成/训练/新模型eval0。X交付后Codex审查/隔离部署/完整命令，用户启动新输出generated-003，不自动执行。评测日志小增量非阻断，无自动merge或清理，待删=[]。下方为历史。

---

## 2026-11-03：002真实生成结束，技术错误0；数据未可训，v2恢复提案待用户确认

用户已结束generated-002，来源处理100%（180/180）、技术错误0%；normal合格1.11%（2/180），两个父来源产生的6次10尝试全合格=100%，但仅dual_mugs/train、任务覆盖1/9=11.11%，dev两域0。不是1080次10已执行，也不是模型评测SR。当前不发空池训练命令，R3解释器修复验收保持。[R4裁决](reviews/035_round4.md)、[阶段总结](../docs/stage_summaries/2026-11-03_task035_generated002_data_bottleneck.md)。

180份既有资格只读分析：120/180=66.67%含事件未知，61,098逐帧未知全为table_drop；73/180=40.56%仅因此失败、完整任务和释放/连续确认已通过，无已确认违规。固定benchmark主评分已将table_drop通道仅诊断，而现教师硬拒它；这是Codex筛选设计瓶颈，不要求X为忠实实现返修。[详细分析和v2提案](../docs/research/2026-11-03_task035_generated002_filter_analysis.md)。

拟仅将教师table_drop未知转诊断，确认违规/其他关键未知/完成释放/A保护和正式评分不变；旧8条合格HDF零重放复用，另只恢复73候选（53train/20dev、五任务），不重跑全部180。原rejected没保存RGB，不能改JSON就冒称已有训练数据。原split/9文件/原状态与两基线保持，旧事实不覆写。

**下一执行者用户：确认v2与新增上限73次normal重放＋438次10尝试**（不保证产量），训练一组1000/评测90+90预算不变。已发确认问题，目前未收到批准，未向X下达实现或启动新增真实作业；批准后Codex交精确清单/详细任务，X实现、Codex审查部署/命令、用户启动。训练/新模型eval0。无自动merge或清理，待删=[]。下方为历史。

---

## 2026-11-03：035 R2路径修复已验收部署，用户直接启动generated-002

PR10固定HEAD eecd25f5（实现e56e3e70），[R3裁决](reviews/035_round3.md)accepted/closed限解释器软链路径修复及部署；[阶段总结](../docs/stage_summaries/2026-11-03_task035_interpreter_fix_accepted.md)。X本修复无返修；原R2路径阻断关闭，035研究仍open。

Codex独立受影响CLI CPU/fake8/8通过（100%、0skip、0.35秒），包含X在Windows无法执行的两项真实symlink及plan/request/fake subprocess全链拼写。只有一个生产文件的5增2删，其他版本锁/算法/数据/计分不改。归档SHA01ec27eb与CLI SHA5c892731本地/服务器一致，独立目录code/task035-eecd25f5已部署；实际配置纯JSON计划一次核对，解释器保留原oft_worker/bin/python，180父来源/最大1080次10尝试不变，未创建仿真/模型或升级环境。

**下一执行者用户：按[002完整命令](../docs/experiment_plans/2026-11-03_task035_generation_retry002_server_commands.md)直接启动正式轨迹生成**。继续复用9个HDF/180清单/train136-dev44和原configs/trajectory035-564c91c9/generate.json，输出换data/trajectory035/generated-002，日志generate-002.log。不再执行旧001命令，不重下载、不等X、不追加MVP或真实预检。

原001的180条初始化错误及normal=0、10=0保持，未覆盖/改分；002未启动，有效数据/训练/新模型eval仍0，修复软件不代表实际资格通过。生成报告交回后Codex给混训命令。原10/00基线24.44%/86.67%不重跑，实验仍用户启动。评测实时SR/去重复读子项为非阻断open，不卡本次生成/混训。无自动merge或清理，待删=[]。下方为历史。

---

## 2026-11-03：X提交035 R2解释器路径最小修复，等待验收

[PR10](https://github.com/No1dry/Learning-Not-to-Act/pull/10)增量实现 `e56e3e7031e96308c3e723734944b45166c2f0f7`，见[035 R2回复](responses/035_round2.md)。仅native Python改为expanduser＋基于配置目录的abspath，保留venv入口；其余resolve、版本锁和生成/训练/评分主体不改。

实现100%；本机受影响CLI测试6 passed、2 skipped（0.40秒）。两项真实文件symlink因Windows WinError1314无权限未执行，另两项模拟解引用的fake回归完成红绿验证；不能把真实symlink写成已通过。原失败/skip证据保留，没有扩大测试或改环境。

下一步Codex在支持软链机器补验两项CPU/fake、做一次实际配置JSON路径核对并隔离部署，复用9个HDF/180清单/原锁，给generated-002命令，由用户亲自启动。generated-001全部180初始化失败及旧日志保留，当前合格两域仍0，不能开始混训。本轮X真实作业0，无自动merge/清理，待删=[]。

---

## 2026-11-03：035首轮180初始化错误，已定位venv解释器被resolve，X仅修路径

用户已结束generated-001：来源处理180/180=100%，初始化技术错误180/180=100%，全部annotation library version lock mismatch；合格10=0、normal=0，无法进入混训。这不是物理重放成功率或模型SR，不把处理100%当成数据ready。[R2审查](reviews/035_round2.md)、[失败阶段总结](../docs/stage_summaries/2026-11-03_task035_initialization_failure.md)。

根因实际请求已证实：正确配置的.../.runtime/oft_worker/bin/python经035 cli.build_plan的Path.resolve变成/root/anaconda3/envs/peft-openvla/bin/python3.10，失去venv语义。正确worker版本与原锁完全相符；被调用base是numpy1.26.0/mujoco3.4.0而非1.24.4/2.3.7。这是Codex R1审查遗漏，不以修改版本锁/升级环境/重下载处理。

**下一执行者X：按[最小修复工单](tasks/035_round2_preserve_native_python.md)只修解释器拼写保留＋symlink plan到subprocess的精简CPU/fake**。其余035/030软件验收保持、不返工主体、不增加MVP/全库或真实预检。Codex验收隔离部署后给新输出generated-002命令，仍由用户启动。180清单/9原文件/划分复用，原001全部失败记录保留，不覆盖、不伪造成功；真实物理重放/10桥接尚未开始，不自动扩大预算。训练、新模型eval均0%。原评测实时SR小增量为非阻断并行；无自动merge/清理，待删=[]。下方为历史。

---

## 2026-11-03：035文件准备100%，用户可直接启动正式轨迹生成

九任务9/9原始HDF共12,790,079,988字节已下载、上传并核验固定LFS SHA；180条普通种子清单/六配置已准备并逐文件核验传输，父分组train136/dev44。最后微波炉分段续传后完整SHA通过，旧网络失败/部分文件保留，不改写旧日志。[文件阶段总结](../docs/stage_summaries/2026-11-03_task035_data_files_ready.md)。

**下一执行者用户：按[完整conda/python命令](../docs/experiment_plans/2026-11-03_task035_generation_server_commands.md)启动正式生成**，不再等X、不增加MVP或仿真预检。固定代码task035-564c91c9，配置trajectory035-564c91c9，输出data/trajectory035/generated-001。最多180普通重放＋1080次10尝试，不保证成功量；已有原始文件和清单不等于已生成合格10训练轨迹。Codex未启动真实作业，生成/训练/新模型eval均0%。

仅HDF属性/shape用于文件绑定，原动作统计/相机/控制器/九任务谓词不变；真实输出将重放并记录新鲜状态—动作。父组未知demo/init物理祖源仍unknown，正式90测试状态/模型轨迹不进训练。生成报告交回后Codex给1000更新7:3混训命令；同adapter10/00各90及原24.44%/86.67%基线保持，不重跑基线。X非阻断实时SR/读取效率小增量仍open，不阻塞生成/训练；无自动merge或清理，待删=[]。下方为历史。

---

## 2026-11-03：035主体软件accepted并隔离部署，用户已同意预算与文件准备；日志小增量并行

PR10固定564c91c9（主体fda3c95a、超时示例e98ecc36），[035 R1](reviews/035_round1.md)accepted限真实生成器/7:3混训/同adapter双条件计分主体与文件部署；[软件阶段总结](../docs/stage_summaries/2026-11-03_task035_software_acceptance.md)。X不返工主体、030验收保持，当前不宣称实际数据非空或SR提高。

Codex分组三组CPU/fake：生成初次37通过/1因缺同级历史依赖目录失败，补链接后该项单独通过；训练25、评测24通过，87个不同用例均获通过证据、0skip，初次XML保留。没有对真实native/7B做预检。只读实际原统计JSON确认action mask六真一假/proprio默认全真；源归档SHA5da2b238本地/服务器一致，独立新目录部署，15+97+6=118依赖文件锁匹配，无环境升级/热改/仿真/模型。

仅有[评测实时报告小增量](tasks/035_evaluation_live_reporting_followup.md)为non-blocking/open：当前126单元最多128次从头reader，控制台只报condition/task/status；建议X补两条件完成百分比/live SR、循环只验新任务、最终一次完整复验。评分/源/模型不改，不做真实profile，不阻塞数据生成或混训；PR10未自动merge。

当前下一执行者Codex：本地下载并上传九任务种子，绑定原控制器/统计/相机、旧native与00/10来源配置，给普通conda/python完整命令。用户已明确同意035预算及文件准备：最多180种子重放＋1080新10尝试、一组1000更新及同adapter10/00各90；**只授权Codex准备/搬运文件，所有真实作业仍由用户亲自启动**。不用旧380普通来源/两轮训练/126评测的旧问答替代本轮许可。种子文件正在准备，真实生成/训练/新模型eval均0%。

主目标10优先、00保持第二、泛化后置；原10合规24.44%和00原生86.67%两基线不重跑。无FINISH/selector/benchmark扩张、自动merge或清理，待删=[]。下方为历史。

---

## 2026-11-03：X提交035完整实现，等待Codex集中审查

独立分支 `x/task035`，基于已验收030 `5bb32713` 并合入最新main `cb026b3`；主体实现 `fda3c95ab5a95d7f3d7db388b3c4ad42cde46f46`，配置说明修正 `e98ecc366cbb29eb1c3727cf17773cb851da379f`。见[035 Round1回复](responses/035_round1.md)、[生成/混训完整命令](../docs/trajectory_augmentation.md)与[双条件评测](../docs/trajectory_augmentation_evaluation.md)。提交独立PR，不更新或自动合并PR9。

软件实现100%：实际native正常重放、robot-only起点变换、两种有界桥接、真实controller目标B续接、固定core资格与失败journal、T+1/T新数据导出、7:3域独立混训、固定末1000 adapter及同adapter10/00各90评测。复用030模型/LoRA/head/normalization/恢复与证据主体；benchmark、旧数据/结果、物理判据和034报告不改。

最终定向CPU/fake87/87通过（100%，0skip/error/failure）：生成数据38、训练25、评测24，分三个进程。单进程组合因本机NumPy/PyTorch重复OpenMP中止的失败及独立复现已在回复保留，不记通过；未改环境。独立实现复核无剩余已证实阻断项，真实数据获取/生成/训练/新评测本轮均0%。

下一步Codex集中审查、绑定实际来源/依赖/配置并隔离部署；用户确认035新预算并亲自启动真实阶段。尚无生成率或方法效果结论，不重跑基线、不增加MVP/全库测试前置、不自动merge，待删=[]。

---

## 2026-11-03：035已交X——10轨迹增强为主、00保持第二、泛化后置

用户明确优先级：提高mask10合规SR第一，保持00原生SR第二，泛化第三。[035方案](../docs/experiment_plans/2026-11-03_mask10_robot_rewind_augmentation_v1.md)和[实现工单](tasks/035_mask10_robot_rewind_augmentation.md)替代未启动的普通演示续训路线：正常种子先真实重放并记录控制目标，取A完成/B未完成且无持物的场景，仅在新episode起点重置机器人，用真实桥接＋B控制目标跟踪生成匹配的新图像/动作。只收合格专家轨迹，保留所有生成失败分母；不改图贴动作，不用正式90测试样本训练。

首轮候选只用九任务各自然前20普通demo，最多180来源组；每来源3个起点、每起点最多2桥接，最多540起点/1080实际尝试，外加最多180种子重放；不是保证生成这么多成功数据。旧Goal/Object200不作本轮主配方、不删除。训练一组候选1000更新，损失7:3混合10和正常完整任务；同一个adapter评固定10/00各90，共180新model episodes。10与24.44%、00与86.67%各自同口径比较，不用正式测试挑checkpoint。

**上述数据获取/生成、训练/eval预算均未授权真实执行。** 本轮X只写完整035代码与必要CPU/fake，Codex审查/文件准备部署/命令，用户确认并亲自启动。不要套旧380普通来源、两次1000更新、126评测的旧确认问题；该未执行候选现已被替代，不视为035新增仿真许可。035本轮尚无真实生成或训练结果，不能因MimicGen参考机制/030软件通过宣称本方法有效。

030 R2@5bb32713软件accepted/closed保持，035是新研究需求而非返修：复用原完整OFT/LoRA/adapter/索引/固定core报告。新数据有独立provenance、T+1观测与T实际动作，预先投影实际控制到原统计可监督范围，防执行与标签裁剪不一致。模型仍只见完整指令/RGB/proprio，生成器可离线读truth但不进入策略或STOP。旧原图对应标注门槛不套用到新鲜执行记录，不伪造旧对齐passed。

034原90二元报告已完成100%，成功24.44%（22/90）、不成功75.56%（68/90）、完整性错误0；00基线86.67%（78/90）保持。旧基线不重跑，不扩01/11/90、不训练FINISH或复活selector，不以MVP/全库测试为前提。未自动merge或清理，待删=[]。

---

## 2026-11-03：030 R2软件accepted并部署，进入Codex数据准备；034真实报告完成

PR9固定5bb32713（实现dd61b5b6），[R2裁决](reviews/030_v2_round2.md)accepted/closed限约定软件与隔离文件部署；[软件阶段总结](../docs/stage_summaries/2026-11-03_augmentation_software_acceptance.md)。两处阻断已解：合法eef/夹爪proprio精确放行；已交真实可调用的隔离native生产路径，一锚点一条完整指令PROGRESS/chunk8，不插值阶段或伪造ATOMIC。X本轮无返修，不再增加纯审阅或重复训练/评测回归。

Codex独立84/84受影响CPU/fake通过（100%、0skip、10.42秒），实际恢复边界fake，未读取真实轨迹生成标签。源包SHA fb7b6441本地/服务器一致，独立新目录部署；历史native15、执行core97、034包6共118文件字节锁通过。无pip升级、旧目录热改、模型/仿真或真实数据作业。

034实际原90条只读二元派生已结束并取回：90/90=100%，22成功、68不成功，正式SR24.44%，完整性错误0、未解决作业0。两文件SHA与服务器一致，原未知释放留diagnostics，不是第三结果，没有episode重跑。[实际报告闭环](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/stage_summaries/2026-11-03_binary_report_complete.md)。下方旧“仍在读文件”仅为此前快照。

下一步执行者Codex：绑定实际普通HDF、字段/动作时序/normalization/相机与旧backend配置，给准确普通conda/python命令；不用用户手填200记录。不要求九项全部ATOMIC完备；实际增强比例如实报告。**新增九任务最多180普通来源/下载、真实局部导出、两次1000更新及A90+C36=126新eval仍是候选，正在请求用户确认；不自动启动。** 软件完成不代表正式数据/PROGRESS已ready，训练/新模型eval0%。

PR未自动合并，软件交流因未合并依赖继续保留；研究实验未闭环，无清理，待删=[]。

---

## 2026-11-03：X提交030 R2增量，等待Codex审查/部署

[PR9](https://github.com/No1dry/Learning-Not-to-Act/pull/9)增量实现`dd61b5b603a064f30ca5e22d649f378a863477a3`，
见[回复030 R2](responses/030_v2_round2.md)及[生产入口指南](../docs/augmentation_progress.md)。
合法ee/gripper proprio字段按角色精确放行；新增元数据稀疏计划、隔离固定原生组件的PROGRESS producer、
同次export与原证据复用。只标记可靠当前锚点，完整指令/原chunk8/episode尾mask，ATOMIC不足按原约定RAW回退。
已有训练/adapter/评测主体与034保持，不改判据/基线/冻结部署。

本轮实现100%，相关CPU/fake84/84通过（100%，0skip，14.58秒）；含真实已验收SourceEpisode读取合成HDF的RPC测试，
不代表实际物理恢复或真实数据就绪。独立窄审查问题已修。真实数据准备/恢复/训练/新评测本轮均0%。
下一步Codex审查、隔离部署并绑定实际manifest/旧封存runtime与对应证据，用户决定预算并亲自启动真实阶段。
不要求全部技能段标完；无自主作业、清理或自动merge，034无需返修。

---

## 2026-11-03：030 PR9已审，只修真实proprio及进度证据生产；034软件通过

X交付PR9固定9a62732b（实现46dac7c7），[030 R1](reviews/030_v2_round1.md)限定changes_requested两处：[集中工单](tasks/030_v2_round2_production_data_path.md)。一是state子串禁令误拒真实合法obs/gripper_states与ee_states（服务器仅HDF字段/shape/attrs取证，未读轨迹内容/仿真）；二是增强只交外部插件，尚无实际可信进度生产路径。训练、adapter、普通评测主体保留，不整套返工、不因偏好加检查。

Codex独立49个不同CPU/fake用例均获通过：初次48通过/1因测试硬编码同级034目录且mock依赖导入失败，显式提供已交报告包后仅该项通过；原失败XML保留。不是原命令49/49，也不要求X改目录风格。034独立12项通过（0skip、0.79秒），[benchmark R1](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/034_round1.md)accepted软件并隔离部署，无返修。真实原90条二元报告纯文件派生已启动、此时未结束，不是新模型评测。

首轮可用实际可靠PROGRESS锚点，ATOMIC不足按既定RAW回退并报比例；不强迫九任务技能段全标完、不全量重建旧视觉标注。X交两处增量和受影响CPU/fake即可，Codex继续真实文件映射/部署/完整命令。旧2429 selector query不能冒充本轮动作段。

基线完成100%、二元合规24.44%（22/90）、不成功75.56%（68/90）不变；正式训练/新模型评测0%。新增数据及两次1000更新/A90+C36真实预算仍待确认；用户暂不启动。无自主真实实验、merge或清理，待删=[]。

---

## 2026-11-02：X提交030 v2代码（待审）

[PR9](https://github.com/No1dry/Learning-Not-to-Act/pull/9)，实现`46dac7c7`；
[回复030 v2](responses/030_v2_round1.md)与[完整命令](../docs/augmentation_commands.md)。
数据索引导出、RAW/增强OFT LoRA续训、A90/C36普通adapter评测和034公共报告接口已实现。
方法定向CPU/fake49/49通过（100%，0skip），034独立12/12通过；原core d8541ef4和旧数据/判据不改。
034依赖固定`d2afce4e`，见[benchmark PR15](https://github.com/No1dry/LIBERO-Remain/pull/15)，不自动merge。

真实导出/训练/新评测均0%；实际来源/映射、可信增强证据和环境路径待部署，24GB未实测。
局部恢复仅交付显式provider接口，未内置新物理标注器；无增强证据不能冒称Aug已就绪。
下一步Codex审查/部署并集中补齐输入，用户另行确认后启动；不重跑90基线。

---

## 2026-11-02：030 v2直接交实现；正式SR采用二元口径

用户决定正式合规结果只有成功/不成功：九任务mask10基线24.44%（22/90），不成功75.56%（68/90）。旧22 success/67 failure/1 unknown原证据保持；释放未确认的已完成记录在新二元报告记0，不剔除、不伪造违规。原unknown仅作diagnostics，技术错误/缺失作为运行不完整，不能冒充模型失败。benchmark[034](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/034_binary_compliant_success_reporting.md)实现单一报告映射，不重跑或改变物理判据。

[030 v2方案](../docs/experiment_plans/2026-11-02_progress_aware_data_augmentation_v2.md)与[实现工单](tasks/030_v2_progress_augmentation_implementation.md)已交X，直接写代码/必要CPU-fake，不再先等一轮纯方案审阅。当前main未见030_round1交付，不冒称X已审阅。旧v1/旧审阅任务保留为历史并明确被v2替代。

路线：正常完整任务数据＋进度均衡＋真实原子段指令重标注＋轻微photometric，直接对OFT语言attention作动作L1 LoRA适配；在线完整原指令/RGB/proprio，无selector/新头/记忆/FINISH。复用既有200来源/160:40，候选新增九任务各最多20普通演示=180；两次1000更新、A90条+C固定36条=126新增eval。**这些真实数据/下载/GPU预算仍待用户确认；本轮仅代码实现与CPU/fake交接。** 不把同任务适配冒称未见组合泛化，不将正常后缀冒充编辑初态动作覆盖，正式90状态/模型轨迹禁止进训练。

代码交付后Codex一次集中审查、隔离部署并给完整conda/python命令，用户确认后启动；不追加MVP、全库测试、FINISH、旧selector或额外基线，不要求所有增强字段完美覆盖。034报告小改与030开发并行，不让它成为训练代码开发前置。实现/新增数据导出/训练/新模型eval尚未开始；033已完成基线范围保持closed，无自动作业/merge/清理，待删=[]。

---

以下状态段落为此前历史；与本节冲突的旧当前范围、预算和UNKNOWN主结果口径，以本节及v2/034为准。

## 2026-11-02：九任务00/10完整基线已结束，进入030九任务方案收敛

[完整基线结果](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/stage_summaries/2026-11-02_nine_task_baseline_complete.md)和[033 R10](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round10.md)已发布。00/10各90条、总180记录覆盖100%，技术错误/缺失/工件/模型身份异常0。新三30条10全部completed，旧六60复用；同口径官方目标达成00=86.67%（78/90）、10=40.00%（36/90），下降46.67个百分点。10合规确认24.44%（22/90），67失败、1UNKNOWN；不把UNKNOWN改为成功/失败。

新增三项官方13.33%（4/30）、合规3.33%（1/30）；抽屉/微波炉均0%、双壶合规10%。九项完整保留，高分双杯100%与汤罐奶酪90%不删除。新30原视频全部取回并SHA核验；唯一UNKNOWN双壶3号目标在348步达成、到520释放仍未知，不为单条不确定追加实验或改评分。

033仅基线准备/执行/本轮结果审查范围closed，研究/030仍open。下一步Codex更新030为当前九任务版本，明确数据/有效动作覆盖、普通续训对照与预算，用户确认后交X实现。旧030 v1含8任务/旧90/80条与32子集，不能照旧预算直接执行。正常演示后缀不等于外部完成A且机器人初始位姿；正式90评测状态/轨迹禁止进训练。

不再扩benchmark、重复基线或加FINISH/probe；不复活旧selector为前提。当前无训练/导出/采集授权，X无本轮基线代码待办，用户暂不用启动新实验。无自动真实作业/merge/清理，未合并PR所需交流保留，待删=[]。

---

## 2026-11-02：R7位姿稳定软件accepted并隔离部署，用户启动必要补建

[benchmark R8审查](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round8.md)接受固定d8541ef4（实现c8c50e63）。独立95项本轮CPU/fake通过，0skip、10.01秒；复用X既有153项受影响原回归，不重跑历史大组。A完整150步/151观测位姿准入，qvel只诊断、非A0.01及其他物理/观察/paired回放保持，stability v7与RGB v6分开；旧v4/v6/证书、旧失败保留。

已隔离部署LIBERO-Remain-task033-r7-d8541ef4，输出根task033_r7_d8541ef4。实际服务器纯文件复验原20及证书、三个输入SHA/R5真实20/1/9、固定XML，23.56秒；归档和五个源码SHA一致。没有仿真/模型/训练，microwave_repair输出尚未创建。[完整用户python命令](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/experiment_plans/2026-11-02_task033_r7_server_commands.md)可直接启动，不需等X再确认。

真实初态仍20/30=66.67%ready、新三模型0/30，不能声称v7物理已通过。0真ready才派发剩9，齐30后一次评30；不部分20/allow-missing、不重跑00/旧六/旧20。正式10模型覆盖60/90，00完整78/90保留。X本轮无返修、033open，030训练未启，无自动真实作业/merge/清理。

---

## 2026-11-02：R5真实首源失败；用户确认A位姿稳定修订，已交X

R5新几何/姿态首0的24候选仍400 HOLD未达20低速帧，本轮最长3，实际9680控制调用（约221秒）；其余9正确未派发。新三来源仍20/30=66.67%ready，新增模型0/30，没有VLA失败分数。原R6软件验收保留，但不代表物理修复成功。

[033 R7审查](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round7.md)：保存的末150采样点中，24候选杯子位移跨度约0.111mm/姿态0.086°，native10/Open保持，却各118/150=78.67%瞬时速度超0.01；不是正式150步/151观测证书，缺完整state/接触不能离线造ready。继续只改摆放或加等待缺乏依据。

用户已明确同意[版本化A位姿稳定工单](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/033_round7_pose_stability_revision.md)：A杯子完整150步位置≤5mm、姿态≤1°，A速度诊断，非A速度/原谓词/穿透/机器人/观测及paired回放保留；物理stability_profile与RGB v6分开。旧失败/raw/20ready不改。X现可实现+必要CPU/fake，Codex审查部署，用户启动真实补建；新规则尚未实现/部署。

仍齐30后一次评30，不部分20/allow-missing，不重跑00/旧六，不按模型成败选来源；正式10模型覆盖60/90，00完整78/90。033open、030训练未启，无自动真实作业/merge/清理。

---

## 2026-11-02：033 R5软件accepted并部署，用户启动仅微波炉准备

[benchmark R6审查](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round6.md)接受固定942db12f（实现fc2dd617）：独立45项定向CPU/fake通过，0skip、3.10秒；新工件可被未改06817e61 reader读取/归档，缺第二回放被拒绝。不重跑旧全组。四姿态真实碰撞几何重算，原24/400及全部物理/评分/v6门槛保留，首0真ready才派发剩9。

隔离代码LIBERO-Remain-task033-r5-942db12f，输出根task033_r5_942db12f。服务器仅文件复验旧20原引用/证书、两个输入SHA和固定真实XML，22.09秒；无native/model，microwave_repair尚未创建。[完整用户python命令](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/experiment_plans/2026-11-02_task033_r5_server_commands.md)可直接启动，无需再等X确认。

真实初态仍20/30=66.67%ready、微波炉待补10，不能声称已物理修好。用户选择齐30后一次评30，不部分20、不allow-missing或自动串联。九任务10模型覆盖仍60/90，00完整78/90；原20/旧六/00不重跑。033整体open，X本轮无返修，训练030未启动；不自动merge或清理。

---

## 2026-11-02：真实R3来源20/30通过；用户决定齐30再评

用户完成来源补建，新三10初态20ready/10failed=66.67%：抽屉/双壶各10ready，微波炉10构造失败，不是VLA 0%成功率。实际原记录240候选/96,000保存样本均400 HOLD未达连续20低速帧，最长13；微波炉共96,800控制调用，无150构造/paired回放通过。X后续a8958bf5仅确认R4文档，未改已冻结06817e61实现；不重复测试或部署。

[033 R5](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round5.md)与[微波炉窄修复工单](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/033_round5_microwave_candidate_construction.md)已发布：仅A几何/姿态候选，保持门槛/24及400上限，避免同方案十次盲重跑；旧20、00、旧六不动。用户明确等待微波炉修好后一次评30，不启动部分20或allow-missing。Codex文件配置/盘点ready20，不是模型/仿真启动。

九任务10模型覆盖仍60/90=66.67%，新三0/30；00仍78/90=86.67%、覆盖100%。033仍open，训练030未启动，数据/预算待确认；无自动真实作业、merge或清理。

---

## 2026-11-02：033 R3已验收部署，用户可启动必要22来源准备

benchmark [033 R4审查](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round4.md)接受固定06817e61（实现65e0509d），独立53项CPU/fake通过；R2物理修复沿用，不返工。隔离部署代码LIBERO-Remain-task033-r3-06817e61；实际服务器纯文件plan exit0、无blocked/reuse问题，原5＋完整原记录派生3＝新三10来源8/30=26.67%就绪。其余22来源为20物理补建＋双壶7只paired300回放＋9必要构造/回放。

[用户启动命令](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/experiment_plans/2026-11-02_task033_r3_server_commands.md)已给；Codex没有运行native或模型，不自动串联eval。九任务00仍78/90=86.67%、覆盖100%；10模型记录仍60/90=66.67%，新三30未开始。X本轮无返修，033整体open，未merge/清理。训练030的数据与预算仍待确认，本轮不增加方法实现或启动训练。

---

## 2026-11-02：九任务00收齐86.67%；10来源仅余RGB接入收尾

用户完成新三30条00：26成功/4失败、30全部completed；与旧六60合并，正式九任务00为78/90=86.67%，覆盖100%，UNKNOWN/技术/工件/模型身份异常均0。新增抽屉90%、双壶80%、微波炉90%。[完整结果](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/stage_summaries/2026-11-02_task033_nine_normal00_complete.md)及30原视频已本地归档，不重跑00。当前10只旧六60已评，新30尚未启；总记录覆盖150/180=83.33%，不是全九10 SR。

[PR14 R2审查](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round3.md)：独立280 CPU/fake通过，原venv软链接复现1 passed；抽屉/微波炉/续跑/解释器software accepted，不返修这两项。RGB当前仍提案，无真实25 ready声明。

Codex完整原审计新增step15有10像素差1，9像素提案仍会拒绝该来源。已作任务无关v6裁决：同状态、相机/来源与非RGB原规则通过时，uint8最大通道差≤1，变化面积只作诊断；原v4/旧失败不改。[033 R3最后接入任务](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/033_round3_rgb_profile_implementation.md)已交X，优先复用完整已存证据，缺回放仍用户补，不能伪造。

待X完成v6全链后Codex一次隔离部署/给必要补建命令，避免用户重复跑已知旧面积门槛。当前不用再跑00或部分10，也不自动启动真实仿真、模型、训练或合并。方法库不复制评分；030数据/预算仍另行确认，旧90不恢复，资料不清理。

---

## 2026-11-02真实制备：先跑已就绪00，10缺口交X独立修

用户运行033制备后，新三任务00为30/30 ready（100%），Codex已纯文件配置并验证selected30/ready30，用户可直接启动30条00模型评测。10仅双壶index1/3/4/5/6共5/30 ready（16.67%），其余25是来源制备失败，不是模型失败。

[benchmark R2结果](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round2.md)与[实际修复任务](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/033_round2_source_construction_fixes.md)已交X：抽屉In容积90°坐标系被旧支撑假设拒绝、微波炉杯子角速度未稳定、双壶细小RGB比较/重置差异。旧00、旧六和五条有效10全部复用，不热改aedfe169或改旧失败为通过。

下一步用户跑00模型，X修10构造/观测兼容性，Codex随后审查给仅补25来源命令。新三模型本次读取时尚未启动，Codex只读原报告/配置，未运行真实仿真/回放/模型/训练。030预算与数据仍另行确认，不因准备问题增设训练前置或恢复90范围。

---

## 2026-11-02：033运行路线软件accepted，用户可启动新三任务制备

[benchmark PR #13](https://github.com/No1dry/LIBERO-Remain/pull/13)固定aedfe169，Codex独立187项CPU/fake通过。新九任务软件与本机已冻结runtime路线accepted，源码隔离部署及文件准备完成；[033 R1](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/033_round1.md)与[阶段记录](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/stage_summaries/2026-11-02_task033_review_and_file_deployment.md)给出范围和证据。

有一个便利配置工具会解引用venv解释器的P2，新增CPU复现失败并已交X最小修复；本机逐字节复用已跑通runtime，正确venv路径不变，用户不必等工具补丁。未热改a23或旧环境，PR未自动merge。

旧六00/10各60记录已实际只读复用，来源与模型身份issues均=[]。当前九任务记录覆盖66.67%，不是新来源ready或成功率；官方达成00=86.67%、10=53.33%，合规10=35.00%另列。新三任务来源还未真实准备，新60条模型0%。用户下一步启动来源构造/回放，Codex读取后给新增模型命令；X小修不作为新门槛。

当前方法库不复制benchmark实现；030训练数据/预算仍待确认，未自主启动仿真/模型/训练、停止作业或清理资料。

---

## 2026-11-02用户范围替换：九个LIBERO-10，取消旧90补建

用户明确批准官方LIBERO-10全部九个复合任务（ID 0,1,2,3,4,6,7,8,9），四个90退出当前默认范围，原数据/代码保留。见[本库033交接](tasks/033_libero10_nine_compound_tasks.md)与[benchmark完整033](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/033_libero10_nine_compound_tasks.md)。旧两缺90任务准备/补测取消，不再启动此前031命令，也不伪称物理修复成功。

旧六主轨00/10各60复用，共120/180已有轨迹覆盖66.67%；补id3/8/9各10条00/10，只新增60条，正式两条件各90。新实现/制备/模型评测尚未完成，不因更新harness重跑六任务。X负责benchmark实现及032适配，Codex审查部署给命令，用户启动。方法库不复制评分。

同时更正旧00口径：六主轨已有官方目标达成52/60=86.67%；此前58.33%是合规率诊断，不是官方SR。旧10合规35.00%不可直接与00官方SR相减。032按官方达成同口径对照，掉桌检测降诊断，旧分数/UNKNOWN保留。

030的数据增强评测目标跟随新范围；训练数据/预算仍待确认，不自动增采或训练。补九任务不妨碍分析已有六任务，也不把旧90当方法开训门槛。当前仅文档交接，无自主真实作业、实现代码推送、merge或清理。

---

## 2026-11-02：80条00完成，R2制备软件已接受

[benchmark阶段结果](https://github.com/No1dry/LIBERO-Remain/blob/main/docs/stage_summaries/2026-11-02_task031_normal00_eighty_results.md)：80/80完成（100%），确认合规成功43.75%、明确失败36.25%、待定20.00%、技术错误0；旧同八任务10合规26.25%。六主轨00确认58.33%、10为35.00%；两个迁移任务00/10均0。保留16条UNKNOWN，不称它们模型失败；两个缺任务尚未评测，不记0%。

[R2软件审查](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/031_round2.md)accepted，42项CPU/fake及原R1复现通过，不再要求X返修。制备源码隔离部署，文件盘点00可复用18/20（90%），10有18个候选、均仍待独立回放及2个构造。用户下一步启动真实制备，Codex随后读取结果再提供补20条00/20条10命令。评测固定a23，不重跑已完成80条00或旧80条10。

现有篮子任务出现清楚落差，支持推进增强设计；不等待额外全库/全mask检查，也不按模型成败挑任务。030数据范围与训练预算仍待确认，本次没有启动训练或任何真实作业，没有自动merge/清理。

---

## 2026-11-01：031首批00已验收部署，可由用户启动

[benchmark 031 R1](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/reviews/031_round1.md)：固定a23a8116首批00路径accepted，独立190项定向CPU/fake通过，服务器纯文件来源80/80 ready。没有新仿真/回放/模型/训练/评测；用户下一步启动八任务80条00，030训练暂不启动。

另有一处明确P2：原库存ready且operations为空时，依赖丢失后普通制备continue可能自动重建。已将完整fake复现和最小小修实际提交benchmark工单；X只修这一处，不阻塞首批00，不新增GPU验收。修复前不使用该制备continue组合。两个00阶段保留相同冻结评测源码，制备小修另部署、不热改当前目录、不因此重跑80。

缺两任务仍待真实制备及结果审查，不冒称已恢复100条。分工保持X实现、Codex审查部署、用户启动，PR未自动merge，旧数据/失败/交流保留。

---

## 2026-11-01最新优先级：先补00能力对照，同时修复两项缺失任务

用户希望先测对应原始00的SR，再开始030增强，并提出同时修复原两个准备缺口。已实际交接[benchmark源库031](https://github.com/No1dry/LIBERO-Remain/blob/main/collaboration/tasks/031_normal00_control_and_missing_two_tasks.md)，本库[031指针](tasks/031_normal00_and_missing_two_benchmark_handoff.md)仅用于定位，不复制评分或制备实现。

X实现00独立入口与selected-mask10有界修复；Codex审查部署/给命令，用户启动真实阶段。先已有8任务00共80条，不被两任务修复拖住。若全部恢复，00共100条、10复用旧80并补20条，新模型目标120条；尚未启动、不得自动追加。原20缺失不是模型失败。

本次只读原审计：场景9来源4在150步中仅step142腕部7像素差1超旧6像素限；黑碗来源5仅step7 qvel[12]绝对值0.163608超0.01。真实成因和修复有效性尚未确认；没有新sim/回放/模型或改阈值。旧raw/失败/80条结果保留。

030数据增强方案可继续一次审阅，但真实训练排在本轮能力对照/补齐结果审查后。030的数据范围和GPU预算仍待确认；不将写方案视作数据已ready或实验授权。实现代码在benchmark源库，不自动改纯导出的Eval库或合并旧PR。

---

## 2026-10-31最新：030数据增强方案已提出，等待一次集中审阅

用户要求将数据增强想法写成具体方案。Codex已提交[030方案](../docs/experiment_plans/2026-10-31_progress_aware_data_augmentation_v1.md)与[给X的审阅任务](tasks/030_progress_aware_augmentation_plan_review.md)。当前仅完成方案/文档交接，不代表用户已经批准新数据范围、GPU预算或代码实现。

候选路线：正常完整任务数据＋进度均衡采样＋真实原子段指令重标注＋受控photometric扰动，直接适配OFT；首轮不绑定旧selector、新关系头/记忆或FINISH，在线仍用原完整指令和RGB/proprio，原benchmark保持。旧三模块架构是后续组合候选，不再当作本次数据路线的准备前置。

必须显式确认的范围修订：旧20任务只有1个双最终目标；方案建议加入六主轨复合任务的正常演示、最多120新增来源，定位“同任务正常演示适配→外部进度干预测试”，不冒称未见组合泛化。旧20任务/160:40分组不改；编辑评测初态和轨迹不进训练。已有2429条selector监督query不是动作数据集。

建议预算为普通续训/增强各1000次更新，增强同80条＋对照固定32条=112新增episode；均尚未批准/启动。旧100计划/80可用/20缺来源保持，基线不重跑，不自动补状态。24GB训练显存与新动作数据可用性尚未知，不能称ready；X一次给出实际实现路径，不再安排MVP或无关检查。

029后续用户已明确表示停止；保留已完成/未完成轨迹和失败历史。本地已读取的旧快照为5/80完成、SR0/5，仅basket，不冒称停机时最终分母或全部模型结论。016—029已有软件验收不倒改，也不把软件通过当方法有效。

**下一步执行者：X只审阅030并回复一次技术可行性意见；Codex收敛。用户确认数据范围/预算后再进入实现、部署和亲自启动真实阶段。** 本次无GPU、HDF处理、下载、部署、自动merge或清理。当前文档提出范围完成100%；新实现/数据导出/训练/评测尚未启动。

---

以下为历史记录；其旧“当前”用语不覆盖上方2026-10-31交接。

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

## 2026-10-25：028第3条因重复supports暂停，029修复/续跑已验收部署（最新）

028已完成basket s000/s001两条，均模型失败，SR0%，2/80=2.5%；s002 q3技术错误是supports重复entity，不能记模型失败。该生成约束遗漏由Codex负责；旧3条attempt及所有数据保留。

用户要求下一步，Codex直接完成[PR #8](https://github.com/No1dry/Learning-Not-to-Act/pull/8)@5af83dcb：无放回标签语法保留325种合法有序子集，不事后去重、不改validator/权重/评分。原q1/q2/q3保存图像+模型历史重建失败请求，6图/2766输入tokens，真实生成666 tokens、原严格校验通过；无仿真/动作。36项受影响CPU/fake通过（100%，42.50秒）。

新增显式--continue-from：验证旧raw/sidecar/video及固定来源/模型配置，继承全部已完成结果（含失败），只跑剩余；新目录/版本lineage单列，不假装旧2条是029执行，不改旧技术失败。控制台已补[SR/live completed]及最终双口径SR。三环境部署100%，服务器文件级预检passed（模型/仿真未创建），明确2继承/78剩余/下一条s002。selector五文件与真实诊断一致，复用证据、不为评测入口改动再跑GPU。

029软件修复/部署范围accepted；新78条尚未启动（0%），总已完成仍2.5%。下一步用户按已交完整conda/python新命令启动剩余78条；Codex分析结果，X无返修。旧2条不重跑、第三条明确从原初态重试，不中段恢复、不自动启动整批/merge/清理。见[修复与续跑总结](../docs/stage_summaries/2026-10-25_unique_supports_and_explicit_continuation.md)。
