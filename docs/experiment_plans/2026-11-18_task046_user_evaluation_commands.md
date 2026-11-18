# 046已由Codex实现部署，用户启动固定P1→P2

2026-11-18。用户明确“要改的话你改一下就行了”，覆盖此前待X的分工。PR21固定a1179099c61317aba90ef8af4bc334f21fb10c88，X无需重复实现或泛审，不自动merge。

准备100%，新正式0%。83个不同CPU/fake最终通过；部署后实际配置、H1@3000权重与P0文件字节绑定通过，两个原环境仅no-deps映射新隔离代码，无升级。未运行真实模型、物理、标签/索引、plan生产或评测。

## 启动

沿已部署的原simulation环境；具体私有绝对路径与完整conda/python命令在聊天和本地`046_H1_3000提示词评测完整命令_2026-11-18.md`。source本轮`session046.sh`后：

```bash
cd "$LNA046_CORE"
nohup python -u -m egrs.prompt046 run-both \
  --p1-config "$LNA046_CONFIG/evaluation.p1.json" \
  --p2-config "$LNA046_CONFIG/evaluation.p2.json" \
  --p1-output "$LNA046_ROOT/runs/task046-p1-eval-001" \
  --p2-output "$LNA046_ROOT/runs/task046-p2-eval-001" \
  --marker "$LNA046_ROOT/launches/task046-p1-p2-001" \
  >> "$LNA046_ROOT/logs/task046-p1-p2-001.console.log" 2>&1 &
echo "PID=$!"
```

只启动一次。P1正式90正常并有完整报告后才启P2；P0复用已完成的同H1@3000 68.89%（62/90），无新执行。原90初态/完整目标评分/所有视频/H520/chunk8/seed7不变。旧044、045命令历史，不重开；没有新训练/00/标签索引或额外MVP，不需再次prepare/pip/plan。

```bash
watch -n 5 "tail -n 6 '$LNA046_ROOT/logs/task046-p1-p2-001.console.log'"
```

最终原核验后才有正式SR；两组结束后的`launches/task046-p1-p2-001/comparison.md`列P0/P1/P2总分及九任务，comparison.json保留所有配对得失。失败保留输出/marker，不覆盖、不自动退款重跑。用户交回后由Codex读取现成报告。
