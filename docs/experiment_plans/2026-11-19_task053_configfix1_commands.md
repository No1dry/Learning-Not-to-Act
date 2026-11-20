# 053 configfix1：改用v3，不删除旧标记

旧v2在激活benchmark前调用identity而退出，未加载模型/未新执行；实际fresh CLI已在相同conda/venv/session通过CPU-only入口测试。

~~~bash
# PROJECT_ROOT为已确认服务器方法根目录
nohup bash "$PROJECT_ROOT/configs/task053-index50-continuation-v3/continue_and_eval_sequential.sh" \\
  >> "$PROJECT_ROOT/logs/task053-continue-eval-configfix1.console.log" 2>&1 &
echo "PID=$!"
~~~

脚本内部激活原环境，新marker task053-launch-configfix1；旧task053-launch-001/失败日志不删除。只继承原11、base新439→H1新450→comparison，不重建450源、不重训、不加预算。原run尚未创建，沿原ID。

~~~bash
watch -n 5 "grep -E '^\\[(053|049)\\]' $PROJECT_ROOT/logs/task053-continue-eval-configfix1.console.log | tail -n 5"
~~~

原11核验/继承会先显示百分比，模型阶段实时任务/总体SR。具体完整路径与conda/python替代命令见用户本地docs/053_configfix1_启动修复命令_2026-11-19.md。不要重开旧v2或052，不删除marker/原输出退款重跑；全部真实阶段用户启动。
