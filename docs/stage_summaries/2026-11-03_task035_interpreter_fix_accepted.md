# 2026-11-03｜035解释器路径修复验收与002交接

用户首轮001的180条来源全部在初始化时失败，合格10/normal均0；原始错误与原plan/数据全部保留。根因是CLI将venv Python软链resolve到base，导致NumPy/MuJoCo版本变化，不是版本锁错误、任务物理失败或模型SR。

X在PR10交付HEAD `eecd25f59c43757509b639ef0c8a995547499a16`，实现`e56e3e7031e96308c3e723734944b45166c2f0f7`。只把解释器字段改为expanduser＋基于配置目录的os.path.abspath，保留venv入口拼写；其余路径、模块/版本/资产锁、数据、策略、训练与评分不改。[R3验收](../../collaboration/reviews/035_round3.md)closed仅限此路径阻断，研究仍open。

X的Windows环境真实symlink两项无权限而skip，保留事实。Codex在Mac独立补齐真实软链，并运行受影响CLI文件：**8/8通过，100%，0skip，0.35秒**；fake仅在子进程边界，不运行NativeSession/仿真/模型。不重复全库或R1历史大组。

源归档SHA `01ec27eb4218f13050368219986b855870b49991c8346abaf536d98ce5e84672`、CLI SHA `5c892731ed5fa03005cedacaf288a37f192d2793b9e5e9275a80f81bc712c6ac`本地/服务器相同。已隔离部署`.../Learning-Not-to-Act/code/task035-eecd25f5`，保留旧代码与001失败；没有pip/环境修改、自动merge或重下载。真实配置纯JSON计划一次核对，worker解释器保留正确venv入口、180父来源和最大1080次10尝试不变，未创建仿真或加载模型。

九原始HDF/180清单/train136-dev44与原配置复用；用户按[002完整conda/python命令](../experiment_plans/2026-11-03_task035_generation_retry002_server_commands.md)启动新输出generated-002。此时002未开始、有效生成数据仍0、训练/新模型eval0，不预言修复后资格通过量。不增加MVP或真实预检，不等待无关评测报告小增量。

下一执行者：用户正式生成；Codex在用户交回报告后分析实际合格数据并给一组1000更新混训命令。原10/00基线24.44%/86.67%保持、同adapter正式90/90计划保持。X本修复无返修；评测实时SR/去重复读子项仍open。无清理、待删=[]；本总结提交GitHub并按来源commit/SHA备份本地。
