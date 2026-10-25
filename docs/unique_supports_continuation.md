# 029：支持标签唯一与显式续跑

028正式运行已完成2条（均模型失败），第3条q3因`supports=["entity","entity"]`技术中断。029只修复生成约束漏掉的唯一性，不事后去重旧输出、不改validator、权重、评分或状态。

支持标签用无放回的有限状态语法生成，允许全部325种非空有序子集，不强迫新增任何证据标签；schema同步标注uniqueItems。原q1/q2/q3保存观测与先前模型预测/命令已复用重建失败请求：6张图、原与新输入均2766 tokens，真实3B/checkpoint-3输出666 tokens，原严格校验通过；无仿真、动作或训练。该真实验证使用修复后selector文件；后续只修改评测编排，release与诊断的selector文件逐一核对SHA，不为入口修改再跑模型。

新增`run --continue-from CLOSED_RUN`只继承已验证、status=completed的全部结果，包括success/failure/unknown，不按成败筛选。原技术失败尝试保留在旧目录和lineage，新命令显式从该episode原初态重新开始；不尝试从中断轨迹中段恢复。继承结果不复制/覆盖原数据。

执行前核对固定来源、状态、底座、checkpoint、selector配置、memory及原视频/raw/sidecar证据。新目录保留完整100计划，以父结果引用+新结果合并原core统计；原2条单独记录旧method SHA，新增78条记录029 SHA，不能冒称全部由029重新执行。技术失败历史在continuation清单中单列，不伪造旧失败从未发生。旧文件被改动或来源/配置不同则在创建模型前拒绝。

控制台`[SR/live completed]`显示已完成有效episode中的累计SR（unknown留在分母），明确inherited/new数目；最终`[SR/verified summary]`同时显示完成子集SR和计划100分母SR。原summary/report的主指标不变；实时SR不是新评分或提供给policy的真值。

本轮实际旧2/80已完成，剩余78由用户启动。Codex只运行必要selector复核和CPU/fake/文件级检查，不启动整批续跑，不重放/重建物理状态，不重跑原2条或自动merge。
