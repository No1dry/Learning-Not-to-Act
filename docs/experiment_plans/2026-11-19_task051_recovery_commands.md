# 051用户启动失败项补救

软件/部署100%，真实补救0。完整实际conda/python、后台串行和绝对路径watch位于本地`docs/051_只补45项并接续评测_2026-11-19.md`；公开库不复制服务器路径或凭证。

新脚本source原conda/仿真venv/session051，先保留405、只处理45失败；完成450/450后才接续原049的原版450和H1@3000 450。原049完整流程不要重开。若050 H0还在运行，用户自行选择等其结束再启，不由Codex启停任何作业。

只补建的拆解入口：

~~~bash
python -u -m egrs.remain051 recover --config CONFIG --parent ORIGINAL_BANK --output NEW_BANK
~~~

新bank与模型输出都独立。显式continue只继续pending、不重试新failed；任何旧成功、旧失败、原图/状态/账本不覆写。42源build（40微波炉＋stove21/pots34）、45源replay（其中3pot只replay），一轮有界补救，内部规则不变。RGB仍1档、没有悄悄放宽到2；5项仍可能失败，未全450则退出并阻止模型启动。

全部就绪后仍用原049模型/rollout/判据/评分/全视频/逐条live SR，不新训练/扩population/加seed/基线重测。补建看[051]，原评测沿[049]；过滤两个前缀即可简洁查看实时百分比与SR。用户亲启，Codex只准备，X无重复实现任务，PR26不自动merge。
