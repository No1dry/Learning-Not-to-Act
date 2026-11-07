# 039：新数据生产，然后两组正式训练和评测

2026-11-07，Codex。用户已批准039预算；[R1](../../collaboration/reviews/039_round1.md)限软件/CPU-fake与隔离文件部署。**以下真实作业全部由用户启动，本次没有代跑。** 不需要额外pip、plan、真实MVP、旧六任务回放、初态重建或重测基线。

## 1. 激活既有环境，启动一次数据生产

沿用peft-openvla Conda底座与原OFT venv；不是selector环境。venv保留原numpy/MuJoCo等固定依赖，不能换成Conda底座的另一套包。

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/activate
source /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21/session039.sh
cd "$LNA039_CODE"

nohup python -u -m egrs.coverage039 generate \
  --config "$LNA039_CONFIG/generation.json" \
  --out "$LNA039_PRODUCTION" \
  >> "$LNA039_ROOT/data/coverage039-production-001.console.log" 2>&1 &
echo "PID=$!"
```

简洁实时日志：

```bash
tail -n 8 -f "$LNA039_ROOT/data/coverage039-production-001.console.log"
```

`Ctrl+C`只退出tail，不停止nohup作业。该命令一条完成60父源的新普通/10轨迹生产→引用合并→两索引，不加载VLA或训练。source进度按60个原父源计，尝试数量最多60普通＋360次10，失败也计入；不是保证420次全部发生或全部成功。完成源百分比不等于训练/评测进度。

初始化/动作日志在`$LNA039_PRODUCTION/generated/artifacts/source-*/worker.stdout.log`与`worker.stderr.log`；总进度文件`generated/generation_progress.json`。每源/当前attempt与控制step心跳约30秒刷新，哈希/索引阶段有阶段与字节/行数日志。未完成的单个source没有可信ETA，不把控制step百分比冒充整轮完成率。

正常完成后，`$LNA039_PRODUCTION/preparation_report.json`给出`new_qualified_train10`、`training_ready`、实际新/复用来源及索引路径。**有新增合格train10即可直接进入C0，不需交回再等人工检查，也不凑每任务N条。** 若为0，入口拒绝重复训练旧数据；或出现技术错误，保留全部输出/账本交回Codex，不删除目录/账本、改阈值或自行重开生产。本轮生产入口拒绝覆盖已有输出，不隐式续跑或退款。

## 2. 数据正常生产后，启动C0

使用上述shell；重连时重新执行四条source/activate与cd，不重跑generate。确认没有其他模型作业争用显存，不自动终止其他进程。

```bash
nohup python -u -m egrs.coverage039 train --arm c0 \
  --config "$LNA039_CODE/configs/task_control/task_control_factorization.json" \
  --runtime "$LNA039_RUNTIME" \
  --benchmark-root "$LNA039_CORE" \
  --index-dir "$LNA039_INDEX" \
  --output-dir "$LNA039_ROOT/runs/task039-c0-train-001" \
  >> "$LNA039_ROOT/runs/task039-c0-train-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 4 -f "$LNA039_ROOT/runs/task039-c0-train-001.console.log"
```

训练先验证文件身份与加载原7B，随后每update显示`completion_percent`、loss、参考/学生计数与ETA；紧凑采样计数替代巨型字典，完整RNG/层级保留checkpoint。训练没有SR。两组使用同一新索引和seed7、同1000更新，从原SOG10分别新初始化；不是旧C1续训。

## 3. C0完成1000并正常退出后，启动C1

无需等Codex额外确认；不要并行两组。遇到错误保留日志/账本，别删除后重跑，也不要擅自`--resume`退款。

```bash
nohup python -u -m egrs.coverage039 train --arm c1 \
  --config "$LNA039_CODE/configs/task_control/task_control_factorization.json" \
  --runtime "$LNA039_RUNTIME" \
  --benchmark-root "$LNA039_CORE" \
  --index-dir "$LNA039_INDEX" \
  --output-dir "$LNA039_ROOT/runs/task039-c1-train-001" \
  >> "$LNA039_ROOT/runs/task039-c1-train-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 4 -f "$LNA039_ROOT/runs/task039-c1-train-001.console.log"
```

每组参考≤9024、student≤24560，两组合计≤18048/49120，固定末1000。损失/网络及C0/C1系数保持038；本轮差异是新数据包，不把覆盖/收尾/采样效应包装成纯模型创新。

## 4. 两组末1000产生后，正式评测

以下完整命令已经填写实际配置。可在两组训练完成、没有训练占用时由用户依次执行；不需要额外plan或模型小样。Codex收到完成消息后读取既有产物核对/归档，不重复训练或评分。各评10/00各90，共360新模型episode，保留全视频、H520/chunk8/seed7/原双bridge与评分。

评测父进程要切回原simulation venv；VLA子进程仍由runtime指定原OFT worker。不能把旧模型分数继承到新模型。

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
source /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21/session039.sh
cd "$LNA039_CORE"

nohup python -u -m egrs.coverage039 eval --arm c0 --mode run \
  --config "$LNA039_CONFIG/evaluation.c0.json" \
  --out "$LNA039_ROOT/runs/task039-c0-eval-001" \
  >> "$LNA039_ROOT/runs/task039-c0-eval-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 8 -f "$LNA039_ROOT/runs/task039-c0-eval-001.console.log"
```

等C0同进程生成正式summary并正常退出后才开C1；模型执行100%后原进程可能仍在CPU正式核验，不另启动report或重复评测。

```bash
nohup python -u -m egrs.coverage039 eval --arm c1 --mode run \
  --config "$LNA039_CONFIG/evaluation.c1.json" \
  --out "$LNA039_ROOT/runs/task039-c1-eval-001" \
  >> "$LNA039_ROOT/runs/task039-c1-eval-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 8 -f "$LNA039_ROOT/runs/task039-c1-eval-001.console.log"
```

039正式输出目前尚不存在，不能由软件通过宣称三任务恢复/训练/成功率改善。原003/035/036/038原始数据、权重、视频、分数和失败全部保留；本轮无自动merge/清理或真实作业。
