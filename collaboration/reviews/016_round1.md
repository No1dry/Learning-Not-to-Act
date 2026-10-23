# 016 Round 1：Codex实现审查

日期：2026-10-22。审查对象：[PR #2](https://github.com/No1dry/Learning-Not-to-Act/pull/2)，固定head `116818ca27577387551b74ee661fbe1288aa7d80`。

## 裁决

**主体实现符合016；仅一项已复现P2待修，016保持open。** 不改主架构，不要求重做数据、跑MVP或新增真实实验来验收此修正。PR未合并，服务器未部署。

独立选择器、可撤销历史、冻结actor语言桥接、真实训练/保存/恢复代码、数据与标注工具、薄core接入及双worker均已落地；不是设计稿或训练替身。真实模型效果尚无证据。

## 唯一必要修正：逐项确认的evidence被静默丢弃

位置：[supervision.py第35—38行，固定head](https://github.com/No1dry/Learning-Not-to-Act/blob/116818ca27577387551b74ee661fbe1288aa7d80/egrs/selector/supervision.py#L35)。

`source_for`支持JSON pointer继承，但`walk`在evidence父列表未确认时直接返回空列表，尚未检查其已完整确认的子项。合法外部标注可以逐项确认，导入接受后却无声失去证据字段监督，影响本方法的实体绑定训练。

纯CPU复现（PR checkout，无模型）：

```python
from tests.test_data_training import example
from egrs.selector.supervision import prepare_answer

sample = example()
provenance = {
    "/goals/0/relation": "human",
    "/goals/0/evidence/0": "human",
}
answer, supervised = prepare_answer(sample["answer"], provenance)
print(len(sample["answer"]["goals"][0]["evidence"]))  # 1
print(answer["goals"][0]["evidence"])                # []，确认项被清空
print(sorted(supervised))                          # 只有relation
```

[016 §9](../tasks/016_egrs_full_implementation.md#9-round1最小修正2026-10-22)给出实际执行要求。推荐按条目计算完整有效provenance，保留安全确认项；弱/不完整物理证据仍在teacher forcing前删除。若选择限制格式，至少在导入/构建时明确拒绝并提示所需父pointer，不能静默吞标签。现阶段给父列表标human可规避，但不代替修正。

## 已复现的定向软件验证

| 组 | 独立结果 |
|---|---:|
| runtime / policy / RPC / delivery | 20 passed |
| data / selector training | 24 passed |
| 原core fake集成 | 2 passed |
| 安装后双worker | 1 passed |
| 合计 | 47/47，100%通过 |

四组分进程执行，Python3.12.7；toy Torch/fake processor，不加载研究权重。core集成使用原仓库`c6dc98de0c54517c976057598b60f4cedf7fa3e5`固定参考；另对实际Eval pin `515e87d9b93ab838428791273a0f3020d6f56e9c`、内层OFT transfer及模拟OpenPI跨目标RNG做纯CPU核对。没有真实仿真或物理回放。

最初一次复核在参考依赖clone尚未完成时启动，因缺benchmark/HEAD失败；是Codex准备时序错误，不算X代码缺陷。依赖完成后上述四组全部通过。JUnit与交付快照已本地保留。

## 非阻塞建议，不要求本轮顺带返修

- `cli.py:97` compose覆盖整个selector.runtime，会丢已有CUDA可见卡/超时；部署可用明确最终配置规避，后续可改为保留未覆盖字段。
- `selector/infer.py:30`独立predict允许不传core配置，建议显式固定依赖；主方法双worker已强制activate，不受此问题影响。

## 未运行范围

真实数据准备、标注、真实processor校验、Qwen/VLA forward、研究训练和新方法评测本轮均为0。X已正确披露；不把fake通过写成研究效果或真实端到端就绪。014批处理对接、数据标签与真实资源另列，不成为这处CPU修正的新门槛。

下一步操作和执行者：X仅修监督边界并补受影响CPU/fake回归，在原PR回复016 round2；Codex增量复核后准备部署/命令，用户另行确认并启动真实阶段。
