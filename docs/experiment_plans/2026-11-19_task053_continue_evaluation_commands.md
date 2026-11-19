# 053：保留11条、原版续439→H1 450

最终代码/配置短名task053-index50-continuation-v2。具体路径版本在用户本地docs/053_保留11条续跑完整命令_2026-11-19.md；旧052及053早期v1不再启动。

~~~bash
# PROJECT_ROOT为已确认服务器方法根目录
nohup bash "$PROJECT_ROOT/configs/task053-index50-continuation-v2/continue_and_eval_sequential.sh" \\
  >> "$PROJECT_ROOT/logs/task053-continue-eval-001.console.log" 2>&1 &
echo "PID=$!"
~~~

脚本内部原conda+仿真venv，无安装。只读取已完整450来源；先文件核验继承11（原10已报结果只核对字节，第11完整校验一次），原版仅新执行439，再H1新450，最后comparison。动作阶段实时SR包含继承11。原900预算、原指标/权重/原初态全部保持，无额外训练/生成/MVP。

~~~bash
watch -n 5 "grep -E '^\\[(053|049)\\]' $PROJECT_ROOT/logs/task053-continue-eval-001.console.log | tail -n 5"
~~~

启动先Verifying/Verified inherited，随后加载模型，再逐条任务/总体SR。新输出独立、不复制或覆盖父原件；旧11视频仍在旧run，新增视频在新run。旧partial summary保留10/450历史，不改成旧run成功。新marker防重复；错误保留，不删旧目录/marker或重开已跑轨迹。全部真实阶段仍用户亲启，Codex只文件诊断/软件/部署/结果。
