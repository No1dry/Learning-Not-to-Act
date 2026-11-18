# 047：Codex直接实现并部署，下一用户正式3000

用户在批准官方pipeline与3000条后明确“你直接完成吧”，覆盖待X工单。Codex已直接实现CPU/fake、自查与文件部署，X不重复实现/泛审；全部真实评测仍用户亲启。

PR22固定bd871dea127a2049134be4fb0fa7f392061d28d5，依赖accepted PR21@a1179099；源树dbff1510与本地测试树一致，不自动merge。新047直接调用固定官方OFT e4287e94的eval_libero原主体及run_task/run_episode、观察/动作/原生done/全视频；初始化后H1加载一次原rank16 LoRA，base不注入。旧生产egrs源码逐字未改，不接Remain评分器、提示、FINISH、VLM或训练辅助模块。官方会捕获部分Episode error，新旁路将技术错误显式报告并停后续，不把它静默当有效500条模型结果。

047独立核对同底座组件、固定H1@3000字节与原训练10统计，训练identity/PT不改；实际推理各suite由官方选择spatial/object/goal_no_noops，官方cfg.lora_rank仍32，原LoRA已合并不重复加载。保留原像素、动作/夹爪和成功bool；新代码只负责任务/初态对应、日志与隔离路径、六cell串行。三套各全部10×50，两模型各1500、总3000；上限220/280/300、等待10/chunk8、seed7/env0、原指令/两图proprio/center_crop保持。全视频和轻量逐条JSON，实时总百分比/live SR，最终逐任务/三套/总体SR和差值；旧九任务不拼四套AVG。

42不同CPU/fake最终通过（首31；新增8通过，3个直接Observer测试未切独立cwd触发正确视频保护，修正测试装配后仅补3通过）。原红灯JUnit保留，未改生产断言。包括完整调用未修改且附MIT许可的官方runner的六组假500和toy CPU LoRA恢复/统计/RNG/异常/保护。属Codex软件自查，不是独立审查或真实模型/SR/物理证明。

隔离code/config均task047-official-cross-suite-v1，126源依赖模板与8实际配置/脚本SHA一致。只用本shell显式PYTHONPATH，不pip、不改全局editable或依赖，不影响旧作业环境。既有simulation venv已具Torch/TF/Transformers等，实际六配置、H1 adapter78a96aa7、三套统计和各10个BDDL/init文件路径静态核对；未反序列化真实初态/训练state或加载ML/物理，未来run不存在。新命令的只读progress入口已在实际conda/venv/session下返回not_started。

准备100%、真实正式0。下一用户按2026-11-18_task047_user_evaluation_commands或本地047_三任务集官方评测完整命令，一条nohup Python按base/H1两两串行六cell完成3000；不MVP/新prepare/index/基线额外重复或训练，动作块请求自然上限101000。异常保留停止、不自动重试/删输出或退款；不代启动实验。

代码源tar/测试原JUnit/实际配置/私有部署receipt与关键文档精确commit读回SHA本地归档manifest登记；所有旧数据权重分数失败署名、脏研究checkout保持，无自动merge或删除，待删=[]。软件交付closed、真实效果open；本条覆盖旧047待X/实现部署0，不覆盖未来决定。
