# 025：接入已训练selector，直接运行冻结100条mask10评测

## 目标和分工

训练已经完成，不再处理训练数据、重训或新增MVP。X只补齐方法仓库的实际批量评测入口，Codex审查部署并给出完整conda/python命令，用户启动唯一正式100条评测。不要启动任何真实模型、仿真或额外rollout。

在`No1dry/Learning-Not-to-Act`交付。最新方法实现为Codex PR #3，固定`ed779093c52bcde50034d53e5abe0697b934c08c`；在该实现上增量开发，不能退回main尚未合并的旧代码。原PR #2/#3不自动合并。原先提及的014泛化批处理需求，本轮只落实OFT＋完整方法所需范围，不要求先支持所有VLA或所有消融。

## 已有真实结果和冻结输入

024训练3 epochs完成，369 optimizer steps，每轮train1958/dev471。Dev loss为0.2074258072、0.1753628745、0.1675368237。因此按dev loss选checkpoint-3，不看任何测试结果选权重。3个checkpoint均有COMPLETE；选中adapter字节与保存hash一致。

固定3B基座/processor revision `66285546d2b821cf421d4f5eb2576359d3770cd3`，完整方法、history=true、role_supervision=true。选中adapter SHA-256为`e8ea45be6d466c6d3eacfe290eda14dd41f464a92aa13b2f09676c7d35aa82c8`；同级state SHA-256为`9ee11b8c28e9dbecd2f48b81762ea46bbe1eb38310ea0f0878b13ff241632867`。不能重封state、仅复制adapter而丢失COMPLETE，或加载无LoRA底座代替。

复用既有十任务×official-init0..9×mask10，共100条；primary60、extension40，policy seed7、H520、20Hz、K4、chunk<=8、完整双视角20fps视频。实际输入是已通过mask10范围验收的旧batch JSON及其manifest/replay引用，不重新prepare、回放或抽状态；00/01/11旧失败不连坐这些10输入。来源与episode排序、development标记保留。

底座仍用此前官方OpenVLA-OFT SOG10权重、原执行配置和normalization。libero_90沿用原zero-shot transfer与libero_10_no_noops统计，不新增suite checkpoint或改归一化。

## 已定位的缺口（不是新增研究门槛）

固定eval core `No1dry/LIBERO-Remain-Eval@515e87d9b93ab838428791273a0f3020d6f56e9c` 中，headless/planning.load_config只接受原OFT batch结构；workflow.make_policy固定SubprocessPolicy，后续身份核验假设顶层OFT；它不接方法配置、selector worker与finish_episode。方法侧已有egrs.core.run_episode薄桥及compose，但没有可启动的100条批处理入口。不能只把原policy_factory字符串换掉而绕过嵌套身份/终结流程。

## 实现范围

1. 在方法仓库增加独立、可运行的评测CLI，例如`python -m egrs.evaluate plan/run/inspect`（名称可调整）。plan/help/inspect只做文件工作，run才实例化模型和仿真。配置明确引用旧batch、固定core和每suite的完整method配置；复用已有compose，并保持actor/selector各自解释器隔离。Codex后续填服务器绝对路径，公开模板不写机器路径或凭证。
2. 方法侧仅做必要编排：直接调用固定core原source_plan/验收、环境/视频/evidence与headless.run_episode（经已有薄桥也可）、原schema/evidence验证和原metrics汇总；不可复制一套成功、错误抓取、释放、table-support或距离计分。沿用已修正table-support口径与基线比较。不修改固定core树、不monkeypatch、不借新core pin绕过原版本锁；若发现确实无法通过方法侧薄编排实现，先指出具体符号/合同冲突，不能静默放宽。
3. 真实构建`egrs.policy:make_policy`，每次episode按原流程reset一次，执行后必须finish_episode，关闭两模型worker并保留异常/partial。原OFT的完整实际身份独立核验，完整方法/selector checkpoint/配置/训练指纹另行绑定并连接raw/evidence/sidecar；不能把完整方法伪装成原baseline运行。跨suite必须保持同一selector和同一OFT资产，仅原suite/transfer区分。输入仍只有原传感白名单、instruction和合法过去历史；禁止读mask、目标真值、step指标或未来帧给策略。
4. 输出新目录，保存100条固定分母、raw/evidence、完整视频与方法sidecar，统计直接用冻结core输出；技术失败与任务失败分开，不静默替换、技术错误后整集fallback成baseline、自动补跑或改变来源。既有memory在没有可靠目标时选择原指令的正常方法回退保持不变。补齐inspect时对方法query与core query的关联及完整性核对；已结束episode保留证据，partial不装成completed。
5. 必须有可见进度：控制台及progress.json报告`已完成episode/100`、百分比、当前任务/episode和query；不要像训练入口一样仅更新静默文件。若现有接口无侵入拿不到真实环境step，不强求逐step输出，也不可把query冒称环境step。无需新增GPU或VLM进度任务，不扩展模型rollout预算。

## 精简验收与交付

仅做受影响CPU/fake：两个suite的嵌套配置接入、旧100来源计划复用、selector checkpoint正确加载配置/错版本拒绝、实际method factory与finish/close顺序、一个成功/失败/技术中断的证据保留、原指标函数复用，以及百分比进度。用fake模拟完整100个source分母不等于真实100 rollout。不重跑全库、多平台或重复原物理检查。

交付固定commit/PR、变更文件、定向测试结果、可填写部署模板、完整`conda activate`＋`python -m ...`命令示例，在collaboration/responses/025_round1.md记录。不要只交文档或“未来可接入”的伪代码。只补本入口，不改selector学习方法、数据/评测协议，不做训练重构、扩任务、FINISH或消融套件。

下一步操作和执行者：X实现及CPU/fake交付；Codex一次集中审查、隔离部署和命令准备；用户直接启动正式100条评测，不先加额外模型预检。
