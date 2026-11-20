# Task053 configfix1：全新CLI依赖激活顺序勘误与v3交接

## 2026-11-19：053 configfix1修复全新CLI激活顺序，用户改用v3

v2由用户启动后在run→validation.identity即报benchmark未导入，未到parent、模型/动作0、新run不存在；旧task053-launch-001及失败日志保留。原因是Codex先调用依赖身份函数、后在parent激活core，旧CPU fixture与文件诊断预激活遮住错误，不是用户conda/权重/数据问题。

PR28更新8fc4a041ebc58fa4d83b059899c99749c5593724（本地19658d1同树c87d0608）；生产仅run入口提前old.activate(cfg)一调用和注释，源/RGB/评分/继承/预算不动。新增全新独立解释器CLI回归，053受影响16/16通过，先前38项的索引/证据/续跑验收保留，不重复23旧049测试。实际服务器同conda+venv+v3 session、真实CLI/config/protect/activation/identity入口已通过，在parent前CPU哨兵截断；无旧数据重审、torch或native env导入、模型/物理/真实启动。

最终task053-index50-continuation-v3隔离147源依赖测试文档＋3配置SHA一致，源码包22d3ae34ba8db3084d566f52ba4cc33d7ce7cf2d9a693ee0f9c8a28808135b38。原450bank54a22533与partial summary05b388fd不变，原11轨迹保持；旧v1/v2与旧marker均不删。新task053-launch-configfix1和configfix1.console.log防重复/保留旧失败；新marker/run仍不存在，无预算消耗/退款重置。软件100%、真实新889=0；下一用户新一条v3先继承11/base439，再H1 450，仍原900，不重开旧v2/052或重建状态。

具体本地053_configfix1_启动修复命令已给，公开task053_configfix1_commands/勘误/evidence与同日stage为入口。Codex未代启停，X无返修；关键文档精确commit读回SHA归档、旧dirty checkout/数据权重失败署名保持，无merge/删除，待删=[]。本节勘误旧v2可直接启动结论，不覆盖未来决定。


## 验证边界

此次本地16受影响CPU/fake通过，新增测试使用独立Python进程、明确benchmark未导入，从实际main解析配置后运行，激活固定core/reporting/legacy依赖，抵达parent前截断。实际服务器在用户同conda、原仿真venv、v3 session中同样通过。它只证明此前失败的fresh startup接线，不声称已启动或验证真实模型评测；没有再次检查原11条大trace，沿用前轮实际文件证据。

原先38项（15新索引/证据/继承＋23旧049）不是本次重新全部执行；本次16项覆盖15受影响及新增冷启动回归。生产除了提前原activate调用没有其他逻辑变化。旧benchmark ModuleNotFoundError和全部历史文件/消耗保持，不伪改原失败。

PR28 https://github.com/No1dry/Learning-Not-to-Act/pull/28 ，固定8fc4a041ebc58fa4d83b059899c99749c5593724；规格docs/task053_startup_activation_fix.md，记录responses/053_codex_configfix1.md、evidence/053_startup_configfix1.json。公开命令docs/experiment_plans/2026-11-19_task053_configfix1_commands.md；用户本地完整053_configfix1_启动修复命令_2026-11-19.md为最新入口。

新真实续评仍用户启动。原11＋439＋450=900，450状态不重建、零新训练/MVP/seed；旧run未创建所以原ID沿用，不重置预算。源/权重/原二元合规不变。关键文档精确main commit SHA本地备份和两个stage目录副本/manifest核验；不合并PR、不删除任何内容，待删=[]。
