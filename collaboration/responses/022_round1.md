# 022 首轮交付：固定 Object 十任务历史名称表

**最终 remote 实现 SHA：[`4e945eb978a76db7b09977f119fdc30f4e0963fb`](https://github.com/No1dry/Learning-Not-to-Act/commit/4e945eb978a76db7b09977f119fdc30f4e0963fb)**，既有 [PR #2](https://github.com/No1dry/Learning-Not-to-Act/pull/2)未合并。该提交包含本轮全部代码、测试、指南和最新工单/审查，完整Git tree与本地受测实现`5b11be3617f941e7b27c6cfc9c64292313661717`一致。本回复随后提交；含回复的最终交付HEAD和完整tree核验记录见PR交接评论，不伪造自引用SHA。

准备/实现100%；定向选择238项：234通过（98.32%）、4因Windows symlink权限跳过（1.68%）、0失败；实际执行234项全部通过。内部任务审查和最终增量审查均通过，无遗留代码问题，待Codex独立验收。本轮真实标注/训练/评测0%，没有启动或停止真实作业。

## 精确补表与证据

本轮是[022工单](../tasks/022_object_historical_name_coverage.md)批准的补充，021原五对Goal名称范围已验收，不倒改旧裁决或失败。固定dataset仍为`yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`，catalog、任务数量、原始数据和预算不变。

`egrs.sim.historical-bddl-names.v2`包含15条独立精确记录：原5条Goal和新增10条Object。每条显式绑定suite、旧basename、canonical basename、源文件和完整原instruction；指令已与冻结registry/目标映射核对。运行时不按文件名推断语言、不做全局pick→pick_up替换或模糊匹配。

Object条目的证据来源为[022已有文本证据](../tasks/022_object_name_evidence.json)：alphabet soup、bbq sauce、butter、chocolate pudding四条`observed_in_prior_events=true`，`evidence_status=observed_in_prior_events`；cream cheese、ketchup、milk、orange juice、salad dressing、tomato sauce六条为false和`anticipated_unobserved`。后六条仅为获准预期兼容，不标为真实已观察/物理验证。原五条Goal仍指向021证据并记录已观察；旧v1产物和历史指南保留。

原`name_compatibility`新增观察状态字段，保留版本、来源、dataset/revision、source/file/task_group、episode/source_id、完整instruction和原/规范化标识。所有已存在字段仍须校验，canonical仍须由data.attrs明确提供；缺失canonical、全旧名、未知别名、混用两个已知别名、跨suite/task、错误物体/目的地/指令或registry均拒绝。原安装BDDL hash锁、历史字节`unverified`、native目标和对象检查保持，不据名称表直接产生SAT。

新增证据状态经worker inspection/audit保留，但不进入冻结样本、history或processor prompt。原Mac XML包装、固定c6依赖、XML拓扑、state/RGB、可观察性及输入白名单均保持。未改模型、评分、目标映射、控制器、原数据或运行环境。详见[离线监督指南](../../docs/offline_sim_supervision.md)。

## 定向验证

使用已有Python、固定`EGRS_CORE_ROOT`和新建忽略临时目录；原生边界为fake，没有修改依赖或启用OpenMP绕过。

```text
python -m pytest tests/test_sim_metadata.py -k object_historical --basetemp .work/task022/red-metadata -q
42 failed, 19 passed, 73 deselected           # 旧v1缺少兼容的有效RED

python -m pytest tests/test_sim_native.py -k 'metadata_native_constructor and object_' --basetemp .work/task022/red-native-final -q
24 failed, 96 deselected                     # 最终fixture对旧v1生产代码的RED

python -m pytest tests/test_sim_metadata.py --basetemp .work/task022/final-metadata -q -rs
130 passed, 4 skipped in 0.47s

python -m pytest tests/test_sim_native.py -k 'metadata or dataset_identity or transport' --basetemp .work/task022/final-native-2 -q -rs
87 passed, 33 deselected in 3.20s

python -m pytest tests/test_sim_pipeline.py -k 'mixed_run or export or operational_request or actual_cli_dispatch' --basetemp .work/task022/final-pipeline-2 -q -rs
17 passed, 19 deselected in 6.08s

git diff --check                             # exit 0
```

共234通过、4跳过；native/pipeline另有52项未选择，不声称重跑全模块。名称用例覆盖全部十条、四种旧/新字段组合、21类绑定负例及原五条Goal。fake构造覆盖全部十个Object、错误native原子和错误hash；传输/导出保留真实兼容审计结果而不改变原样本/history/prompt。

初次fake构造fixture误把占位`object_1`当成原生对象名，随后改为冻结目标映射中各物体的准确名称；生产谓词没有改变。对最终fixture再次使用旧v1取得24项全部失败的RED，再恢复v2并取得上述GREEN。中间失败与修正记录完整保留，不将fixture错误当成有效修复证据。

四个skip均为既有BDDL symlink测试的Windows `WinError 1314`：suite_outside/suite_other/file_outside/file_other。本机没有执行这四条symlink分支，不把skip算作通过，也不为此添加平台预检门槛。

没有重跑完整XML测试模块、全库或多平台测试，没有新增GPU/物理预检。合成HDF/PNG和fake原生边界仅验证软件契约，不是读取本批真实数据的证据。

## 未证实项与下一步

历史作者BDDL/资产字节相同、真实native兼容、state/RGB物理对应和可用监督覆盖仍未证实。Codex针对021已有文本/安装文件的247项通过和495引用解析记录保留为既有证据，不冒称是X本轮新跑，也不当成标签成功。

旧020r2的134个失败事件且无最终manifest仍是旧记录，不据此声称全量结束或可以导出。原021代码、旧失败、全部分母、RGB/窗口/registry和160/40划分保留，不因未知来源阻止可靠子集，也不热改旧运行目录。

**下一步操作和执行者：Codex审查固定remote实现和PR最终交付HEAD后，准备新方法目录/配置/输出并给完整命令，复用c6和现有数据；用户亲自启动真实标注。** X本轮软件交付100%；未读取真实HDF/图像、加载仿真、恢复/渲染、运行模型或训练/eval，不自动重跑或串行追加后续阶段。
