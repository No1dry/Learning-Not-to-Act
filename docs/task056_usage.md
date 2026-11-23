# Task056：Base/H0/H1三个未见组合同源评测

只读取Task055完成的150个预完成来源，分别评测原版Base、H0@3000和H1@3000，每模型150条，共450条。没有普通状态、状态重建、训练或额外seed。

## 接口

```bash
python -m egrs.composition056 run --config configs/composition056/evaluation.example.json --model base --output /new/output/base
python -m egrs.composition056 run --config configs/composition056/evaluation.example.json --model h0 --output /new/output/h0
python -m egrs.composition056 run --config configs/composition056/evaluation.example.json --model h1 --output /new/output/h1
python -m egrs.composition056 compare --base /new/output/base --h0 /new/output/h0 --h1 /new/output/h1 --output /new/output/comparison.json
```

配置使用环境变量展开：`LNA055_BANK`、`LNA_BASE_RUNTIME`、`LNA_REPORTING`、`LNA_H0_ADAPTER`、`LNA_H1_ADAPTER`、`LNA_EXISTING_DATA_ROOT`、`LNA_EXISTING_RUNS_ROOT`。实际部署时使用绝对路径，不保留占位符。`run`在导入`libero_remain_reporting`前显式激活`reporting_root`，避免仅完成core激活后缺少报告包。

每个模型在独立CLI进程中运行。计划前只读检查完整bank与manifest/artifact SHA；执行时使用对应派生`task.bddl`和冻结`state.npy`，私有注册新suite/task ID，不把新组合冒充旧任务。原HeadlessLiberoEnv、runner、完整视频、证据验证及034二元合规评分保持。

结果验证复用053的index50私有校验，接受固定索引0..49但不改变评分。输出保护拒绝覆盖。技术错误停止，不自动重试或启动后续模型。若父run仅因原core索引10上限中断，可用`--continue-from`显式继承连续完成前缀；新输出仍必须为空，父run和旧结果不修改。最终comparison包含三模型总数、逐任务结果、配对新增/丢失、原生目标及重叠诊断。新旧人口不混算，不声称unseen-scene或任意任务泛化。

## 定向测试

```bash
export LNA_CORE=/absolute/path/to/frozen/eval-core
export LNA_REPORTING=/absolute/path/to/frozen/reporting
python -m pytest tests/test_composition056.py -q
```

当前独立测试为10项CPU/fake通过；不代表真实模型或物理结果。
