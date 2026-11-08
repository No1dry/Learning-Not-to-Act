# 039：两组末1000已就绪，一条命令自动完成两组正式评测

2026-11-08，Codex。[R3训练产物核对](../../collaboration/reviews/039_round3.md)接受C0/C1均1000/正常退出与末1000身份；两组adapter及完整续训状态/配置日志29文件已本地SHA备份。训练100%，评测文件准备100%，真实模型评测0%。原已批准360条不增加，**只由用户启动以下作业**。

## 一条命令：C0正式180结束后，自动C1正式180

```bash
nohup bash /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task039-113ded21/eval_both_sequential.sh >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-eval-both-001.console.log 2>&1 & echo "Launcher PID=$!"
```

启动器已上传/SHA核对并只做bash语法检查，未执行。它自行激活原Conda＋**simulation评分venv**、原session/core cwd；模型仍按runtime在原OFT worker启动，不用selector环境或再pip。沿用原串行评测方式，C0完成包括正式summary、正常退出后才开C1，不改造并行仿真/评分。

每组九任务，mask10合规90＋00官方90，各固定末1000；H520/chunk8/seed7、原完整指令/双RGB/proprio、原九任务来源与双bridge-proxy、评分reader不变，全视频/raw/action/query保存。不是把旧模型成功或失败复用到新模型；无FINISH/外部VLM/评测教师或GT动作路由。

脚本只检查末checkpoint存在和拒绝已有eval输出/原子launch marker以防重复。正式`--mode run`自己绑定实际权重和原来源、创建新plan，不另跑plan/MVP/来源物理预检/重建初态或基线。发生错误停止启动后续arm、保留当前run/日志/marker，不退款重试/自动report；勿与旧逐组eval命令同时运行。

## 简洁查看两组进度

```bash
tail -n 2 -F \
  /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c0-eval-001.console.log \
  /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c1-eval-001.console.log
```

C1尚未开始时提示对应日志不存在是正常的，`-F`会在后续自动跟踪。`Ctrl+C`只退出查看，不停止nohup。execution为模型执行百分比，verification为同进程正式核验百分比；每模型180条，原六任务执行单元可能每10条才更新一次，不是每控制步都变。

加载/来源绑定或一个单元尚未完成时可能暂时没有新行，不因此重开进程。**模型执行100%不等于该组评测完全结束**：同一进程还要写原有正式summary/report，随后打印10/00的`formal_SR=xx.xx%`。pending不是0%；训练loss/计数准确率不是SR，不单独启动第二份report。

总启动状态、两arm接力/退出状态看：

```bash
tail -n 10 -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-eval-both-001.console.log
```

日志只读，没有GPU评测副作用。若要过滤JSON为上一轮中文简洁格式，可按下面命令；其中ARM随tail文件头自动切换：

```bash
tail -n 1 -F /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c0-eval-001.console.log /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/task039-c1-eval-001.console.log 2>/dev/null | python -u -c '
import sys,json
arm="?"
for line in sys.stdin:
    if line.startswith("==>"):
        arm="C0" if "task039-c0-" in line else "C1"
        continue
    try: d=json.loads(line)
    except ValueError:
        if "formal_SR=" in line or "Traceback" in line: print(arm+" "+line.strip(),flush=True)
        continue
    phase=d.get("phase")
    if phase=="execution": print("{} 模型执行: {}/180 ({:.2f}%)".format(arm,d["model_completed"],d["percent"]),flush=True)
    elif phase=="verification": print("{} 结果核验: {}/180 ({:.2f}%)".format(arm,d["checked"],d["percent"]),flush=True)
    elif phase=="final": print("{} 结束: {} | {}".format(arm,d.get("status"),d.get("software_exit")),flush=True)
'
```

## 绑定与保留

- C0：`runs/task039-c0-train-001/update-001000`，adapter SHA `e9d481030c35011498c9172db9c22c335b5cf4c52397b72309f9208a6fcb4060`。
- C1：`runs/task039-c1-train-001/update-001000`，adapter SHA `6d340e99186090bab6739f173ecb118d03eb1bf574ae96d5f1c34241b02d644e`。
- 两组同新index `b85875658da033a144d6be1fb0da4726edc20033d4f3b8cf3ed7dfc4a18d377c`，305有效pair/九任务覆盖；白杯训练仅1父源3变体的限制保持记录，不调split/补来源或保证SR。

配置已指向实际存在的末权重，但本轮没有运行build_plan/模型/仿真或真实评测。所有旧数据、权重、中间checkpoint、分数、视频、失败及039生产/训练原件保留；不挑250/500/750权重，不重训或追加预算。039 C0也是同网络/标签的对照，不叫纯BC基线；后续主要比较10/00正式SR、每任务变化及同episode配对差异。

下一步操作和执行者：用户运行上面一条启动命令；Codex读取实际结果、归档权重/报告/代表视频并分析，X无代码修改任务。无需再等其他验收/MVP。
