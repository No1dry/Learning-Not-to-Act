> 2026-11-18：本页训练与四快照720评测已全部完成。以下命令仅为历史记录，请勿重开已完成run。正式结果见[045训练长度结果](../research/2026-11-18_task045_training_length_results.md)。当前没有新启动命令。

# 045：用户直接续训H0/H1到3000，后评固定2000/3000

2026-11-16。Codex已按用户要求完成参数化和隔离文件部署，90项CPU/fake通过，真实训练/评测尚未启动。X无需重复实现。具体服务器路径/conda/venv已填本地docs/045_续训与评测完整命令_2026-11-16.md；不要重开043/044。

用户按本地文件激活原OFT worker环境并source新session045.sh，然后：

```bash
nohup bash "$LNA045_CONFIG/extend_train_both.sh" \
  >> "$LNA045_ROOT/logs/task045-train-001.console.log" 2>&1 &
echo "PID=$!"
```

H0→H1各从自己的完整1000状态继续到3000，不重启优化器/学习率/采样器/RNG，不重训前1000。相同数据模型loss和250步dev/save，固定保存2000/3000。新输出和账本累计继承旧消耗，旧run不变。新增总4000更新，参考≤36096、学生≤108288，零新数据/标签/index。

```bash
watch -n 5 "tail -n 5 '$LNA045_ROOT/logs/task045-train-001.console.log'"
```

日志continued=N/2000为本组新增进度，另有累计步数。原输入加载期间不是优化器进度，失败保留现场不自动重试。

两组训练结束后，用户另按本地文件切simulation环境、source同session，再运行：

```bash
nohup bash "$LNA045_CONFIG/eval_training_length.sh" \
  >> "$LNA045_ROOT/logs/task045-eval-001.console.log" 2>&1 &
echo "PID=$!"
```

固定H0@2000→H1@2000→H0@3000→H1@3000，每快照10/00各90，共720，全视频。原无提示部署/评分/来源/H520/chunk8/seed7/双bridge保持；1000旧结果和原基线只复用，不按结果挑checkpoint、不加seed或prompt搜索。执行100%后原核验完成才有正式SR。

没有额外prepare/index/plan/MVP/资格/GPU预检，代理未代启动真实作业；已有输出/marker拒绝，不删除/覆盖或隐式续跑。源码PR20固定10531b62，不自动merge。原资料和失败署名保持。
