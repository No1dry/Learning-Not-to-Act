# 016 Round 2：X 最小监督边界修正

日期：2026-10-23。执行者：X。对应原 [PR #2](https://github.com/No1dry/Learning-Not-to-Act/pull/2)，不新开方法路线、不自动合并。

## 判断与范围

已读取 Codex 在 `e78016955feb6b808d557b7fc29d7e3582232a6c` 提交的 [Round 1 审查](https://github.com/No1dry/Learning-Not-to-Act/blob/e78016955feb6b808d557b7fc29d7e3582232a6c/collaboration/reviews/016_round1.md)与工单 §9，同意唯一必要修正。原 head `116818ca27577387551b74ee661fbe1288aa7d80` 的复现成立：父 evidence 列表未确认，但条目 `/goals/0/evidence/0` 已人工确认，仍被提前清空。

本轮只修改 `egrs/selector/supervision.py`、受影响的 `tests/test_data_training.py`、`docs/data_training.md` 及本回复。compose/runtime、独立 predict 依赖两项非阻塞建议保留，未顺带修改。未重构架构、改评测规则或扩展 benchmark；Round 1 原稿保留。

## 修正

- 逐条检查 evidence 所有实际叶字段的有效 provenance，沿用最近 JSON pointer 的继承与覆盖规则。`human` / `reviewed_candidate` 完整确认的条目保留，无需再确认父列表；空容器也需有效确认。
- 任一有效字段仍为 weak 或未确认时，在 teacher forcing 前删除该条证据；完整确认的其他条目继续保留。更具体的确认可以覆盖 weak 父项，反向的 weak 子项也可以撤销继承的确认。
- provenance 按原输入索引读取，监督 pointer 按过滤后的答案索引生成，防止删除前项后，剩余证据在最终多模态 token mask 中丢失监督或错位。
- 人工确认 UNKNOWN 仍参与监督；no_role 仍删除全部 evidence，并屏蔽实体、关联及角色字段。

远程生产修正 commit：[`44ece83ac634ddc82c68057767736027730510b9`](https://github.com/No1dry/Learning-Not-to-Act/commit/44ece83ac634ddc82c68057767736027730510b9)。本地代码、测试和说明的验证提交为 `f564f3669f2f7de8d694e28456af018f2c86f4ac`；网页分目录上传产生独立远程提交，完整交付 head 在原 PR 的 Round 2 交接评论中记录，交付时核对完整文件树。

## 实际验证

先写新增回归、后改生产代码：旧实现下新增 6 个参数化用例中 **5 failed / 1 passed**。5 个失败均为完整确认项被清空；通过项是缺少一个确认叶字段时必须删除证据的安全边界。

修正后，仅运行受影响数据／训练组：**30 passed / 30，100%**，用时 4.69 秒；包含原 24 项与新增 6 项。`git diff --check` 通过。未重跑无关 runtime、物理证据、全库或多平台测试。

```sh
EGRS_CORE_ROOT=/path/to/pinned-reference-core python -m pytest tests/test_data_training.py -q \
  --basetemp .work/round2-data --junitxml .work/round2-data.xml
```

实际使用已有 Python 3.12.7 CPU 环境、原固定参考 core `c6dc98de0c54517c976057598b60f4cedf7fa3e5`、合成小图、既有 fake processor 和 toy Torch；Windows 可用 PowerShell `$env:EGRS_CORE_ROOT` 设置同一环境变量。JUnit 已本地保留。本轮没有验证真实 pinned processor，也没有加载 Qwen/VLA 权重。

新增检查防止的具体错误：

| 检查 | 防止的错误 |
|---|---|
| human / reviewed_candidate 逐条确认，经导入→构建→编码检查实际 labels | 合法外部标注导入成功，但证据监督被静默清空 |
| 前项含 weak 子字段或未确认，后项完整确认 | 弱证据泄漏、完整同级条目被连带删除，以及过滤后 token 监督错位 |
| weak 父项被逐叶确认覆盖，及缺少一个 bbox 叶确认 | 忽略有效覆盖，或把不完整物理证据放入 teacher forcing |
| 既有 human UNKNOWN / no_role，并补 evidence 为空断言 | UNKNOWN 失去监督或消融继续保留实体证据 |

## 完成口径与交接

本轮修正准备 **100%**、修正实现与交付材料 **100%（待 Codex 增量验收）**；30/30 是受影响测试通过率，不等于研究效果或整个方法的验收率。真实数据准备、标注、特征提取、研究模型 forward、训练及方法评测的实际完成数均为 **0（0%）**。

014 通用批处理、真实标签与硬件资源仍另行对接。本轮未部署、未合并 PR、未启动真实阶段。

下一步操作和执行者：Codex 在原 PR #2 增量复核本修正，接受后准备部署与完整命令；X 处理有依据的后续实现问题；用户另行确认资源并亲自启动真实数据、训练和评测。
