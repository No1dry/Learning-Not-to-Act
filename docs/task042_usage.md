# Task042：F0/F1任务—控制信息隔离

基于accepted PR16@`e8dcf87979d14d081666629a2de3483629a4f59c`及最新042工单/SDPA源审计。新入口`python -m egrs.tcif042`。两臂基础均为原C1，都从完整041 R0末1000初始化；F0保留原OFT padding-only双向图，F1仅增加每层`T query ← C key`禁边。两臂使用同一实例级SDPA包装、同尺寸显式dense mask和`is_causal=False`，没有新参数、头、loss、数据或评分。

本轮只实现与定向CPU/fake；没有部署、真实模型/数据/仿真/生成/标注/训练/eval，也没有额外seed、MVP或基线重跑。下列真实命令由Codex验收、隔离部署并填好现存路径后，**仅用户执行**。保留039/040/041全部数据、权重、日志、视频、失败与分数，不热改冻结目录、不自动合并PR。

## 执行合同与布局

只支持审计到的Transformers **4.40.1**、Torch **2.4.1+cu121**，实际`LlamaForCausalLM/LlamaModel/LlamaSdpaAttention`及完整源SHA `3aac24cec583a6ef5f60b6ec634a8bd3c8377784c5c63c8cc14cb6790554c52e`。正常初始化只读实际类、版本、源码和dtype，记录到`run_config.json`、adapter身份和eval metadata，不增加诊断前向。类/backend/source不符、cache、output_attentions/eager回退或实际布局不符均报具体错误，不静默切方法或升级依赖。历史文件审计不证明旧7B实例分支已被动态追踪。

包装只绑定本042实例的attention forward和mask转换，保留原q/k/v/o Parameter、native LoRA路径、RoPE、GQA、dropout和动作并行计算；不编辑site-packages、OFT/core源码，不全局替换torch primitive。旧030–041不自动安装042。

在原单次融合中捕获真实proprio projector输出，核对`BOS, image patches, P, raw[1:]`的实际插入长度和P值。A来自原`labels[:,1:]`的56个shifted action hidden全局位置；`a0=min(A)`，T是有效`pos<a0`且非P，C是其余有效位置。图像/指令全部H_v/H_l必须属T，P/全部A属C，首个A即便仍是prefix/scaffold也保留读P权限。padding key始终屏蔽，各query有合法key；T内部及C读取T/C均保持原双向。

完整4D additive mask在融合后直接传到LM、decoder及每层checkpoint。层重算仅使用保存的显式tensor，不读取“当前样本”全局字段或临时hook；成对变长u/v各有自己的mask。临时融合hook在finally删除，不做额外vision/projector/VLA前向。训练/dev/eval都经`egrs.tcif042.oft.prediction`共享原准备、选择和解码。

8个原SOG10参考先于任一22学生图完成，仍旁路全部新增LoRA/context/count/residual及学生布局hook。其原2D padding经同包装变为native双向dense mask；F1不改变参考目标。复用041保护恢复模式、hook、RNG、cache、checkpointing和requires_grad，dev保持原固定选择及预算。

## 固定输入和预算

- 初始化：完整041 **R0**，字节SHA `d4e726a867531f655d28e11f358ce0af597d4ada0f4928f4597aeadb28d38397`，其真实041身份和原source链保持，包括LoRA/context z/残差/count；不载旧optimizer/RNG/余额。
- 现存040 index：`8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe`。370ten/370pair、105fresh、180raw、143960主行，原train/dev及顺序不变；新normal仍pair-only，不生成新index/标签。
- 两臂原C1：`.50 BC_ten + .25 ref_fresh + .25 ref_raw + .10 count + .05 self + .05 swap + .01 align`。每更新12ten+4fresh+4raw+1pair两端；交换仅z，保留接收端自己的H/proprio/动作/mask。
- seed7、lr2e-5、warmup50、bf16、r16/alpha32/dropout0、micro1、checkpointing和原22观测归一化保持，250/500/750/1000保存和原固定dev，只选末1000。实际JSON保留浮点`photometric_probability: 0.0`，类型变为整数0也拒绝。

| 每臂 | 数量/上限 |
|---|---:|
| 新stage更新 | 1000 |
| 原SOG10 train/dev参考 | 8000 + 1024 = 9024 |
| train/dev学生 | 22000 + 2560 = 24560 |
| 039教师、新仿真/索引/标注 | 0 |
| 正式10/00 | 90 + 90 = 180 |

两臂合计新增2000更新、参考≤18048、学生≤49120、正式360条。每臂保存`reference_budget.json`及`student_budget.json`，每次forward前持久扣账，失败不退。041 R0已有**2000祖代更新**，042新1000后累计3000；日志区分祖代、新增和累计，不称只有1000总训练。

## 配置与环境模板

沿用现存OFT与policy-worker环境，由Codex确保两边导入同一验收042方法包；无需新建环境、升级依赖或做额外GPU预跑。脱敏示例：

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task042-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
```

将`configs/tcif042/training.f0.example.json`、`training.f1.example.json`填为`$LNA_ROOT/configs/task042/training.f0.json`、`training.f1.json`。支持显式环境变量及相对配置目录路径。两者init都指向现存041 R0末1000，字段没有teacher/old10项。完整固定preset、重复字段、未定义变量/占位符、错臂、source字节/祖源/index均严格核验，source在模型构建前检查。

eval复制**原041 R0实际评测配置**，只换042 schema/group/实验臂及各自新末1000学生，不改变任何来源/core/reporting/runtime/dispatch：

```bash
export LNA_PREVIOUS_EVAL=/path/to/unchanged-task041-r0-evaluation.json
python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['LNA_ROOT']).resolve()
base = json.loads(Path(os.environ['LNA_PREVIOUS_EVAL']).read_text())
assert base['schema_version'] == 'task041-old10-retention-eval-v1'
assert base['arm'] == 'c1' and base['experiment_arm'] == 'r0'
for arm in ('f0', 'f1'):
    cfg = dict(base, schema_version='task042-tcif-eval-v1',
               group='task_control_information_firewall', arm='c1', experiment_arm=arm,
               adapter=str(root/f'runs/task042-{arm}-train-001/update-001000'))
    with (root/f'configs/task042/evaluation.{arm}.json').open('x') as stream:
        json.dump(cfg, stream, indent=2)
PY
```

库内`evaluation.f0/f1.example.json`也是脱敏原协议模板；`<...>`需由Codex填现存绝对路径，不是可运行默认路径。训练配置纯读取可用于核对文件，不要求额外真实prepare/plan/MVP。

## 用户训练、串行接力和恢复

每个新stage各建新输出：

```bash
python -u -m egrs.tcif042 train \
  --config "$LNA_ROOT/configs/task042/training.f0.json" \
  --output-dir "$LNA_ROOT/runs/task042-f0-train-001"
python -u -m egrs.tcif042 train \
  --config "$LNA_ROOT/configs/task042/training.f1.json" \
  --output-dir "$LNA_ROOT/runs/task042-f1-train-001"
```

上述是分别启动模板；若要两训练自动串行，使用下列替代命令，任一失败立即停止，不自动重试/退款/eval：

```bash
set -e
for arm in f0 f1; do
  python -u -m egrs.tcif042 train \
    --config "$LNA_ROOT/configs/task042/training.$arm.json" \
    --output-dir "$LNA_ROOT/runs/task042-$arm-train-001"
done
```

需后台串行时，在同样已激活的环境/变量/目录运行以下替代模板：

```bash
mkdir -p "$LNA_ROOT/logs"
nohup bash -c 'set -e; for arm in f0 f1; do
  python -u -m egrs.tcif042 train \
    --config "$LNA_ROOT/configs/task042/training.$arm.json" \
    --output-dir "$LNA_ROOT/runs/task042-$arm-train-001" \
    > "$LNA_ROOT/logs/task042-$arm-train-001.console.log" 2>&1
done' > "$LNA_ROOT/logs/task042-relay.console.log" 2>&1 &
tail -n 5 "$LNA_ROOT/logs/task042-f0-train-001.console.log"
```

逐更新简洁JSON含百分比/ETA、base/exp、祖代2000/新增/累计、原loss、reference/student train/dev/total和compact sampler；完整状态保留checkpoint。需要显式恢复同一042 run时：

```bash
python -u -m egrs.tcif042 train \
  --config "$LNA_ROOT/configs/task042/training.f1.json" \
  --output-dir "$LNA_ROOT/runs/task042-f1-train-001" \
  --resume "$LNA_ROOT/runs/task042-f1-train-001/update-000250"
```

F0同理。resume必须保留原输出绝对目录及其两账本，不能复制checkpoint另开预算或换臂/source/index/config/runtime/backend/route版本；完整恢复本run学生、optimizer/scheduler/sampler/RNG/更新。已完成1000或已有输出不覆盖。checkpoint落后于已花预算会拒绝精确恢复，保留失败现场，不删账本/回填通过/另开真作业。初始化和resume的checkpoint都不是旧R0 optimizer严格连续续训。

## 用户正式评测

两臂均训练100%并通过身份核验后，由用户另行启动；训练不会自动衔接eval：

```bash
python -u -m egrs.tcif042 eval --experiment-arm f0 --mode run \
  --config "$LNA_ROOT/configs/task042/evaluation.f0.json" \
  --output "$LNA_ROOT/runs/task042-f0-eval-001"
python -u -m egrs.tcif042 eval --experiment-arm f1 --mode run \
  --config "$LNA_ROOT/configs/task042/evaluation.f1.json" \
  --output "$LNA_ROOT/runs/task042-f1-eval-001"
```

每臂原九任务10二元合规90、00官方90、H520/chunk8/seed7、全视频/raw、core/reporting、双bridge/proxy和端点保持。eval只加载一个学生，通过训练共享042预测路径，原双RGB/完整指令/8维proprio→8×7动作，无reference/GT/partner。原run包含来源核验/报告，不要求另跑计划进程。`progress.json`显示实际进度；最终`summary.json/report.md`给总体/每任务SR，原task_run引用全视频。不得继承旧R0分数。

主比较是**F1−F0**；与旧R0相比同时混有新增训练和显式backend变化。CPU固定像素/文字/布局的p非干涉检验只支持信息路由机制，不能推断物理rewind后z严格不变、A成果硬保护、目标身份正确、GPU速度或真实SR。

## 本地定向CPU/fake验证

以下不加载真实模型或仿真。复用已存在固定core/reporting测试fixture；不是新增服务器预跑门槛：

```bash
python -m pytest tests/test_tcif042_attention.py tests/test_tcif042_layout.py \
  tests/test_tcif042_identity.py tests/test_tcif042_evaluation.py \
  tests/test_tcif042_entry.py tests/test_tcif042_training.py \
  tests/test_task_control_model.py tests/test_task_control_reference.py \
  -q --tb=short --show-capture=no \
  --basetemp=../../.release-tools/t42/final01 \
  --junitxml=collaboration/evidence/042_cpu_fake.junit.xml
```

证据与限制见[042交付回复](../collaboration/responses/042_round1.md)。下一步执行者：Codex审查并隔离部署、准备实际配置；用户亲启两训练及正式360，X不启动真实作业。
