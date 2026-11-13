# 042固定末1000两模型正式360评测

2026-11-13，Codex。F0/F1新增1000均100%完成，[R2文件审查](../../collaboration/reviews/042_round2.md)accepted；完整权重和续训状态已本地SHA备份，正式eval0%。下一步所有真实作业仍由用户启动。

直接一次运行已部署configs/task042-7d28d515/eval_both_sequential.sh即可，自动激活原Conda与simulation venv；模型使用原OFT worker。完整绝对路径命令在本地docs/042_正式评测命令_2026-11-13.md和聊天，不在公开GitHub暴露私有服务器路径。

脚本内部依次执行普通python命令：

~~~bash
python -u -m egrs.tcif042 eval --experiment-arm f0 --mode run \
  --config "$LNA042_CONFIG/evaluation.f0.json" \
  --output "$LNA042_ROOT/runs/task042-f0-eval-001"
~~~

F0的summary/report生成并正常退出后执行f1。只启动一次，不叠加逐组命令；已有输出/原子marker拒覆盖，失败保留并停止，不隐式重试退款或接下一臂。启动器SHA a6de7deff37111031a573724a6e25a837b769cd3be5b4b1bd3c23af0f2178c2c，同原部署且仅语法检查，Codex未执行。

每模型九任务10二元合规90＋00官方90，共360；绑定F0末adapter8afe299e、F1末79ad5b7f，原H520/chunk8/seed7/全视频/raw/来源人口/runtime/core/reporting/双bridge/评分与原041保持。F0 native与F1 firewall实际合同随各自checkpoint执行；主比较F1−F0，不借用旧R0分数，不从dev挑checkpoint。

无需prepare/index/plan/MVP、重复物理资格、GPU预检、重训或基线。执行100%后可能同进程继续核验，需summary/report及正常退出；不另启动第二个report作业。训练本身没有SR，新SR需这次真实评测给出。旧训练启动命令是历史，不再运行；全部原权重/数据/失败/署名保留，PR17不自动merge。

给X的简短prompt：

> 042两组训练已完成并通过产物验收，接下来由用户启动正式360评测。无需修改代码或返修，保留PR17与原交付；等待真实结果反馈，不启动真实作业。
