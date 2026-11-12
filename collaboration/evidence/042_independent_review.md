# Task042 独立定向代码审查

审查日期：2026-11-12。审到的状态：Task042 工作树 HEAD 为 `e4c0b4a82c6e2cbf0a89d6c2773cd18e46c6ebee`，含尚未提交的 `egrs/tcif042/`、配置、六个定向测试文件，以及 `egrs/task_control/oft.py` 的可选 `forward` seam。本报告审的是工作树实现，不将 HEAD 冒称为已包含实现的提交。未修改实现、提交或运行任何真实模型、训练、评测、仿真或服务器作业。

结论：在本次定向审查范围内，未发现可确认的缺陷、信息泄漏或需要阻塞交付的关键合同缺失。交付文档仍由主代理完善，不在此作为缺陷提出。

核对范围与判断：

- 先读了 `collaboration/tasks/042_task_control_information_firewall.md` 和 `collaboration/evidence/042_audited_sdpa_source_excerpt.md`。F0 保留审计的 padding-only 双向有效图；F1 的禁边方向是 T query 读取 C key。两臂相同显式 dense SDPA 路径，最终 primitive 每层接收完整 4D additive mask，`is_causal=False`，未依赖会被 last-row expand 抹掉的上游 mask。
- 布局来自原准备后的 ids/placeholder labels、`labels[:, 1:]` 产生的 56 个 shifted A，以及本次融合 embedding 和原 proprio projector 输出。首个 A 被划入 C；H_v/H_l 必须在 T；P 必须匹配本次真实插入。Padding 不作有效上下文证据。未发现 task ID、动作真值、未来帧或外部状态参与路由。
- 每次观察的 mask 是独立的新 tensor，作为 decoder/layer/checkpoint 输入传递；样本 hook 在 finally 中移除，没有最近样本全局 mask。不同长度 u/v 存活并反向重算的 tiny CPU 测试覆盖了各自 mask，以及原 reference 介入后的状态恢复。
- 原 SOG10 references 直接走原 prediction，禁用新增 LoRA/context/residual/count 分支，使用 2D 原 padding 输入，经 stateless native 分支恢复双向图；每更新的八个 reference 在任何学生图之前完成。沿用原模式、hook、RNG、cache、requires_grad 保护；未发现 F1 防火墙渗入 reference 目标。
- 初始化严格绑定完整 041 R0 final1000 的字节 SHA 和原 040 index，加载完整 LoRA、z、残差和 count 参数；祖代更新数为 2000，本阶段新增 1000，保存元数据如实记为 2000 + update。两臂新 optimizer/scheduler/sampler/RNG 和独立 reference/student 持久账本，失败前扣费，落后于已花账本的 checkpoint 拒绝恢复。
- 新 schema 与历史 reader 隔离；同 run resume 绑定 arm/source/index/config/attention contract 和观测 runtime，完整训练状态及参数保存/恢复；部署加载核对实际执行合同和 runtime。未改变原 Parameter 路径或替换 Parameter 对象。
- 两个真实训练 example JSON 完整匹配原 preset，类型检查保留 photometric_probability 的浮点 0.0。训练/dev/评测共享 042 prediction。评测沿用原固定 180、90/90、H520/chunk8/seed7、来源、全视频、raw、正式二元评分和单学生 worker 路径；无训练后自动 eval。

实际执行的定向 CPU/fake 检查：

1. `python -m pytest tests/test_tcif042_attention.py tests/test_tcif042_layout.py tests/test_tcif042_identity.py tests/test_tcif042_training.py tests/test_tcif042_entry.py tests/test_tcif042_evaluation.py -q --basetemp ../../.release-tools/t42/review01` — **90 passed in 15.73s**。
2. `python -m pytest tests/test_task_control_model.py tests/test_task_control_reference.py tests/test_retention041_reference.py -q --basetemp ../../.release-tools/t42/review02` — **32 passed in 3.82s**，检查共享 seam 和原 reference 受影响路径。

使用本机既有Python。这些证据仅支持 CPU 小模型/fake 合同与兼容性，未声称 GPU 数值、性能或真实成功率；无需为本次代码审查增加真实 GPU 验证。
