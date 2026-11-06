# 038：一次索引，然后两组正式训练

2026-11-06，Codex。用户已批准两组各1000更新、reference≤18048/student≤49120及两模型10/00各90共360条；[R1验收](../../collaboration/reviews/038_round1.md)通过。代码/文件部署100%，真实index/标签、训练和模型eval尚未启动。**下列命令仅由用户执行。** 不需要pip、plan、模型小样/MVP、仿真预检或重建初态。

## 1. 激活原环境，执行一次文件索引

不是selector环境。沿用原Conda底座及既有OFT venv，不安装/升级包。

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/activate
source /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task038-5a6452ab/session038.sh
cd "$LNA038_CODE"

python -u -m egrs.task_control index \
  --generated-export "$LNA038_ROOT/data/trajectory035/generated-003/export" \
  --retention-index "$LNA038_ROOT/data/retention036/index-001" \
  --out "$LNA038_INDEX"
```

它只处理已有文件，建立本轮训练必需的标签/配对，不重放、不生成新仿真、不加载VLA。索引会读取既有来源身份/SHA和HDF结构，耗时不等于GPU训练；配对实际数量由该次生产报告给出，本次未伪造数量。

只执行一次，新目录已存在会拒绝覆盖。正常结束后直接继续C0，**不需交回再做一轮人工验证**。缺失/错误文件或训练零有效pair会明确报错，保留目录与日志反馈，不删除工件/放宽规则/自主重复预算。

## 2. 启动C0（相同网络/数据，独立上下文学习对照）

沿用上面的shell；若重连，重新执行上面的四条source/activate和cd，不重跑index。确认不与其他训练抢显存；不自动杀他人进程。

```bash
nohup python -u -m egrs.task_control train --arm c0 \
  --config "$LNA038_CODE/configs/task_control/task_control_factorization.json" \
  --runtime "$LNA038_RUNTIME" \
  --benchmark-root "$LNA038_CORE" \
  --index-dir "$LNA038_INDEX" \
  --output-dir "$LNA038_ROOT/runs/task038-c0-train-001" \
  >> "$LNA038_ROOT/runs/task038-c0-train-001.console.log" 2>&1 &
echo "PID=$!"
```

实时日志：

```bash
tail -n 30 -f "$LNA038_ROOT/runs/task038-c0-train-001.console.log"
```

`Ctrl+C`只退出tail，不停止nohup训练。开始会读取文件身份并加载原7B，随后每update打印`completion_percent`、各损失/参考与学生计数、elapsed/ETA；这不是评测，训练时没有SR。每250更新保存/dev，固定末1000，不能按dev或测试分数挑权重。

## 3. C0完成1000后，启动C1（配对交换＋保持约束）

**不要同时启动两组。** C0正常完成后可以直接运行，无需等Codex重复验证。若C0报错，保留日志/ledger/目录先反馈，不删目录重开或擅自resume。新shell先重新激活/加载session，不重跑index。

```bash
nohup python -u -m egrs.task_control train --arm c1 \
  --config "$LNA038_CODE/configs/task_control/task_control_factorization.json" \
  --runtime "$LNA038_RUNTIME" \
  --benchmark-root "$LNA038_CORE" \
  --index-dir "$LNA038_INDEX" \
  --output-dir "$LNA038_ROOT/runs/task038-c1-train-001" \
  >> "$LNA038_ROOT/runs/task038-c1-train-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 30 -f "$LNA038_ROOT/runs/task038-c1-train-001.console.log"
```

两组均从同原SOG10及相同新LoRA/小模块初始化开始，不继续035/036；同三池/配对序列和1000更新。C1只比C0多swap/align这一包，不是额外图像/更长训练。每组参考≤9024、学生≤24560；无第二个7B、外部VLM/FINISH/GT动作路由。

## 4. 训练后评测

两末权重分别在`runs/task038-c0-train-001/update-001000`与`task038-c1-train-001/update-001000`。交回完成消息，Codex仅读取实际身份/既有产物后给两模型新10/00各90的完整评测命令。真实标签/pair量、loss、SR、新颖性不是同一件事，不能由CPU通过宣称实验完成。

两个未来eval配置已经上传`configs/task038-5a6452ab/evaluation.c0.json`与`evaluation.c1.json`，原runtime/来源保持；最终adapter尚不存在，因此未生成真实权重绑定的plan。不得套用035/036旧adapter/旧分数，原360预算之外不补基线或挑测试checkpoint。

所有旧003/036索引、raw、权重、分数、原视频与失败保留；本轮不自动清理/merge/启停实验。
