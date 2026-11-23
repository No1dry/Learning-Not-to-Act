# 047：用户直接启动官方三套正式3000

已由Codex按用户新授权直接实现并部署，X无需重复。PR22@bd871dea127a2049134be4fb0fa7f392061d28d5，42项不同CPU/fake最终通过，126源/8实际配置脚本SHA匹配；不代表真实SR已验证。准备100%、正式0。

在已确认的peft-openvla＋simulation venv环境，source部署的session047.sh后运行：

~~~bash
cd "$LNA047_ROOT"
nohup python -u -m egrs.official047 run-all \
  --config-dir "$LNA047_CONFIG" \
  --output "$LNA047_ROOT/runs/task047-official-three-suite-001" \
  >> "$LNA047_ROOT/logs/task047-official-three-suite-001.console.log" 2>&1 &
echo "PID=$!"
~~~

本地完整文档047_三任务集官方评测完整命令_2026-11-18.md含实际conda/venv/session路径。这里不另要求安装依赖、prepare/index、MVP、GPU预检或启动旧044/045/046。

顺序base-spatial→h1-spatial→base-object→h1-object→base-goal→h1-goal，每cell500，总3000。官方原始任务/50初态/成功done/视频，三套各自归一化和220/280/300上限，seed7/env0/等待10/chunk8/两图proprio/crop不变。只H1加载一次固定045末3000 LoRA，base原版四套联合模型不注入。不是Remain评分，也无完成提示或训练。

实时只读：

~~~bash
watch -n 5 "python -m egrs.official047 progress --output '$LNA047_ROOT/runs/task047-official-three-suite-001'"
~~~

或简洁日志：

~~~bash
watch -n 5 "grep '\[047\]' '$LNA047_ROOT/logs/task047-official-three-suite-001.console.log' | tail -n 3"
~~~

加载阶段暂0%正常；随后显示当前组、总进度百分比和live SR。六组正常完整结束后run根下comparison.md/json给30任务/三suite/总体两模型SR差值；各组summary、episodes.jsonl、official_logs和rollouts保留原视频。技术异常保留并停后续，不自动重试/删输出；部分live SR不冒称满额正式结果。用户启动，Codex待交回结果，未代开实验或合并PR。
