# 018视觉候选结果与标注质量核查（2026-10-24）

## 决策摘要

当前7B候选不能整批直接作为训练监督。解析修复有效，但通过schema的输出仍出现明确视觉错判与错误区域绑定。018软件验收不撤回，不以改宽validator或再修release枚举掩盖标注问题。暂不启动新教师推理或训练。

本次核查读取既有结果和既有RGB，没有新模型调用、仿真恢复或重抽帧。原始manifest与错误全部保留。

## 本轮实际结果

manifest identity：`fde202e1a3922a25c6173fd3764e9cd9f10872bb7470be9d0e63b8febc76c676`；代码`119cd50bde04a53f41ddac47871d0f688276b146`；教师`Qwen/Qwen2.5-VL-7B-Instruct@cc594898137f460bfe9f0759e9844b3ce807cfb5`。

| 结果 | 条数 | 占3200条计划查询 |
|---|---:|---:|
| schema通过 | 1072 | 33.50% |
| 实际调用失败 | 822 | 25.69% |
| 前序失败后未调用 | 1306 | 40.81% |

实际generation_attempted=true共1894次；其中56.60%通过schema。不是任务成功率、标注准确率或训练数据验收率。通过记录分组846 train / 226 dev；原来源160/40未变。字段失败645条与release枚举相关，占822次失败的78.47%，但仅修枚举不能证明其余字段正确。

17/20任务至少有一条通过（85%任务覆盖）；开顶部抽屉并放碗、butter入篮、milk入篮均为0。完整按计划分母统计如下：

| 任务 | 通过 | 占该任务160条 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| open the middle drawer of the cabinet | 150 | 93.75% | 8 | 2 |
| open the top drawer and put the bowl inside | 0 | 0.00% | 60 | 100 |
| push the plate to the front of the stove | 123 | 76.88% | 22 | 15 |
| put the bowl on the plate | 60 | 37.50% | 36 | 64 |
| put the bowl on the stove | 156 | 97.50% | 3 | 1 |
| put the bowl on top of the cabinet | 53 | 33.12% | 39 | 68 |
| put the cream cheese in the bowl | 45 | 28.12% | 45 | 70 |
| put the wine bottle on the rack | 10 | 6.25% | 56 | 94 |
| put the wine bottle on top of the cabinet | 90 | 56.25% | 26 | 44 |
| turn on the stove | 134 | 83.75% | 16 | 10 |
| pick up the alphabet soup and place it in the basket | 24 | 15.00% | 50 | 86 |
| pick up the bbq sauce and place it in the basket | 24 | 15.00% | 52 | 84 |
| pick up the butter and place it in the basket | 0 | 0.00% | 60 | 100 |
| pick up the chocolate pudding and place it in the basket | 3 | 1.88% | 59 | 98 |
| pick up the cream cheese and place it in the basket | 36 | 22.50% | 48 | 76 |
| pick up the ketchup and place it in the basket | 39 | 24.38% | 45 | 76 |
| pick up the milk and place it in the basket | 0 | 0.00% | 60 | 100 |
| pick up the orange juice and place it in the basket | 37 | 23.12% | 47 | 76 |
| pick up the salad dressing and place it in the basket | 55 | 34.38% | 41 | 64 |
| pick up the tomato sauce and place it in the basket | 33 | 20.62% | 49 | 78 |

## 内容分布：异常信号，不是准确率

1072条合法预测中有788条运输目标。783/788（99.37%）被标为SAT，只有4条UNSAT、1条UNKNOWN；742/788（94.16%）标为HELD。46条合法运输起始帧中45条（97.83%）也标为SAT。208条同时写RELEASED与HELD，只有4条同时满足SAT、RELEASED、NOT_HELD。

这些是预测标签分布，不能仅凭分布断言每条真假；但若直接训练，会有明显标签塌缩风险。示例框[0.1,0.1,0.7,0.7]出现17次，不支持把全部问题简单归因为复制该示例框。

## 双视角抽查

按预先记录的各任务first/last eligible规则抽12条：9条schema合法、3条失败，覆盖9类任务。不是随机抽样，不估计总体视觉准确率，不把这12条核查伪装成全量标注验收。

- **碗放炉子，demo_0/w0/q1，帧0**：图中碗仍在桌上、夹爪空着；输出却为SAT、HELD。agentview框[0.45,0.8,0.55,0.9]落在机械臂/夹爪区域而非碗。
- **巧克力布丁入篮，demo_4/w2/q3，帧59**：目标仍在左侧被搬运，篮子在右侧；输出SAT、RELEASED、HELD，框却在桌面上方其他物体附近。
- 开抽屉与碗放炉子的一些后期图像中，SAT本身可能成立，但所附证据框错位；不能据此把整份标签视为正确。
- butter/milk的失败记录不只是release枚举问题，所附wrist框与目标主体也不对应。
- 开炉子末期有视觉上合理的样本，因此不把全部1072条判作错误；仍需可靠来源和字段级核查。

图像、选择规则和逐条笔记在本地结果报告中保留；未将原图替换、翻转或重画，未生成任何新的“已确认训练标签”。

## 已确认的下一步：仿真监督标注（2026-10-24）

建议利用现有仿真轨迹生成**离线监督标签**，保留VLM候选作辅助，而不是直接拿当前7B结果当真值。保留原RGB、窗口、20条文本规格、160/40分组及③选择器＋④可撤销历史的主线。

边界：状态/谓词/实例映射只能留在标注侧；不能进入模型输入、推理记忆、执行控制或评测策略。不可观察或证据不足的字段保持UNKNOWN/不监督，不把隐藏真值强塞给视觉模型。不能用oracle历史替代合法历史，也不能把GT框画到模型输入。

官方LIBERO生成脚本保存states、动作和RGB，且有On/In/Open/TurnOn等谓词实现，支持这一路线的可行性；但**未据此确认本批20个HDF的状态与RGB同索引对齐**。脚本中动作执行、RGB记录和state切片的顺序提示潜在对齐问题，后续实现必须核实真实对应关系。这是防止监督标签配错帧的必要核对，不扩为新一轮benchmark物理检查。

- [官方数据生成脚本](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/scripts/create_dataset.py)
- [官方谓词实现](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/libero/libero/envs/predicates/base_predicates.py)

也不能把该脚本最后一帧置1的dones/rewards直接当成每个子目标的完成标签。所需字段、XML/版本兼容性与对应关系仍须实际核实；不声称全部仿真标签已可得或无需任何渲染成本。

另一选择是维持视觉标注但换更强标注器；模型/API成本与启动权限必须另行确认，不能静默下载或追加调用。用户已明确选择“改用仿真监督标注”。正式实施范围见[019工单](../../collaboration/tasks/019_sim_supervised_annotations.md)，由X实现、Codex审查部署、用户启动。

下一步操作和执行者：X实现019及CPU/fake验证；Codex审查部署，用户启动实际标注生成。当前不新增教师推理或训练。
