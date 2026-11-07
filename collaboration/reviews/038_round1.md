# 038 R1：软件验收通过，已部署；预算已批准，用户启动

2026-11-06，Codex。审查[PR13固定head](https://github.com/No1dry/Learning-Not-to-Act/pull/13) `5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`，038实现`b5849e4e4f7f56b888922e1267870126f5368ccf`，相对已验收036 `205d6530`审增量，而非重审全部依赖。

**裁决：accepted/closed限本轮软件实现、受影响CPU/fake和文件部署；X无需返修。** 方法SR、真实配对覆盖和新颖性仍open，PR未自动merge。用户本轮明确批准两组1000更新/参考≤18048/学生≤49120/新模型360和文件准备；所有真实index、标签、训练、模型eval仍用户亲自启动。

## 通过的关键点

- 原双RGB/完整指令/8维proprio是唯一策略输入。任务ID、mask、pair、计数标签、动作或未来事实不进提示词/网络。
- `training._student`与`TaskControlPolicy.predict`共用`oft.prediction`。一次backbone取得56动作hidden与当前图像/原指令prefix，实际插入长度由projector_features读取；未只改训练、让eval绕过新模块。
- 128维z、256瓶颈残差、仅W_out零初始化；原action head冻结但允许对输入求导。只交换z，两端H/proprio/自身真实动作/尾段mask不交换；两个z都有梯度，不多跑backbone。
- C0/C1相同三池/pair流及新初始化；公式、类归一化、22学生观测/更新与两个budget符合规格。原策略参考先于学生图，旁路全部新增LoRA/上下文/残差，逐模块training/checkpoint/cache状态正确恢复。
- 新adapter严格保存全部新参数、hash、arm/原base/统计/index身份；完整optimizer/RNG/采样器/budget恢复。账本超前于checkpoint会明确拒绝精确恢复，不假退款。tiny连续/恢复训练一致。
- index使用active goals，不套official前两项；实际记录非robot状态/layout、同父split/语义/释放/required-open、T+1/T与确认帧排除都有定向正反例；不合格pair不移除原动作源，零pair不伪成功。
- 两arm各新180使用原九任务10二元合规/00官方评分、双bridge/proxy与原reader，全视频。036评测引擎只是显式contract提取，旧默认与回归保留，不改benchmark core/评分。

## 本地独立检查

受影响共130个独立CPU/fake用例最终通过，0遗留失败/错误：初次112 passed、18 setup errors（本地测试所需兄弟core/reporting目录未映射）；复用已验收d8541ef4/cb8aca6a本地快照建立**测试专用符号链接**后，只重跑这18项，18 passed。未修改生产代码、锁或原fixture判据，也没有把第一次setup error记成通过。原/后续XML保存在本地review目录。

X提供的130 passed/Windows原子写隔离边界原文保持、固定PR head本地备份，未据此声称真实模型运行通过。没有跑全库、多平台、真实tokenizer/模型、仿真、标签或训练/eval。

另仅读服务器已固定OFT源码与tokenizer配置：官方get_processor经AutoProcessor/AutoTokenizer默认加载、projector_features包含实际proprio插入；本轮没有发现其与新增切片合同冲突。未加载真实tokenizer/模型，不替代后续实际训练前向证据。

非阻断建议：index/数据构造有若干重复SHA读取，后续如真实准备耗时明显，可在不减弱身份绑定的前提下按path缓存；当前不为此返修/延迟、不新增检查门槛。不得把缺少全量真实pair统计当作已通过，也不补做物理回放。

## 部署与已批准预算

独立目录`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task038-5a6452ab`，配置`configs/task038-5a6452ab`。19关键源/配置文件与PR源SHA相同、4个实际配置上传SHA一致；原worker和simulation两个venv的包映射指向此副本、从core cwd核对模块来源，未升级依赖。旧035/036目录和工件未改；两venv当前editable映射更新是部署变更，明确保留该事实，不宣称环境零变化。

base-runtime逐字节复制原036实际runtime，旧九任务来源/core/reporting/双bridge输入保持。两个eval配置已写，但adapter尚未训练，**未生成/冒称最终权重绑定的真实eval plan**。

用户已批准：零新仿真生成/重建状态/重跑原始基线；一次新文件索引，C0/C1各1000，共2000更新；reference≤18048，student≤49120；两模型分别10/00各90，共360新episode。每组固定末1000，原三组3000与036续训仍未批准。

部署100%；真实index/标签准备、训练、模型eval均0%。原003/036文件、035/036权重/结果/视频、旧失败及037审阅保留，不删除/merge或代启停真实作业。

## 下一步操作和执行者

**用户**按[已部署的完整常用命令](../../docs/experiment_plans/2026-11-06_task038_index_training_commands.md)运行一次index，正常结束后直接训练C0，完成后C1，不并行占同GPU、不再等人工预检。**Codex**读取用户交回的实际产物，准备末1000的360条评测命令与结果分析；不自己启动。**X**本轮无需改动，等待真实明确问题，不追加功能/实验。
