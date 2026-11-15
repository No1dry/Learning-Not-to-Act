# Task043-v2训练完成与正式评测交接

2026-11-16。用户交回“跑完了”，Codex读取现成日志/元信息/metrics并按字节SHA核对；没有训练状态反序列化、模型加载、仿真、标签生产、重计分或代启停真实作业。

## 训练结论

H0/H1各连续1000更新，四checkpoint 250/500/750/1000齐全，固定末1000。总启动日志有COMPLETE两臂和COMPLETE both，无FAILED；两训练console正常返回complete=true，无Python traceback，无043残留prepare/train/evaluate进程。未另采数值shell退出文件，正常结束以原启动器成功分支为证。

两模型均从固定原始SOG10新装LoRA、祖代0/新增1000，非035–042续训。原040索引8ef04d91、主行143960、sidecar44fd03bb及原底座/归一化一致；两run除arm/输出及有意辅助提示路径外同配方。各1000行原metrics逐update连续、每步12ten/4fresh/4raw计数与记录batch-key摘要一致；不冒称全tensor/RNG因果审计。H0辅助不加提示，H1辅助加当前事实，正式两臂均无提示。

每组原参考8000train+1024dev=9024；模型main_train20000+aux_train4000+main_dev2048+aux_dev1024=27072。两组合计参考18048/模型54144，恰等批准上限，不追加前向/搜索/训练。原第0次路径失败产标签/前向0，原日志/marker及pathfix1全部保留。

| 项目 | H0 | H1 |
|---|---|---|
| adapter SHA-256 | 371f9f137333b48060ce3ba3ec295970a240365d862d1c1a10565577f60dae6f | 1479edd46c47ae10fe66eafa85e928c7043fd9954d54a126e06d83442a1b6aee |
| 完整训练状态SHA-256 | 8f39bca36cb8c7fb7c52e779d6696d2df6dc380c52b41cc24db24835a268e434 | 32c4768d8eb868de78bf2910622bc501537b82d900cb25909bd02d0ed946312d |
| 最终无提示dev10 L1 | 0.1234438700 | 0.1230172414 |
| 最终辅助dev10 L1 | 0.1234438700 | 0.1298933607 |

dev误差不是闭环SR，辅助有文字也不必更低；不据此宣称成功率/机制/泛化有效，不挑其他checkpoint。实际效果等待正式H1−H0匹配对照。当前训练100%、正式eval0%。

## 正式评测与角色

现有两evaluation配置已指向各自末1000，原部署SHA保持；三脚本bash语法核对通过、未执行启动器。两个未来eval目录和eval-launch marker不存在。用户直接按公开2026-11-16_task043_dual_model_evaluation_commands或本地043-v2正式命令，在既有simulation环境source pathfix1 session后启动eval_both_sequential.sh。

先H0正式180正常报告后H1正式180，共360，全视频；两模型无提示、无sidecar/在线GT/教师，原九任务来源、H520/chunk8/seed7、双bridge和10二元合规/00官方评分保持。正式入口自行绑定真实末权重，不再prepare/index/plan/MVP/GPU预检或基线，不重训/加seed。旧启动训练命令已标历史，勿重开。

Codex负责只读核对/原产物备份/研究解释，用户亲启所有真实阶段。X无需新实现/泛审，PR18与PR17未自动合并。正式SR/研究结论仍open。

## 保留与归档

现成两末adapter/identity/完整training_state/hash、metrics/配置/进度/预算/console、实际评测与session/启动器、sidecar小manifest共32个原文件518497361字节，复制到本地独立归档并SHA核对；不伪称完整143960行sidecar或所有中间权重已下载。服务器全部原数据/sidecar/中间checkpoint、旧失败、分数及署名保持。阶段/状态/命令精确GitHub commit读回SHA备份，manifest登记，无删除，待删=[]。下方旧0%快照不覆盖本轮状态，本条不覆盖未来用户执行。
