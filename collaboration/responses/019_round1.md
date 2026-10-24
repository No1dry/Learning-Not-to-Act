# 019 round1：现有观测的仿真监督与固定划分导出

执行者：X。日期：2026-10-24。准备100%；实现及本轮受影响CPU/fake验证100%，最新证据见末节，历史146项运行单列。内部限定审查及最终全变更审查已完成，发现的修正已实现；本轮定向复审、X发布既有PR #2增量及外部Codex审查/部署待执行。真实标注、原生状态恢复/渲染、模型推理、训练、eval均为0。没有打开真实批次HDF/图片，没有导入或初始化真实仿真环境，没有下载模型，没有运行全库测试。

本地实现SHA：Task1 `2256163b33411c17dd606181385cf5d375fe3b46`；Task2及其最终修正 `f09d69cc93945250bee67ff6ec5ba6efed3bcce0`（初始worker为`5e13bcc616a2cd173bf8b5579ec16d11331b10e1`）；Task3首轮 `93ed01b85ddf603904d00c9a407cd68b6f12a554`；导出兼容性修正 `309e5e1fe0d939369b7de9d9b8eed963eac725ed`。这些本地SHA不冒充最终远端head；X在发布既有PR #2增量后，在交接评论记录经核验的精确remote head，供外部Codex审查部署。本回复不自引用未知最终SHA。运行manifest另外锁定实际代码文件字节/hash，导出要求同一实现。

## 已接通的工作流

1. 版本化goal map绑定20条原instruction / 21个独立goal atom。纯契约/label builder按可见支持产生逐字段、逐证据项`sim_supervised`，既有encoder真实获得状态监督token；UNKNOWN、身份/框单独存在及NOT_APPLICABLE不冒充状态监督。既有人类、reviewed_candidate、weak语义和合法history来源保持不变。
2. 独立原生worker使用原保存控制器、机器人、相机顺序/尺寸、场景XML/BDDL及获准asset路径。对齐可显式认证next-state/replay物理等价，记录代表规则，并核对每个获准known-next请求帧；方向歧义、状态/RGB不一致及未认证末帧保留gap。初始化前的stage与重复inspection事件同步保留，超时/硬退出不会丢失已完成证据。
3. 实际CLI `label-sim`先校验固定输入、registry、source/frame/query/camera及分组绑定，再逐来源启动明确指定的独立解释器。每个事件、已完成标签及失败立即flush；最终annotation恢复原query顺序，仅替换样本副本answer/provenance。原payload/history/group_ids/ancestry_known、原窗口/RGB及160/40来源划分不变，不造GT history。
4. `export-sim`核验manifest/全部文件与PNG字节hash、输入/config/mapping/code identity、原payload/group/history/ancestry/query顺序和固定split；由journal事实重建标签并重算覆盖，再调用现有`build_dataset`。原排除attestation只须三个显式true布尔项，任何已有basis/额外依据原样保留。truth/audit侧车不进入train/dev。
5. 新目录拒绝覆盖。所有UNKNOWN/只有身份证据的产物拒绝可用导出；有状态监督的部分子集允许导出，诚实保持`ready:false`。报告提供总体/逐任务/train-dev的计划、处理、有意义监督、gap、UNKNOWN、字段覆盖、自然类别分布、来源及历史可用性；processed不等于supervised。

完整运行配置、版本/hash采集、两条独立命令、文件schema、操作预算及限制见[offline_sim_supervision.md](../../docs/offline_sim_supervision.md)；可复制[backend示例](../../configs/sim_backend.example.json)。示例中的空版本/hash锁须先用文档标准库脚本采集填写，不导入native模块找路径，不热改依赖，不将路径/凭证/权重写进仓库。

Task2最终修正预算：默认F<=18、P=3、E<=15、C=2、M<=100，保守每来源<=57次restore、21次replay action、2100 action物理substeps、264次直接标注render、4698次相机render API调用，初始化另计；这些是源码上限，不是GPU实测。source-wide timeout默认600秒，无自动重试或新采样，无模型操作。

## CPU/fake证据与本机限制

Task3最初RED为21个预期缺模块/CLI失败；实现后20通过、1个失败来自fake将transport异常抛入adapter callback的错误位置，修正fake层次后新增PNG字节变更用例得到预期1失败/23通过，再实现PNG锁后24通过。自查增加额外split来源拒绝用例RED为1失败/27通过，补绑定检查后28通过。另覆盖实际CLI分阶段dispatch、启动阶段hard exit、部分frame超时、stream/result不一致、旧model history保留与oracle history拒绝。

历史受影响完整集合（早于导出兼容性与本轮worker绑定修正，并非最新树重跑）：

```text
EGRS_CORE_ROOT=<既有固定core参考checkout>
python -m pytest tests/test_sim_native.py tests/test_sim_labels.py tests/test_sim_pipeline.py tests/test_data_training.py tests/test_offline_pipeline.py tests/test_offline_review.py -q --basetemp .work/task019/task3-final2
146 passed in 10.80s
```

CLI两个`--help`及变更Python文件compile均exit0，`git diff --check`通过。Task3的28项用例只用合成PNG/来源和fake worker；既有测试含合成HDF、fake子进程与CPU toy单元测试，没有真实标注/模型作业。

必须披露：首次将`test_sim_pipeline.py`排最前的同一六文件组合在既有`surface_support` NumPy矩阵乘法处**进程abort、exit3，未完成验证**。最小数字数组子进程复现：先import torch再首次NumPy matmul触发本机`OMP Error #15`（重复`libiomp5md.dll`）；先NumPy matmul再import torch则exit0。上面的最终顺序采用Task1/2已验证的native-helper在前，146项完成。没有设置`KMP_DUPLICATE_LIB_OK`、改依赖或改实现绕过该问题。该本机测试运行时限制仍存在；独立native worker与模型进程边界保持不变。

真实HDF字段、源场景兼容、对齐残差、可见区域/部件与实际监督覆盖仍待用户作业验证。抽屉内部/容器支撑隐藏、机构活动面不足、倾斜目的物、不确定抓持/释放，以及next-state末帧边界均可产生诚实gap；这是可观察覆盖限制，不承诺真实全部成功。fake通过不代表已得到3200条可用标签。

下一步操作和执行者：X完成本轮定向复审后发布既有PR #2增量，在交接评论记录精确remote head；外部Codex审查该远端head并部署、给出隔离部署命令；用户亲自启动真实标注、检查coverage，再分别启动导出及任何后续模型作业。本地实现子任务未push，未修改Codex维护的验收/状态文件。

## Task3返修1：导出兼容性（取代首轮额外前置条件）

已按审查I1/I2分离历史配置校验与标注运行时可用性：`export-sim`不再要求原worker解释器/导入目录仍存在，只核验配置结构和封存identity；`label-sim`启动前仍检查实际文件/目录。所有原图字节、来源/样本绑定、manifest/config/code/mapping/hash校验保持。导出直接复用原`build_dataset`三个显式true布尔attestation，不要求补写`basis`；已提供的basis（包括空值）和额外依据原样进入report及export manifest。本节明确取代首轮要求“导出须有worker路径、须非空basis”的条件。

focused RED：3 failed,1 passed,28 deselected（缺失worker路径、三布尔无basis及空basis被旧代码拒绝）；修复后focused GREEN：4 passed,28 deselected。扩展覆盖仅解释器、仅导入目录、二者均不可用，并检查此时label仍拒绝启动；只移动`.work/task019`测试临时目录内合成runtime，未触碰系统解释器或真实native环境。

```text
EGRS_CORE_ROOT=<既有固定core参考checkout>
python -m pytest tests/test_sim_pipeline.py -q --basetemp .work/task019/task3-fix1-final
34 passed in 6.23s
```

compile与diff检查通过；按审查范围未重跑未改变的146项组合，无真实作业/依赖修改。发布与审查分工以本回复末节为准。

## 内部审查修正与最终worker绑定

内部限定审查已修正原保存相机顺序/非等尺寸绑定、next-state/replay逐帧物理等价认证及代表规则、原生初始化前的inspection/stage保留，以及上述导出兼容性。最终全变更审查仅余I1：调用者工作目录中的旧`egrs`可能覆盖控制器归属的方法代码。本轮通过绝对路径bootstrap在worker导入前固定方法包根目录、核对控制器冻结的全方法源码identity及实际包/worker路径；原生工作前不符即失败，封存前代码变化拒绝manifest。继承cwd不变，相对core/BDDL/assets仍按调用者目录解析。公开request/event/frame/answer/provenance和manifest版本未改变。

回归保留实际Popen/bootstrap启动路径，只用fixture启动import hook替换原生adapter；覆盖竞争旧包cwd、合法完整事实、相对core/BDDL/两类asset路径、源码identity不符，以及预载错误worker路径。所有不符均在原生工作/事实前拒绝；另验证CLI传递冻结identity及运行中变更不封存。最初focused RED为4 failed,68 deselected；补充worker路径守卫的RED为1 failed,37 deselected；最终focused GREEN为5 passed,68 deselected。

最新受影响集合（native-helper优先，区别于历史146项运行）：

```text
EGRS_CORE_ROOT=<既有固定core参考checkout>
python -m pytest tests/test_sim_native.py tests/test_sim_pipeline.py -q --basetemp .work/task019/final-fix-final
73 passed
```

本轮只验证受影响native/worker与pipeline合成测试；本机OpenMP顺序限制及真实物理覆盖待用户作业验证的边界仍如上。没有依赖修改、真实作业、模型作业或全库重跑。

下一步操作和执行者：X做一次本轮定向最终复审，发布既有PR #2增量并在交接评论记录精确remote head；外部Codex审查并部署；用户亲自启动所有真实作业。本轮本地实现提交由X的发布流程收录，不把内部审查冒称外部Codex验收，不虚构远端SHA。
