# 035 R3｜R2路径修复验收并隔离部署

2026-11-03，Codex。PR10固定HEAD `eecd25f59c43757509b639ef0c8a995547499a16`，实现`e56e3e7031e96308c3e723734944b45166c2f0f7`。**accepted/closed，限R2解释器路径阻断修复及约定软件部署**；X本修复无返修，R1其余验收保持。真实生成、训练与研究效果没有因软件通过而闭环。

生产差异只在`egrs/trajectory_augmentation/cli.py`：5行增加/2行删除，解释器字段用expanduser与os.path.abspath保留调用拼写，其他路径保持原resolve；未改版本/资产/模块SHA/物理判据/评分、种子与split、3×2尝试或训练。生成器写request后直接使用该解释器argv[0]，后续没有再次resolve。

X如实交付Windows6 passed/2 skipped，不能当真实软链全过。Codex在Mac独立运行受影响CLI文件，**8/8通过（100%）、0skip、0.35秒**，包括真实文件symlink的绝对/相对两项，以及plan→request→fake subprocess的调用拼写断言。只做本轮精简CPU/fake，不跑全库、原生成/训练/评测大组，也不调用真实NativeSession或模型。

源归档SHA256 `01ec27eb4218f13050368219986b855870b49991c8346abaf536d98ce5e84672`本地/服务器相同；修复CLI SHA `5c892731ed5fa03005cedacaf288a37f192d2793b9e5e9275a80f81bc712c6ac`一致。已部署独立目录`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-eecd25f5`，没有热改原目录、安装/升级包或自动merge PR。

服务器对既有真实配置做一次**纯JSON build_plan**，解释器保留`.../.runtime/oft_worker/bin/python`，180来源/最大1080次10尝试不变；simulation_created=false/model_loaded=false。该核对直接防止R2故障复发，不创建仿真、不加载模型，也不是新的物理预检。未重复验证已适用的原依赖/状态/基线。

复用现有九个HDF、180清单、原配置`configs/trajectory035-564c91c9/generate.json`和版本锁；`generated-001`全部180初始化错误仍保留、合格normal/10均0。新输出`generated-002`未创建。**下一执行者为用户，直接按[002完整命令](../../docs/experiment_plans/2026-11-03_task035_generation_retry002_server_commands.md)启动正式生成**，不等待X、不增加MVP/真实预检。生成合格量未知，不许用软件通过宣称可以空池训练。

独立评测实时SR/读取效率小增量仍non-blocking/open，不纳入本阻断修复，不能卡生成或混训。研究open，无自动merge/清理，待删=[]。
