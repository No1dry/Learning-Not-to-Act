# 030 v2 R2｜合法 proprio 与可执行 PROGRESS 生产路径

2026-11-03，X。按[集中工单](../tasks/030_v2_round2_production_data_path.md)及
[R1 审查](../reviews/030_v2_round1.md)增量修复，继续更新
[PR9](https://github.com/No1dry/Learning-Not-to-Act/pull/9)。

- 已 fetch 并合入最新 main `4ee76bc`，同步提交 `057d8b2`。
- 本轮实现：`dd61b5b603a064f30ca5e22d649f378a863477a3`。
- 软件实现 100%；本轮相关 CPU/fake 84/84（100%，0 skip）通过。真实数据准备、局部恢复、训练和新模型评测本轮均 0%，没有启动任何真实作业。
- 保留首轮训练、adapter、评测主体；034 无返修、无改动、无重测。没有更改物理判据、基线、旧数据、冻结部署或自动合并 PR。

## 两项修复

1. **proprio 按角色精确放行。** 允许 `obs/ee_pos`、`obs/ee_ori`、`obs/ee_states`、`obs/gripper_states` 的合法 3+3+2 / 6+2 输入，保留原 synthetic `proprio` 别名。世界 `states`、`robot_states`、物体/谓词/接触/reward/success/future 字段仍拒绝；没有修改 HDF 绕校验。显式顺序、8/7 维、时间偏移、归一化和模型 item 白名单保持。
2. **提供实际 producer，不再只有外部插件接口。** `egrs.augmentation.progress_native.NativeProgressBackend` 在隔离子进程中调用固定已验收恢复组件；`export --progress-config ...` 同次生成证据和非空 PROGRESS 索引。`progress plan` 只读元数据，输出来源/锚点及恢复数量上界，不读取 HDF 内容或创建仿真。

生产路径复用历史 `Learning-Not-to-Act@fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391` 的 15 个文件字节锁，保留既有 XML/名称、BDDL、controller、恢复、原图对应和 native 谓词验证。没有 merge 旧 PR、调用旧全景标注流水线或重新实现物理评分。native worker 的 annotation core 与现有训练/评测 core 分开绑定，版本和路径见[生产指南](../../docs/augmentation_progress.md)。

稀疏步幅或局部窗口须事先声明、与模型/任务成败无关；禁止全轨迹锚点和超出声明 cap。最多每锚点 4 次局部恢复（3 个对应候选及一次原生事实复核），**不包括**每来源初始化、XML 编译/场景 reset 开销。两相机原图/前景误差、朝向歧义、完整状态等价与既有阈值继续约束准入，未清零速度或放宽判据。

每个可靠非终局锚点只产生当前 `t` 的一条 PROGRESS：完整原指令＋原专家 chunk8，允许跨后续阶段，只在 episode 尾 mask。两个锚点之间不插值，终局不生成 FINISH/停车监督。九任务目标与 holding constraints 固定，双壶 stove-on 约束保留。旧 base 来源有完整多目标 native 绑定时也可生成 PROGRESS，继承原 split；单目标保持 RAW。

产物额外保存 `progress_report.json`：source/file SHA、state/obs/action 绑定、依赖字节锁、实际初始化/XML/BDDL 审计、逐锚点原生事实、RGB/状态对应测量及排除原因。证据不会进入训练 item、策略 prompt/历史或停止决策。提供 `recorded` backend 精确复用已保存报告，无新增恢复；不匹配/缺失锚点保留排除，不补写通过。

不自动生产 ATOMIC，不要求九任务全部标完。缺少整段可信动作归属时该池为空，按原采样约定回退 RAW 并记录实际比例。已有可信原子段可通过 `--evidence` 同时输入；重复导出已保存证据不会重复计数 PROGRESS 或丢失嵌套原子段。两种增强池都为空时，原 Progress-Aug 训练仍在加载模型前拒绝，不冒称增强已就绪。

## 定向验证与审查修复

本机实际命令（在 PR9 worktree 中）：

```powershell
$env:EGRS_PROGRESS_HISTORICAL_ROOT = (Resolve-Path '../Learning-Not-to-Act-task016').Path
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_augmentation_data.py tests/test_augmentation_proprio.py tests/test_augmentation_progress.py tests/test_augmentation_progress_native.py -q --tb=short --basetemp=.work/task030-r2-final-20261103 --junitxml=.work/task030-r2-final-20261103.xml
```

结果：**84 passed in 14.58s，0 failed / 0 skipped**。JUnit 留在上述本地测试产物位置；合成 HDF/fake 输出不作为真实标注提交。

| 测试文件 | 通过数 | 防止的错误 |
| --- | ---: | --- |
| `test_augmentation_data.py` | 27 | 原 RAW/证据/分组/归一化/动作边界回归 |
| `test_augmentation_proprio.py` | 17 | 真实合法字段误拒、隐藏状态或错误角色放行 |
| `test_augmentation_progress.py` | 18 | 计划意外执行、单次导出无增强、跨阶段误裁 chunk、证据复用/排除/原子段丢失、路径绑定及输入泄漏 |
| `test_augmentation_progress_native.py` | 22 | 原生接口/物理长度错配、对应歧义、状态等价不成立、依赖错配及 RPC 混流 |

独立审查发现并在提交前修复：新 manifest 的 `data/demo_N` 与旧 reader 的 `demo_N` 接口、logical length 与 physical T 的区别；初始化审计丢失；`asset_roots` 字典和 `core.root` 路径解析；重复导出证据导致重复 PROGRESS/丢失 ATOMIC。相关失败测试先复现后通过。最终独立窄审查无剩余代码阻塞；最终组合测试为上述本机 84 项，不把中途审查测试冒称最终全组复验。

其中 3 项通过实际已验收 `SourceEpisode` 读取**合成** HDF，并走真实父子进程 RPC，原生仿真边界用 fake 替代。共同 offset 0/0 与 1/1 通过；物理 state/action/camera 长度不一致明确排除，未改数据或放宽 reader。没有运行真实仿真、读真实轨迹内容、加载权重或重跑无关训练/评测测试。CLI help 和 `git diff --cached --check` 也已通过。

## 部署配置与完整入口

模板：[progress_native.example.json](../../configs/augmentation/progress_native.example.json)。
完整环境/固定依赖/已封存配置复用/证据复用说明：[augmentation_progress.md](../../docs/augmentation_progress.md)。
保留的训练与 A90/C36 命令：[augmentation_commands.md](../../docs/augmentation_commands.md)。

由 Codex 绑定已有普通演示 manifest、原 200-source inventory、旧 Task022/023 已封存 backend 的真实 interpreter/module paths/native 版本和文件锁。复制已有 `worker.python/module_paths/timeout_seconds` 与 `native` 到新配置，不要求用户手写 200 条记录。补齐实际计划任务的已核验 BDDL 字节锁；示例中的空 runtime hash 表和路径占位不能当成正式配置。固定九任务定义从 `data_scope.json` 复制，state_alignment_basis 必须指向实际原状态—观测—动作对应依据。

下列路径由 Codex 部署替换；命令是入口说明，本轮没有执行真实版本：

```bash
conda run -p /absolute/path/to/export-env python -m pip install --no-deps -e /absolute/path/to/this-method

conda run -p /absolute/path/to/export-env python -m egrs.augmentation.progress plan \
  --manifest /absolute/path/to/sources.local.json \
  --base-inventory /absolute/path/to/base-inventory.json \
  --config /absolute/path/to/progress.local.json \
  --output /absolute/path/to/new-progress-plan.json

conda run -p /absolute/path/to/export-env python -u -m egrs.augmentation.export \
  --manifest /absolute/path/to/sources.local.json \
  --base-inventory /absolute/path/to/base-inventory.json \
  --progress-config /absolute/path/to/progress.local.json \
  --output /absolute/path/to/new-progress-export
```

最后一条执行真实局部恢复，须由用户在真实阶段获准后亲自启动；plan 不执行恢复。已有可信 ATOMIC 文件可给同一 export 加 `--evidence /absolute/path/to/trusted-evidence.json`。已核验报告则使用 `backend.kind=recorded`、原报告路径和实际 SHA，同一命令换新输出即可只复用证据。所有来源/hash/绑定及不通过记录保留。

跨机器重现 CPU 测试（不需要模型或仿真）：

```bash
export EGRS_PROGRESS_HISTORICAL_ROOT=/absolute/path/to/accepted-method-at-fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391
conda run -p /absolute/path/to/cpu-env python -m pytest \
  tests/test_augmentation_data.py tests/test_augmentation_proprio.py \
  tests/test_augmentation_progress.py tests/test_augmentation_progress_native.py \
  -q --basetemp=/absolute/path/to/new-cpu-test-temp
```

## 硬阻塞与下一步操作和执行者

本次软件交付没有已知未修代码阻塞。**真实阶段前置输入尚未在本轮验证**：实际普通 HDF/manifest 和已有 alignment 证据；隔离历史组件及原生运行环境的路径/锁；新增九任务 BDDL 可用性。未绑定或对应不可靠时如实 RAW/排除，不能据 fake 测试宣称真实 PROGRESS 已生产或九任务覆盖已齐。原生桥保留原 reader 的等长物理数组约束，异长记录可继续 RAW，但不能无依据挪动/补齐后拿去恢复。

Codex 下一步审阅本提交、隔离部署并一次性绑定实际文件/配置、给用户最终命令。用户决定真实数据/局部恢复、两次 1000 更新及 A90+C36 预算，并亲自启动。X 本轮不下载新增数据、不启动真实实验、不重跑基线、不修改冻结目录、不自动合并。034 按既有验收继续，无需等待本轮返修。
