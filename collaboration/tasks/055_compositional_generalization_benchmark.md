# Task055：LIBERO-Remain未见物体组合测试集构建

日期：2026-11-23  
状态：用户已要求形成简洁构建方案并交X实现；本工单只授权软件与CPU/fake，真实状态构建和模型评测仍由用户亲启。

## 1. 目标与范围

为LIBERO-Remain增加一个小型**未见物体—目标组合**测试集，检验当前方法是否只记住九个训练任务，还是能够迁移到相同场景、相同技能下的新组合指令。

本轮固定只做**3个新任务**，不凑满9个，不加入牛奶、不换场景、不扩到LIBERO-90，不训练模型。已有三个已见篮子组合作为历史对照，不重复构建。

论文表述使用“held-out object combinations / compositional generalization”，不声称unseen-scene或任意unseen-task泛化。

## 2. 固定任务清单

三个任务均使用`LIVING_ROOM_SCENE2`现有篮子场景与物体资产。每个任务保留两个原生`in`目标，完整指令在该任务的普通与预完成条件下保持不变。预完成对象固定为表中第一项，避免按模型成败选择角色。

| task key | 新完整指令 | 两个官方语义目标 | 初态中已预完成 | 初态中剩余 |
|---|---|---|---|---|
| `composition_soup_butter` | `put both the alphabet soup and the butter in the basket` | `in alphabet_soup_1 basket_1_contain_region`；`in butter_1 basket_1_contain_region` | alphabet soup | butter |
| `composition_tomato_cheese` | `put both the tomato sauce and the cream cheese box in the basket` | `in tomato_sauce_1 basket_1_contain_region`；`in cream_cheese_1 basket_1_contain_region` | tomato sauce | cream cheese box |
| `composition_tomato_butter` | `put both the tomato sauce and the butter in the basket` | `in tomato_sauce_1 basket_1_contain_region`；`in butter_1 basket_1_contain_region` | tomato sauce | butter |

现有已见组合为汤罐＋番茄酱、奶酪＋黄油、汤罐＋奶酪。前两者可作SCENE2内对照；汤罐＋奶酪来自SCENE1，只能在论文中分层比较，不能把场景差异混入组合泛化差值。

## 3. 初态数量与人口

每个新任务固定：

- 50个普通初态：两个目标均未达成；
- 50个同源预完成初态：指定物体已在篮中且满足当前稳定、释放与物理准入，另一物体仍未入篮；
- 每任务合计100个任务—初态绑定，三任务共300个绑定。

普通初态优先复用并重新绑定现有SCENE2的50个canonical来源，不重复制造独立布局；预完成侧最多新构建`3×50=150`个状态。普通与预完成来源必须按同一source index配对，顺序和身份冻结，保存SHA-256与祖源。

不允许因Base/H0/H1或任何其他策略的成功、失败而删除、替换或重排来源。若真实构建有失败，保留错误和未完成状态，不静默换成更容易样本，也不冒称150个预完成状态已全部就绪。

## 4. 实现要求

1. 在独立055扩展中实现任务注册、普通来源绑定、预完成状态构建、验证、证据和清单；不得覆盖官方LIBERO任务、现有九任务、450来源bank、训练数据或旧结果。
2. 复用固定eval core的物理、观测、释放、终止和二元合规评分，不复制或暗改一套评分。部署策略仍只接收双RGB、proprio和该任务完整指令，不输入完成mask、隐藏物体ID、谓词、坐标或未来状态。
3. 普通初态的两个目标均为false；预完成初态只将指定目标改为true，剩余目标为false。第三物体不得被误计入目标，非目标物体和无关场景状态应保持。
4. 预完成物体必须已释放、稳定、无非法穿透，机器人处于合法执行起点；保存状态恢复、渲染观测对应和来源谱系证据。沿用当前正式协议的确认窗口，不另造阈值。
5. 每个新任务使用表中新指令和对应BDDL目标，不把旧任务指令改名冒充新组合，也不改变官方已有任务资产。
6. 输出真实ready/failed计数、逐来源结果、失败原因、配置与实现身份。已有输出拒绝覆盖，失败不得删除后自动退款重开。
7. 新任务不得进入任何训练ten/fresh/raw、语言sidecar、dev或checkpoint选择；本轮没有训练、教师动作数据生成或模型评测。

## 5. 定向CPU/fake验收

X只需新增和运行受影响的精简测试，至少覆盖：

- 三个task key、完整指令、物体名、region及两个目标精确对应；
- 普通/预完成事实、指定角色、第三物体隔离及同源index配对；
- 50条/任务的上限、确定性顺序、重复/缺失/越界拒绝和SHA绑定；
- 未释放、不稳定、穿透、剩余目标误完成、错误物体或观测不对应时拒绝；
- 新任务不在现有训练索引、提示sidecar和正式旧bank中，旧文件字节不变；
- 假构建只写新输出，真实模型与仿真未被调用。

测试不得把假状态冒称为真实物理准入，也不设置全库、多平台或真实MVP门槛。

## 6. 交付与执行边界

X直接实现并提交新PR及`collaboration/responses/055_round1.md`，包含变更、测试、配置示例和仍存限制；不先写泛审，不SSH，不启动真实状态构建、模型训练或模型评测。Codex负责建议式审查、隔离部署和完整命令，用户亲启真实构建。

本轮软件交接后的下一流程为：Codex验收→用户启动真实150个预完成状态构建→确认全部bank与证据→另行决定Base/H0/H1普通及预完成配对评测。普通能力校准与预完成结果必须分任务报告，不能只用三任务平均掩盖基础技能失败。

最终泛化结论必须等真实评测：普通新组合失败主要提示基础技能/语言问题；普通可做但预完成失败才支持续接缺口；H0/H1差异才用于分析训练期状态信息的独立迁移收益。当前不预设正结果，不承诺SR或ICML novelty。
