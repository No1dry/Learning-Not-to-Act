# Task056：三个未见组合的Base/H0/H1同源评测

日期：2026-11-23  
状态：用户已同意下一步。只授权X实现与定向CPU/fake；真实模型评测仍由用户亲启，不自动merge。

## 1. 目标与固定预算

基于Task055已经完成的150个预完成来源，新增最小评测适配，对三个新物体组合分别运行Base、H0@3000、H1@3000：

- Base：原版SOG10，无研究adapter；
- H0：`runs/task045-h0-train-001/update-003000`，adapter SHA `e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20`；
- H1：`runs/task045-h1-train-001/update-003000`，adapter SHA `78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d`；
- 每模型150条，总计**450条模型episode**，顺序Base→H0→H1，共享同一source bank、顺序、指令和policy seed7。

状态新建0、训练0、普通状态/普通模型episode 0、额外seed/prompt/模型0。不得重跑旧九任务450或改变其分数。

## 2. 已验证输入

固定bank：`composition055/production-001`。`sources.json` SHA-256为`4a60ea3c25c379204353b0c5dfc167b16718f535426b918618f5a5221282ee0b`，preparation identity为`dd36fda6e6bf355db0682652e1b82329d01df8cbb77d43b1ebaa20d1daecc348`。真实构建已150/150 ready、三任务各50、失败0、pending0，自动全bank inspect完成；没有普通状态库。

每个`source.json`已经包含：

- `episode`中的task key/name、完整instruction、`initial_state_index`、source/episode ID、goal specs、horizon520和`[true,false]`预完成事实；
- 派生`task.bddl`及SHA；
- 冻结`state.npy`及SHA，只用于用户启动评测时的初始状态恢复，不重新构建；
- `initial_observation`引用、model XML SHA、环境身份、祖源和完整证据/控制账本；
- 三个固定task key：`composition_soup_butter`、`composition_tomato_cheese`、`composition_tomato_butter`。

依赖accepted PR30 head `6d9d0111881727f8765fce0c6affc881db949985`及PR29的054评测能力；不自动合并任何PR。保留最新main文档，但不能把文档main误当完整可运行代码。

## 3. 实现要求

1. 在独立056扩展中实现配置、bank读取、计划、模型分派、执行、原报告映射和三模型比较；不得修改Task055构建产物、旧九任务、训练数据、旧结果或冻结core。
2. 模型/物理工作前，离线核验完整150人口、来源顺序、manifest/artifact SHA、preparation identity和实现身份。复用055 `inspect`证据语义，不把缺文件、损坏或不完整bank当作可评测，也不为评测重新运行150条构建审计。
3. 不要求source manifest直接冒充旧scoped-source格式。写显式适配层，把现有episode/environment/goal/state/initial_observation证据映射到原rollout/plan；不得伪造source acceptance、环境fingerprint、任务ID或旧episode身份。
4. 每条模型rollout使用对应派生`task.bddl`和冻结`state.npy`，输入双RGB、proprio和该条完整新指令；H0/H1部署均无状态文字、mask、谓词、隐藏ID、坐标或未来状态。Base不得误加载研究adapter，H0/H1不得互换。
5. 直接复用固定core/034二元合规评分、原H520、chunk8、seed7、目标与释放确认端点、成果保持、错抓错放、完整视频和原始证据。不得另造评分、只看剩余单物体成功率或自主FINISH。
6. 每个episode执行前绑定计划中的模型身份；执行后使用原验证与报告映射。技术错误、缺文件、损坏或不完整记录保持unresolved/停止，不能伪装成模型失败或完整450。
7. 输出必须为新目录，保留全部成功和失败及视频/raw；已有输出拒绝覆盖，失败停止，不自动重试、退款、换目录或启动后续模型。首版不要求resume。
8. 控制台按来源显示completed和总体SR；最终分别输出三模型总数、三任务各自50条结果、逐episode证据、summary/report及Base→H0、H0→H1、Base→H1新增/丢失/共同成功。另保留原生完整目标达成和重叠诊断，不能把诊断相加当互斥原因。
9. 只读比较不得将新450与旧90或旧450人口混为同一分母，不虚构普通00，不声称unseen-scene或任意任务泛化。

## 4. 定向CPU/fake验收

新增并运行受影响的精简测试，至少覆盖：

- 固定150人口、三任务各50、真实manifest字段映射、BDDL/state/指令/目标/环境身份绑定；
- 不完整bank、篡改、错位、重复、普通状态混入或错误角色在模型前拒绝；
- Base无adapter、H0/H1精确3000步和SHA分离、无提示输入及冷启动激活顺序；
- 原rollout/score调用保持，fake三模型各150只计新450，普通状态/训练/新建源为0；
- 输出保护、失败停止、技术错误不记模型失败、实时计数、三任务和三模型配对统计；
- 旧bank/旧结果字节不变，fake不能冒充真实模型或物理通过。

不设置全库、多平台、真实MVP或模型预跑门槛。

## 5. 交付与执行边界

X直接实现并提交新PR及`collaboration/responses/056_round1.md`，包含变更、测试、配置示例和限制；不先泛审，不SSH，不启动真实模型、仿真、训练或状态重建。Codex负责建议式审查、独立测试、隔离部署和完整启动命令，用户亲启真实450。

下一流程：X软件交付→Codex验收部署→用户启动Base/H0/H1共450→Codex读取结果并做组合泛化分析。普通状态或剩余物体操作诊断只在结果难解释时另行讨论，不是本轮门槛。当前不预设正结果，不承诺SR、泛化或ICML novelty。
