# 018教师输出修复与部署阶段总结（2026-10-24）

旧视觉候选运行曾在一个快照处理到33.03%：397次调用全部未过原JSON解析，660条后续查询跳过。去除包装后仍有实体ID、完整目标集合、release类型和绑定证据等错误。旧快照不是VLA成功率，旧失败不改写。

X交付了`119cd50bde04a53f41ddac47871d0f688276b146`：包装解析协议`egrs.teacher-wire.v2`和教师专用提示`egrs.offline-teacher-guidance.v2`，以及只读已有输出的CPU诊断。未放宽既有语义契约，未改学生提示、VLA、指标或训练。原raw、错误、跳过和历史保留；严格合法不等于视觉正确或有用监督。

Codex独立55/55受影响CPU/fake测试通过（100%，1.61秒），20个变更文件Git blob一致；软件验收和新目录部署100%。固定快照archive SHA256：`e997848ecf5d0c321e3df2796de83f2dffc8976f8a907dcdb9789ad847794b00`。新parser/prompt静态入口已确认；未改环境依赖，也未触碰旧运行树。PR #2未自动merge，X当前无返修项。

原200来源、1200窗口、3200查询及160/40分组继续复用；文本规格20条/21目标不重做。当前旧PID已不在运行，未由Codex停止。Codex本轮真实数据处理/forward/训练/eval新增0；新一轮尚未启动。真实tokenizer适配、候选合法率与视觉质量不是本软件验收已经证明的结果。

下一轮由用户亲自启动，最多3200查询，使用新输出目录并与旧调用预算分开记录；不插入GPU最小验证或重复抽帧门槛。可选CPU诊断不是开跑前置条件，不自动串行训练。详见[验收裁决](../../collaboration/reviews/018_round1.md)及[018交付原文](https://github.com/No1dry/Learning-Not-to-Act/blob/119cd50bde04a53f41ddac47871d0f688276b146/collaboration/responses/018_round1.md)。

下一步操作和执行者：用户启动并监督新版视觉候选；Codex审查交回结果，X当前无需返修。
