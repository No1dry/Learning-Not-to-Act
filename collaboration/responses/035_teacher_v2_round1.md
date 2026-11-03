# 035教师v2恢复｜Round1实现交付

2026-11-03，X。按[已批准工单](../tasks/035_teacher_v2_recovery.md)和[精确引用](../tasks/035_teacher_v2_recovery_refs.json)直接实现，交[PR10增量](https://github.com/No1dry/Learning-Not-to-Act/pull/10)，等待Codex集中审查。

基于已验收 `eecd25f59c43757509b639ef0c8a995547499a16`；已fetch main `5448e8a` 并在 `64bd07f` 合入最新任务/批准/验收文档，双方历史STATUS保留。**实现HEAD `20647cce386dfe2a3f768a029f909fa32350aa60`**，之后仅补交付记录。

软件实现100%。受影响CPU/fake **66 passed、2 skipped，15.29秒，0 failure/error**；两skip为本机Windows缺少文件symlink权限的原R3回归，不能算通过。R3此前在Codex支持机器8/8通过的验收证据保留；本轮没有重新执行真实恢复/仿真/渲染/训练/模型评测。新增真实实验进度0%，002已有2normal/6个10仍是此前实际数据，不因软件交付宣称003已产出。

## 具体实现与接口

1. `native.py` 新增显式策略 `strict-event-unknown-v1`（默认）/`table-drop-unknown-diagnostic-v2`。`qualify_frames(..., teacher_policy=...)`在v2仅将table_drop未知另列 `diagnostic_events`；原 `core_analysis.event_unknown` 与None保留。全部confirmed事件（包括table_drop）、其他关键未知、完成/释放五观测、10初态/A保持/禁重抓/invariant继续拒绝。固定core与正式计分未改。
2. `generation.py` 沿用原动作投影、正常重放/交接/3×2桥接/B目标跟踪、H520与解释器调用。metadata/qualification/lineage写策略及诊断；v2即使rejected也保留真实完成对齐前缀HDF。未完成末动作只留journal/audit，初始化零帧不造T+1；确认HOLD仍仅证据。旧v1筛选行为保留。
3. 新 `recovery_plan.build_recovery_plan(config_path)` 纯文件验证原180与原父分组后选固定73（53train/20dev）。核对批准refs身份、原config/manifest/报告/分析、候选qualification/metadata SHA与唯一table_drop未知/streak≥5；核对旧8条、完整180 parents、原组/split及全部引用SHA/大小。旧8来自两个train父源且与73不相交，异常直接报错，不替换来源。
4. 新 `recovery.recover(config_path, output, source_generator=None)` 默认调用现有真实 `generate_source`。旧8先复制到新run内并再次核SHA，源ID/父组/split/语言/映射/长度/HDF及原qualification/lineage字节不变，外围标记 `reused_from_generated002.new_execution=false`，不重判为v2或重放。只对73运行生成器，保持失败和实际分母。
5. `data.export_generated`仅增加可选 `generation_context`，默认旧行为保持。v2策略、恢复plan身份和v1复用语义进入sources/report身份，实际训练器继续绑定这些字节。仍只索引qualified，失败HDF不进训练；模型item白名单不变。没有修改训练器、7:3/1000更新配置、LoRA、评分或正式来源。
6. CLI：`python -m egrs.trajectory_augmentation.recovery plan|recover|generate --config ... --output ...`；generate是recover别名。import/plan不启动native/HDF内容读取/模型。输出必须独立新目录，不能覆盖或置于legacy run内。

API返回plan含 `original_plan/sources/reused_sources/evidence/legacy_root/population/identity`。恢复报告含 `new_execution/reused/merged_data/pools/training_ready/source_errors`，逐来源控制台和progress显示完成/73、百分比、错误、新合格normal/10及复用量。只有train/dev×10/normal四池窗口均非空才ready，不自动训练或补跑。

## 计数和产物

固定新预算为73正常重放、219起点、438次10尝试、265720控制步；初始化时间另计。旧8条零物理执行，不计新attempts。`new_execution.attempts`是本轮实际分母；`merged_data.attempts`是索引审计记录总数，包含旧8条，不能把预算上限当实际分母。

产物：`recovery_plan.json`、`reuse_manifest.json`、`reused/generated002/`、新 `artifacts/source-NNN/`、`recovery_progress.json`、`recovery_report.json`、`export/`。旧001/002所有失败、原plan和raw不改、不覆盖；没有重下9个HDF或重跑基线。

**合成fake端到端示例，非真实003结果：**完整180先验证，固定73执行，每来源fake返回1normal＋1个10，共146个新实际attempt记录；复用旧8条/2父源，最终154条qualified，四池非空、training_ready=true。73候选与旧父源完全不交；新attempt146、复用8分列，438仍只作上限。另用全拒绝fake验证失败前缀文件保留、训练索引只有旧样本、空dev导致ready=false。

## 精简测试证据

| 覆盖 | 最终不同用例 |
|---|---:|
| v1/v2未知、全部确认违规、完成/释放/A保护、失败前缀/未完成动作 | 17通过 |
| 完整180→固定73/53:20、旧8/2父源、引用/分组/资格篡改拒绝 | 10通过 |
| 复用/新生成→导出、精确73＋旧8端到端、字节/路径保护、空池与失败排除 | 4通过 |
| 受影响旧generation、data、原R3 CLI | 35通过、2 skip |
| 合计 | **66通过、2 skip** |

新路径按TDD先失败再实现；开发红灯及Windows skip XML保留。最终由X主进程运行以下合并定向命令，没有全库或训练/评测大组：

```powershell
$env:EGRS_PROGRESS_HISTORICAL_ROOT=(Resolve-Path ../Learning-Not-to-Act-task016).Path
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_teacher_v2.py tests/test_trajectory_recovery_plan.py tests/test_trajectory_recovery.py tests/test_trajectory_generation.py tests/test_trajectory_data.py tests/test_trajectory_cli.py -q -rs --tb=short --basetemp=.work/teacher-v2-final --junitxml=.work/teacher-v2-final.xml
```

`recovery --help` exit0；最终暂存diff whitespace检查通过；独立窄审查未发现剩余已证实阻断。测试只用tiny状态机/合成HDF/fake worker边界。真实symlink两项仍可在支持机器随上述CLI回归执行，当前Windows的skip没有改写为通过。

## 配置与普通命令

完整说明及训练示例见[恢复指南](../../docs/trajectory_teacher_v2_recovery.md)。配置模板：[recover_teacher_v2.example.json](../../configs/trajectory_augmentation/recover_teacher_v2.example.json)。字段为：

```json
{
  "format": "task035-teacher-v2-recovery-config-v1",
  "evidence": "../../collaboration/tasks/035_teacher_v2_recovery_refs.json",
  "path_roots": {}
}
```

evidence必须等于仓库批准refs；`path_roots`仅定位证据/legacy，原config中的执行路径仍须可用。生产沿原服务器原配置，空映射即可；模板复制到别处时Codex绑定evidence绝对路径。缺文件/hash不符直接报错，不给候选回退、不改锁。

Codex在新隔离方法目录准备并交实际完整路径，随后用户启动：

```bash
conda run -p /absolute/path/to/export-env python -m pip install --no-deps -e /absolute/path/to/method035-v2

# 纯文件plan，不启动实际生成。
conda run -p /absolute/path/to/export-env python -m egrs.trajectory_augmentation.recovery plan \
  --config /absolute/path/to/method035-v2/configs/trajectory_augmentation/recover_teacher_v2.example.json \
  --output /absolute/path/to/new-recovery003-plan.json

# 本轮未执行；由用户亲自启动新generated-003。
conda run -p /absolute/path/to/export-env python -u -m egrs.trajectory_augmentation.recovery recover \
  --config /absolute/path/to/method035-v2/configs/trajectory_augmentation/recover_teacher_v2.example.json \
  --output /absolute/path/to/data/trajectory035/generated-003
```

本轮无需先补数据/方案、重下HDF、复写控制器或改变研究预算。没有运行上述真实命令。实际v2产量和ready仍需用户新作业结果确认；ready=false如实报告，不自动增加释放尾动作、截断演示、改划分/任务集或追加训练。

下一步执行者 **Codex**：一次集中审查、在新目录隔离部署、核对实际refs/config并给generated-003完整普通命令；**用户**亲自启动已批准的73/438恢复，之后依据实际报告启动原一组1000更新及同adapter90+90。原8条与失败保留，本轮真实作业0，无自动merge或清理，待删=[]。
