# 052用户命令：只补3项后自动接续原900

已部署，未代启动。实际完整路径版在用户本地docs/052_仅补3项并接续评测_2026-11-19.md，配置目录短名task052-sparse-rgb-recovery-v1。

~~~bash
# PROJECT_ROOT使用已确认的服务器方法根目录
nohup bash "$PROJECT_ROOT/configs/task052-sparse-rgb-recovery-v1/recover_and_eval_sequential.sh" \\
  >> "$PROJECT_ROOT/logs/task052-sparse-rgb-eval-001.console.log" 2>&1 &
echo "PID=$!"
~~~

脚本内激活原conda+仿真venv，无依赖安装。447原样引用，只补stove21构造和3个source独立回放；两壶原v6构造不重做。明确新RGB2档/面积上限，原物理及2×150保持。一轮失败保留并停止，450全ready后自动原版450→H1@3000 450→comparison。沿原预算，不额外模型/训练/seed。

~~~bash
watch -n 5 "grep -E '^\\[(052|049)\\]' $PROJECT_ROOT/logs/task052-sparse-rgb-eval-001.console.log | tail -n 4"
~~~

补救显示已处理/3、ready/450和百分比；模型每条显示任务和总体合规SR。052输出独立于049/051，不能重开旧脚本或重复本启动器；原子launch marker防重复，出错保留不删目录退款。具体conda/python仅补救替代命令、日志与新bank/run位置见本地完整文档。全部真实阶段由用户启动；Codex/X不自动代跑。
