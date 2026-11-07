# 038：两组训练完成，正式评测完整命令

> 后续状态（2026-11-07）：用户已完成本页两个180，360条模型执行/正式报告均100%，正常退出。C0 10/00=53.33%/83.33%，C1=55.56%/84.44%，见[正式阶段总结](../stage_summaries/2026-11-07_task038_final_results_controlled_pair_learning.md)。本页保留操作历史，**不要再次启动/重跑这些命令**，当前无新实验授权。

2026-11-07，Codex。C0/C1均完成1000更新、固定末权重与预算已核对，[训练产物R2](../../collaboration/reviews/038_round2.md)。两组训练100%，正式模型评测0%；原已批准360条预算不增加，**全部真实评测仍由用户启动**。

复用现成九任务来源/初态/评分、已部署代码与两个eval配置，不重训、生成轨迹/重建状态、重跑原始基线，不另加plan/MVP或物理预检。正式`--mode run`自己绑定对应arm的实际末1000及原来源；不是拿旧模型分数复用成新分数。

## 1. 启动C0：10合规90＋00官方90

父进程用既有**仿真/评分venv**，不同于训练时激活的OFT venv；模型会按原runtime自动在原OFT worker里启动，仍一个VLA，不换模型或升级环境。两个环境的方法包部署已在R1完成，无需再pip。

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
source /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task038-5a6452ab/session038.sh
cd "$LNA038_CODE"

nohup python -u -m egrs.task_control eval --arm c0 --mode run \
  --config "$LNA038_CONFIG/evaluation.c0.json" \
  --out "$LNA038_ROOT/runs/task038-c0-eval-001" \
  >> "$LNA038_ROOT/runs/task038-c0-eval-001.console.log" 2>&1 &
echo "PID=$!"
```

只启动一次，已有run不覆盖。C0权重固定`task038-c0-train-001/update-001000`，SHA `f3f4c876f29cca0478e0d37148a0d3f60bbf265cbe1fb91ea0452cd417f3120b`。无需先运行`--mode plan`/独立report或另做模型小样。

## 2. 简洁进度与正式SR

```bash
tail -n 1 -F /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task038-c0-eval-001.console.log | python -u -c '
import sys,json
for line in sys.stdin:
    try:
        d=json.loads(line)
    except ValueError:
        if "formal_SR=" in line:
            print(line.strip(),flush=True)
        continue
    phase=d.get("phase")
    if phase=="execution":
        print("C0 模型执行: {}/180 ({:.2f}%)".format(d["model_completed"],d["percent"]),flush=True)
    elif phase=="verification":
        print("C0 结果核验: {}/180 ({:.2f}%)".format(d["checked"],d["percent"]),flush=True)
    elif phase=="final":
        print("C0 结束: {} | {}".format(d.get("status"),d.get("software_exit")),flush=True)
'
```

简洁命令只读日志。`Ctrl+C`只退出查看，不停止nohup作业。加载/来源绑定阶段或一个执行单元尚未结束时不一定有总体进度；原六任务单元各含10条，进度可能按5.56个百分点跳，不是每个控制step更新。不要因短时无新行重开第二份作业。

**模型执行100%不等于正式报告完成。** 同一个进程会在末尾做原有结果核验并写`summary.json/report.md`，随后打印10与00的`formal_SR=xx.xx%`；不额外启动第二份report核验。当前训练loss/计数准确率不是成功率，运行中的`formal_SR: pending`也不是0%。

如需完整异常/普通日志，另看：

```bash
tail -n 40 -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task038-c0-eval-001.console.log
```

报错时保留run/log/原始数据，交回Codex；不删除后重开、不自动重跑已完成episode或改评分。

## 3. C0正式报告完成且进程正常退出后，启动C1

**不要同时跑两组。** 若新开终端，先重复第1节的环境激活/session/cd，不重训或重建索引。

```bash
nohup python -u -m egrs.task_control eval --arm c1 --mode run \
  --config "$LNA038_CONFIG/evaluation.c1.json" \
  --out "$LNA038_ROOT/runs/task038-c1-eval-001" \
  >> "$LNA038_ROOT/runs/task038-c1-eval-001.console.log" 2>&1 &
echo "PID=$!"
```

C1固定`task038-c1-train-001/update-001000`，SHA `3f3873a435623af0d374e2ea5f5153429f6619ff06b0ec7062eea4cf23cef6c2`。C1同样180条，全部新执行，既不继承C0分数也不继承035/036。看C1时，把第2节日志路径中的`c0`及显示标签`C0`改为`c1/C1`即可。

## 固定评价与保留

九LIBERO-10复合任务、各任务10个episode，mask10与00各90/模型；H520/chunk8/seed7、完整原指令、双RGB/proprio、双bridge/proxy、原10二元合规/00官方判定与原reader不变，无FINISH/外部VLM。所有episode保存原视频/raw/action/query，评测没有原策略教师。

两末1000权重、完整续训状态、训练配置/日志和预算已本地SHA备份，服务器全部中间checkpoint/原console与003/036/035旧工件保留。正式结果出来再比较C1−C0；C0也是同网络/标签的对照，不误叫纯数据增强。原始24.44%/86.67%、03554.44%/73.33%、03650.00%/82.22%直接复用，不重新测基线/挑测试checkpoint。

下一步操作和执行者：用户依次启动C0、C1正式评测；Codex读取既有结果、统计百分比/配对差异和取代表视频，X无需返修，Codex/X不自动启停真实作业。
