# 044：验收部署完成，用户直接P1→P2正式180

2026-11-16。PR19固定e8445b6a软件/文件部署accepted，新增60项CPU/fake通过，原未改bridge fixture历史缺失保留说明，不加真实预检。原90个生产源不变，101源码/依赖与3实际配置SHA一致，原两环境无依赖升级接线。真实模型/仿真/评测尚未启动。

本地完整conda/venv/服务器路径在用户项目docs/044_服务器完整运行命令_2026-11-16.md。按该文件激活原simulation环境、source部署session044.sh并进入LNA_CODE，然后只启动：

```bash
nohup bash scripts/prompt044/run_both_sequential.sh \
  >> "$LNA_ROOT/logs/task044-p1-p2-001.console.log" 2>&1 &
echo "PID=$!"
```

P1正式90正常报告/退出后自动P2正式90，两个独立原官方模型worker，全部视频。P1完整原指令＋初始A完成事实，P2只B；原完整A+B及A保护、错抓、释放、旧二元评分不变。模型没有加载H0/H1等研究权重，P0历史24.44%仅引用、不重测。180总budget与≤11700原predict保持。

## 实时进度

```bash
watch -n 5 "tail -n 5 '$LNA_ROOT/logs/task044-p1-p2-001.console.log'"
```

逐episode有episode_started；旧六批任务每10条执行完成才更新完成比例，新三按每条；加载和原来源核对期间不代表已完成episode。模型执行100%后仍有原正式核验，正式SR看最后summary/report，不把核验checked比例当SR。Ctrl-C只退出watch。

每组输出task044-p1/p2-eval-001，原持久串行marker记录当前组及最终状态。已有输出/marker就拒绝，不删除、不覆盖或自动重试。完整原评分仅原正式入口一次，不另开评分/预检进程。

不需要新prepare/index/plan/MVP/GPU资格或基线，不启动训练/00/额外seed/提示搜索。用户亲启；Codex只文件准备部署/命令/结果审查，X无需再实现。提示诊断不是自主RGB判断或理论性能上界。全部旧资料保持，不自动merge或清理。
