# 2026-11-15：043-v2由Codex实现并部署，用户直接准备＋H0→H1

用户在已批准完整预算后明确“这次你自己改一下吧”，本轮Codex直接代码/CPU-fake/自查与文件部署；X无需重复实现/泛审。PR18固定`da666bc4a5d1aaa04381d64c29dbc0412fee6628`，基于accepted PR17@7d28d515，base=x/task042仅做增量审查，两PR不自动merge。

[交付](../../collaboration/responses/043_v2_codex_round1.md)、[机器证据](../../collaboration/evidence/043_v2_codex_implementation.json)、[自查](../../collaboration/reviews/043_v2_codex_selfcheck.md)、[运行交接](../experiment_plans/2026-11-15_task043_user_prepare_train_commands.md)。本地完整路径命令为docs/043-v2_服务器完整运行命令_2026-11-15.md。

H0/H1均原始OFT新LoRA、036普通参考保持；最多复用4个ten辅助视图，只有H1有当前事实文字，部署无提示。旧z/count/pair/TCIF不装，不续042。JSON-only sidecar、缺失不造假、双壶集合化、旧父元信息身份兼容、独立adapter/完整恢复/不退款计数和原正式360接线保持；无新评分器/VLM/FINISH。

71个不同受影响CPU/fake最终通过（70＋1CLI输出），另3个相同用例复测不重复计数；含完整1000的tiny软件循环及两臂180假接线，不是预训练模型或真实仿真。初次2个fixture setup error、Git HTTP2失败、纯配置0/0.0拦截与修正保留，没有修改断言/科学评分。实现自查不是独立外部审查。

最终源树d166847ffaab7cc6cd2e9262e7e0186ddabb71ec与GitHub/本地相同，归档SHA5a625b0cc7012c6cdae245f09077dce929a9fb3cc1731d8861e97deb0a0a7e5f。隔离code/config task043-codex-v1；108源码/依赖/模板、7实际配置SHA一致。原worker和simulation venv只no-deps editable映射，无升级；实际H0/H1训练配置严格解析、评测原来源保持核对通过，未构造数据或模型，解析无torch/h5py导入。最后CLI摘要修订仅在未运行的本轮新副本做有hash守卫的原子更新，原暂存归档与收据保留。

软件/文件部署100%，真实状态文字、训练/eval0；提示覆盖与模型效果open。下一用户直接启动准备→H0→H1，脚本通过即继续，不等X或额外Codex门槛；正常完成后用户另启动正式360。无需generate旧数据/index/plan/MVP/GPU预跑或旧baseline。

已批预算保持：一次CPU文字≤143960主键，零新仿真；两臂各1000、reference≤18048、含aux/dev模型前向≤54144、末1000正式10/00各90×两模型共360。所有真实阶段仍用户亲启，Codex未代跑/启停；原04270%/80%及全部数据权重失败署名保留，旧dirty checkout不改、无merge/删除，待删=[]。

关键文档按精确main发布commit读回并SHA本地归档、manifest更新；源码归档/私有部署receipt/原始测试日志另保存，不把服务器私有路径和凭证放公开工单。软件本轮交付closed，真实数据与研究效果open。
