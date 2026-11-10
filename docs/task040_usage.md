# Task040：新增train父源覆盖的运行入口

基于已验收PR14@`113ded21434a06e2cdc156e5d6283a11c3f15488`，只扩三任务`stove/mug_pudding/two_pots`的`demo_20..39`候选。按seed7/原alias规则先固定分组，仅新增train代表生产；新dev封存、旧父组及全部dev不动。新normal仅生成和pair，新合格ten追加train；旧105fresh/180raw及其标签、305ten/305pairs、确定性dev选择保留。新增父源不等于已证明独立的物理布局，也不是原SOG10未见数据。

预算已批准：普通≤60、ten尝试≤360（每train代表1normal、3机器人起点×最多2桥），总控制≤218400步；一组原SOG10新初始化C1、1000更新，reference≤9024/student≤24560，固定末1000正式评九任务10/00各90共180。不增加S/C0/seed/续训/基线。X本轮只软件及CPU/fake，未部署或执行任何真实步骤；下述命令由Codex验收后填写实际路径、用户亲自启动。

## Codex验收后隔离部署和配置

使用新checkout，不热改旧039或升级依赖。现有native、OFT及policy-worker环境均须导入**同一新方法包**；父进程PYTHONPATH不能替代worker环境的安装。以下路径和环境名是模板，Codex按原冻结配置填入：

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task040-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
conda activate EXISTING_NATIVE_ENV
python -m pip install --no-deps -e .
conda activate EXISTING_OFT_ENV
python -m pip install --no-deps -e .
python -m egrs.coverage040 --help
```

安装仅属于后续隔离部署模板，本轮未执行。原035完整180父清单、官方HDF/revision、统计、原生环境controller/双bridge指纹、原SOG10 checkpoint/head及core/reporting保持。无需下载新模型/示范、重建正式初态或复跑基线。

复制`configs/coverage040/generation.example.json`到`$LNA_ROOT/configs/task040/generation.json`，配置只有三个字段：

```json
{
  "format": "task040-parent-coverage-config-v1",
  "generation_config": "${LNA_ROOT}/configs/trajectory035-564c91c9/generate.json",
  "old_task_control_index": "${LNA_ROOT}/data/coverage039/production-001/indices/task_control"
}
```

JSON中的环境变量由040 planner显式展开；未定义变量、缺输入和原039身份不匹配直接拒绝，不把占位符变成假目录。retention/merged、原旧根和SHA由旧task-control索引的已有绑定推导，写入新plan，不手工拼凑。冻结旧039 index=`b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c`，report=`64a2d4923dda271ffeb2a67f080c81c40bbdb277bae6351328a779791e1abdaf`。实际原配置路径如有不同，由Codex修改这两个路径，不能修改冻结身份以迁就别的数据。

## 用户一次生产：候选元数据→train-only真实生成→增量索引

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_NATIVE_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task040-ACCEPTED_COMMIT"
cd "$LNA_CODE"
python -u -m egrs.coverage040 generate \
  --config "$LNA_ROOT/configs/task040/generation.json" \
  --output "$LNA_ROOT/data/coverage040/production-001"
```

同一命令先确定恰好60候选，保留旧180父组/136train与44dev，生成计划不读取正式eval轨迹。旧锚点重复继承旧split但不生成；新重复只生成自然序最小代表；连接旧train/dev的新增组件拒绝并记录。新候选dev不生成、不进入本轮dev。物理祖源未知仍unknown，不新做全库重复扫描。

教师、真实动作/观测导出及双壶变换完整复用039：原V2准入/连续5观测释放不放宽，收尾≤40新增步、总H520；只在双壶新normal首帧前交换指定两freejoint qpos7/qvel6，其他状态和A/B语义不动。新ten使用新normal真实handoff，仅rewind机器人，再实际桥接续接；监督是自己执行动作，不能复制normal动作给另一机器人状态。

初始化前持久占槽；失败/异常/中断均算已花，缺metadata槽补失败不退款。已存在输出拒覆盖，本轮不提供自动生产续跑或追加预算；中断保留账本/前缀，不能删除旧目录冒充未消费。预算是上限，不保证60父组都入train或360次都执行。

完成后的入口是`preparation_report.json`：包含新合格train10数、是否可训、路径和哈希工作量。`generated/`保留新attempts/HDF/audit/lineage、完整计划与预算；`indices/`提供新数据视图。旧039文件不重写/不建立可写hardlink。新normal只在独立pair来源表可解析，不带伪fresh池或零权重主样本；新ten缺pair仅单列缺口，不删除其BC数据。原pair按原字节来源复用；新pair以原1e-8非机器人比较和真实出站动作核验。

父生产进程的规划、export和索引共用稳定canonical path/stat的SHA上下文，同一文件在该上下文只算一次，改变文件拒绝；不建立跨进程永久免校验缓存。每个独立native worker仍按039原规则首次完整复验其原始HDF/统计，父进程缓存不豁免这次身份检查，因此子进程总读取量不是全任务只读一次。进度以已处理train父组/计划train父组计算生产百分比，同时列已花normal/ten与预算；不能用已花/360当完成率。文件字节、阶段与worker控制进度每≤30秒可见。

若没有来自新增合格train父组的ten，报告`training_ready=false`，训练入口在加载模型前拒绝；有新增即按实际量继续，不设每任务N或新pair最低数，也不自动追加生成。

## 用户一组C1训练及显式恢复

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task040-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
python -u -m egrs.coverage040 train \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/coverage040/production-001/indices/task_control" \
  --output-dir "$LNA_ROOT/runs/task040-c1-train-001"
```

arm默认且仅允许`c1`。从原SOG10新初始化，不传039 adapter或恢复旧run。复用原038固定preset：seed7/lr2e-5/warmup50/bf16/gradient checkpointing、12ten+4fresh+4raw及1pair两端，原所有loss与采样层级；每250保存/dev，只选择末1000。保存完整新index identity、模块、optimizer/scheduler/RNG/sampler和两账本；新身份不伪装旧b8587565。训练日志显示update/1000、百分比、loss、耗时/ETA，完整sampling状态只存checkpoint。

仅恢复**这个run**已有checkpoint时，沿同一环境和变量执行完整命令：

```bash
python -u -m egrs.coverage040 train \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/coverage040/production-001/indices/task_control" \
  --output-dir "$LNA_ROOT/runs/task040-c1-train-001" \
  --resume "$LNA_ROOT/runs/task040-c1-train-001/update-000250"
```

原strict恢复保持：若已花账本领先checkpoint，拒绝精确续跑，不删账本/退款/暗加额度。不得恢复039权重开始本次实验。

## 用户固定末1000正式180评测

Codex复制**原039 C1实际评测配置**，只修改adapter和新run输出，保留其schema/arm、九任务来源、core/reporting与双bridge。不要从旧模板重新填一套来源。示例文件`configs/coverage040/evaluation.c1.example.json`说明相同协议；实际配置使用展开后的绝对路径。以下仅处理JSON，不是模型/仿真：

```bash
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_OLD_C1_EVAL=/path/to/unchanged-task039-c1-evaluation.json
python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['LNA_ROOT']).expanduser().resolve()
cfg = json.loads(Path(os.environ['LNA_OLD_C1_EVAL']).read_text())
assert cfg['arm'] == 'c1' and cfg['schema_version'] == 'task038-task-control-eval-v1'
cfg['adapter'] = str(root/'runs/task040-c1-train-001/update-001000')
target = root/'configs/task040/evaluation.c1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(cfg, stream, ensure_ascii=False, indent=2)
PY
```

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task040-ACCEPTED_COMMIT"
cd "$LNA_CODE"
python -u -m egrs.coverage040 eval --mode run \
  --config "$LNA_ROOT/configs/task040/evaluation.c1.json" \
  --output "$LNA_ROOT/runs/task040-c1-eval-001"
```

正式run自行绑定原来源/新模型，不额外要求plan/MVP/独立report进程。仍单VLA、原双RGB/完整指令/proprio，无GT/sourceID/未来信息或teacher路由；10二元合规/00官方各90、H520/chunk8/seed7、原reader/代理/全视频不改，不继承039分数。报告沿原038算法schema，通过新index/adapter身份区分040，不因阶段名另造评分。

## 可选nohup和精简进度查看

用户需要后台运行时，可将对应**一条**前述命令换为下例；先进入正确代码/环境并填写原变量，后阶段等前阶段正常结束，不能整套同时启动：

```bash
mkdir -p "$LNA_ROOT/logs"
nohup python -u -m egrs.coverage040 generate \
  --config "$LNA_ROOT/configs/task040/generation.json" \
  --output "$LNA_ROOT/data/coverage040/production-001" \
  > "$LNA_ROOT/logs/task040-production-001.console.log" 2>&1 &
tail -n 20 "$LNA_ROOT/logs/task040-production-001.console.log"
```

训练或eval同样用其完整命令替换generate参数，各自使用独立日志名；stdout/stderr都必须保留。eval既有`progress.json`是过程记录，最终`summary.json`/`report.md`才是正式SR与每任务表，视频沿原task_run引用查找，不另行按视频改分。所有后台命令本轮未执行。

验证范围、测试证据和交付状态见[040回复](../collaboration/responses/040_round1.md)。同一Anaconda进程混合NumPy SVD与Torch有已知OpenMP冲突，因此fake记录器使用独立NumPy子进程，文件与模型测试分组运行；不改依赖或用忽略开关。本轮软件交付不能证明真实生成覆盖或SR提高。
