# 023 第二轮交付：修正两处生产输入误拒绝

固定 remote 修复实现：[`7f26b6ed30f0c35681cec6aec924880ec1eed00e`](https://github.com/No1dry/Learning-Not-to-Act/commit/7f26b6ed30f0c35681cec6aec924880ec1eed00e)，完整 Git tree 与本地受测实现 `3ad657d925dc00b69f8da06ff2ca82a6e7fc30a7` 一致。首轮实现和[首轮回复](023_round1.md)原文保留；本回复随后单独提交，包含回复的最终 HEAD 与 tree 核验见 [PR #2 交接评论](https://github.com/No1dry/Learning-Not-to-Act/pull/2)。PR 未合并。

本轮针对 [023 首轮审查](../reviews/023_round1.md)的两项 P1。准备/修复实现100%，`89/89项受影响CPU/synthetic/fake测试通过（100%，0跳过、0失败）`。内部独立复核完成；Codex生产输入复核与部署尚待执行，本轮真实诊断恢复/渲染、训练和方法评测均0%。

## 修复内容

1. **core 版本身份**：移除对 `core.root` 目录basename的字面限制，不替换成另一目录名。继续要求固定 revision `c6dc98de0c54517c976057598b60f4cedf7fa3e5`、`allow_reference is True`、原manifest/code/config及消费文件绑定；既有core激活时Git版本和干净状态核验不变。指南已说明路径名称不代表版本身份。
2. **计划与来源schema**：要求所选来源和计划记录分别唯一，按七项计划身份字段比对：`sample_id`、`source_id`、`file`、`episode`、`group_ids`、`task_group`、`ancestry_known`。每项必须存在；descriptor合法增加的instruction、T、orientation、split等字段不再触发全字典误拒绝。source与旧request的完整相等、instruction/registry、T、PNG/相机、split和complete结果等绑定保留。

没有改写、重封或重建生产inventory/manifest，没有重命名/复制core目录来迁就校验。production测试仅用临时合成fixture与受控身份边界，实际进入production分支；这不等于已经读取或验证用户的生产输入。

## 定向验证

在隔离工作区使用合成PNG、临时JSON和fake边界运行：

```text
python -m pytest -q tests/test_sim_diagnostics.py --tb=short --basetemp=.work/task023-round2/green-temp
89 passed in 45.79s
```

受影响诊断模块共89项，全部通过（100%），0跳过、0失败；不是全仓库测试。此前在未修改consumer时运行新增用例：

```text
python -m pytest -q tests/test_sim_diagnostics.py -k "planned_base_schema or production_consumer or consumer_rejects_each_planned or consumer_requires or verified_source_extensions" --tb=short --basetemp=.work/task023-round2/red-temp
12 failed, 34 passed, 43 deselected in 6.54s
```

其中两个正例分别在目录名校验和完整字典比较处被拒绝；另有3个缺source_id案例抛出原始KeyError、7个扩展绑定负例被上游schema误拒绝遮挡，修复后均达到预期校验结果。首次使用默认pytest临时目录时另有46项setup权限错误，未进入测试体；改用新的工作区临时目录后才取得上述行为RED，未删除原临时目录。该环境错误与产品行为失败分别保留，不算通过证据。

此前 `planned_sources=deepcopy(sources)` 的测试结构掩盖了真实schema差异，本次改为计划基础字段与验证后扩展字段。新增回归覆盖异名合法core进入production分支、错误revision/allow_reference拒绝、七项计划身份缺失/矛盾、缺失/重复计划或来源、完整request扩展字段绑定。RED证据见上述记录；`git diff --check`通过。仅重跑受影响诊断CPU/synthetic/fake测试，未重跑全库、完整XML模块或多平台/GPU检查。

## 运行与边界

入口仍为 `python -m egrs.offline diagnose-alignment --manifest /path/to/completed-022/manifest.json --output /path/to/new-023-diagnostics`；完整参数含义见[诊断指南](../../docs/alignment_diagnostics.md)。占位路径由Codex按实际部署提供，不应修改旧manifest以匹配示例。

固定两条旧train来源、各三个既有probe、三个原候选与两个原相机不变；上限18恢复、6旧动作、36比较、72直接渲染。内部初始化/restore/refresh渲染仍另计并受原source timeout/reset/substep预算约束。没有调整0.03/1e-6、标签、原160/40划分或后续任务。旧200来源/3200查询、165可监督条目与dev0均保留。

没有新打开真实HDF/图像、恢复状态、渲染、调用模型或启停作业；实际生产解析、真实诊断与物理对应仍待后续核验。两例诊断不能据此推断全量修复或偏差成因。

下一步操作和执行者：**Codex复核固定修复版本及现有生产文本/选中绑定，隔离部署并提供完整命令；用户亲自启动两来源诊断；Codex根据图像、分组状态误差和原子审计再作研究决策。** 不自动追加全量标注、export、训练或eval。
