# 方法研究当前状态

更新：2026-10-22。

## 当前决定

主路线已定：③独立实体/目标关系选择器＋④可撤销证据历史，冻结VLA，仅训练selector LoRA。通过稳定子目标语言驱动，不把bbox当空间动作约束。

## 任务

| 任务 | 状态 | 下一执行者 |
|---|---|---|
| [015设计审阅](tasks/015_remaining_goal_selector_design_review.md) | accepted/closed，仅设计审阅范围；[裁决](reviews/015_round1.md)；X原文见PR #1固定提交，PR未自动合并 | — |
| [016完整软件实现](tasks/016_egrs_full_implementation.md) | implementation delivered on this PR，等待集中审查；[回复](responses/016_round1.md) | Codex审查，X按意见修正 |

设计审阅100%；本轮软件准备100%、实现与定向CPU/fake交付100%（待Codex接受）；真实数据准备/标注/训练/新方法评测各0%。软件交付不表示方法有效、真实processor已验证或014批处理已联通。

## 授权边界

X现在可以实现完整方法、训练/推理入口、数据导入/弱标签支持、历史与facade、core契约和定向CPU/fake。不要继续停留在候选方案罗列，不先跑MVP。

未批准真实数据恢复、物理/教师标注、特征抽取、真实Qwen/VLA forward、训练或eval；这些仍由用户另行确认并启动。55—80人时不默认生效，20文件候选不冒充200条ready。无数据可完成软件，真实训练前必须另确认标签与资源。

## 后续

X在本库交016 PR与响应 → Codex集中建议式审查与部署/完整命令 → 用户启动确认的真实阶段。014在评测侧单列，不能在此复制评分；其尚未交付不阻塞方法本体与fake契约实现。

不自动merge、扩benchmark、加01/11模型评测或FINISH。原稿/失败/数据保留，不清理开放或未闭环事项。
