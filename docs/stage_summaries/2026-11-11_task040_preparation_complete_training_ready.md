# 040真实准备完成，单C1训练就绪

2026-11-11，Codex。[R2](../../collaboration/reviews/040_round2.md)接受用户启动的040 production-001现成产物范围；未运行新标签/索引/验证器/仿真/模型，仅文件读取复制与SHA核对。

准备100%、training_ready=true、source_errors=0；原进程已结束，无preparation_error，未采集独立shell退出码。耗时6100.924秒约1小时41分41秒。轨迹生成100%时仍有导出/索引收尾，不能用generation_progress替代最终ready。

- 60候选中46train代表生成，14dev封存；实际46普通/69次10，未超60/360。新增65合格train10/65新有效pair、pair gap0。10尝试资格率94.20%不是模型SR，所有失败保留。
- 开炉新增32、train36→68、父组12→23；白杯新增9、train3→12、父组1→4；双壶新增24、train24→48、父组8→16。旧其他六任务保持，不保证覆盖或SR充分。
- 新总ten370（289train/81dev）、pair370全有效、143960行；fresh105（78/27）/raw180（136/44）及旧dev选择保持，新normal不进fresh。
- task-control identity `8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe`，report `c87e6eba02fa987024cf57985f1fad4fff180b0132bc615042674ce9138c47c0`；六现成小文件服务器/本地SHA一致，[证据](../../collaboration/evidence/040_preparation_complete.json)。全部大HDF、原资料/失败/权重保留服务器，不伪称全量下载。

下一用户直接按[命令第2节](../experiment_plans/2026-11-10_task040_user_generation_training_commands.md)在原OFT环境启动C1 1000，从原SOG10新初始化、固定末1000/reference9024/student24560，之后新模型10/00各90；没有额外Codex预检/MVP/凑N或基线，当前不重跑generate/index。获取本快照时训练/eval0，Codex只归档/命令，不代启停；X无返修、PR15@428c1358不自动merge。

R2/证据/当前状态与本总结精确commit读回SHA本地备份，更新manifest；旧039 58.89%/85.56%及所有数据权重失败/署名保持。不续训、加S/C0/seed、改评分或清理，待删=[]。数据准备closed、训练/真实SR open。
