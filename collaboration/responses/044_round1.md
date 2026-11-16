# Task044 R1：原版官方SOG10的P1/P2提示词诊断交付

2026-11-16，X。实现commit **`8259a1040b0a83551678db5cbb7849c836bac090`**；基于accepted PR17@`7d28d515be610f33f959f36d25623e86796671ce`，fetch并读main@`5e48028`的044工单、冻结语言表与预算批准记录，本地合入文档的merge为`e390c38`。仓库为 **No1dry/Learning-Not-to-Act**；未向benchmark库提交修改。新分支`x/task044`、PR base为`x/task042`，便于审查本轮增量；不自动合并PR17/18或新PR。

已发布[新PR19](https://github.com/No1dry/Learning-Not-to-Act/pull/19)，保持open、未合并。实现和交付正文分别固定于上述`8259a104`与`9812638c55bdab881eaeb369c6087d53196014a3`；后续本条仅补PR链接。最终远端head/tree及关键文件blob核对收据保留在本地044交付备份，不使用可变分支名冒称固定实现。

**实现及定向CPU/fake交付100%，待Codex验收；部署、真实模型/仿真/评测均0%。** 本轮未SSH、下载/加载7B、操作服务器、生成初态/标签/索引、训练或重跑基线。所有旧数据、模型、分数、raw、视频及失败署名保留，删除/待删清单为`[]`。

## 已交付的实现

- `egrs/prompt044/prompts.py`：标准库冻结合同与18句精确映射。manifest原始字节SHA为`e648ef202c31e6e99e14478f6ec36952a1791d2187bf023a224b25974f669566`，同时校验JSON内容；`.gitattributes`阻止换行转换，原JSON字节未改。P1严格为原完整指令＋`. `＋固定初始事实；P2仅冻结B指令；双壶无实例编号。未知/冲突指令及错误variant拒绝，不做模糊匹配、搜索或改写。
- `policy.py`：专用外层factory消费044字段后恢复原native factory，直接构造原`OpenVLAOFTPolicy`，不attach研究adapter，不加载H0/H1或042权重。冻结官方SOG10@`638918f3d1c2e43a39a8a20772bdb8b91835e4b7`、原OFT@`e4287e94541f459edc4feabc4e181f537cd569a8`，校验实际原动作头/proprio投影/统计/推理源码metadata和`libero_10_no_noops`。双RGB、proprio8、中心裁剪、chunk8、seed7、H520及非量化native推理保持。
- **语言仅在`base.predict(clean_observation, model_instruction)`边界改变。** 原传感器白名单过滤后只有RGB/proprio进入底座；原source instruction、goal_specs、完整A+B目标仍留给原执行器/评分器。提示整episode固定，不读逐帧谓词、sidecar、未来、VLM或训练标签。原native formatting/tokenization照常执行；审计的是实际传入其API的字符串，不冒称字符串等于最终token序列。
- `evaluation.py`：独立`task044-prompt-eval-v1`、native ten-only入口。完整原043 H1 plan字节SHA `bafc7238da1ed94e8a1b6d4b98ce7f9d41bb59bad887be2d7de9e1d2ce5d68df`仅作来源/runtime/环境元数据；绑定expected10 SHA，逐一用原API重建并exact compare六旧批＋三新任务的36执行单元/90条。原core@`d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`、reporting@`d2afce4eb074b777364daddea2c08bd70731865f`、双bridge/proxy身份保持；复用原runner、直接原workflow reader及034二元report，不塞假adapter/空00进入旧036合同，不继承043模型结果。
- 原完整A+B、A回退/错抓/炉子约束、释放/放置、视频/raw及端点验证保持。P2目标达成但A被破坏仍失败；底层UNKNOWN保留诊断并按既定binary规则计不成功，固定90分母；技术错误或工件缺失报告不完整，不伪造正式成功。P0仅历史22/90=24.44%的aggregate-only引用，未提供逐条可绑定证据，不编造配对，不以训练过的H0替代。
- 实际调用前独占、持久写入`prompt_audit.jsonl`：原/模型语言与SHA、variant/table SHA、episode/query序号、返回或错误。先记账再forward；每组90次reset、每episode≤65次、总≤5850次predict；失败不退款、不在同实例重试。最终绑定原attempts/raw query数、包括零query初态失败，并核对closed-worker audit SHA；缺失/篡改/错误返回使正式证据不完整。
- `launch.py`、CLI及`run_both_sequential.sh`：两个独立进程/worker，P1正常退出且正式90报告完整才启动P2。持久独占marker、新输出拒绝覆盖/重复、配置SHA及相同输入检查；首组失败停止次组，不自动恢复/清理。输出和marker保护原data祖先、源/旧run、权重与依赖输入根。每组逐episode记录started，原执行单元完成后更新数量/90和百分比；执行与正式核验分开，最终每任务/总体SR、视频/raw沿原合同保存。

新增文件还包括`configs/prompt044/evaluation.{p1,p2}.example.json`、三个定向测试文件、[完整运行文档](../../docs/task044_usage.md)、[CPU机器证据](../evidence/044_cpu_fake.json)和两份JUnit。既有模型/训练/评分/bridge模块均未修改。

## 定向CPU/fake结果与命令

最终主组 **80 passed，0 failed/errors/skipped**：policy21、evaluation20、entry/launcher19、原双bridge/proxy20。新60项11.44秒，原bridge20项2.25秒；[60项JUnit](../evidence/044_cpu_prompt.junit.xml)与[20项JUnit](../evidence/044_cpu_bridges.junit.xml)保留断言结果。额外原reader2项及A/炉子约束2项也通过，**另列4项，不重复累计主组**。原读写/评分边界覆盖真实已有Python实现上的合成数据，未调用真实reset/step。

在本地044 worktree中使用`C:/ProgramData/anaconda3/python.exe`执行下列命令。测试复用同级已验收的`LIBERO-Remain-task033-r2`与`LIBERO-Remain-task034` CPU fixture checkout（上述固定revision），未重新构建真实数据；临时文件放工作树外。

```bash
python -m pytest tests/test_prompt044_policy.py tests/test_prompt044_evaluation.py tests/test_prompt044_entry.py \
  -q --tb=short --show-capture=no --basetemp=../../.release-tools/t44/final01 \
  --junitxml=collaboration/evidence/044_cpu_prompt.junit.xml
python -m pytest tests/test_trajectory_environment_dispatch.py tests/test_trajectory_proxy_transition.py \
  -q --tb=short --show-capture=no --basetemp=../../.release-tools/t44/bridges01 \
  --junitxml=collaboration/evidence/044_cpu_bridges.junit.xml
python -m pytest -q --basetemp ../../.release-tools/t44/review-reader-temp \
  'tests/test_trajectory_evaluation.py::test_original_readers_verify_archive_actions_observations_and_video[v3-mask10]' \
  'tests/test_trajectory_evaluation.py::test_original_readers_verify_archive_actions_observations_and_video[v3-nine-mask10]'
# 以下2项在既有LIBERO-Remain-task033-r2 CPU fixture目录运行：
python -m pytest -q \
  tests/test_headless_runner.py::test_single_goal_a_regression_is_sticky_even_after_recovery \
  tests/test_headless_nine_runtime.py::test_nine10_preserves_invariant_and_original_five_observation_endpoint
# 回到044源码目录：
bash -n scripts/prompt044/run_both_sequential.sh
python -m egrs.prompt044 --help
git diff --check
git diff --cached --check
```

fake完整90→90使用实际044规划、调度入口和原binary mapper，仅模型/执行/reader边界使用合成fixture；两组fresh worker、无00、每源一次，实际模板严格解析及首组失败不启动第二组均验证。原scorer三种A violation即使终态恢复也89/90，原读取器篡改视频拒绝。audit错误schema/序号/结果/字符串、零query失败及持久写失败不继续调用也覆盖。

早期TDD缺模块红灯、audit字段绑定失败和修复记录保留本地。原scorer回归fixture最初缺verified-source绑定造成3失败，补fixture证据后20项通过，未放宽评分。原reader第一次默认Windows临时目录PermissionError，测试体未执行，指定外部basetemp后2项通过。JUnit仅脱敏hostname与规范LF，原始日志本地保留，不把历史失败改写成通过。集中接口复核未发现已知阻断缺陷；其worker模块接线文档建议已补充。这是实现团队复核，不替代下一轮Codex验收。

## 运行交接

完整conda、两解释器editable接线、配置模板填写、环境变量、前台/后台替代命令及输出语义见[044运行文档](../../docs/task044_usage.md)。两既有环境需指向同一验收方法源码：原worker从core目录启动并设置自己的PYTHONPATH，不能只靠外层`cd`。后续部署命令使用`--no-deps --no-build-isolation`，不升级环境/改全局源码；worker解释器直接取原runtime，保留venv symlink路径。本轮没有执行这些部署命令。

验收并填好文档中的现存路径后，**用户**在原simulation环境、验收源码目录执行：

```bash
export LNA_P1_CONFIG="$LNA_ROOT/configs/task044/evaluation.p1.json"
export LNA_P2_CONFIG="$LNA_ROOT/configs/task044/evaluation.p2.json"
export LNA_P1_OUTPUT="$LNA_ROOT/runs/task044-p1-eval-001"
export LNA_P2_OUTPUT="$LNA_ROOT/runs/task044-p2-eval-001"
export LNA_044_MARKER="$LNA_ROOT/launches/task044-p1-p2-001"
bash scripts/prompt044/run_both_sequential.sh
```

预算严格P1 90＋P2 90＝180新episode，predict总上限11700；00、训练、初态/标签/索引、额外seed/prompt/前向probe/MVP、P0基线重测均0。入口自身做既有必要来源绑定，不增加另跑plan/预检门槛；运行失败保留现场，交回用户决定，不自动重跑。

批准JSON的ten-task input projection摘要未提供字段选择定义。本实现以批准的**完整reference plan文件SHA**、expected10 SHA和逐源exact compare硬绑定，另记录完整ten任务投影及批准声明，不猜字段放宽准入，也不冒称未知投影已匹配。现存完整文件足以严格绑定；该记录限制不是新增真实实验前置任务。P0配对证据不足如实aggregate-only。

无新增已知软件硬阻塞。真实服务器路径/依赖/模型初始化与实际SR未验证，CPU/fake不能证明提示收益或真实180完成。下一步执行者：**Codex**验收新PR、隔离文件部署及填实际配置/命令；**用户**亲启P1→P2正式180；再由**Codex**汇总两种informed diagnostic相对历史P0的结果。X不部署、不代跑、不自动merge。
