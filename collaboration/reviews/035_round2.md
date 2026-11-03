# 035 R2｜用户首轮真实作业初始化失败：解释器路径阻断

2026-11-03，Codex。对PR10@`564c91c920a521c6c5ea909d69350e70d14a5e7e`真实交回结果的裁决：**changes_requested，仅限native解释器路径的symlink处理**。R1其余生成/混训/计分软件验收和全部文件传输证据保持；实际有效训练数据为0，不能进入混训。

`generated-001/generation_report.json`：来源处理180/180=100%，source_errors180/180=100%，全部为`annotation library version lock mismatch`；合格10=0、normal=0，model_loaded=false。`export/report.json`保留180条初始化失败分母、两个域0窗口/0有效动作，不把这类技术失败计作模型任务失败。

原配置解释器`.../.runtime/oft_worker/bin/python`被`cli._resolve/build_plan`的`Path.resolve()`解引用为`/root/anaconda3/envs/peft-openvla/bin/python3.10`，实际source-000请求证实。包元数据只读检查表明前者完全匹配原锁，后者numpy1.26.0/mujoco3.4.0，不是锁本身写错。此前仅JSON计划字段/来源预算通过，并未比较解释器调用拼写，这处是Codex R1审查遗漏。不能以放宽锁、升级/降级包或重下数据处理。

[最小修复工单](../tasks/035_round2_preserve_native_python.md)只要求保留venv解释器拼写，以及symlink布局的CPU/fake plan→subprocess回归；相对路径仍基于配置目录绝对化。其余生成策略、划分、物理门槛/评分与训练不变。日志末尾打印实际合格数量仅建议，不因偏好扩大阻断。

原始报告SHA：generation_report `a25abb2f6147efbb58e11198d07d741eb4b486729dd537bde3e09566a77c217f`；generation_progress `be8f39ed4c7b1969e60f5f19283e9381562ac0e0ae57b7b87b9fc57022ada182`；export/report `ad4ced9698aff34e7f60749e82c66adcd6f0fe087b262a3766dd0acc0c6863df`。已取证为既有文件读取和包元数据读取，没有新仿真、回放、训练或模型运行。

下一执行者X修复并交CPU/fake；Codex验收/隔离部署后给`generated-002`命令，用户启动。当前不给会因空池失败的训练命令，不新增MVP或真实预检。保留全部原失败与数据，研究open，无自动merge、无清理，待删=[]。
