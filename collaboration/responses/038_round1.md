# Task038 R1：037-v2实现与CPU/fake交付

2026-11-06，X。按[038工单](../tasks/038_task_control_factorization.md)直接实现，未另写研究综述。**实现与受影响CPU/fake完成100%，待Codex软件审查；真实索引/标注、模型、仿真、训练、评测和部署均0%。** 软件通过不代表真实pair覆盖或方法效果已验证。

实现commit：**`b5849e4e4f7f56b888922e1267870126f5368ccf`**，分支`x/task038`。依赖已验收036 PR11固定`205d6530e1ba389f74166a2e9520a3db7ae0edbf`，本地合并main `62718bc`的任务/证据文档为`120654b`；不自动合并PR11/12或本PR。main尚未含依赖代码，审038增量请比较`205d6530..b5849e4`并区分main文档合入；新实现集中在`egrs/task_control/`。

## 已交付

- **共享训练/评测路径**：`training._student`和`TaskControlPolicy.predict`均调用`task_control.oft.prediction`。同一次OFT前向按实际BOS/图像/proprio/原指令/placeholder布局取56×d动作hidden和图像/原指令prefix；MLP256→z128，瓶颈256残差、只W_out零初始化，再经原冻结head输出8×7。评测不调用旧`base.predict`绕过新模块，保留原相机方向、resize/crop、proprio归一化、动作反归一化与夹爪转换。
- **一次新文件索引**：`index`绑定原003 export及036三池、原父split、全部源与audit/lineage SHA，输出labels/pairs/report/sources/identity。active计数按谓词语义；raw无标签、缺失mask。pair使用normal交接/ten0的实际记录state，按原真实layout排time/机器人坐标，非robot差≤1e-8且robot有变化，双端各保留自身真实动作和有效mask。confirmation不导出；不合格pair保留原BC源；零pair明确不可用且训练拒绝。
- **两组固定训练与恢复**：相同网络/初始化/三池与pair序列，主项12+4+4与.50/.25/.25保持，再加pair两端共22观测。准确实现C0/C1指定count/self/swap/align公式，swap只换z、双方不detach、不多跑backbone。所有8次参考先于训练学生图，旁路全部新增LoRA/上下文/残差，恢复逐模块模式/checkpoint/cache状态。每组1000、末1000、参考≤9024、学生≤24560，dev和head-only诊断有明确上限。
- **完整新adapter合同**：保存全部新增tensor与LoRA、逐tensor/文件SHA、arm/recipe/base/原统计/index身份；缺/多/错形/错dtype/错hash拒绝。checkpoint保存optimizer/scheduler/RNG、三池/pair sampler与双budget；相同checkpoint续跑与连续tiny训练tensor逐字相等。
- **独立两arm评测入口**：`eval --arm c0|c1`默认文件plan；显式run才执行。原九任务10合规/00官方各90、双bridge/proxy、原reader、H520/chunk8/seed7与全视频保持；每arm新180，不继承旧分数，旧输出拒绝覆盖。新schema/factory/arm严格绑定；只对036评测引擎提取显式内部contract，036公共默认合同和旧测试保持。

输入始终只有双RGB、完整原指令、proprio8；action标签、count、pair、mask、时间、task/source ID不进模型。count只作辅助，不硬路由、不FINISH；单个底座、无外部VLM/第二教师模型。

## 测试与集中修复

最终组合 **130 passed，0 failed，0 errors，0 skipped，27.89秒**；其中新038测试90、原数据/036评测回归40。证据：[汇总JSON](../evidence/038_cpu_fake.json)、[原JUnit](../evidence/038_cpu_fake.junit.xml)。

```bash
python -m pytest \
  tests/test_task_control_cli.py tests/test_task_control_evaluation.py \
  tests/test_task_control_index.py tests/test_task_control_model.py \
  tests/test_task_control_reference.py tests/test_task_control_training.py \
  tests/test_retention_data.py tests/test_trajectory_data.py \
  tests/test_retention_evaluation.py \
  -q --tb=short --show-capture=no \
  --basetemp .pytest-task038-handoff --junitxml .pytest-task038-handoff.xml
```

实际本机最后一次使用`C:/ProgramData/anaconda3/python.exe`及仓外隔离basetemp，完整命令在证据JSON。全部为合成文件/微型CPU网络；未跑全库、多平台、真实GPU或原模型实验。

独立集中审查发现0 Critical、1 Important：legacy/显式语义可让抽屉/微波炉空required-open列表通过。已固定两任务所需谓词，并对双端长度与严格`is True`逐一校验，空/缺失/false/非bool拒pair；32个新增定向case覆盖该缺口，原BC源保持。先红后绿，scoped复查确认解决，无遗留material finding。

较早一次组合在冻结core的Windows `os.replace`遇到WinError5，随后残留`.tmp`导致FileExistsError，失败XML与红绿工件保留本地。新fake流程测试隔离该文件系统原子写边界，仍写真实临时JSON并保留exclusive-new/update语义；**没有修改生产core**。最后组合仍包含原reader/视频和036回归，不宣称完成Windows原子写认证。

## 必要实现选择与边界

1. 旧035 lineage不一定有新`task_semantics`。通过generated父源、scope谓词和lineage.source核对后使用原`facts.goals`（其生产路径已按active语义映射）；若有显式映射则继续核验。两路径均独立绑定固定required-open，不能由空声明放宽。不是取official前两项或重做旧资格。
2. 原指令token跨度使用offset与processor实际ID核对。固定官方默认AutoTokenizer加载链支持Fast offsets；本轮仅静态核对，未实例化真实tokenizer。自定义慢tokenizer或不一致映射明确拒绝，不猜切片。
3. durable预算前向前落盘，恢复不退款。若账本已超前于所选checkpoint，明确拒绝精确续跑；需集中报告实际消费量再决定获批恢复方式，不能删账本继续。正常保存点完整恢复已由CPU测试验证。
4. C0/C1对照的是swap/align这一包，不能从两组单独归因每个loss。真实有效pair量、训练收益、SR、新颖性及更强泛化均待后续；未放宽物理/评分或添加真实预算。

没有需用户现在决策的软件硬阻塞。上述真实工件覆盖与预算仍是既定后续准备事项，不以本轮测试伪称已具备。

## 部署文件、命令与下一执行者

完整模板见[Task038使用文档](../../docs/task038_usage.md)，含`source conda.sh`、`conda activate`、一次index、两arm训练/显式resume、两armplan/run及独立report命令。模板使用占位路径，**尚不是已获批准可立即启动的实际实验指令**。

Codex验收后使用新checkout中的完整`egrs/`及现有依赖锁，新文件为`egrs/task_control/*.py`、三份`configs/task_control/*.json`。必要共享提取是`egrs/retention/evaluation.py`；训练与policy worker解释器都需能导入同一新包。索引引用原003/036及其源文件，不复制模型/HDF/raw至GitHub，不覆盖冻结部署。

下一步：**Codex**审查本PR、隔离部署并准备真实路径配置，向用户确认最终预算；**用户**批准后亲自启动真实index、两组训练和360条评测。035/036全部代码证据、分数、权重、视频、失败/raw、原037文档/PR12均保留；未删除、未启动/停止服务器作业、未自动merge。
