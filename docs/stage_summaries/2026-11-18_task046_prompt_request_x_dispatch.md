# 046交接：用户要求H1@3000的P0/P1/P2诊断

2026-11-18。用户要求在045 H1@3000上重做原提示词实验。按同模型既有评测复用P0=68.89%（62/90），只新增P1/P2各90，共180，predict合计≤11700；全部真实作业仍用户亲启。P0复用是减少重复工作的执行解释，已明确告知，不冒充新执行；若用户另要求重跑P0，再单列90。

详细工单`collaboration/tasks/046_h1_3000_prompt_diagnostics.md`、固定绑定`collaboration/evidence/046_reference_bindings.json`及`docs/experiment_plans/2026-11-18_task046_h1_3000_prompt_diagnostics.md`已交X。X直接最小版本化接线和受影响CPU/fake，交新PR及046_round1，不先泛审/SSH/真实MVP。依赖PR20@10531b62，参考PR19@e8445b6a，不自动merge。

定向阅读发现旧044刻意禁止研究adapter，不能只换路径或删除其检查；新046组合045的H1/显式step3000加载与044逐字语言替换、实际predict审计、ten-only正式180。冻结adapter SHA78a96aa7、P0 plan/summary完整字节SHA与同九任务来源；不改旧044/043/045入口、权重、评分、失败或署名。外层如实标为有初始语义提示及研究adapter，原artifact内部无提示训练身份不改。

P1为原完整指令＋初始A完成事实，P2仅剩余B，均逐字沿044冻结表、episode内固定；模型只接RGB/proprio与该文字，评分仍完整A+B/A保持。训练/00/新训练物理数据/标签索引/额外prompt与seed/MVP均0，不引FINISH/VLM/在线GT。当前H1的P0不混作原版模型22/90；P1/P2没有00，不拼旧00伪造新AVG。

方案与交接100%，046实现、部署、新正式评测0%。下一X实现；Codex验收后隔离部署并给用户常用conda/python一条P1→P2完整命令。现在没有可启动的新命令，不重开任何045/044旧run。真实结果open，不预判prompt收益或语言理解机理。

六关键文档按精确commit读回SHA归档并登记本地manifest；现有脏研究checkout不改，无删除，待删=[]。045原结果和四新快照保留。研究记录册045更新的本地版/源码已完成，在线发布两次归档上传超时、仍旧第3版；该网络问题独立保留，不成为046实现前置或新的GPU工作。
