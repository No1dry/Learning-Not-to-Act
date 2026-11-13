# 042用户训练与正式评测交接

> 2026-11-13已完成：F0/F1训练及正式360均100%，10/00分别68.89%/80%与70%/80%。以下启动命令仅历史，勿重开。当前入口为[042详细结果](../research/2026-11-13_task042_results_and_failure_mechanisms.md)和[最终阶段总结](../stage_summaries/2026-11-13_task042_final_results_attention_firewall.md)。

2026-11-12，Codex。[R1](../../collaboration/reviews/042_round1.md)已accepted并隔离部署，固定PR17@7d28d515，92源/依赖＋8配置SHA匹配。准备100%，真实训练/eval0%；此页脱敏，具体绝对路径在聊天与本地docs/042_服务器完整运行命令_2026-11-12.md。

用户直接启动已部署configs/task042-7d28d515/train_both_sequential.sh一次。脚本自动激活原Conda peft-openvla＋OFT venv，F0新增1000正常完成后接F1新增1000，不自动评测/重试/退款；已有输出或marker拒重复。原R0完整初始化、原C1及数据/采样/dev保持，祖代2000＋新增1000累计3000。内部仍是普通python，单臂替代入口：

~~~bash
python -u -m egrs.tcif042 train \
  --config "$LNA_CONFIG/training.f0.json" \
  --output-dir "$LNA_ROOT/runs/task042-f0-train-001"
~~~

F0正常完成再替换f1，与一键互斥，不叠加执行。实际训练JSON已用同一严格loader读取通过，浮点0.0保持，不需要pip/generate/index/plan/MVP/新baseline或GPU预跑。初始读已有输入/加载权重阶段还没有update时看对应console，不因此重复启动。

本地文档第2节给一段每5秒自动刷新两组update/百分比/ETA/L1的只读Python命令，Ctrl+C仅退出查看，不停训练；训练无SR，不用loss代替SR。出错保留现场，按同run完整状态/预算与attention合同处理，不能删目录/账本退款。reference总≤18048、student总≤49120，不追加真实干预诊断前向。

两组固定末1000正常结束后用户另启动eval_both_sequential.sh。它切原simulation环境、模型由原OFT worker执行：F0完整正式180及正常报告后F1正式180，共360，新模型各九任务10合规90＋00官方90，原H520/chunk8/seed7/来源/双bridge/评分/全视频/raw保持。单臂替代命令：

~~~bash
python -u -m egrs.tcif042 eval --experiment-arm f0 --mode run \
  --config "$LNA_CONFIG/evaluation.f0.json" \
  --output "$LNA_ROOT/runs/task042-f0-eval-001"
~~~

F0完成后替换f1，与一键互斥。正式入口自行绑定实际权重与来源创建plan，无额外plan/资格扫描/report作业；模型执行100%后可能仍在原进程核验，等summary/report及正常退出，不继承旧R0/041分数。

本轮只软件/静态配置/随机tiny CPU检查，无预训练VLA/GPU/轨迹数据/仿真/训练eval预跑；真实实例与布局准入由用户正常作业完成。不承诺GPU速度/显存/SR，主比F1−F0。X无需返修，用户下一启动训练，Codex后续读取结果；旧全部权重/数据/分数/失败/署名保留，PR17不自动merge，无删除。
