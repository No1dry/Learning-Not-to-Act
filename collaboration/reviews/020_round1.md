# 020首轮审查：软件范围验收

结论：**accepted/closed（软件范围）**，2026-10-24。固定PR #2交付 `dc4dfa97d131fcdf8c1cc116e18d529a9d4d0efb`，未自动合并。

## 审查结果

- 缺少内嵌BDDL正文时，使用来源中明确且一致的标识解析固定suite/精确basename；保留可选字段缺失，拒绝冲突、错误路径与不一致正文。未将缺失字段默认为任意任务。
- 安装文件模式记录 `metadata_resolved_installed_bddl`，诚实标记历史原件字节一致性未证实，不伪造source正文或hash。仍锁定实际安装文件、已有native模块及原图/任务对应。
- partial inspection在SourceEpisode构造失败时可保存，worker保留精确失败阶段；诊断侧车不进入student样本、history或prompt。
- Codex独立运行受影响三文件CPU/fake回归：**148/148通过（100%，4.55秒）**，无跳过。X的Windows四项symlink跳过为平台限制，未将其报告冒称全通过；本次独立运行覆盖了这些已有用例，不增加额外平台前置。
- 16个变更文件Git blob与固定PR提交吻合；部署到新目录，复用旧环境、已有3200查询与原160/40划分。源码字节identity为 `06c6ec1aa020254bd40f80b20bcec470634557bed4fcaa2ff823585faea18396`，本地/服务器一致（45文件）。配置静态校验与三个传输文件SHA校验通过。
- 安装的20个精确BDDL文件与官方LIBERO固定 `8f1084e3132a39270c3a13ebe37270a43ece2a01` 的GitHub内容逐一SHA-256相同，补入配置锁。没有依赖目录名或祖先Git HEAD宣称版本，未修改实际LIBERO或依赖环境。

## 范围与下一步

没有发现需要X再次返修的明确错误。交付回复中的早期本地提交仅是历史说明，以本裁决固定remote SHA为准；建议后续回复直接给最终remote SHA，不据此退回实现。

**真实兼容/标注覆盖仍待用户启动验证**。CPU/fake通过及部署准备100%不等于实际HDF、XML、对齐或标注已通过。019旧manifest `2cd2df5f78b7148b1f490f31c56ce5b55df6bad15c6131dc88172b756bc7b82d` 的200来源失败、3200查询processed/supervised均0%保持不变，不解释成模型失败。

Codex未打开原始HDF、恢复状态、渲染、调用模型或启动真实标注；不新增元信息预读/GPU预检。用户下一步在新配置/输出目录启动label-sim；结束后Codex审查coverage，再准备独立导出与后续训练命令。原RGB/窗口/文本规格/分组不重建，旧源码和失败不覆盖。
