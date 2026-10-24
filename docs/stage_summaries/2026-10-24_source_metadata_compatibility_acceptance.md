# 2026-10-24：019入口失败与020兼容修复交接

## 本阶段结果

用户首次运行019后，200/200来源（100%）在读取缺失的 `bddl_file_content` 属性时失败；3200查询有效处理0%、监督覆盖0%，ready=false、usable=false。失败在元信息入口，尚未进行状态恢复/图像对应，UNKNOWN是占位，不能当成物理对应或模型能力的结果。原产物保留。

020实现已在软件范围验收并完成新目录部署，下一步可由用户直接启动修复后的标注，不新增MVP、元信息预读或GPU预检。训练和新方法评测仍0%。

## 决策与实现

来源未内嵌BDDL不必全量拒绝：若已有来源元信息唯一指定任务，就从固定LIBERO安装按suite/精确basename解析，并锁定实际文件。历史原件字节一致性明确未证实；有内嵌正文时继续严格比对。歧义、矛盾、错配和后续图像对应失败仍如实记gap，不猜默认控制器、相机或任务。诊断与仿真真值仅在离线侧车/监督，不进入模型输入或历史。

X固定交付 [PR #2提交](
https://github.com/No1dry/Learning-Not-to-Act/commit/dc4dfa97d131fcdf8c1cc116e18d529a9d4d0efb)；Codex独立148/148受影响CPU/fake通过（100%，4.55秒），16变更文件blob与提交相同。已有原图、1200窗口/3200查询和160/40来源划分不重建。

配置的20个精确BDDL文件均与[官方固定LIBERO版本](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01)内容SHA-256一致；以逐文件证据建立锁，而非仅相信目录名或上级Git仓库HEAD。新旧源码隔离，原环境不修改，部署字节identity为 `06c6ec1aa020254bd40f80b20bcec470634557bed4fcaa2ff823585faea18396`。

## 下一执行者及未证实事项

X本轮无需返修；Codex已部署并提供完整conda/python命令；**用户亲自启动label-sim并运行/监督**。真实HDF剩余字段、native/XML/asset兼容、state/RGB对应及可观察监督覆盖尚未验证，不能因为软件测试通过便写成训练集ready。没有新增教师调用或模型轨迹、训练、eval。

实际标注后根据可用状态监督子集决定导出，不要求所有字段完美；全UNKNOWN或只有身份/框不能当作可训练状态数据。旧失败、原始结果及开放事项不删除，不自动合并PR。详见[020裁决](../../collaboration/reviews/020_round1.md)。
