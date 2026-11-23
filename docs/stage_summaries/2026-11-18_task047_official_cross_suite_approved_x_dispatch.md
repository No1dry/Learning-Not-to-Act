# 047 已批准：官方pipeline、三套×10任务×50初态×两模型

用户明确要求直接采用OpenVLA-OFT源码评测流程，并将上一建议600提升为3000正式episode，一步到位。base为官方四套联合SOG10原版，h1为同底座＋045 H1@3000 adapter78a96aa7，各在Spatial/Object/Goal全部10任务×50默认初态评测，共每模型1500/总3000；旧九任务00/10与046分数不改。

新047是方法仓库的最小加载/观察/串行接线，不是扩展Remain benchmark。固定原OFT e4287e94，直接委托官方eval_libero/run_task/run_episode、环境/图像动作/原生done/全视频。官方各suite归一化和220/280/300上限、seed7/env seed0、settle10/chunk8、两视角/proprio/center_crop、task order0/init0..49保持。H1的训练10 lineage不可改写；047独立核验同底座及实际训练统计，再显式记录不同的当前推理suite统计并严格恢复原rank16 LoRA；旧验证器不放宽、不重复官方已合并adapter、不改action/proprio组件。

用户只启动一条串行六cell，每cell500，正常完成自动下一个，失败保留并停后续、不自动重试/换初态。不以低SR中止正常实验。原生异常若被捕获也需记录技术失败，不能伪称有效满额模型结果。输出官方日志/全视频、轻量逐条JSON、实时进度百分比与live SR、最终30任务/三suite/总体两模型SR和差值。不使用Remain合规评分器/FINISH/外部VLM/新提示，不将旧九任务拼成官方四套AVG；这是已见任务能力保持而非严格zero-shot。

预算正式3000、动作块自然上限101000，零新训练/生成/标签索引/教师/真实MVP或预检/额外seed。047任务、批准证据及reference_bindings为入口；X直接实现＋受影响CPU/fake、新PR和047_round1，不先泛审、不SSH或真实模型物理。建议基于accepted PR20@10531b62，不自动merge PR20/21。Codex建议式验收后隔离部署并给常用完整命令，用户亲启，授权不扩代跑权限。

本轮仅公开源码只读下载/AST与既有adapter源码阅读、工单与归档；官方runner701a20b6和libero_utils489c16dc与历史动作来源SHA一致，未加载模型/仿真或读新真实状态。交接100%，实现/部署/真实正式0，下一执行者X。旧dirty checkout、所有数据权重分数失败署名保持，关键文档精确commit读回SHA本地manifest备份，无删除待删=[]。下方046无新实验许可历史被用户本次新047批准覆盖，不重开已完成046。
