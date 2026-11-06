# 037：X设计审阅接受，原候选需实质修订

2026-11-06。用户交回X037，Codex读取PR12@e9f162a7c57819d40c44b3f8d5b9fffc2cb3e457，确认相对main15f仅新增X的037_round1.md。**审阅交付accepted/closed，X无需返修/重复综述；037方法与新颖性open，未授权实现或训练。** 不自动合并PR或倒改X原稿。

## 裁决与修订

[Codex完整裁决](../../collaboration/reviews/037_round1.md)采纳关键意见：剩余指令progression已有LTL2Action先例；完整角色标签下pair零误差冗余且单独可塌缩；遮挡使潜态完成关系不能直接升为当前观测后验点态等变；soft角色不能承接硬保护保证。基础构造/等价/三角界继续作条件性解释，不作为已成立的新原理或成功率/zero-shot保证。

单次OFT前向的候选接线可行，但正式predict、参数收集/保存、strict identity、参考旁路需贯通；双同类目标实例与静态D/K规格并非简单取文本embedding就解决。原设计/理论加裁决提示，保持旧版本证据。

决定保留增强和035/036，**原037不直接进入三组3000训练**；pair最多是待验证有限样本正则。Codex后续优先凝练任务语义状态与机器人执行阶段解耦的候选关系，仍须单独论证近邻差异和泛化，不能换名字当新颖性。原81216参考/540eval及1000→3000预算均未批准，不追加真实作业。

## 直接补齐的现有字段证据

Codex只读现成003 JSON/036索引，提供[脱敏小metadata包](../../collaboration/evidence/037_existing_metadata_samples.json)：5源记录的audit/lineage均存在、三池索引各一行、原文件SHA，未读RGB像素/新生成标签或运行仿真/模型。原完整摘录留本地，公开包为投影，不冒称全数据role/pair证书。

basket的normal交接158、drawer交接187，与各10初态均为A真/B假：这两端应是目标角色保持，不是完成A翻转。normal初态与10初态才有完成语义变化，但其他变量匹配尚不能由同父自动推出。抽屉active `[true,false]`和官方谓词顺序`[false,true]`的差异要求正确语义映射。找到的旧未知是table_drop诊断，不是role UNKNOWN标注；audit-only确认帧不自动并进HDF。

证据包SHA `dea5c7c0b654b0e587afe474bd28bcc46f7b8049769b233ef005bdd96bba93fd`。原X稿按固定PR head读回/本地保留，不复制为main已合并；本次文档精确新commit读回与SHA备份，更新manifest。无删除/自动merge/实现代码推送。

下一步操作和执行者：Codex据本裁决重新收敛037-v2的主张、监督关系与预算；X等待真正实现工单而非再审同稿，用户暂不启动实验。审阅100%，新实现/标注/训练/eval0%；035/036分数/权重/原数据、Eval九任务已发布状态均保持。
