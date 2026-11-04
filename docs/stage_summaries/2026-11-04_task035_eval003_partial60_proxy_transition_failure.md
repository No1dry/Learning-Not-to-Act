# Task035：eval003完成六任务60条与连续切换故障交接

2026-11-04。002在首推理因CUDA分配失败退出，0动作；当时GPU约79%被当前容器不可见进程占用。用户释放资源后003实际跑通旧六任务60条，直到切换首个新三任务失败。Codex未自主启动/停止/重跑模型或仿真。

## 保留的实际结果

总进度60/180=33.33%；10进度60/90=66.67%，合规30/60=50.00%，00尚未执行。

| 10任务 | 完成 | 合规成功率 |
|---|---:|---:|
| basket | 10/10 | 90.00%（9/10） |
| basket_cheese_butter | 10/10 | 60.00%（6/10） |
| stove | 10/10 | 0.00%（0/10） |
| dual_mugs | 10/10 | 50.00%（5/10） |
| mug_pudding | 10/10 | 0.00%（0/10） |
| basket_soup_cheese | 10/10 | 100.00%（10/10） |

来自原执行与已核验报告；未完成项/技术错误不伪造模型失败，正式全90SR仍N/A。此阶段50%覆盖仅六任务，不与全九90基线24.44%直接作同人口提升。全部60成功/失败、视频、raw与输入/动作证据都保留，不因后续代码修复重跑。

## 新错误与证据

首条bowl_drawer_close_s000_10状态runtime_error、n_steps=0。环境完整fingerprint/constructor通过，reset链遇`unexpected LIBERO utils.collections binding; refusing to hide a foreign patch`。旧/新compat源码字节相同，但两个模块的_CollectionsProxy类身份不同，旧实例仍占共享utils.collections，新shim当成陌生补丁拒绝。

Codex用两份固定compat源码＋同一合成utils对象纯CPU复现：old→old通过，old→current抛完全相同错误；未导入LIBERO、实例化环境或模型。R9先前两套身份与34项测试是真实通过，但单版隔离测试漏了连续切换；兼容执行子项重新open，原训练/身份/评分验收保持。

原服务器runs/trajectory035-eval-003及.console.log不改。本地reports/task035_eval003_transition_failure_2026-11-04保存console/batch/summary/report、首失败task/sidecar/raw、CPU复现源码/JSON；原60大工件仍在服务器，不用复制改raw身份。

## 决策与下一步

[X任务](../../collaboration/tasks/035_proxy_transition_and_resume.md)仅修方法侧受控共享代理状态与显式--continue-from：严格固定源/环境锁与陌生补丁拒绝，双向切换；用父003原reader核验继承全部60（含成功失败），在新run只执行120＝剩余10的30＋00的90。父003未完成/0步技术attempt按缺口处理，不要求先完整180；父已完成证据被改动则拒绝，不默默替换来源。旧失败和代码lineage保留，不能把继承60冒称新代码执行。

固定同一update-001000，原180人口/各90分母、原指令/双图/本体、seed7/chunk8/H520、原端点、10二元合规/00官方评分与原两基线保持。不同代码/继承与新执行明确分列。下一执行者X做受影响CPU/fake，Codex审查隔离部署/命令，用户直接启动剩余队列；不重训、重建状态、重跑60或基线，不新加GPU/物理预检/MVP或全库门槛。

训练完成100%，10实际完成66.67%，00为0，方法全量效果待定。兼容/续跑open，实时SR小项仍非阻断open。原始数据/运行refs/开放任务不清理，待删=[]。
