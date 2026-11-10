# 040：软件已验收部署，用户直接一次生产→一组C1→正式180

> 2026-11-11完成更新：生产/导出/索引100%、training_ready=true、新65train10及65pair。**跳过第1节历史生成命令，直接第2节单C1训练1000。** 获取本快照时训练/eval未开始，不重开已完成production-001。

2026-11-10，Codex。[R1](../../collaboration/reviews/040_round1.md)接受PR15@`428c1358`的软件/CPU-fake和隔离文件部署，X无需返修；[机器证据](../../collaboration/evidence/040_codex_acceptance.json)。实现不是main快照，不自动merge。以下真实步骤**只由用户启动**，本轮未代跑。

## 环境与准备

已部署代码/配置目录名`task040-428c1358`。保留原peft-openvla Conda底座＋原OFT venv，评测父进程切原simulation venv；不是selector，不安装或升级依赖。Codex已填实际generation/eval/runtime与session040.sh，70源码/依赖文件和4配置SHA匹配，两venv包映射核对。

本页为不含服务器私有路径的命令版；实际source/activate绝对路径及所有完整命令已在聊天交付，并保存在用户工作区`docs/040_服务器完整运行命令_2026-11-10.md`。先按该文件激活相应既有环境、source部署的session040.sh，使下列`LNA040_*`成为真实路径，不将占位符原样运行。无需用户再pip/改JSON/做plan或真实MVP。

## 1. 原OFT环境，启动一次数据生产

```bash
cd "$LNA040_CODE"
nohup python -u -m egrs.coverage040 generate \
  --config "$LNA040_CONFIG/generation.json" \
  --output "$LNA040_PRODUCTION" \
  >> "$LNA040_ROOT/data/coverage040-production-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 6 -f "$LNA040_ROOT/data/coverage040-production-001.console.log"
```

Ctrl+C仅退出tail，不停止后台作业。此命令完成候选分组→仅新train代表的真实生成→增量索引，不加载VLA训练或评测。进度是已处理train父组/实际计划父组，60候选不等于60生成父组，最多60普通/360ten不保证跑满或成功数。源/attempt/H520控制心跳与hash/索引进度沿日志；训练/评测进度此时仍0。

正常完成后preparation_report.json给new_qualified_train10、training_ready和索引。**有新增且ready即可直接下一步，不再等待Codex额外预检或凑N。** 没新增或技术错误则保留目录/账本/全部前缀交回，不删除后重跑、加来源/改阈值；本轮未提供生产resume。

## 2. 生产正常且ready，在原OFT环境训练单组C1

```bash
cd "$LNA040_CODE"
nohup python -u -m egrs.coverage040 train \
  --config "$LNA040_CODE/configs/task_control/task_control_factorization.json" \
  --benchmark-root "$LNA040_CORE" --runtime "$LNA040_RUNTIME" \
  --index-dir "$LNA040_INDEX" \
  --output-dir "$LNA040_ROOT/runs/task040-c1-train-001" \
  >> "$LNA040_ROOT/runs/task040-c1-train-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 3 -f "$LNA040_ROOT/runs/task040-c1-train-001.console.log"
```

从原SOG10新初始化、C1默认且唯一、1000更新/固定末1000；不是续训039。原loss/任务均匀采样/旧dev与fresh/raw保持；新normal只pair，实际新train10追加。训练没有SR，显示update/百分比/loss/耗时/参考学生账本；reference≤9024、student≤24560含dev。不要重复点击或主动删账本，恢复需求交回说明，不用旧039 checkpoint。

## 3. 训练正常1000后，切原simulation环境评新模型180

source原simulation venv，再source同一session040.sh、在core目录运行；模型子进程仍原OFT worker，不改包或重建状态。

```bash
cd "$LNA040_CORE"
nohup python -u -m egrs.coverage040 eval --mode run \
  --config "$LNA040_CONFIG/evaluation.c1.json" \
  --output "$LNA040_ROOT/runs/task040-c1-eval-001" \
  >> "$LNA040_ROOT/runs/task040-c1-eval-001.console.log" 2>&1 &
echo "PID=$!"
```

```bash
tail -n 4 -f "$LNA040_ROOT/runs/task040-c1-eval-001.console.log"
```

原九任务10合规90＋00官方90、H520/chunk8/seed7/全视频、原source/core/reporting/双bridge保持。正式run自己绑定实际末1000，不另跑plan、旧物理资格/基线或第二个report进程；不继承039分数。模型执行完成后同进程可能仍做正式核验，summary.json/report.md及正常退出才是最后完成；进度文件不替代正式SR。

本轮不包含S/C0/额外seed/续训或新评分；生成/训练/正式效果必须按实际结果报告，不将软件验收当SR提升。Codex只文件与后续结果审查，不代用户启停。
