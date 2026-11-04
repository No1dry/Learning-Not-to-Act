# 035 R7：混训产物核对通过，180条评测已部署

accepted/closed仅指1000更新训练完成、产物身份与文件部署；研究效果仍open。PR10保持44b6ca02，不自动合并或要求主体返修。

1000/1000更新完整、数值有限，四checkpoint及固定末1000选择正确。adapter/续接状态SHA、导出身份、原组件/统计/训练源码核对通过。训练首/末50均值下降59.00%，250→1000的10 dev下降7.48%、normal上升1.43%；这些不是任务SR。训练覆盖仍6/9，正式测试不裁剪。

两环境必要方法包无依赖安装，7个使用文件字节匹配、factory可导入。纯文件计划180/180通过，模型/仿真未创建，新输出未创建。首次误指00空模板的MissingSourceError已保留，仅修为实际已构建sources，不重建初态或改变评分。新runtime仅repo_path使用训练同一干净OFT副本，旧脏目录/runtime/基线不动。

下一执行者用户：[完整正式评测命令](../../docs/experiment_plans/2026-11-04_task035_dual_condition_evaluation_commands.md)，同一最终adapter的10/00各90，直接启动、不另跑plan/pip/GPU试推理/MVP。全部视频/原始证据、端点与原评分保持；10对24.44%、00对86.67%分别比较。Codex不代启动/监督真实实验。

X既有[实时SR/去重复读](../tasks/035_evaluation_live_reporting_followup.md)尚无新交付，保留非阻断open，本轮无新增实现要求。当前入口按任务单元更新报告、控制台仍condition/task/status，不假称已补实时SR。

[训练与交接总结](../../docs/stage_summaries/2026-11-04_task035_mixed_training_complete_eval_handoff.md)。历史/原数据/运行refs不清理，待删=[]。
