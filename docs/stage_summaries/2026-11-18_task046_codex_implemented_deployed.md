# 046：Codex最小模型适配已部署，用户可启动180

2026-11-18。用户认为实验本质仅换模型，并明确由Codex直接改。此前046待X工单现被本交付覆盖，X无需实现/泛审。旧044主动拒绝研究adapter，故新增046小接线，不放宽旧044；所有真实作业仍用户启动。

PR21固定a1179099c61317aba90ef8af4bc334f21fb10c88，基于accepted PR20@10531b62；源树412f9ab7与本地测试树相同，不自动merge。逐字携带accepted PR19@e8445b6a的044模块与X来源，原045生产文件不动。新策略继承044原predict/reset/close/输入白名单与实际文字审计，仅内部构造045 HintPolicy、一次加载固定H1@3000；模型、动作后处理、原完整A+B评分和来源不变。

CPU/fake共83不同最终通过（旧60、新23）；初次模板缺失与fixture tmp_path碰撞记录保留，不改旧源码或断言；修正装配后补测，加强串行报告身份后重复1项而不另计。属Codex自查，非独立第三方/真实7B性能验证。

隔离code/config名task046-h1-prompt-v1，117源依赖/模板＋4实际配置SHA一致；原worker/simulation两venv只no-deps映射新副本，无升级。实际配置、固定H1 adapter78a96aa7、P0 plan1d1c79e0/summary4e745dbe与62/90、冻结文本e648ef20均文件核对，未加载模型、仿真、训练state或新plan/评分。两新run与marker均不存在，无残留方法进程；没有代启动。

准备100%，真实新评测0%。下一用户直接一条Python run-both，在原simulation环境先P1正式90，正常完整后P2正式90；P0复用同模型68.89%不重跑，总predict≤11700。comparison.md/json给P0/P1/P2总分/九任务/P0及两新臂配对。无新训练/00/标签索引/数据生成/MVP或额外seed/prompt，保留旧全部权重/原视频/失败署名，不拼旧00算新AVG。

完整私有conda/python与watch命令在本地046运行文档，公开运行文档只用会话变量。用户无需pip/prepare/index/plan/额外GPU检查或等待X。技术异常保留输出与marker，不删除退款重开。

软件交付closed，真实效果open；用户交回结果后Codex只读现成报告。所有关键文档精确commit读回SHA本地备份/manifest登记，源tar、JUnit初始与修正记录、实际配置和私有部署收据保留；旧脏研究checkout不改，待删=[]。045研究网页上传失败是独立网络问题，不作为本实验前置。
