# Task052：稀疏RGB准入修订软件验收、部署与用户交接

日期：2026-11-19。研究主问题与动作评分不变。本轮软件交付closed；真实3项补救、450×两模型和效果open。

## 2026-11-19：052稀疏RGB修订已批准并部署，仅补3项后接续原900

051实际447/450 ready=99.33%、3失败：stove21构建、pots11/45独立回放均仅RGB一致性；原审计最多2档/腕图2、4、2像素，其余检查通过，不宣称已证明GPU/cache bug。用户拒绝减为447并明确批准版本化稀疏RGB：每相机通道差≤2且差异像素≤max(1,floor(HW/10000))（256²为6），原图/非RGB/状态/物理与评分不变。旧447完整走051路径，不重建；stove21原legacy配对producer只补一轮build，pots11/45原v6构造字节复用，只补3个source的2×150 replay，不改旧failed或退款/循环重试/换index。

PR27固定429e4d7483477dd48533db1c2f7ea66e6694c94e/树2407679e（本地c1aec1d同树），依赖PR26，不自动merge。新增8文件；私有新rule/数值guard/完整source reader与snapshot按3个ID路由，canonical仍1档、两个原native桥接/placement/hold/物理/动作评分不变。61不同CPU/fake最终过（16新＋45旧），初次环境变量/合成fixture字段错误保留，是Codex自查非独立真实审查；含旧v6构造→新版回放→归档和假450原实时SR。

隔离task052-sparse-rgb-recovery-v1的143源依赖测试文档＋3实际配置SHA匹配，源包705befe9；父报告86578053未变，篮子0/双壶10/微波炉49三个原447文件样本plan SHA不变，两个旧双壶构造仅读验证通过，未重复全447资格。未导入torch/创建场景/真实补救或模型，未来bank/run/marker不存在。软件/部署100%，真实补3与900均0；下一用户一条052启动器，仅全450就绪才原版450→H1@3000 450→comparison，沿049原900预算，无训练/MVP/额外seed或模型预算。X无需重复实现或泛审，Codex不代启停。

050 H0官方完整LIBERO-10已由用户完成并仅读核对：90.40%=452/500，对原版94.80%低4.40pp，H1为88.80%；普通官方500不混成Remain10。新052仅解决来源准入，不修改这些分数或权重。关键文档/源包/测试/私有receipt精确commit与本地SHA归档，旧dirty研究checkout、数据权重失败账本署名保持，无删除待删=[]。本节覆盖051真实未完成/052未批准的历史快照，不覆盖后续用户决定。


## 依据与边界

原始051报告SHA：8657805313b12d384d6252011b46fb3008eedda45706d3db60a712339deb1eef。原049、051所有失败原件和物理计数保留。3项仅RGB检查不通过；诊断不等于已证渲染根因，不把技术失败记成模型失败。

新3项实际audit/replay声明named-uint8-rgb-sparse-two-level-task052-v1及实际2档/面积上限，绑定方法源码SHA。旧447不被改写成新profile；统一外层来源协议明确两条接纳路径，两模型使用同一固定450。旧v6双壶construction可保留原1档监督并和新2档稀疏replay共存，原始数据不滤波。源归档后依然完整重验新旧证据，不绕过reset/非RGB/物理/谓词/释放或动作评分。

新source build≤1、source replay≤3，每个原2×150；旧内部候选/构造上限保持。真实作业仍只用户亲启，一轮失败即保留停止，不自动追加。全450就绪才继续原900，不追加新训练或重测已完成官方500。

原出处：PR27 https://github.com/No1dry/Learning-Not-to-Act/pull/27 。完整规格见docs/task052_sparse_rgb_recovery.md（PR固定源）；发布记录见collaboration/responses/052_codex_round1.md和evidence/052_sparse_rgb_revision.json。公开命令见docs/experiment_plans/2026-11-19_task052_sparse_rgb_recovery_commands.md；具体服务器路径留本地文档/聊天。

关键决定和证据按本次main精确commit读回核对SHA并本地归档；不自动合并PR、不删除任何交流/源代码/原始数据。待删=[]。
