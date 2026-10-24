# 027：registry字段提示修订

## 真实证据

用户启动的026独立文本调用已产生完整原文审计。输出为单个完整JSON围栏，026 wrapper/JSON解析正常；原schema拒绝instruction被首字母大写并增加句号。两个source_text同样被改写，actor_text均为`the person`，而该字段既有含义是交给VLA的子任务动作指令。只忽略大小写不能解决后两个问题。

该调用为instruction-only，image_count=0；模型和checkpoint-3已真实加载，但不是视觉状态预测或环境评测。不能据此宣称视觉SFT失败。

## 修订边界

仅明确registry既有字段含义：instruction逐字保留、source_text为原文连续片段、actor_text为动作命令而非人类角色。添加两个通用文本示例（蓝积木/绿球和抽屉/杯子），不包含benchmark任务、状态、mask或目标完成真值。例子通过原validator；生产路径不回填/改写字段，不自动重试。

版本`egrs.registry-prompt.v2`及prompt SHA写入selector metadata。共享离线prompt身份随实际registry修订更新，但视觉PREDICTION_SCHEMA和视觉build_messages保持字节不变；不重新生成旧标签、不重训、不改变checkpoint、控制策略、计分或输入白名单。

## 必要验证与后续

- 55项定向CPU/fake通过（37未选），验证示例符合原契约、旧错误仍被拒绝、视觉prompt未改变及审计/包装兼容；不是模型效果。
- 新增文本示例会增加上下文，因此用固定processor做一次文件/tokenizer-only预算核对，防止真实调用因截断而失败；不加载权重或运行模型。
- 隔离027代码和新输出，026原失败保留。下一次真实文本调用仍由用户启动，只有新审计才可确认提示修订的实际效果；不得提前标记真实问题闭环。
