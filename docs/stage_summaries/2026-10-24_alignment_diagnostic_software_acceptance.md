# 2026-10-24：023两来源对齐诊断软件验收与部署

023首轮两处生产消费层误拒绝已修正：不把目录名当Git版本身份；不将计划基础记录与读取后扩展descriptor强制全字典相等。原版本、封存输入、来源/PNG/registry/split绑定及固定预算保持。[首轮问题](../../collaboration/reviews/023_round1.md)与失败测试证据保留，不倒改历史。

固定交付 `fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391` 按软件范围验收；Codex独立89/89受影响CPU/fake通过（100%，12.10秒、无skip），8变更blob一致。新代码/会话隔离部署100%，源码identity `9f530d42cb38b6bbea0e0ef319c27f8424418fd4c44b6c0965ade177a2461d18` 与服务器一致，两传输hash通过，未自动合并PR。

用真实封存022结果执行纯消费解析，2来源/6 probe/12个既有PNG绑定均通过，未创建诊断输出或启动worker。原始HDF、仿真、恢复/渲染、模型与标签生成均未运行；旧manifest/code identity与当前诊断identity独立记录。

准备100%，真实两来源诊断、训练与方法评测仍未启动。用户下一步亲自执行独立diagnose-alignment，读取的仍是原200来源作业中的两个固定train案例，不重建数据或全量跑200来源。固定18候选恢复/6旧动作/36比较/72直接render上限，内部初始化/restore渲染另计并受原预算/timeout约束。

产物是PNG对照、RGB分量、time/qpos/qvel/act与native原子审计，不是训练标签或对齐放行结论。完成后Codex看图及误差再作研究决策；不预先抬高阈值、指定next_state、改dev划分或自动补标/训练。旧165条/5.16%监督、dev0、全部数据与失败记录保留，不清理。

[第二轮裁决](../../collaboration/reviews/023_round2.md)。执行者仍为：X软件交付；Codex审查部署及结果；用户启动/运行/监督真实作业。
