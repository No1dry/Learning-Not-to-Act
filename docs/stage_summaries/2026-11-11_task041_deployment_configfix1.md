# 041部署配置勘误configfix1及用户重启交接

2026-11-11，Codex。[证据](../../collaboration/evidence/041_deployment_configfix1.json)、[原审查补正](../../collaboration/reviews/041_round1.md)。

用户首次启动R0为22:01:50，22:01:55在严格配置读取退出，R1未启动。Codex本地生成实际部署JSON时把photometric_probability的浮点0.0序列化成整数0，导致完整固定preset的类型比较拒绝。错误在Codex部署，不要求X放宽正确的严格检查；166软件CPU/fake通过仍属实，但没有覆盖后生成的错误部署配置，原“可直接启动”结论在此补正，不倒改或隐去原失败。

修复仅新建两份training.r0/r1.configfix1.json，0→0.0；原配置保留。新train_both_sequential.configfix1.sh读新配置、使用新configfix1 marker；原launch-001、原两失败console保留、没有删除。新旧方法/数据/权重/采样/loss/dev/评分/初始化、两臂run ID与预算保持。失败发生在dataset/model/output/ledger创建前，train-001两个目录不存在、模型和参考调用0；不构成账本退款或已花预算重开。

本地用既有严格loader重现原配置失败；两份新配置在本地和服务器原worker实际load_config均通过，三新文件SHA一致，启动器仅bash -n。没有读取真实数据轨迹/生产标签索引或加载模型/仿真/训练/eval，CUDA未初始化；没有重复166/新GPU预检/MVP。旧失败日志从服务器取回与SHA核对保存，修复前完整私有命令文档另存。

**修复准备100%，真实训练/正式评测0%。下一用户直接按更新运行说明启动configfix1 R0→R1，每组新增1000；两组正常末1000后另行正式360。** 不再启动旧脚本，不generate/index/prepare、不换模型或追加预算；X无需返修。Codex/X本轮只文件修复/静态配置检查，不代启停真实作业。

六关键文档（本总结、证据、审查补正、运行说明、STATUS、仓库AGENTS）以同一GitHub提交发布，精确commit读回SHA本地归档manifest；新三配置/服务器检查收据/原两失败日志和修复前命令另存。软件accepted保持、真实效果open，PR16未自动merge，全部旧权重/数据/分数/失败/署名不变，删除清单=[]。
