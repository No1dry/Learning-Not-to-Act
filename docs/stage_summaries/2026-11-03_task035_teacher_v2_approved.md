# 2026-11-03｜035教师v2与73来源恢复获批

用户已明确同意：table_drop未知仅留诊断，确认违规/完成释放等原条件不变；复用002已有8条合格轨迹，重建73个候选（53train/20dev），新增上限73普通重放＋438次10尝试。原训练一组1000更新与同adapter10/00各90预算不变，用户亲自启动所有真实作业。

[直接实现任务](../../collaboration/tasks/035_teacher_v2_recovery.md)与[精确引用](../../collaboration/tasks/035_teacher_v2_recovery_refs.json)交X，不再先等一轮方案。这是版本化研究需求，R3解释器修复验收保持；teacher v1和旧资格不改，不修改正式benchmark评分/原状态或原24.44%/86.67%基线。

73候选按002原资格唯一失败=table_drop未知、完整任务/释放确认已通过且无已确认违规选择，不按模型评测表现挑选；覆盖basket14、basket_cheese_butter19、bowl_drawer_close17、basket_soup_cheese16、mug_microwave_close7。原180先验证/分组后选73，保留父ID/source_group/split，不假装自然firstN子集或重分组。候选不是新成功标签。

旧2normal/6个10共8条合格数据从002按HDF/资格/审计等SHA复用，不再模拟、不计新尝试。新73须真实重建RGB，再实际判资格和进行10桥接，合格量不保证；新失败也保存已真实记录的对齐RGB/动作前缀而不进训练，避免再次因筛选调整丢观测。

交接总引用SHA `e13bc97c610ac93404d6c49b89d9d4233dcb280922811e1cdd8f918258bddc80`；结果复用清单SHA `0e3a9f98246a884b9546a24ea1c718a49fd89545b014d210fc000b696fd77056`；原002 export/sources SHA `e1cfd07111f2fac37e27dc824635d05f391b45efc2fb35c4d15851f08e501e43`；73只读分析SHA `0e8e302d05cac1fd307a309f4a022d4a9887342110570ba3424066c106466768`。引用按原文件读取/哈希编制，未恢复状态、抽取轨迹值、生成新物理标签或加载模型。

目前实际数据仍2normal/6个10、全dual_mugs/train、dev空，训练/新模型eval0；批准预算不是已经生成成功。下一执行者X实现＋受影响CPU/fake，Codex审查/配置部署/完整命令，用户启动generated-003。无自动作业、merge或清理，待删=[]；本总结提交GitHub并按来源commit/SHA备份本地。
