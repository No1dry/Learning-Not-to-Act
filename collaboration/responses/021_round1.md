# 021 首轮交付：历史名称与 XML 资源前缀兼容

**最终 remote 实现 SHA：[`5d8e67a240e96d41c7080f6c2ac5652be327d09e`](https://github.com/No1dry/Learning-Not-to-Act/commit/5d8e67a240e96d41c7080f6c2ac5652be327d09e)**，位于既有 [PR #2](https://github.com/No1dry/Learning-Not-to-Act/pull/2)，未合并。该提交包含本轮全部代码、测试、运行指南与最新工单/审查，已核对完整 Git tree 与本地受测提交 `a30c609c6040e5ef74700bfcc65411809d4d3e25` 相同。本回复是随后新增的交付说明；含本回复的最终交付 HEAD 和完整 tree 核验结果另记于 PR 交接评论，避免在文件内部伪造自引用提交 SHA。

准备与实现完成度 **100%**。本轮受影响 CPU/fake 共247项：**242通过（97.98%）、5跳过（2.02%）、0失败**；已执行项通过率100%。任务审查和整体增量审查均通过，无未处理代码问题；不代替外部 Codex 验收。修复后真实来源验证/标注、训练、评测均 **0%**，未启动或停止真实作业。

## 改动与规则

- `egrs.sim.historical-bddl-names.v1`只包含[021已有事件样例](../tasks/021_runtime_compatibility_examples.json)中的五对准确名称。绑定 `yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`、`libero_goal`、catalog源文件/task_group、`demo_0..9`/source_id、原instruction和严格registry目标映射。canonical必须由`data.attrs.bddl_file_name`明确提供，不能凭旧字段一致或缺失canonical推断通过。
- 仅归一实际存在的env_args/kwargs旧标识；保留各原值、basename、规范化结果、missing/validated/normalized/conflicting/malformed状态、映射版本及来源依据。未知别名、跨任务/suite、错误dataset/revision、指令/registry不符仍拒绝。控制器将已核对inventory的`dataset_identity`放在操作请求中，与原source descriptor分开；旧的非别名请求继续兼容，不重建inventory、窗口、RGB或原HDF。
- canonical安装BDDL的原hash锁和构造前复核保持；内嵌正文存在时仍严格比较，缺正文时历史原字节一致性保持`unverified`。名称表不是历史语义/物理相同的证明。cream-cheese继续使用冻结的`on`原子；伪造为`in`仍在native目标核验失败，不用改谓词迁就文件名。
- `egrs.sim.historical-xml-assets.v1`在方法侧新增纯包装器，只将直接asset mesh/texture/hfield的file属性内精确Mac前缀转为固定c6已支持的历史home前缀。复用c6的XML字节span与真实有界resolver；保留suffix直到core执行`.`/`..`归一、歧义根、缺文件、symlink包含关系和目标hash检查。无basename搜索、资产下载、core热改或环境修改。
- XML审计区分真正`source_xml_sha256`、`intermediate_xml_sha256`、最终`processed_xml_sha256`；core报告明确名为`intermediate_core_report`。按引用occurrence记录原值→中间值→归一suffix→目标文件及hash，重复引用不覆盖。错误reason提供未解数量与有限原因摘要，完整证据仍在inspection/events/audit。
- 原XML拓扑、相机/控制器、native目标/对象、state/时间规则、原RGB对应和残差阈值保持。元信息/XML诊断不进入student样本、history或prompt；实际fake pipeline导出测试覆盖该隔离边界。

完整映射与配置说明见[离线监督指南](../../docs/offline_sim_supervision.md)。新包装器依赖固定完整annotation reference core **`c6dc98de0c54517c976057598b60f4cedf7fa3e5`**；本轮核对该core为干净工作树，未改固定依赖或旧eval core。此处不是新增部署或预检门槛。

## 受影响验证

全部使用合成文本/HDF/PNG、临时资产和fake原生边界；XML专门用例及映射构造用例执行真实c6纯资源解析，不把resolver mock成永远成功。使用已有Python与`EGRS_CORE_ROOT`，无依赖调整或OpenMP绕过。

```text
python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py tests/test_sim_xml_assets.py tests/test_sim_pipeline.py -q --basetemp .work/task021/red-02 --tb=short
53 failed, 152 passed, 5 skipped in 11.66s  # 实现前缺少接口/规则，预期RED

python -m pytest tests/test_sim_native.py -k historical -q --basetemp .work/task021/red-native-03 --tb=short
8 failed, 86 deselected in 0.79s            # 映射构造入口RED

python -m pytest tests/test_sim_native.py -k historical_cream_wrong_atom -q --basetemp .work/task021/wrong-atom-01 --tb=short
2 passed, 94 deselected in 0.37s           # 错误native原子继续拒绝

python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py tests/test_sim_xml_assets.py tests/test_sim_labels.py tests/test_sim_pipeline.py -q -rs --basetemp .work/task021/final-01 --tb=short
242 passed, 5 skipped in 11.96s            # 最终受测实现树

git diff --check                          # exit 0
```

首次RED的临时目录父级缺失造成setup错误，随后只创建忽略的临时目录并取得有效RED。首轮GREEN有两条测试把冻结`on`误写成`On`；核对原映射后只修正测试字面值，最终结果如上，未变更生产谓词。所有中间证据保留，不将失败轮次隐去。

五个skip均为Windows创建symlink的`WinError 1314`：既有BDDL的suite_outside/suite_other/file_outside/file_other四种，以及新增XML symlink escape。普通越界、歧义、未知前缀、缺文件和外部依赖拒绝均已执行；**本机未实测这五条symlink分支**，不把skip算作通过，也不为此新增全平台门槛。

## 尚未证实与交接

未读取本批真实HDF/图像，未加载原生仿真、恢复状态、渲染、调用教师/模型或训练/eval；没有代停/重启020r2，也不假定其已结束。历史作者BDDL/资产字节、真实native兼容、物理/RGB对应、可观察监督覆盖仍未证实。当前安装hash仅约束实际选择的文件字节，CPU/fake通过不保证后续物理对应成功。

旧019、020及020r2输出、失败解释和分母保持。021工单的82/200失败（41%尝试；42名称、40XML）仍只是已有日志快照；3200查询processed/supervised均0，不改成全量统计或成功。局部来源仍可独立产生可靠监督，全部计划来源/查询继续进入覆盖分母。

**下一步操作和执行者：Codex审查上述固定remote实现及PR最终交付HEAD，再部署新的方法目录/配置/输出，复用c6和现有数据；用户亲自启动真实标注。** 不重下载、重建inventory/窗口/RGB，不自动串行导出、训练或评测，不新增GPU预检。X本轮软件交付100%，真实阶段0%。
