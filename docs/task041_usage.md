# Task041：040初始化的R0/R1旧10行为保持

本轮软件基于accepted PR15@`428c13585cebac1d6c90fd86a205e914caa2bb8f`，新入口为`python -m egrs.retention041`。R0/R1的基础算法**都是原C1**，都从040末1000全部可训练模块初始化，分别新建优化器/调度、sampler和三类调用账本，额外各1000更新。R0不是旧C0，也不是对完成040执行`--resume`。

| 项目 | R0 | R1 |
|---|---|---|
| 学生/原loss/采样/dev | 040初始化、原C1 | 相同 |
| 本阶段更新 | 新增1000 | 新增1000 |
| 039旧10参考 | 0，不加载teacher | 已有12ten中前最多4个合格位置 |
| 新损失 | 无 | `0.10 * L_old10` |
| 原SOG10参考上限 | 9024含dev | 相同 |
| 039参考上限 | 0 | 4000仅train，0dev |
| 学生上限/正式模型评测 | 24560 / 180 | 相同 |

两臂合计原参考≤18048＋039≤4000=全部参考≤22048、student≤49120、正式新模型360；祖代1000与本阶段新增1000分别记录。预算已批准，**只有用户启动真实作业**。X本轮仅实现和定向CPU/fake，没有部署、SSH、真实模型/仿真/标签/数据/索引/训练/eval，也没有下载/基线/MVP/额外seed。

## 固定现成输入与隔离部署

Codex验收后部署新checkout并填实际路径；原039/040代码、权重、完整续训状态、数据、视频、失败和分数不改不删。现有OFT与policy-worker环境应导入同一新方法包，不升级依赖或搭新真实环境。部署模板如下，本轮未执行：

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task041-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
python -m pip install --no-deps -e .
python -m egrs.retention041 --help
```

固定依赖在训练前核验，不生成新索引/标签、回放或重做物理资格：

- 040初始化adapter字节SHA：`a51f9062fc5a54982233ffdb93f7fa164eaf78b6dbdc097721db9d7f87f57b12`，C1末1000，包含LoRA、context z、残差和count全部参数。
- R1独立039教师SHA：`6d340e99186090bab6739f173ecb118d03eb1bf574ae96d5f1c34241b02d644e`，保留其原039 index `b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c`，不得改成040身份。R0配置teacher必须null，不读其模型。
- 已有040 index：`8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe`，370ten/370pair（289train/81dev），105fresh（78/27）、180raw（136/44）、143960主行；全部dev及选择顺序原样，新normal仍只pair。
- 原SOG10底座/头/proprio投影/统计、core/reporting/双bridge和controller沿旧身份。source reader验证完整键/形状/dtype/tensor hash/base lineage后才加载，不靠名字或只加载LoRA。

将`configs/retention041/training.r0.example.json`和`training.r1.example.json`复制到`$LNA_ROOT/configs/task041/training.r0.json`、`training.r1.json`。配置包含experiment_arm、完整原固定training_recipe及index/init/teacher/core/runtime路径，支持`${LNA_ROOT}`/`${LNA_CORE}`/`${LNA_RUNTIME}`显式展开及配置文件相对路径。未定义变量、重复字段、残留占位符、错误arm/原1000配方、SHA/index/祖源均明确拒绝，不自动换来源。实际目录由Codex填，GitHub不存私有权重或凭据。

## 用户训练：两个独立新stage

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task041-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
python -u -m egrs.retention041 train \
  --config "$LNA_ROOT/configs/task041/training.r0.json" \
  --output-dir "$LNA_ROOT/runs/task041-r0-train-001"
```

R0正常完成后再启动R1：

```bash
python -u -m egrs.retention041 train \
  --config "$LNA_ROOT/configs/task041/training.r1.json" \
  --output-dir "$LNA_ROOT/runs/task041-r1-train-001"
```

可串行一键执行以下模板，任一步失败停止，不自动退款/清理/重试，也不自动接评测：

```bash
set -e
for arm in r0 r1; do
  python -u -m egrs.retention041 train \
    --config "$LNA_ROOT/configs/task041/training.$arm.json" \
    --output-dir "$LNA_ROOT/runs/task041-$arm-train-001"
done
```

原seed7/lr2e-5/warmup50/bf16/checkpointing、12ten+4fresh+4raw与1pair两端、count/self/swap/align和.50/.25/.25保持。每250保存与原固定dev，只选本stage末1000。原040 optimizer/RNG/账本不继承；因此是040祖代1000＋本轮新增1000、且优化器重启，不能称原optimizer严格连续1000→2000或总共仅1000。

R1队列只认已绑定040→039→old003六任务的train ten记录；不根据task/path子串或正式评测成败认旧源。从原12ten按位置顺序取前最多4个，重复样本位置保留；少于4按实际数、0个loss和teacher调用都为0，不重抽或向fresh/raw/pair/新三任务fallback。各样本以自己的有效chunk mask对7维动作先做masked mean，再按实际所选个数求mean，BC专家标签仍保留。

原8个SOG10参考及最多4个039参考全部先于本更新22个学生图。039完整独立LoRA/context/residual/count冻结分支只共享原冻结骨干，不把教师权重copy进活跃学生图；模式/hook/requires_grad/checkpoint/cache/Python-NumPy-Torch及已初始化CUDA RNG均隔离恢复。保持项加进对应学生的同一图，原梯度尺度和pair/count归一化保持，无额外student forward。CUDA实现路径有CPU/fake覆盖的结构证据，但没有真实GPU显存、速度或SR结论。

## 同一041 run的显式恢复

仅对这个run及其现存checkpoint，用同样环境/配置和输出恢复：

```bash
python -u -m egrs.retention041 train \
  --config "$LNA_ROOT/configs/task041/training.r1.json" \
  --output-dir "$LNA_ROOT/runs/task041-r1-train-001" \
  --resume "$LNA_ROOT/runs/task041-r1-train-001/update-000250"
```

R0同理替换两个arm路径，不能换臂、换init/teacher/index/config或把checkpoint移到另一个run续跑。新阶段与resume是两条逻辑：041完整学生/optimizer/scheduler/sampler/RNG/当前新增update和三账本恢复，不重新当040初始化。完成1000的run拒绝再次训练；已有输出要求对应resume，不覆盖旧目录。

三类`reference_budget.json`、`old10_budget.json`、`student_budget.json`独立记train/dev/total/budget（含R0显式0教师账本），每次forward前写已花；失败也不退。checkpoint落后于任一已花账本时明确拒绝精确恢复，不能删除账本或改数字凑继续。没有可恢复checkpoint的失败现场保留，程序不隐式另开预算。

041 `identity.json`是独立严格schema，包含`arm=c1`和`experiment_arm=r0/r1`、阶段祖代/输入身份及三counter；`student_identity`保存真实公共C1参数清单，但根目录不会写旧schema冒充040。旧root reader拒041；新reader全量恢复学生所有模块，教师权重不保存进学生adapter。

## Codex准备两臂原协议eval配置

复制**040 C1实际评测JSON**，仅换041 schema/group、实验臂和各自新末1000学生路径；原来源、runtime/core/reporting/dispatch不改。以下仅配置文件准备模板，本轮未执行：

```bash
export LNA_040_EVAL=/path/to/unchanged-task040-c1-evaluation.json
python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['LNA_ROOT']).resolve()
base = json.loads(Path(os.environ['LNA_040_EVAL']).read_text())
assert base['arm'] == 'c1' and base['schema_version'] == 'task038-task-control-eval-v1'
for arm in ('r0', 'r1'):
    cfg = dict(base, schema_version='task041-old10-retention-eval-v1',
               group='old10_behavior_retention', arm='c1', experiment_arm=arm,
               adapter=str(root/f'runs/task041-{arm}-train-001/update-001000'))
    with (root/f'configs/task041/evaluation.{arm}.json').open('x') as stream:
        json.dump(cfg, stream, indent=2)
PY
```

库内`evaluation.r0/r1.example.json`为脱敏原协议模板，实际配置需展开绝对路径，不能把`<...>`字符串当有效路径；无需重填全部来源或另跑真实prepare/MVP。

## 用户两臂正式评测：各180，不继承旧分数

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task041-ACCEPTED_COMMIT"
cd "$LNA_CODE"
python -u -m egrs.retention041 eval --experiment-arm r0 --mode run \
  --config "$LNA_ROOT/configs/task041/evaluation.r0.json" \
  --output "$LNA_ROOT/runs/task041-r0-eval-001"
```

R0正常结束后，同环境执行：

```bash
python -u -m egrs.retention041 eval --experiment-arm r1 --mode run \
  --config "$LNA_ROOT/configs/task041/evaluation.r1.json" \
  --output "$LNA_ROOT/runs/task041-r1-eval-001"
```

独立新模型各九任务10/00各90、H520/chunk8/seed7、全视频/raw、原core/reporting/双bridge/proxy及10二元合规/00官方端点保持。eval只加载一套学生，调用原训练共享预测，无teacher或训练祖源输入/GT路由。正式run自带原来源/身份验证与最终报告，不另外要求plan/MVP/report进程，已有输出拒覆盖，不继承039040分数。

## 后台模板和进度

需要后台时，在上述正确环境/变量/目录中将对应完整命令包为下例；每阶段独立日志，前一阶段结束再启动下一步，本轮未实际执行：

```bash
mkdir -p "$LNA_ROOT/logs"
nohup python -u -m egrs.retention041 train \
  --config "$LNA_ROOT/configs/task041/training.r0.json" \
  --output-dir "$LNA_ROOT/runs/task041-r0-train-001" \
  > "$LNA_ROOT/logs/task041-r0-train-001.console.log" 2>&1 &
tail -n 5 "$LNA_ROOT/logs/task041-r0-train-001.console.log"
```

逐更新日志含base/experiment arm、新增update/1000、祖代1000和总祖代更新、百分比/ETA、原loss、old10未加权/加权loss、eligible/selected数及三类调用；全采样/RNG细节保留checkpoint，不刷巨大字典。正式eval过程看原`progress.json`，最终`summary.json/report.md`给SR/每任务表，视频由原task_run引用定位，不从训练loss编造SR。

比较主结论是R1−R0。R1−040混有额外训练和优化器重启；跨版本旧行为保持不是episode内A成果硬保护，不保证闭环SR、zero-shot或新颖性。本轮实际命令与CPU证据见[041回复](../collaboration/responses/041_round1.md)，软件验收后由Codex隔离部署、用户亲启真实2000更新及360评测。
