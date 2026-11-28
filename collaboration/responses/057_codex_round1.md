# 057 Codex 交付：反事实探针（G0a）

日期：2026-11-27

## 交付

- `egrs/composition057/`：4 个反事实探针任务（汤罐/番茄酱 × 牛奶/橙汁），每任务 15 个状态、共 60；只跑 base；复用 055 的 canonical→A 预放构建与 056 的 rollout/证据/评分；输出标记 `diagnostic_only`。
- `configs/composition057/`：build/eval 配置样例（base-only，无 adapter 字段）。
- `tests/test_composition057.py`：20 项；连同 055 既有 catalog/preparation 45 项回归，本地 65 项全通过。

## 设计要点

- 不重绑 055 冻结状态，直接新建 60 个探针状态；证据链完整。
- environment identity 与目标无关（055 三个不同目标共用同一记录），无需 bind 步骤。
- 探针结果不进入任何正式分母，不构成方法结果。

## 限制

- 未部署、未跑真实构建/探针（SSH 连接被拒绝）。
- 055/056 包字节未改；056 测试需服务器 `LNA_CORE`，本地未跑。
