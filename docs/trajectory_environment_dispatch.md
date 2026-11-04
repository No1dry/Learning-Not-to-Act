# 035正式评测：旧/新桥接的严格环境分派

本入口修复[035环境兼容工单](../collaboration/tasks/035_legacy_environment_dispatch.md)。eval001首环境初始化即因指纹不匹配暂停，attempts/results为空、完成0/180，不能报告为模型SR=0。原训练完成和固定末1000权重验收保持；新评测仍由用户启动。

## 固定实现与选择

显式配置版本 `task035-dual-condition-eval-v2` 增加 `environment_dispatch.legacy_root`。其他来源、runtime和同一adapter保持。完整示例为 [eval_robot_rewind_dispatch.json](../configs/trajectory_augmentation/eval_robot_rewind_dispatch.json)。旧v1配置/plan/错误仍可读取，旧eval001不补写sidecar或结果。

| 来源锁 | 实际实现 | 固定bridge SHA256 | 原环境fingerprint |
|---|---|---|---|
| 旧六10/00，120条/66调用 | LIBERO-Remain@ac130177 | fa85ae08e1a09fcab1b95f0d25880d4fcb6d0948088e1f49ca7e3746ab95d603 | 27939e2d2a9a592a7c788ab5c91021d83f4ba88831615ef86aff0fb03ea7942b |
| 新三10/00，60条/60调用 | 原d8541ef4 core | 3a515dddc29311012180d4479dacd77511b510de44021ab6bc09516ca9a51efa | e7d58f354d2b013b362d181f9af3ef48dca136cdff2801c7de68606c16ed4883 |

旧实现额外锁定 `benchmark/remaining_goals/libero_compat.py` SHA `d7519cd0817b99b6178370d3e1d64915bf2a14bd6c465a8e76b6c73983517555`、`schema.py` SHA `3b554f4e913b587d59238287c8b2830d2c99598e0688519c0a2db8ae7236ec20`；这三文件是旧bridge的全部内部依赖。旧源码可使用已有 [ac130177固定目录](https://github.com/No1dry/LIBERO-Remain/tree/ac1301779cf6ae4c34ebc80c20936a4f7a4953be)，无需重建状态或复制模型。新实现及headless测量/协议辅助函数继续原97文件锁。

方法侧 `environment_dispatch.py` 在私有模块命名空间执行原旧文件字节，保留真实 `__file__`；旧compat从其邻接旧bridge计算SHA。headless环境本身仍执行固定core原源码，基类绑定旧bridge，测量/协议等依赖绑定已验证core模块；新版直接用原core类。不替换标准benchmark模块，不改冻结core文件，不另写runner/恢复或评分。

选择依据是来源的完整环境锁：先确认lock与fingerprint自洽及支持的bridge/compat，然后原环境类独立重算实际LIBERO源码、资产、版本、控制频率和compat身份并严格比较；最后方法侧还比较完整actual identity。未知bridge/不同依赖或实际环境均拒绝。不把expected覆写为actual，也不人为返回旧fingerprint。

## 运行与证据

方法只给原 `_run_task` 的函数globals副本绑定环境factory，原runner字节、relative imports、closure/kwdefaults保持；标准workflow模块不改。一个相同adapter worker服务原126调用/180条，条件和实现选择不进入策略输入。旧六00、新三00和10原端点/评分继续固定core/034。

每task新增 `environment_dispatch.json`，绑定冻结plan/source hash、完整来源环境锁、实际实现与源码锁、构造状态、实际identity和类MRO；batch绑定该文件SHA。独立reader先验证实现文件锁，再核sidecar/plan/source及actual identity，仍调用原archive/raw/query/action/video reader。报告附已验证的环境分派记录；技术初始化错误保留phase/error/missing，未执行不补为模型失败。旧v1没有sidecar仍可读。

`plan`只核文件、来源和实现依赖，不构造环境或加载模型。CPU/fake测试调用原环境constructor时，仅使用合成安装包字节/元数据进行身份计算，`env.env`仍为None，没有reset/step或场景创建；不能据此声称实际服务器已完成环境初始化或正式180评测。

Codex隔离部署新方法目录，复制原eval配置到新位置，只改schema并新增正确legacy_root，其他字段与原权重不变。运行路径均由Codex绑定，以下为普通入口：

```bash
conda run -p /absolute/path/to/libero-eval-env python -m pip install --no-deps -e /absolute/path/to/method035-dispatch

# 只读文件计划，无native/model。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation plan \
  --config /absolute/path/to/eval002.local.json --out /absolute/path/to/new-eval002-plan.json

# 本轮未执行：用户直接启动原180条，使用独立新输出。
conda run -p /absolute/path/to/libero-eval-env python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /absolute/path/to/eval002.local.json --out /absolute/path/to/runs/trajectory035-eval-002

# 只读既有产物派生报告，输出与原run分离。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation report \
  --run /absolute/path/to/runs/trajectory035-eval-002 --out /absolute/path/to/new-eval002-report
```

不要覆盖eval001或热改其代码/配置，也不重新生成初态、训练权重或重跑baseline。软件交付后由Codex审查、部署和给实际命令，全部真实评测由用户亲自启动；没有新增MVP/GPU预跑或实验预算。实时SR/去重复读子项仍独立，不是本修复的前置。
