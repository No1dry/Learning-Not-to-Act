# 025：Codex直接实现并部署方法评测入口

用户要求025不再等X，改由Codex直接实现。已基于024方法增加`python -m egrs.evaluate plan/run/inspect`，正式GPU评测仍由用户启动。没有新模型/仿真/回放调用，没有更改训练权重或基线运行。

## 软件与部署

方法侧薄编排复用固定`LIBERO-Remain-Eval@515e87d`的source验收、环境、视频、runner、evidence/schema和metrics，不复制或修改计分。分别记录完整方法、selector和嵌套原OFT身份；选择checkpoint-3，并在动作前比对原基线的实际资产/归一化身份，防止换底座导致虚假的方法收益。保留H520/K4/chunk8、seed7、双视角完整视频与原指标，不加入FINISH或测试真值输入。

新版28项受影响CPU/fake全部通过（214.37秒）；另首版27项通过。覆盖合成100条全流程、显式90/100部分来源、违规抓取原规则判失败、技术中断留痕、close/video/sidecar/source篡改及错误底座的动作前拒绝。合成来源接收使用fixture，不能冒称新物理验收；正式核对复用旧文件证据，没有GPU预检、模型forward或重复状态回放。

隔离部署025-codex-v2；controller、原OFT worker、selector三个解释器仅更新方法wheel，不更新依赖。补入已有LIBERO源码路径，三解释器均能解析实际模块。源码身份均为`ccbbb9bcde1a6baae68a0c190b1dd85350be5355a20d32833b5eb032ff63d8f1`。

传输SHA-256一致：source包`e7ba32326daade94d70e024b466d2a7a326788ccf6edc14d854cbd24c42dc3bb`；wheel `5a87156b923cb96dcdec49457b83895ea4eb8859de436a9992c46de194974ba6`。代码见[PR #4](https://github.com/No1dry/Learning-Not-to-Act/pull/4)，不自动合并旧PR。完整机器路径、conda/venv/python命令、初版/新版文件计划及测试记录保存在本地reports/egrs_eval025_2026-10-24/，不上传公开机器配置。

## 必须纠正：100是计划，原基线只实际执行80

生产文件级计划`7fefa6279b93c46ecf5d02c4a042d779e2ac0b27563d60272a5ea6cb99dc3587`为80/100可用，models_loaded=false、simulation_created=false。frypan_stove9、cabinet_close_top_bowl各10条缺旧replay_report.json，旧baseline batch本身亦记录同两项preparation_error、实际运行80；不是这次新出现的模型或状态失败。此前将100计划说成100可直接执行不准确，本记录纠正。

原基线table-support v2离线结果是21/80=26.25%（实际执行分母），21/100=21%（原计划分母）；来源证据见既有013离线rescore，不重跑模型。新方法若先比较，应使用相同可用80来源和相同计分版本，明确保留100计划中的20条missing，不能把缺失算作失败或宣称跑满100。

默认入口拒绝来源不全；显式`--allow-missing-sources`才允许直接运行已通过的来源，避免20条连坐80条。来源选择由旧证据可用性决定，不按模型成败选择。完成状态是completed_with_missing_sources、进度80%，分母仍100。控制台和progress.json显示初始化阶段、episode百分比、当前task/episode/query，query不冒称环境step。

软件实现和三个环境部署100%；可用来源覆盖80%；真实方法评测0%。025软件/部署范围已完成；20条来源证据缺口仍开放，不伪造闭环。若要实际跑满100，另需恢复原证据或用户授权准备；本轮不擅自补状态、替换初态、追加rollout、消融或重训。

没有删除或覆盖旧基线、训练数据、三个checkpoint、旧失败或初版计划；本轮待删清单为空。下一步操作和执行者：用户按完整标准python命令明确启动同80来源评测；Codex分析交回的日志、指标和视频。
