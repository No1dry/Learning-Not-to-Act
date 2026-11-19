# 051：049失败补救软件交付

用户已批准修复。原049来源405/450 ready=90%，45/450 failed=10%；新增360中315/360=87.5%通过。40个微波炉10..49因Codex漏扩R7内层索引限制失败，原23测试未覆盖该路径；另5项仅observation_matches_fresh失败：stove21、two_pots11/34/36/45，抽查腕图像少数RGB通道差2档、原规则1档。责任与旧失败证据保留，不记模型失败；原049模型eval未启动。

PR26固定498e2f61a5127ba2a902c4ceb1d4ef0397afa5df，树b0dfe3c94935e81a330a46b90bba8cb3a95e2277与本地18295a7同树，依赖PR25、不自动merge。7新增051文件，旧生产源逐字不动；另携带4已main050文档保证源树一致。私有完整helper导入图统一四个index guard到0..49，覆盖R7构造/回放/验证/读取；canonical模块/冻结依赖文件不修改，原bridge/compat模块直接alias，保持两个owned proxy与完整环境身份。所有物理、RGB/非RGB阈值保持；source包/扩展SHA如实记录，非冒称原执行完全无改。

严格绑定原sources SHA2b34a4f34bf9fae699098d34f39a277ee01ea3a2cd65dc987e8087198b6829e9。405原成功条目/origin/state/plan hash只读复用，不重建、不另跑完整405预资格；模型原loader在使用前仍核验全部源证据。失败轮进入新bank：40微波炉＋stove21/pots34共42次bounded build；pots11/36/45保留已过construction、只新replay；独立source replay总≤45次，均原2×150规则。各源只一轮，失败不自动重试/更换索引/放宽像素；旧计数不退款，旧失败不倒改。5个RGB可能仍不通过，必须如实保留，非保证450可用。

45不同CPU/fake最终全过（旧23＋新22），含曾遗漏的index49 R7真实函数内层构造/validation/replay/reader路径、canonical仍拒绝49、布局/XML/目标与阈值不松、RGB2仍拒绝、精确405复用/42+3分派/失败不重试，以及修复协调器完整假450/逐条SR。初44首轮过，补计数约束和完整假450后全45过；原JUnit保留。是Codex自查，不是独立审查/真实物理效果。

隔离task051-remain50-recovery-v1；136源依赖/文档测试、3实际配置脚本SHA一致，源包4207a1eb1a156bc37c997be242c37fea7cf2ebfef268763f8d5934f06149ce6a。实际配置/parent405/45与抽样旧basket0、two_pots10、microwave0的source_plan SHA完全一致；原conda/venv/session help和bash语法通过，torch未导入，无新native/model，未启停050/049，新bank/run不存在。软件100%、真实补救/模型评测0%。

下一用户按本地051_只补45项并接续评测完整命令，启动新脚本；450全准入才自动原版450→H1@3000 450→comparison，沿原049已批900预算，不是追加模型实验。仅换准入helper，原049 rollout/evidence/scorer/034二元报告和目标/模型保持，schema沿049但有明确修复溯源。任一源未过停在模型前；不原地重开旧script。X不重复实现/泛审；Codex待交回结果。全部旧数据权重分数失败署名、dirty研究checkout保留；文档精确commit/SHA及parent原件/源包/JUnit/私有配置收据本地归档，不merge/删除、待删=[]。
