# 043-v2首次prepare路径错误与pathfix1

2026-11-15，用户询问“报错了？”。Codex只读取现成控制台/文件/进程，未代启停实验。

## 原因及影响

首次用户启动总日志`FAILED phase=prepare exit=1`，具体为`ValueError: Output overlaps protected input`。旧040 retention元信息中generated data_root声明为整个data目录，Codex原部署把sidecar输出设在data/hint043/status-001，被防覆盖规则拦截。属于Codex部署配置错误，不是模型或训练失败；不应放宽输出保护。

异常发生在build_sidecar的metadata读取之后、创建输出目录/production_started之前。旧status输出不存在，H0/H1训练目录/日志不存在，无043真实进程。首轮实际产标签0、原参考/学生前向0、optimizer更新0，只有空launch marker及两份失败控制台。原143960键/18048参考/54144模型/360正式预算不变，不是消耗退款。

## 修复

新增独立pathfix1七份部署配置，旧配置/两日志/空marker完整保留。状态文字输出改为data树外annotations/task043/status-001；两训练配置仅sidecar_dir改变。session指向新配置目录，启动marker/prepare日志使用pathfix1名。训练输出沿用尚不存在的H0/H1 train-001，评测JSON逐字节不变；运行源码、网络、损失、数据、统计归一化、评分和依赖不变。没有热改运行代码/更换环境映射。

已在服务器现有worker Python进行两份实际配置严格解析、逐字段仅sidecar变化、实际全部保护根无重叠、评测配置字节相等、三脚本bash语法检查；未导入torch/transformers/h5py、未构造数据或模型。七文件本地/服务器SHA一致。两项新增CPU/fake测试最终全通过，首次新增fake脚本对-u参数计数错误导致1测试失败，修正fixture后通过；保留两份JUnit，不将它称真实训练。

## 下一步与归档

下一用户按更新本地完整命令source pathfix1 session，再运行准备→H0→H1；Codex不代启，不追加预检/MVP/基线。准备成功正常进入训练，正式评测仍须用户另启。真实训练/效果仍open，X不重复实现或泛审。

本地保留两原失败日志、新旧配置、两JUnit和文件部署收据；阶段文档精确GitHub commit读回SHA备份。PR18仅补模板/文档/软件回归，不自动merge任何PR。旧权重数据失败和署名保持，无删除，待删=[]。本条覆盖旧043-v2“未启动”快照，不覆盖以后用户执行状态。
