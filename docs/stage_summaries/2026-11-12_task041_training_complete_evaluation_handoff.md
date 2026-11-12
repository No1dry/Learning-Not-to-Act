# 041两组训练完成与正式360评测交接

2026-11-12，Codex。[R2裁决](../../collaboration/reviews/041_round2.md)、[机器证据](../../collaboration/evidence/041_training_complete.json)。

## 训练事实

R0/R1各新增1000、连续1..1000、固定末1000，训练100%。两者基础都C1、同040完整参数初始化，新optimizer/scheduler；祖代1000＋新增1000分记，不是旧040 resume。run配置除臂/teacher/stage/output预期项外一致，1000条记录batch摘要/采样计数相同，不冒称独立全tensor/RNG因果核查。学生末SHA d4e726a8/45680122不同，完整训练状态SHA3da3cd0a/d2df244a与文件/保存值匹配。

原SOG10参考各9024（总18048）；R1的039 train-only3999/4000，R0为0，总参考22047/22048；student各24560、共49120，全部不超。少1次旧10参考是允许的实际选择结果，不补前向/凑预算。R0/R1原dev10动作L1 0.119043632/0.118295638，略低不是SR，不据此换权重或断言方法有效。

串行用户启动11-11 22:12:34，R0于11-12 01:43:05完成、R1于05:28:12完成，合计7h15m38包含已有输入读取。启动器两次及总COMPLETE来自成功分支，进程已结束、当前尝试无异常；未另采独立数值exit文件。11-11首次Codex部署类型错误及其零调用失败证据继续保留，软件PR16@e8dcf879/configfix1验收保持、X无需返修、不自动merge。

## 保存

34现成文件共514830066字节服务器/本地SHA一致，含两末adapter/identity/完整optimizer-RNG training_state、metrics/config/三账本/console、实际eval配置/启动器与原040index小记录。保留服务器全部中间checkpoint/原大数据/权重失败，不重写原事实；本地归档task041_training_complete_2026-11-12/preservation_manifest.json，SHA80db2c4e5d9428e3fa79f4311a188a697a6cbf5e155487ceacca17c9d1b7f967。复制/字节校验不是新模型/仿真实验，未新跑标签/index/评分/特征或训练。

## 下一步

**正式评测0%。用户现在按[命令](../experiment_plans/2026-11-12_task041_dual_model_evaluation_commands.md)及本地041完整命令第3节，一次启动已部署eval_both_sequential.sh，R0完整正式180成功退出才接R1正式180，共360。** 实际JSON各绑定本模型固定末1000，来源人口/runtime/core/reporting/评分/双bridge/全视频/seed7/H520/chunk8保持，启动器SHA cbf69a1b与原部署相同，仅bash语法核对、未执行。未来两eval/marker均不存在，没有继承039040分数或另开report。

不再generate/index/plan/MVP/旧资格/GPU预检/基线，不重开已完成训练或挑其他checkpoint/新seed。出错保留现场不自动重试/退款或启动下一臂，真实作业只用户亲启；Codex随后读原结果分析R1−R0，不全把R1−040归新保持项、不把跨版本稳定性称A硬保护/ICML创新或泛化保证。

训练closed、正式SR与研究open，X暂无修改任务。六关键文档精确GitHub commit读回SHA本地阶段备份/manifest，原dirty checkout不改，所有历史分数/权重/数据/失败/署名保留，无自动merge/删除或Codex代启停。精确待删=[]。
