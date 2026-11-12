# 041用户训练与正式评测运行交接

2026-11-11，Codex。[R1](../../collaboration/reviews/041_round1.md)已accepted并隔离部署；固定PR16@e8dcf879，80源码/依赖＋8配置SHA匹配。准备100%，真实训练/eval0%。本文脱敏，实际绝对路径见聊天及本地docs/041_服务器完整运行命令_2026-11-11.md，不上传凭证/私有服务器路径。

## 2026-11-11部署勘误：改用configfix1

首次用户启动在数据/模型前因Codex把浮点0.0写成整数0而失败；不是X源码错误。新两份training.r0/r1.configfix1.json仅修该类型，本地和服务器实际严格配置loader通过、SHA一致；旧配置、失败日志和launch-001保留，没有真实调用/账本/训练输出，不退款清零。下面入口已更新，别重复原脚本。

## 下一直接训练，不再准备数据

用户只需启动已部署configs/task041-e8dcf879/train_both_sequential.configfix1.sh一次。脚本自己激活原Conda＋OFT venv，R0新增1000正常结束才接R1新增1000，独立日志/输出/账本；失败即停，不退款重试，不自动接评测。已有输出或原子marker拒重复；不要叠加逐臂命令。脚本仅语法检查，Codex未执行。

若希望显式普通命令，进入原OFT环境后使用：

~~~bash
python -u -m egrs.retention041 train \
  --config "$LNA_CONFIG/training.r0.configfix1.json" \
  --output-dir "$LNA_ROOT/runs/task041-r0-train-001"
~~~

R0正常完成后同环境将r0替换r1。实际040数据/初始化、039教师、core/runtime路径已写入两份配置，不需要重新下载、generate/index/plan/pip/MVP或基线。R0/R1基础都C1；祖代1000＋新增1000，不旧040resume。

进度看各run/metrics.jsonl的update、completion_percent、eta_seconds和old10_calls；本地命令文档给直接输出两臂百分比的简洁命令。训练不显示SR，loss不能代SR。逐臂console记录加载或异常，一键console记录START/COMPLETE/FAILED；Ctrl+C只退出tail，不停止后台。

## 训练结束后另行正式360

两臂固定末1000均正常完成后，用户另行启动已部署eval_both_sequential.sh；它切原simulation环境，R0完整报告/正常exit后再R1，单学生由原OFT worker执行。每臂九任务10/00各90，共360，原H520/chunk8/seed7/全视频/来源端点/二元口径不变，不继承039/040分数。

~~~bash
python -u -m egrs.retention041 eval --experiment-arm r0 --mode run \
  --config "$LNA_CONFIG/evaluation.r0.json" \
  --output "$LNA_ROOT/runs/task041-r0-eval-001"
~~~

逐臂执行时R0完成后替换r1；与一键入口互斥，不重复启动。模型执行100%后原进程可能仍在正式核验，summary.json/report.md生成并正常结束才交回，不另开第二个report任务。

本轮参考总≤22048、student≤49120、两组新增2000更新、正式360保持，新数据/仿真/标签/index生产0。已有checkpoint落后于已花预算时不能删账退款恢复；出错保留给Codex/X明确处理。主比R1−R0，软件验收不保证真实SR/显存/速度。下一执行者用户；X无需返修，Codex后续读取现成结果分析，不代启动或监督实验。
