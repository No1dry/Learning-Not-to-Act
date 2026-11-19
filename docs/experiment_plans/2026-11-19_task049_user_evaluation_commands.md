# 049用户运行入口

软件/部署100%，真实状态扩展与评测0%。用户等当前048结束后启动；Codex没有代启物理或模型。完整含实际服务器路径的普通conda/python命令，已放本地`docs/049_九任务每任务50次完整命令_2026-11-19.md`，不在公开库复制服务器地址/凭证。

部署的049串行脚本内激活原conda和仿真venv，自动执行：

1. 旧90初态字节复用，官方索引10..49生成360个新10来源；9任务×50共450，失败不替换。
2. 官方联合OFT原版全部450，同一原合规评分、全视频、逐条live任务及总SR。
3. 045 H1@3000相同450，再生成逐任务/总体及配对比较。

若希望手动分阶段：

~~~bash
python -u -m egrs.remain049 prepare --config CONFIG --output NEW_BANK
python -u -m egrs.remain049 run --config CONFIG --model base --output NEW_RUN/base
python -u -m egrs.remain049 run --config CONFIG --model h1 --output NEW_RUN/h1
python -u -m egrs.remain049 compare --base NEW_RUN/base --h1 NEW_RUN/h1 --output NEW_RUN/comparison.json
~~~

一条后台脚本与手动分阶段不要同时运行。日志过滤`[049]`即可看简洁逐条百分比/SR。准备中断可显式`--continue`，不隐式重试失败。已有模型输出不覆盖或自动续跑；技术错误交回Codex，不当作失败模型分数。新状态未全450准入，脚本不会冒称就绪或开始模型。

这是Remain mask10九任务450/模型，不是官方LIBERO10十任务500/模型；不含新00，不把两种评分合并。模型/原语言/520/K4/chunk8/seed7保持，零训练/新标注/FINISH/VLM/额外seed/MVP，旧047048不要重开。软件规格见`docs/task049_remain50.md`，交付见049_codex_round1。
