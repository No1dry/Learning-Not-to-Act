# 040软件验收与文件部署完成，下一用户直接生产

2026-11-10，Codex。用户要求040交付后推进下一步；审查PR15固定`428c13585cebac1d6c90fd86a205e914caa2bb8f`（实现`0f24e9d46bfbc33edd001facf19d2c1c40ffc166`），依赖accepted PR14@113ded21。

## 完成范围

- [R1](../../collaboration/reviews/040_round1.md)接受软件与隔离文件部署，X无需返修、不自动merge。新8模块只做040，原60个egrs生产文件与039逐字节一致；计划/固定分组、pair-only normal、原dev稳定选择、原C1与保存恢复/正式端点、预算/中断清理符合工单。
- 独立162个定向CPU/fake最终全通过，无遗留失败/错误/skip。首次11项因本地旧固定core/reporting映射缺失setup error；一次Codex cwd错误未建成链接，复用原快照后只重跑11项通过。原错误留存，无实现/测试断言修改，不重跑全库或真实MVP。
- 新代码/配置目录名task040-428c1358：70源码依赖与4配置SHA一致；原runtime原字节复制，原039 C1 eval JSON仅改未来末1000 adapter。最初本地runtime尾部空行归一化被字节守卫在服务器写前拒绝，恢复原字节后部署成功。
- 原OFT worker/simulation venv仅无依赖editable映射切新包，在core cwd静态核对module来源；无依赖升级、旧代码/数据修改、服务器真实metadata/index、模型或仿真。040 production/train/eval目录均不存在。

见[机器证据](../../collaboration/evidence/040_codex_acceptance.json)及[用户命令](../experiment_plans/2026-11-10_task040_user_generation_training_commands.md)，完整具体路径命令在用户本地私有文档，不上传服务器私有路径/凭据。

## 下一步与边界

**软件/文件准备100%，真实生产/索引/训练/eval0%。** 用户按已部署配置在原OFT环境启动一次generate；有新增且training_ready=true，直接单C1 1000，再用户切simulation正式180，不再加Codex预检、MVP、状态重建/基线或凑N。

已批上限60普通＋360ten、原SOG10新初始化C1 1000/reference9024/student24560、10/00各90=180，未追加S/C0/seed或续训。旧305ten/105fresh/180raw/305pair与原dev保持，新ten/pair只train、新normal不入fresh；原核心和二元评分不改。039 C1 58.89%/85.56%与全部旧权重、数据、失败、署名保持，040覆盖及效果仍未知，不冒称ICML创新或保证提升。

关键文档、机器证据及X固定head原稿按精确commit读回SHA本地备份并登记manifest；原测试红灯、源归档与部署receipt保留。无自动merge/删除或启停任何真实作业，清理待删=[]。软件范围closed，真实数据/研究效果open。
