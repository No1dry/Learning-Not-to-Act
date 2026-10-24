# 026：真实025解析暂停与接收层修订

用户交回的025首次启动在basket_s000_10的instruction-only registry阶段暂停。原OFT加载、嵌套资产身份与环境初始化已通过；selector生成159 tokens、无图像输入，随后json.loads报Expecting value。原raw记录n_steps=0、executed_actions=[]；这不是机械臂任务失败或可用的成功率结论。

旧日志没有生成原文，无法证明只是Markdown围栏，也不能据此诊断训练失败。原失败目录/原始结果保留，没有自动重试、重训或修改数据/计分。

Codex已实现026：共享既有严格外层JSON解析，只接受裸JSON或单个完整json/无类型围栏；禁止截取解释文字、补字段、强制enum或语义修复。registry/prediction的原validator、prompt、权重及生成设置不变。新增raw_output和wrapper/json/schema审计，成功与失败均通过RPC/sidecar保留；独立推理增加--audit-output，错误时也写原文与审计。

47项定向CPU/fake通过（39项未选择，不冒称全库通过）。覆盖三种外层格式、额外解释/多围栏/截断拒绝、错误kind等语义仍拒绝、原文不丢失、单次调用不重试、RPC失败帧、CLI成功/失败审计以及既有selector/token审计回归。三解释器源码身份一致，文件传输SHA核对通过；只做文件级dry-run，没有新增真实GPU调用。

实际故障原因仍需生成原文区分：已提供用户启动的一次同指令、同checkpoint文本调用，只加载3B，不加载OFT、不创建仿真或执行策略动作。它不是评测成绩或选权重过程，不能宣称已重建旧原文或确认真实故障彻底解决。若输出语义错误，保留证据再作研究/实现决定，不静默替换成任务真值表或换模型。

下一步操作和执行者：用户启动该文本命令，Codex读取raw/schema结果；旧评测维持technical_pause，尚未恢复。X本轮不需实现，PR不自动合并。
