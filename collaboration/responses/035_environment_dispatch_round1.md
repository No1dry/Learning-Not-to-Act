# 035环境兼容分派｜Round1交付

2026-11-04，X。按[环境兼容任务](../tasks/035_legacy_environment_dispatch.md)及[R8](../reviews/035_round8.md)实现，[PR10](https://github.com/No1dry/Learning-Not-to-Act/pull/10)增量，等待Codex审查。

已fetch main `3d39670` 并于 `8a40121` 合入最新工单/证据/状态，历史双方内容保留。基于已验收方法 `44b6ca02`；**实现commit `1387de381126176312a08d4c2b967c948d2fc541`**，其后仅追加本回复及状态。

兼容软件实现100%；最终受影响CPU/fake **34/34通过（100%，0skip/error/failure，28.37秒）**。实际eval002未启动；既有eval001仍0/180、无动作，不能记模型SR=0。原1000更新训练验收与权重引用保持。

## 实现选择和严格锁

新增 `egrs/trajectory_augmentation/environment_dispatch.py`：

- `describe_dispatch(legacy_root, core_root)`只读验证旧三文件和原97文件core锁，封存descriptor身份。
- `binding_for(environment, dispatch)`先验证完整lock与fingerprint自洽，再由来源的bridge/compat选择实际实现；不是按任务/模型成败选动作。
- `make_environment(config, dispatch)`加载实际选中类，原环境身份函数独立重算LIBERO源码/资产/版本/频率/compat指纹，保留其原严格检查，再比完整actual identity。未知bridge、实际源/资产/版本/compat不同或依赖字节变化均拒绝。

| 输入来源 | 规模 | 实际实现 | bridge SHA256 | 原完整fingerprint |
|---|---:|---|---|---|
| 旧六10＋00 | 120条/66调用 | `ac1301779cf6ae4c34ebc80c20936a4f7a4953be` | `fa85ae08e1a09fcab1b95f0d25880d4fcb6d0948088e1f49ca7e3746ab95d603` | `27939e2d2a9a592a7c788ab5c91021d83f4ba88831615ef86aff0fb03ea7942b` |
| 新三10＋00 | 60条/60调用 | 原 `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9` | `3a515dddc29311012180d4479dacd77511b510de44021ab6bc09516ca9a51efa` | `e7d58f354d2b013b362d181f9af3ef48dca136cdff2801c7de68606c16ed4883` |

旧内部依赖只有 `.schema` 和 `.libero_compat`，三文件均锁：compat SHA `d7519cd0817b99b6178370d3e1d64915bf2a14bd6c465a8e76b6c73983517555`、schema SHA `3b554f4e913b587d59238287c8b2830d2c99598e0688519c0a2db8ae7236ec20`。不执行旧目录未锁的init或任意传递模块。

旧三文件在私有命名空间直接执行经核验的源字节，保留真实 `__file__`，不借未锁pyc。旧compat因此确实从邻接旧bridge算SHA；没有覆盖expected/actual或伪造bridge身份。私有headless环境执行当前core原源码，基类为实际旧LiberoGoalEnv，测量/协议等模块绑定原core已锁模块。新版直接用标准原core环境类。标准benchmark模块及冻结文件未被替换。

## 评测与reader接入

`evaluation.py`增加显式配置/计划版本 `task035-dual-condition-eval-v2` 与 `environment_dispatch.legacy_root`；旧v1计划/001错误仍可读。

使用 `FunctionType` 复制原 `_run_task` 的globals，局部绑定环境factory；原runner bytecode、closure、kwdefaults、relative imports保持，标准workflow全局不改。不另写runner、状态恢复或评分。原126调用/180条、单个同adapter worker、完整指令及传感器输入保持；实现/条件不进入策略。

每task写 `environment_dispatch.json`：plan/source hash、完整expected lock、实际实现/source locks、构造状态、actual identity及类MRO。batch绑定文件SHA，独立reader同时验证descriptor字节、source/plan/item绑定及actual identity，仍走原archive/raw/query/actions/video核验。summary附已验证分派记录。旧六00/新三00的原协议、10二元合规/00官方SR与两基线不变。

初始化错误保留phase/error/missing。旧v1 eval001无需sidecar，仍报告environment_initialize的指纹错误、零结果与N/A正式SR，未执行不补模型失败，也不改写旧文件。

## 受影响CPU/fake

| 范围 | 结果 |
|---|---:|
| 实际旧/新原源码、完整身份重算、源/资产/版本/compat/依赖篡改拒绝 | 12通过 |
| v2精确120＋60队列/同policy、factory局部绑定/sidecar、旧001技术错误 | 3通过 |
| 受影响原评测测试，含四原协议reader分别v1/v2、视频/adapter篡改拒绝及原评分 | 19通过 |
| 最终合计 | **34通过，0skip，28.37秒** |

loader测试从本地固定ac130177 Git对象读取真实旧文件，使用合成LIBERO安装源码/资产与fake包版本/platform边界，让原身份函数独立计算完整fingerprint；不是直接返回任务表里的两个字符串。构造后 `env.env is None`，没有reset/step/真实场景/模型。它证明机制与严格拒绝边界，不冒称已在真实服务器重算并通过上述原fingerprint。

最终命令（035工作目录）：

```powershell
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_environment_dispatch.py tests/test_trajectory_environment_evaluation.py tests/test_trajectory_evaluation.py -q --tb=short --basetemp=.work/env-dispatch-final --junitxml=.work/env-dispatch-final.xml
```

新回归先失败后实现；初次整合发现旧reader测试传入无schema的局部plan导致4个KeyError，已保留旧局部调用兼容并通过，原失败XML保留。最后 `evaluation --help` exit0、暂存diff whitespace检查通过；独立窄审查无已证实剩余阻断。本轮没有全库、训练/生成大组、GPU、模型MVP或物理预检。

## 新配置和完整普通命令

新示例：[eval_robot_rewind_dispatch.json](../../configs/trajectory_augmentation/eval_robot_rewind_dispatch.json)，[完整指南](../../docs/trajectory_environment_dispatch.md)。从已验收原eval配置在新目录复制，其他字段不变，仅：

```json
{
  "schema_version": "task035-dual-condition-eval-v2",
  "environment_dispatch": {
    "legacy_root": "/absolute/path/to/unchanged-LIBERO-Remain-ac130177"
  }
}
```

这是字段差异示意，完整配置仍须包含原group/core/reporting/runtime/adapter及四组来源字段。legacy_root使用既有旧固定源码目录；新core仍原固定版本，adapter仍同一 `update-001000`。Codex替换准确部署路径，不要求用户搬文件或重训：

```bash
conda run -p /absolute/path/to/libero-eval-env python -m pip install --no-deps -e /absolute/path/to/method035-dispatch

# 只读文件计划，不实例化native/model。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation plan \
  --config /absolute/path/to/eval002.local.json --out /absolute/path/to/new-eval002-plan.json

# 本轮未执行；用户启动同一原180条，使用新输出。
conda run -p /absolute/path/to/libero-eval-env python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /absolute/path/to/eval002.local.json --out /absolute/path/to/runs/trajectory035-eval-002

conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation report \
  --run /absolute/path/to/runs/trajectory035-eval-002 --out /absolute/path/to/new-eval002-report
```

下一步执行者 **Codex**：集中审查、只读依赖/配置身份核对并隔离部署，交eval002准确命令；**用户**直接启动原180预算。001/原错误、原初态、训练权重、正式评分与数据保留，无真实新作业/重训/初态重建/基线重跑，无自动merge或清理，待删=[]。实际兼容运行与方法SR仍待用户结果；实时SR/去重复读子项仍独立非阻断。
