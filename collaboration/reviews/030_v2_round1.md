# 030 v2 R1｜保留训练/评测主体，只修真实字段并补进度证据生产

日期：2026-11-03。Codex。PR9固定HEAD `9a62732b8931b531cb837db74c654fd475f0ce71`，实现 `46dac7c7f7af23c6052b5890ce3b2d32c1886274`。裁决：**changes_requested，限定下列两处；不返工已交训练/adapter/评测主体。** 这不是训练或数据已ready的验收。

## 已确认的交付

已审动作字段/时间索引、整轨split与chunk尾mask、正常完整SOG10与原head/proprio加载、语言q/k/v/o-only LoRA、冻结head保留梯度、同RAW dev选择、adapter/RNG恢复与固定A90/C36接入。034单一二元API复用，未发现本轮必须返工这些主体的证据。实际24GB显存、正式数据动作映射、训练提升均未验证，不将fake通过当作真实能力。

Codex独立定向CPU/fake：原命令48 passed、1 failed（7.43秒），唯一失败为测试硬编码同级`LIBERO-Remain-task034`路径且mock掉依赖激活，审查布局下报告包未导入；显式提供已交034包PYTHONPATH后，仅重跑该用例1 passed（0.15秒）。49个不同用例均获通过证据，首轮失败XML保留；不冒称原命令49/49或要求X为测试目录偏好返修。034独立12 passed（0.79秒），0skip。

## 必须修正

### P1：真实LIBERO proprio被过宽的state子串禁令拒绝

`egrs/augmentation/data.py:68-74`把任何含`state`的字段拒绝，`validate_mapping:100-101`也用于proprio。Codex在服务器上仅只读一个原始HDF的字段/shape/attrs，未读取图像/动作内容、未导出或创建仿真：

- `obs/ee_pos`：170×3；`obs/ee_ori`：170×3；
- `obs/ee_states`：170×6；`obs/gripper_states`：170×2；
- 两相机170×128×128×3；原文件为现有Goal复合任务普通demo0。

生产8维proprio需要合法夹爪读数；即使用3+3拆开eef，仍需要`obs/gripper_states`。当前纯函数复现：ee_pos/ee_ori接受，ee_states/gripper_states均抛`forbidden HDF input outside whitelist`。不是“模板没填好”，而是正确映射也无法通过。

修复使用按输入角色限定的真实传感字段白名单或等价精确规则，允许上述合法eef/夹爪字段，**不能简单删除state禁令而开放全仿真states/物体真值**。3+3+2与6+2均保留显式顺序和8维约束；不为绕禁令复制/改名整个HDF。加真实命名的合成HDF回归即可，不要求重跑全库/真实导出。

### 关键功能缺口：尚没有可实际生产进度增强数据的入口

已交`resolve_local_evidence`只是外部插件接口；交付文档明确没有实现生产恢复/标注器，配置为占位。现有200来源全是`domain=base`，当前`_evidence_rows`对base一律不生成PROGRESS/ATOMIC。服务器指定raw目录当前只有旧20个Goal/Object文件；本次没有证明新九任务或可信技能证据已经存在。

因此不能把旧2429条selector query或任意JSON里的`reviewer/exclusive_goal_actions=true`填进去，冒称能开本轮增强训练。需交一个**实际可调用的进度证据生产路径**：优先复用已验收的状态恢复/图像对应/native谓词组件，只做普通demo局部锚点，不重建全轨视觉标注引擎。若已有交付组件本来就能直接完成，给出准确绑定入口/配置即可，不强制新写一套。

本轮提速裁决：可先自动提供可靠PROGRESS锚点，ATOMIC证据不足保持空并按既定规则回退RAW，报告实际比例；不把补齐九任务所有原子段或人工逐条审片设为开训门槛。当前目标false→true不能替代原子段动作归属证明。具体边界与所需CPU/fake见[集中修复任务](../tasks/030_v2_round2_production_data_path.md)。

## 非阻断建议

1. RAW dev当前逐帧全扫且每250更新执行；部署前报告其实际窗口数和预计forward数，避免把1000 optimizer更新误解为很短训练。不为本项先开GPU测速或自行改变dev集合。
2. 生产字段/动作符号、normalization、相机方向与t对应由Codex在正式文件准备时绑定；代码静态通过不能替代这些数据事实。新增最多180演示、两次1000更新、126新eval仍是候选预算，用户未确认，不代启。

下一步：X只完成两处并交PR9增量与必要CPU/fake；Codex集中复核/部署并给完整命令，用户启动真实阶段。其他已交主体保留，不扩benchmark、重跑基线、FINISH/selector、自动merge或清理。
