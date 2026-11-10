# 040覆盖增强预算获批，详细工单交X实现

2026-11-10，Codex。承接[040提案](../research/2026-11-10_task040_parent_coverage_proposal.md)与[039纠错](../research/2026-11-10_task039_analysis_review_corrections.md)，用户明确答复：“按你推荐的吧，提交工单吧”，并要求继续。本阶段只交接规格，不是代码验收或真实实验完成。

## 批准范围

- 三任务stove/mug_pudding/two_pots各demo_20..39候选60；固定seed7父分组，仅新train代表生成，dev封存；旧180的136train/44dev与所有旧数据不动。
- 新普通≤60、10尝试≤360（每父1normal、3×2 ten、H520）；沿039真实释放收尾及仅双壶初始化置换、原V2资格。不保证合格数，不凑N/退款或隐式重试。
- 新ten只追加train；新normal仅生成与pair证据，原fresh105/raw180、原dev及选择键/顺序全部保持。原305ten/305pair复用，实际新增计数进入新040契约。
- 一组C1从原SOG10新初始化1000更新，固定末1000/reference≤9024/student≤24560；原网络/loss/任务均匀采样不变，新模型正式10/00各90共180。无S/C0/续训/新seed/基线或改评分。

## 交付要求和权限

[040详细工单](../../collaboration/tasks/040_parent_coverage_augmentation.md)直接交X实现/定向CPU-fake/新PR与responses/040_round1.md；不另排泛审或真实MVP。工单详细约定了旧source/group身份、20..39版本化范围、train-only/去重、pair-only normal、不改dev选择、预算持久记账、共享推理/保存恢复、单命令生产与常用conda/python及百分比日志，减少后续返修。

Codex验收后隔离部署与完整命令，用户亲自启动所有真实元数据/轨迹生成/标签索引/训练/eval。预算批准不授权Codex或X代启停，X不SSH部署或接触真实实验。原039完成58.89%/85.56%、PR14@113ded21、所有旧失败/权重/数据/署名保持。

**规格/交接100%，040代码实现/部署/真实数据/训练/eval均0%。** 已批准的是上限，不声称新父覆盖已恢复或SR将提升；本轮为覆盖增强强基线，不是ICML方法创新定稿。旧提案“待批准/无X任务”自本节起为历史。

## 归档与下一步

工单、批准机器记录、当前方案/STATUS/AGENTS及本阶段总结以精确提交读回并本地SHA备份，receipt与backup_manifest记录来源。旧dirty checkout不修改、不自动merge或清理；待删除清单=[]。下一执行者X直接软件交付；Codex等交付审查，用户当前无需启动实验。
