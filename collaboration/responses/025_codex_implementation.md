# 025 Codex直接实现

用户最新授权本轮Codex直接实现，不再等待X；真实评测仍由用户启动。基于024固定ed779093增量实现，旧PR/署名保留，不自动合并。

新增`python -m egrs.evaluate plan/run/inspect`和公开模板。只编排既有100条mask10，不改固定eval core、测量、计分、状态、基座归一化或模型方法。直接调用原runner/evidence/metrics和既有方法finish桥；方法、selector和原OFT嵌套身份分别记录，并与旧baseline已加载资产身份比对后才允许行动。输出完整视频、原始证据、方法sidecar、原主指标及固定分母，控制台/文件显示episode百分比与当前query。技术问题暂停并留痕，不自动重试/替换来源或冒充baseline。

27项定向CPU/fake全部通过：13项新编排/负例、14项既有policy/runtime回归。新测试使用假模型、合成来源和原core runner/schema/真实几何证据代码，覆盖两suite完整100条编排、错误抓取判失败、技术失败/中断、sidecar与视频、cleanup失败、原基线统计不一致的动作前拒绝及篡改留痕。合成source接收函数由fixture代替，不声称重新物理验收；原状态证据在部署时由原文件校验入口复用，无仿真回放。

补齐controller/actor/selector三解释器的方法包及原LIBERO源码路径；不更新模型依赖、不改上游代码。代码与wheel字节身份核对，实际配置/已训练checkpoint与冻结输入的文件级计划由Codex继续记录在长期阶段总结。软件通过不等于真实GPU rollout、模型效果或物理成功。

下一步操作和执行者：Codex完成隔离部署和文件级计划后给完整conda/python命令，用户直接启动正式100条评测，无额外GPU预检。X本轮无需重复实现。

## 生产输入核对后的明确修订

旧基线本身只记录80条，另frypan_stove9和cabinet_close_top_bowl共20条原回放文件缺失。前述100是计划分母，不是已完成的100次基线执行。原文件级plan.json保留80/100、exit2和两项缺失原因，未改成通过。为不连坐已有80条，增加显式`--allow-missing-sources`：默认仍拒绝缺来源；用户明确选择后只执行原可用来源，分母保留100，缺失20不算模型失败，不换来源、不重做状态。完成状态明确为completed_with_missing_sources，进度80%，不是100次rollout完成。

新版28/28定向CPU/fake通过（214.37秒），增加严格默认和显式部分来源的90/100合成路径测试；实际部署文件级计划仍80/100，models_loaded=false、simulation_created=false。此前旧参考路径误配的开发测试尝试未用作验收；最终只用正式515核心执行受影响测试，未以跳过或放宽版本锁掩盖。方法源码、wheel和传输hash在三解释器一致，部署隔离于训练与旧基线，尚未启动真实评测。

下一步操作和执行者：用户可按已部署v2命令明确启动与原基线相同80条的正式比较；剩余20条来源缺口保持开放，不自动新建或回放。
