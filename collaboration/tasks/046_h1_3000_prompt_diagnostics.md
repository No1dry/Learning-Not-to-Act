# 046工单：H1@3000的固定提示词对照

状态：用户已提出实验；现在交X实现，不先交综述或泛审。Codex做过定向入口核对，确认不能把旧044原版入口直接指向研究adapter。正常分工仍为X代码/CPU-fake、Codex建议式审查/隔离部署/完整命令、用户亲启真实作业。

## 1. 要交付的最小功能

新增独立`egrs.prompt046`入口（命名可等价清晰），在**固定045 H1@3000**上运行同一批90个10来源的P1、P2。P0直接读取已完成的045同模型原指令报告，不新执行。不要引入训练、规划器、VLM、FINISH、在线状态真值或新数据。

三组定义及预算见`docs/experiment_plans/2026-11-18_task046_h1_3000_prompt_diagnostics.md`。冻结数据见`collaboration/evidence/046_reference_bindings.json`；逐字提示词沿原`044_prompt_manifest.json`，不要增加“更自然”的改写。

依赖accepted PR20固定`10531b626998d02f6168d23df02501ce64d36969`（含045完整状态/显式checkpoint-step）与当前main文档；参考PR19固定`e8445b6ae640f21446533592326c645a6d42894b`的`prompt044`。从已验收依赖建新分支/新PR，不自动merge。需要044纯提示词/审计辅助时可复用或小范围版本化复制；不得为了兼容046放宽旧044的“只许原版模型”验证，旧043/045无提示入口也不修改。

## 2. 策略边界：只改变真正传给模型的语言

推荐外层046包装045的`egrs.hint043.policy.HintPolicy`：

1. 剥离046外层配置，按045原路径构造H1，显式`hint043_checkpoint_step=3000`，只attach一次该LoRA。
2. 校验实际adapter是H1、update3000，actual SHA等于冻结绑定；保留真实官方底座/动作头/proprio/统计/seed等来源身份。不得只写一个期望SHA而不验证实际加载身份。
3. 从原source instruction严格查九任务冻结表。P1/P2只把`model_instruction`传入现有HintPolicy.predict；后者仍调用原生OFT的格式化/processor/forward/action后处理。不新拼token、不改动作chunk、不加另一模型。
4. 观测过滤沿045/044既有白名单，仅RGB/proprio。环境目标、物体ID、接触、谓词、仿真state等不得进入模型。
5. P1是初始A完成事实，整episode固定；P2是固定B指令。均不根据在线GT改写。双壶仍用集合描述，不隐式使用物体实例ID。
6. **source instruction、goal_specs与评分仍完整A+B**，不可随P2改成单B。controller/reset/seed沿旧接口，不把完成事实作为动作门控。

模型身份必须如实为`research_adapter_loaded=true`且绑定H1@3000，不沿旧044写false。046顶层元数据应显式标注`prompt_variant`、冻结manifest SHA、`deployment_initial_semantic_information=true`、`prompt_fact_time=episode_initial_only`和`prompt_fixed_during_episode=true`。不要在046顶层沿用误导的“无提示部署”标记：可以新增明确字段表达当前诊断有外部语义信息，或把外层deployment_hint设为true并按新046合同校验。**artifact内部**的045训练身份`method_adapter.deployment_hint=false`是不可变原证据，不能改写它；046应明确区分它与本次推理期额外提示。此处不是让你修改旧HintPolicy或旧reader的语义。

## 3. 固定90人口和P0复用

配置显式提供：variant、manifest、reference_plan、p0_summary、method_adapter、benchmark/reporting roots、base_runtime、legacy dispatch。所有实际私有路径由Codex验收后填部署配置；X不SSH或请求把大plan/权重推GitHub。

绑定P0源`task045-h1-step3000-eval-001`的原plan与summary字节SHA，加载时验证其H1@3000身份、成功完成、10人口90与原评分口径。从此plan提取原10 tasks/expected，构造ten-only046 plan。metadata/来源哈希校验可沿044/045正式入口复用，不额外做真实预检或重复全量资格流程。

P0应从**已签名绑定的原summary**读取90个10的逐episode二元结果，核对总62/90；不要拿044原版22/90，不拿H0，不仅硬编码68.89%。新summary记录P0来自历史同模型run、未重新执行、原summary SHA，P1/P2原生目标达成与二元合规仍分开。

新执行预算只有P1/P2各90；不把P0标成新执行/继承重跑，也不伪造P0 prompt_audit。既有人口同源且新动作推理路径保留时，可按episode ID列同模型P1−P0/P2−P0得失，声明P0是历史参照。若发现推理路径无法保持可比性，报告具体原因，不暗中补跑90条。

## 4. 审计、报告与失败处理

- 复用044的模型语言字符串/SHA审计：逐predict记录原指令、实际模型指令、variant、调用序号、episode/reset顺序，真正成功返回/异常状态。读取核对真实raw query数和audit闭环，不能只记录配置宣称输入。
- 每组最多90 resets、65 predict/episode、5850 predict；两组总11700。失败不退款重试、不自动换prompt、seed或模型；exclusive audit/output/marker保留，禁止覆盖旧run。
- 沿既有原生reader与二元mapper核验全A+B，不改评分源/阈值/版本或把技术错误算模型失败。新合同必须允许并严格核验真实H1身份；不能借用只许原版模型的044 reader再删除其检查。
- 正常输出plan/batch/progress/summary/report/原视频/raw/审计。显示episode完成数量与百分比，最终原核验后打印正式SR；不得把仅模型执行100%说成正式报告完成。
- 报告至少含：当前模型P0/P1/P2总分、每任务各10条SR、P1/P2各自相对P0的同episode新增/丢失，以及P2相对P1得失；完整原目标评分未变。不要给只有10诊断的P1/P2拼旧00造AVG。
- 可引用044原版三组历史作为另一模型参照，但分开标注模型身份与历史来源。P1失败不直接证明模型不理解完成信息，P2也不是理论上界。

## 5. 一次启动与交付

交付一个用户亲启的P1→P2串行启动器：首组90正常退出且正式报告完整后才启P2；原子新marker、防重复、失败保留且不自动重试，不启动P0/00/训练。示例CLI尽量沿原`python -u -m egrs.prompt046 evaluate --config ... --output ...`，实际完整conda/python命令由Codex部署后给用户。

定向CPU/fake覆盖即可，不跑全库或真7B/真实仿真MVP：

1. H1@3000正确attach且仅一次；H0、1000/2000、错误adapter SHA被拒；底座与控制配置不改。
2. 九任务P1/P2文本逐字相等、完整source/goal不改、模型仅接RGB/proprio；元数据区分研究adapter与当前额外语义提示。
3. P0 summary/plan哈希绑定与90逐episode读取；旧原版P0/错误模型/篡改报告拒绝，不启动P0。
4. 真实predict边界spy、reset/audit顺序、调用上限及失败不退款；两臂同不可变输入、输出和输入隔离。
5. 原reader/mapper连接和新046身份正反例、报告逐任务/配对数据算术；技术错误不假成成功。
6. 串行两次命令、第一组失败不启后组、已存在输出/marker拒绝。测试不含任何真实作业。

交新PR和`collaboration/responses/046_round1.md`，列固定实现head、依赖、改动文件、实际定向测试结果和局限。不先泛审/SSH/部署，不修改旧数据权重、评分、旧结果/失败/署名；不自动merge。除明确错误、泄漏、证据失配或已约定关键功能缺失外，Codex审查以建议为主，不因偏好反复返修。
