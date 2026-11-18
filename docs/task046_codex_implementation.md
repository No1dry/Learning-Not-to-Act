# 046：仅适配模型加载，不改任务或评分

用户于2026-11-18改由Codex直接实现。本分支基于accepted045 PR20固定10531b62，原045实现不变；逐字携带accepted044 PR19@e8445b6a的6个prompt044模块、冻结语言表与原测试模板，保留X来源。

新增prompt046：外层复用044 predict/reset/close与实际文字审计，内层直接构造原045 HintPolicy、一次显式H1@3000 attach。旧044仍只许原版，旧045仍原无提示合同；未改模型、权重、动作后处理、观测、初态、目标或评分。

046执行入口版本化沿044 ten-only编排，仅替换模型/元数据校验及P0来源：固定H1权重SHA78a96aa7、P0 plan1d1c79e0/summary4e745dbe；P0逐episode读取现成62/90，不再执行。P1/P2各90、query合计≤11700；新报告列三组总分/九任务/配对得失，不拼旧00造AVG。

046顶层如实标额外语义提示和research_adapter_loaded=true；artifact内部deployment_hint=false保持不可变训练身份。审计沿原task044-prompt-audit-v1格式，新实验身份为046。P1/P2文字逐字沿044冻结表，评分仍原完整A+B及A保护。

定向CPU/fake验证模型交换、真实字符串边界/传感白名单、P0绑定、ten-only完整90报告/技术失败、串行180/防重复和三组比较；不运行真实模型/仿真。初次旧模板缺2示例文件、7新fixture路径碰撞的测试装配问题保留原JUnit，修正装配后只补相应用例，不改生产断言或旧044源码。

部署后仍仅用户亲启真实评测，Codex提供完整conda/python命令。无新训练、00、数据生成、FINISH/VLM、额外prompt或seed；不自动merge或删除。
