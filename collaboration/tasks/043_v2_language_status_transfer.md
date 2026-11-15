# Task043-v2：语言状态提示迁移（工单草案，待数值预算批准）

2026-11-15 · Codex → X。

**当前不要实现或泛审。** 用户已同意方法方向，正在确认完整预算；本工单仅提前把需求一次写清，STATUS更新为approved后才直接实现。旧043 REGA不是本任务，不执行旧G0/G1、实体/定位头或042续训。

完整规范：[043-v2详细规格与预算](../../docs/research/2026-11-15_task043_v2_language_status_transfer_spec.md)。该规范是功能/损失/预算的权威入口，下面是交付清单。

## 1. 批准后直接做什么

在accepted PR17固定`7d28d515be610f33f959f36d25623e86796671ce`的可运行依赖上开新版本，结合最新main文档，不自动合并任何旧PR。

1. 独立CPU prepare：从040主索引和既有audit生成绑定当前帧的自然语言状态sidecar，≤143960键，不读新像素、不改原索引、不回放/标注模型；缺失不造假。九模板、语义映射、双壶集合化和split见规格§3。
2. 独立新训练入口：H0/H1均原始官方OFT新LoRA；不安装旧task_control模块、pair训练流、041教师或TCIF。共同036三池普通保持；有提示辅助视图只在H1输入r，H0仍原prompt；deploy都仅当前RGB/proprio/完整原指令。
3. 精确实现§4的采样、mask归一化、共享参数两视图、stop-gradient与固定迁移warmup；所有reference先于训练图。aux逐个反向释放，主输出只算一次，无中途optimizer.step。
4. 原配置、reference/模型前向账本与完整状态/恢复、可见日志与末1000保存/开发；CPU prepare另记录处理键数。不能漏记辅助前向。两个1000、reference≤18048、训练模型前向≤54144、正式360，预算待批标识不能绕过。
5. 复用现有正式180入口的population/runtime/core/reporting/评分与双bridge，仅新增adapter读取与方法factory；对照与方法正式输入严格同为无提示。不是在推理中读取sidecar、选择器或额外教师。

建议入口为`python -m egrs.hint043 prepare|train|evaluate`，配置分h0/h1。名称/模块布局可合理调整并说明，不因风格返修；关键是完整功能接线和简单命令。新版本schema与旧reader分离，既有run保持可读。

## 2. 定向CPU/fake验收必需项

- 当前帧vs未来帧、True/False/None、双壶无隐藏ID、抽屉/微波炉active映射、父组split与原指令绑定；缺失不转False、不把释放未知说成未释放。
- 未eligible跳过辅助，不重采样；两臂同主draw与辅助draw slot；零eligible的全局拒训/局部继续规则；原主样本人口不丢。
- H0辅助输入与无提示prompt一致；H1仅辅助多r；student/eval仅三输入白名单。测试故意传入hint/GT被拒绝或隔离，不允许静默进入模型。
- 提示长短变化后依然取正确56个shifted动作隐藏，原8×7/mask/归一化/夹爪符号不变；不要依赖旧固定文本长度或全局可变mask。
- 正确masked标量均值、.50/.25/.25主权重、.25辅助、固定λd日程；aux图反向＋detach目标、reference不回梯度、学生保留真实专家BC。不能拿hint文本做LM生成loss偷偷换方案。
- reference旁路LoRA/mode/RNG恢复，non-reentrant checkpoint反向不受后续prompt/mode变化污染；不同时持有全部辅助图。
- 逐调用前扣预算、无提示/辅助分别记账、开发不重复学生主前向；四次开发/固定末1000/恢复不退款；fake短循环检验公式上限。
- 同初始LoRA、H0/H1独立optimizer/账本；新初始化不得加载历史adapter；完整状态保存恢复、身份和fingerprint；正式配置严格类型，特别0.0不能写0。
- 新模型接原10/00各90 formal接口的fake闭环、全视频配置、实际末权重绑定、正常才接下一臂、防重复输出/marker；不启动真实run。

只跑受影响CPU/fake，不跑全库旧测试、7B前向、真实HDF读取/状态标签生产或仿真。若本地缺固定fixture，报告精确缺失，不改断言/静默skip冒称通过。

## 3. PR与回复

新PR附本次实现commit、依赖head、改变的文件/契约、真实执行的测试数与原始输出；写`collaboration/responses/043_v2_round1.md`及CPU/fake机器证据。报告明确区分软件100%和真实数据/训练/eval0%。若有明确规格错误，集中一次说明；不将非关键风格问题变成下一轮泛审。

交付至少包含CPU生产配置、两臂训练配置、180×2正式评测配置和顺序启动器模板；真实路径/权重由Codex验收后部署填写，不在公开文档写凭证/私有服务器路径。不要自动merge、SSH、发布网站或启停真实作业。

## 4. 批准后可转发X的短prompt

> 请先读最新collaboration/STATUS.md；只有043-v2数值预算已标approved才开始。按collaboration/tasks/043_v2_language_status_transfer.md及链接的完整规格直接实现，不再泛审；基于accepted PR17固定7d28d515的新版本，不执行旧043 REGA。两臂原始OFT新LoRA，唯一计划差异是训练辅助视图是否带当前状态文字，部署均无提示；实现CPU sidecar、精确loss/采样/预算/完整恢复及原正式360接线，做受影响CPU/fake，新PR并回复043_v2_round1.md。不得SSH或运行任何真实生产/模型/仿真/训练/eval，不自动merge；代码验收后由用户启动真实阶段。
