# 026真实输出与027文本拆解提示修订

## 真实结果

用户启动026单次文本调用：同固定3B、checkpoint-3，image_count=0、prompt132 tokens、generated159 tokens。原文完整保存在audit：只有一个完整JSON围栏，wrapper与JSON通过；schema拒绝instruction首字母大写并添加句号。两个source_text也被改写，actor_text均为`the person`，并非所要求的VLA子任务指令。旧失败与原文保留，不能仅消除首个异常后宣称解决。

这证实025存在包装兼容问题的可能，但025未保存原文，不能反推025必然输出同样文本。026失败不属于视觉状态预测、机器人动作失败或最终任务分数；方法评测完成仍0%。

## 027实施

Codex按已有直接实施授权修正registry提示，不再等待X。只定义清楚原字段语义并添加两个通用、非benchmark文本示例。原instruction和source_text逐字保留；actor_text是可交给VLA的动作命令。生产路径不改写/补全生成字段、不放宽validator、不自动重试，不注入场景或完成真值。

实现[PR #6](https://github.com/No1dry/Learning-Not-to-Act/pull/6)，固定commit `a236454a50b20c06674afd8f63c8120c86c0289e`，基于026，未自动merge。registry prompt版本`egrs.registry-prompt.v2`，SHA-256 `cd47cfbf9467db26378a2f417871526a65d4b5b204f9bbc7942bafa4c9ef07b6`。视觉PREDICTION_SCHEMA与视觉消息黄金hash均保持026一致，不重训、不改旧标签、checkpoint、策略、评分或core。

## 验证与部署

55项相关CPU/fake通过（100%，37未选，1.41秒），覆盖通用示例契约、旧错误仍被拒绝、原指令保留、视觉prompt字节一致及wire/audit。不是模型实际行为证明。

027隔离目录上传/三环境方法包部署100%，三个解释器method source hash均为`f08440a2348747aa5657665d8b41b10d91c2800bf1390ad31c7ea9414c6310a4`，未改依赖、原OFT或core。源码归档SHA `181ba3461dadffb6e06b8a7e1fd3664b08b3179c3baa5d7477c182d37616be52`；wheel SHA `89295d58b38cd4c18a8fafc97a9a3455a84c847ce1f53e324a3e78a79ed660fa`，服务器一致。新输出空目录已准备，不覆盖026失败。

仅做固定processor的文本预算核对和CLI dry-run，不加载模型、不调用generate、不恢复仿真、不启动eval。初版预算检查脚本误用processor的tokenize=True接口，CPU TypeError后改用实际生产encode_messages路径；不隐藏该诊断失败，不因此改生产编码。

## 尚未闭环

真实模型能否按澄清提示返回合法、正确registry仍未验证；不能提前把修订称为真实效果修复。下一步由用户启动027单次文本调用；Codex读取新audit后决定恢复正式评测。X无需返修，不先新增训练或多轮诊断。训练完成100%；整体方法评测0%，旧100计划/80可用/20缺来源边界不变。本轮无清理/删除。
