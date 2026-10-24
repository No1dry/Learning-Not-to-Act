# 023 首轮交付：两条固定旧来源的对齐诊断

**固定 remote 实现 SHA：[`77ffdaa8db5a463164fb3b67222c5835ed18024d`](https://github.com/No1dry/Learning-Not-to-Act/commit/77ffdaa8db5a463164fb3b67222c5835ed18024d)**。该提交包含本轮代码、测试、运行指南和最新工单/审查；完整 Git tree 与本地受测实现 `4c02460c08de8c4eb23722041e2d9e4bc543a48f` 相同。本回复随后提交，含回复的最终交付 HEAD 与 tree 核验见 [PR #2 交接评论](https://github.com/No1dry/Learning-Not-to-Act/pull/2)，PR 未合并。

准备/实现100%；53项定向CPU/synthetic/fake测试全部通过（100%），0跳过、0失败。内部独立审查完成，待 Codex 独立验收。本轮真实诊断恢复/渲染、训练和评测均0%；没有代启、停止或重跑真实作业。

## 任务与入口

本轮实现 [023 工单](../tasks/023_bounded_alignment_diagnostics.md) 的取证路径，不修订对齐准入、RGB阈值、完整状态等价证书或监督规则。022已完成作业的200来源/3200查询、165条可监督结果及原160/40划分完整保留；5.16%监督覆盖和dev0不当作训练/验证方案ready。

运行说明见 [两来源诊断指南](../../docs/alignment_diagnostics.md)。由 Codex 部署到新方法目录，使用旧作业的完成 manifest 和一个不存在的新输出目录，随后由用户亲自执行：

```bash
python -m egrs.offline diagnose-alignment \
  --manifest /path/to/completed-022/manifest.json \
  --output /path/to/new-023-diagnostics
```

以上路径是占位符，worker解释器、模块路径、source timeout和native配置复用旧manifest封存的backend-config。无需export或ready=true，不改写旧manifest/code identity；当前诊断实现identity另记并用于worker启动字节锁。固定完整c6参考core、原环境、原数据和原RGB均复用。

固定来源与probe：

| 来源 | probe帧 |
|---|---|
| `libero_goal/open_the_middle_drawer_of_the_cabinet_demo.hdf5#demo_0` | 0,66,129 |
| `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5#demo_0` | 0,72,139 |

两条均为原train来源；每个probe仅运行same_state、next_state、replay_action三种原操作，agentview/wrist两原相机，保留原orientation和下标。总上限18次候选恢复、6条已有动作、36组图像比较、72次直接RGB/segmentation渲染；初始化及原restore/refresh内部渲染另计，仍受原source timeout、reset/substep预算约束。无settle/hold、换样、重试扩容、新视角或模型forward。

## 独立诊断产物

输出均在新的诊断目录，主要包括：

| 产物 | 用途 |
|---|---|
| `config.json`、`requests.jsonl` | 固定计划、预算、旧backend和选中绑定，旧/新实现身份 |
| `events.jsonl`、`errors.jsonl`、`progress.json` | 逐步刷盘事件、初始化/运行异常和保守计数 |
| `measurements.jsonl` | 每个source/frame/rule/camera的whole、foreground、background MAE、像素数、每通道偏差和旧max度量 |
| `states.jsonl` | 源next_state对replay，以及实际恢复next_state对replay的独立比较；完整状态hash/max及time/qpos/qvel/act分组 |
| `png-index.jsonl`及PNG | 原RGB、按原orientation对应的候选RGB、x1绝对差异、foreground mask和带绑定标识的对照图 |
| `manifest.json` | 新诊断完成/部分失败状态、身份、原split、已完成产物hash |

状态分组使用运行时state类的`from_flattened(flat, sim)`，完整round-trip一致后读命名字段，不推测扁平数组分段。缺少codec、act或不支持的布局明确记为不可用；无前景或背景时有关残差为null并记录原因，不以0代替。保留旧完整max与原RGB阈值含义，不据新分区指标校正图像或选择候选。

原native原子逐候选独立记录，异常为unknown/null；源XML、实际重写/运行XML、资产、相机及版本/模块身份沿用既有inspection。只校验消费的文本侧车与12个选中PNG绑定，worker仍核对这些PNG与原HDF指定帧的像素一致性，不重扫3200查询图片。

worker启动由当前源码字节identity锁定，即便旧方法目录出现在cwd或模块路径中，也不会将旧代码身份冒作当前执行版本。超时/进程退出/构造或运行异常保留已完成事件与PNG；缺少工作或协议异常不会写成完整成功。CLI在partial/failed时输出实际状态并返回exit 1。`complete`仅代表固定取证操作完成，不表示某个对齐规则已获准。

## 定向 CPU/fake 验证

使用现有Python环境、合成RGB/临时文件和fake native边界；以下pytest进程不读取真实数据、不加载真实仿真或模型。诊断测试中的隔离子进程验证真实bootstrap/超时/退出协议，但原生构造仍为fake。

```text
python -m pytest tests/test_sim_diagnostics.py -q -rs --basetemp .work/task023/final
43 passed in 39.25s

python -m pytest tests/test_sim_native.py::test_worker_retains_incremental_frame_on_failure_and_stdout_is_json tests/test_sim_native.py::test_duplicate_or_out_of_bounds_frames_rejected_before_factory tests/test_sim_native.py::test_isolated_transport_journals_prior_event_on_timeout tests/test_sim_native.py::test_isolated_transport_rejects_foreign_source_event tests/test_sim_native.py::test_real_launch_binds_method_before_native_with_stale_cwd tests/test_sim_native.py::test_worker_modules_import_without_native_or_model_packages tests/test_sim_pipeline.py::test_cli_exposes_independent_stages_without_native_imports tests/test_sim_pipeline.py::test_actual_cli_dispatch_uses_explicit_worker_and_separate_export -q -rs --basetemp .work/task023/regressions
10 passed in 2.17s

git diff --check
exit 0
```

本次合计53通过、0跳过、0失败（执行项通过率100%），仅上述选择范围。覆盖固定案例/帧/候选与恢复/动作/渲染计数、原相机和下标绑定、历史与当前身份分离、真实API形状的fake codec、残差数值、未知native原子、PNG身份/索引、超时/硬退出/构造失败留痕、无标签/后续任务和旧文件不变。已检查合成PNG对照的绑定文字及x1差异标识。

RED证据：最初22项因入口尚未实现失败；补充边界测试曾暴露预原生配置/当前代码/选中PNG复核、异常native返回和多余result字段缺口，以及早期worker拒绝身份时stderr未及时保存。另以独立失败用例验证构造异常audit丢失与partial CLI误报exit0，随后修复并取得上述GREEN。中间orientation fixture误绑产生的失败已单独说明和修正，不当作产品缺陷证据；原始记录保留。

验证仅使用合成图像/临时文件与fake native，不冒称真实恢复、物理对应或相机/光度成因已验证。未跑全库、多平台或完整XML模块，也未增加GPU预检。旧022的Codex验收与真实作业结果作为既有事实保留，不冒称是X本轮新跑。

## 未验证项与下一步

两条案例尚未真实执行，因此不能断言Object偏差来自颜色、几何或资产，也不能断言完整状态差异只落在速度/时间、或native监督语义一致。诊断数据不会成为selector样本、history、prompt、actor输入或训练标签；没有自动export/train/eval链路。即使两条案例可解释，也不能据此宣称200来源全部修复。

**下一步操作和执行者：Codex审查固定实现与PR最终交付HEAD，隔离部署并提供一次完整命令；用户启动两来源诊断；Codex查看原图/重建图和分组误差后，再决定是否提出版本化修正规则。** 不提前提高阈值、钦定next_state、放宽等价证书、整轨放行、重划dev或生成多候选共识标签。
