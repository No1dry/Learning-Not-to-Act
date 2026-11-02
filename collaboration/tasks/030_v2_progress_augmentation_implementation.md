# 030 v2｜直接实现进度增强OFT微调，不再增加纯方案审阅轮

2026-11-02。状态：open / implementation requested。执行者：X；Codex审查部署，用户启动真实阶段。

权威规格：[九任务方案v2](../../docs/experiment_plans/2026-11-02_progress_aware_data_augmentation_v2.md)。旧030 v1保留，但旧六任务/80条/112评测预算已被替代。当前main没有030_round1交付；本工单直接进入代码，不再要求先写可行性回复。不得复活旧selector作为前提。

## 一次实现的范围

1. 方法库独立分支/PR，建议模块`egrs/augmentation/`（等价组织可接受），不复制benchmark评分/源构造实现。复用固定官方OFT；用依赖路径/明确base ref接入已验收工具，不能假定未合并PR代码已在main，不自动merge旧PR。
2. 数据manifest绑定既有20任务200来源/160:40，候选新增九个LIBERO-10复合任务每项前20普通演示（最多180）。先来源分组再视图，已知重复同组；真实文件/精确instruction/目标定义绑定九任务清单，不猜文件、动作字段或t/t+1。代码支持参数化少于上限的实际数量，不填造数据可用性。
3. 一个用户数据导出入口：原HDF索引＋RAW/PROGRESS/ATOMIC索引、有效action mask、字段/归一化映射、来源和覆盖报告。只恢复阶段锚点/技能边界必要局部证据，不全量重建旧视觉标注。优先复用可信证据；不可信增强片段回退RAW，不能把整AB重标B、不能把错误模型动作当专家。
4. 两个真实训练配置：RAW-control和Progress-Aug（50/25/25＋轻微photometric），来源/split/底座/更新预算/dev规则相同。冻结base/vision/action head/proprio，仅语言q/k/v/o LoRA；原完整SOG10/sidecar必须加载，禁止随机头或重复发布adapter。masked chunk8 L1梯度通过冻结head到LoRA；保存本轮adapter/optimizer/scheduler/RNG、dev选择依据和参数清单。
5. 4090必要训练支持：bf16/microbatch1/accum16/checkpointing、1000 update配置；不能写不存在的flag，不先跑GPU probe，不以测试SR挑checkpoint，不擅自减少视角/proprio/chunk。显存未知如实报，真正OOM后再由用户决定fallback。
6. 普通OFT adapter评测接入：A原90、C固定36（九任务indices0/3/6/9），复用冻结已验收core/source/runtime。只读取原完整指令/RGB/proprio；不读mask、谓词/接触真值、进度标签、未来帧或eval分数。支持声明新adapter身份和基线lineage，别误拒绝预期模型变化。
7. 正式结果采用benchmark034二元报告接口；若034未合入，可固定已验收明确ref依赖，不能私刻另一评分器。两组及baseline同一规则：完成记录原合规success→1，其余已完成→0；技术错误/缺失属于运行不完整，不能伪造0。实时训练step/loss与eval百分比/SR、每条视频/动作/query日志齐全。

## 必要CPU/fake（只防本轮具体错误）

- HDF时间/动作/夹爪/归一化映射：防止训练与执行动作方向/时序错误。
- 整轨split、重复来源同组、输入白名单：防泄漏；不另建全量祖源工程。
- 原子段chunk不越界/尾mask与有效标量loss：防错误指令监督和padding伪降低loss。
- 进度阶段采样、fallback与实际比例：防把RAW重复包装为已覆盖外部进度。
- 完整原head/proprio加载、语言LoRA-only参数与梯度：防随机动作头、误训视觉或梯度断开。使用tiny/fake，不加载真实7B。
- adapter保存/加载与普通eval接入、034结果接口：防训练完成不能评、原子oracle输入或错误分母。只测受影响路径，不跑全库/多平台。

若实现中确有与规格冲突的硬问题，一次列明证据和最小可行修订；风格/目录差异不阻塞，不将额外检查加入开训门槛。

## 交付

- 独立PR与commit SHA、文件清单、上述实际CPU/fake命令及结果，不自动merge。
- `collaboration/responses/030_v2_round1.md`：源文件需求与已具备/待搬运分开、实际实现入口、静态资源限制、缺口，不把候选380来源/显存写成已验证。
- 配置模板和普通`source conda.sh`/`conda activate`/`python -u`命令：一个导出、两组训练、90/36评测；所有flag真实存在，路径使用占位/配置，不提交用户绝对路径或凭证。正式准确路径由Codex部署填写。
- 不重跑基线、不改物理评分/阈值、无FINISH/selector/扩01或11、无新增真实作业。

**本轮授权仅代码＋CPU/fake。最多180新增普通演示来源、两次1000-update训练、126新eval是候选预算，用户尚未批准。** X/Codex不启动下载新数据、真实HDF导出/恢复/标签、模型加载、训练或eval。此边界不阻止立即写代码、配置与tiny合成测试。
