# 028输出契约修复、真实调用与正式评测交接

## 范围与决定

用户要求Codex直接修正并亲自验证，不再把诊断启动交给用户。本轮授权实际用于固定模型/已有输入的必要GPU调用，不包含训练、完整80条评测或机器人动作执行。Codex承担实现、排障和部署；X无需返修。旧027正式启动在首个双相机视觉调用遗漏两个evidence，148 tokens后schema拒绝，0动作、评测完成0%；旧失败不改。

028接口修复及部署范围现已验收；不是视觉准确率、方法有效性或整批运行保证。完整评测仍由用户启动。

## 版本化推理修订

[PR #7](https://github.com/No1dry/Learning-Not-to-Act/pull/7)，最终实现`db74ad408a472315440f26505f1d4c3bec65d333`，未自动merge。固定3B/checkpoint-3、原LoRA、视觉prompt、原生评分和OFT不变，未重训。

生成时约束完整JSON键、每目标恰好一次、自生成entity/query引用一致、紧凑字段顺序、每目标最多3个证据区域、归一化坐标最多8位小数。证据由模型先生成；缺少某字段的区域支持时，该字段在生成时只能UNKNOWN，机制release仍NOT_APPLICABLE。原validator继续拒绝不一致，不添加bbox/support或真值、不后改JSON、不自动重试。此为明确的保守推理规则及输出预算限制，不能冒称原自由生成协议完全不变或UNKNOWN全为模型自主判断。

最终grammar为`egrs.visual-evidence-first.v3`，实现另加`greedy-validity-fast-path.v1`：单beam贪心最高分token已合法时直接接受，否则使用原LMFE完整掩码；不改变掩码后的argmax。源码hash为`bb9a2c50342379fe7ad02f73fd5283637cf3cac58e5f56ab11e2f7a59bd7e8aa`。

## 真实验证及未掩盖的失败

- 001：诊断脚本未先初始化RPC registry，未调用模型；脚本修正，旧失败保留。
- 002：真实registry成功，视觉generation前发现pydantic缺失；仅补选择器小依赖。
- 003：v1真实视觉生成1024 tokens后截断；长小数和重复证据未被当作有效输出。
- 004：v2完整448 tokens，但无release区域支持却声称RELEASED，原validator正确拒绝。
- 005：v3的4类输入、6次视觉调用全部通过原wrapper/JSON/schema校验（100%），进程正常退出。包括027原始NPZ的相同失败输入、单目标、双目标、连续q1/q2/q3（2/4/6图像）。原观测policy hash `5c0b65aa590d72eaf1d6849e129dcfbda54a01736a94d41e81f051be2e78f8e0`；未恢复/渲染仿真。dev案例按输入结构确定，不按模型表现挑选；历史来自本次先前预测，不输入标签。
- 006：最终快路径真实重跑同一原始失败输入，665 tokens，预测及raw逐字等于005；640步直接接受、25步完整筛选，筛选累计3.596秒，原校验通过、正常退出。不用修改模型输出来通过比对。

34项定向CPU/fake通过（100%，2秒级）；其中64组随机贪心序列比较属于CPU掩码等价测试，不是64次真实实验。

## 实际OFT动作边界证据

另做一次完整策略调度/真实OFT调用，selector复用005刚生成且hash绑定的预测（明确diagnostic_replay，不宣称本项又调用3B）。原OFT确实加载并预测；method日志中actor call_end.ok=true，query记录returned_chunk_length=8，原core `_actions`已经验证非空(T,7)有限实数数组。

随后诊断脚本额外使用`assert rows and ...`触发NumPy布尔歧义，所以该report仍为failed，不改成passed。独立复核原sidecar确认错误在策略及动作校验返回之后；脚本写法已修正，复用既有正面边界证据，不仅为报告错误再加载模型。动作数值未保存，不冒称已逐值审计。该原sidecar SHA为`32327cdcce784e4c98633607e426a66a2b979486a274691daf74b20ac1a11dff`；原failed report SHA为`c525c8efc264fc5785f1457206ec90321541580a489ff386514d906d8be5d2e8`。

本轮没有创建仿真或执行动作，没有episode成功率。诊断sidecar partial恰是未执行完整episode的事实，不伪造完成。

## 部署与速度口径

隔离部署028-codex-v4，controller/OFT/selector三环境仅更新方法wheel，源码hash一致。仅selector新增lm-format-enforcer0.11.3、interegular0.3.3、pydantic1.10.22；未升级torch/transformers/core或改原权重。

源码归档SHA `f57724557c4558f185730236ec51aea0ac0d88cd8e3f5daa3540f814bc478e20`，wheel SHA `628f139ad94df3800a347bb523eac1b9ceb423ad3ab75bd5b29c74d1c916ddcd`，本地/服务器一致。新eval配置和完整conda/venv/python命令已准备，正式输出目录仍不存在。

旧双目标case125.78秒包含registry+一次视觉，历史case373.43秒含registry+三次视觉。冷启动同篮子case原版185.31秒、快路径187.60秒，两次均含加载且负载不同，不能宣称端到端加速；仅已测得快路径筛选3.60秒，稳态吞吐未再追加测量。正式评测可能较慢，不保证几小时内完成。

## 研究结果不能混淆

首个真实mask10观测中g0已满足、g1未满足，但模型仍把两者判UNSAT，策略选择g0、发出放汤罐指令。这个模型判断错误明确保留；通过输出契约不等于定位/关系正确或能跳过已完成任务，不能借此宣称方法有效。

准备/软件接口与部署100%，训练沿用已完成模型，正式方法评测完成0%。下一步用户启动同旧基线80条可用来源的正式评测，计划100和20缺来源仍披露；不计缺失为模型失败、不补状态、不重跑基线。双视角视频和原指标保持；Codex分析交回结果。无自动merge、原数据覆盖或清理删除。
