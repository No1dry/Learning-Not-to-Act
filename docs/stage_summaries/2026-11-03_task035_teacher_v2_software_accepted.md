# 2026-11-03｜035教师v2恢复软件验收、用户启动003

用户已批准复用002旧8条合格轨迹、仅重建73来源（53train/20dev），新增最多73普通重放＋438次10尝试。X交付PR10 HEAD `44b6ca02e35cb318e58233d80a65c3c65c675ad0`，实现`20647cce386dfe2a3f768a029f909fa32350aa60`；[R5](../../collaboration/reviews/035_round5.md)accepted/closed限v2软件与文件部署，X无返修，研究仍open。

Codex独立运行六个受影响CPU/fake文件：**68/68通过（100%），0skip，3.21秒**，包括X因Windows软链权限skip的两项真实symlink。覆盖v1/v2诊断分流、确认违规/释放/A保护、失败前缀保存与排除、180原分组→固定73、旧8字节复用、fake导出与预算/进度。合成数据不冒充真实003结果；不跑全库或真实仿真/模型。

仅教师table_drop未知变为诊断，原None不改；确认违规和其他关键未知、完成释放等规则继续阻断。正式benchmark评分/阈值/原90状态、模型输入白名单和训练配方未改。旧8的HDF/资格/lineage字节保持并标记v1复用，不算新物理尝试；新73实际判v2，不直接把旧rejected改成功；新失败HDF只存真实T+1/T对齐前缀且不进训练。版本/复用语义写入export身份。

代码已隔离部署`.../Learning-Not-to-Act/code/task035-v2-44b6ca02`，配置`.../configs/trajectory035-v2-44b6ca02/recovery.json`。归档SHA `0a00690c8a2b0637eec6b605e7147cc88e994a2bf4ec28b3cbcf980003271015`、配置SHA `27946331dd4130511ad8f3e838aeaee5af184d1bcc5f229f474858b8ce919d65`、批准refs SHA `e13bc97c610ac93404d6c49b89d9d4233dcb280922811e1cdd8f918258bddc80`本地/服务器一致。

实际配置只做一次JSON/文件字节核对（不解析HDF轨迹、不构造native）：180原父组、73/53:20、旧8/2父源及73/438上限保持，原venv调用拼写保持。纯文件plan identity `1234a4c02be8344ef189c3a7f772f13ab35d9689bc30f0f914e7bcba6edb0f40`，plan文件SHA `68d559ebd8b15ebd7fed0af1dfa92a29536ed5d56557737047fce99b047c34ad`；simulation_created/model_loaded均false，003未创建、001/002原报告保留。无pip/环境修改、热改旧目录、自动merge或新增物理预检。

**下一执行者用户：按[完整普通conda/python命令](../experiment_plans/2026-11-03_task035_teacher_v2_generation003_server_commands.md)直接启动003。** 不重下数据、不重跑全部180，不用再跑plan或等X。实际合格量未知，当前仍只有旧2normal/6个10、dev空；生成/训练/新模型eval未因软件通过而完成。报告四池非空后Codex给混训命令，仍用户启动。

原10/00基线24.44%/86.67%、正式90/90与原一组1000更新7:3预算保持。评测实时SR/读取效率小增量仍非阻断open。精确refs JSON虽放在collaboration/tasks，已是运行时批准输入，不是可清理交流文件，须保留。无清理，待删=[]；本总结提交GitHub并按来源commit和SHA备份本地。
