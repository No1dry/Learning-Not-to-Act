# Task042 R1：F0/F1统一SDPA与任务—控制信息隔离交付

2026-11-12，X。实现commit **`03e0efcd5a999c77549ed8d7b549a29feb731c13`**，基于accepted PR16@`e8dcf87979d14d081666629a2de3483629a4f59c`，同步main@`ff707d3`工单/预算和附带SDPA源审计（本地merge `e4c0b4a`）。本次新042分支继承尚未合并的PR16及其依赖；未合并或改写旧PR。**实现/定向CPU交付100%，待Codex验收；部署、真实训练、真实评测均0%。**

已提交[新PR17](https://github.com/No1dry/Learning-Not-to-Act/pull/17)，分支`x/task042`，保持open、未合并。代码、回复、完整命令和CPU证据均在该PR；发布后核对精确head及关键文件blob，软件源码/证据另作本地SHA备份，不复制真实数据或权重。

- **F0/F1基础均为原C1。** 两者同一实例级SDPA、同尺寸显式dense mask，F0保留原OFT padding-only双向有效图；F1仅禁`T query ← C key`，C仍读T/C，T内部仍双向，最终所有层`is_causal=False`。没有新增参数、loss、索引、标注、教师或评分变化，不把F0替换为旧R0分数。
- `egrs/tcif042/attention.py`适配审计`LlamaSdpaAttention`的最终primitive，去掉会抹除禁边的last-row expand；原q/k/v/o及LoRA Parameter对象/键名、RoPE、GQA、缩放/dropout/输出投影和并行动作保留。只绑定042实例，不编辑site-packages、OFT/core或全局torch。实际初始化只读类/版本/源SHA/dtype，不做额外前向；严格支持Transformers4.40.1、Torch2.4.1+cu121及审计源SHA `3aac24ce…0554c52e`，不支持的类/backend/source/cache/output_attentions或eager回退明确报错。历史静态审计不冒称旧7B动态分支追踪。
- `layout.py`使用原placeholder labels的shifted56、原指令token map、真实patch数量及本次融合长度；同一原forward捕获proprio输出核对实际P。`a0=min(A)`，T是有效`pos<a0`排除P，其他有效位置为C；全部H_v/H_l在T，P/A在C，**首个A保留读P权限**。padding key保留屏蔽，不整行偷偷解禁。完整4D tensor显式进入LM→decoder→每层checkpoint，变长u/v各保存自己的mask，重算不读最近样本状态；scoped hooks在finally清除。原共享`task_control/oft.py`仅增可选`forward`回调，默认保持；042训练/dev/eval共用`tcif042.oft.prediction`，单次vision/projector/VLA。
- 原SOG10参考完全旁路学生布局hook与全部新增LoRA/z/count/残差，原2D padding经同包装走native双向dense路径。每更新**8个参考全部先于22学生图**，原模式/hook/RNG/cache/checkpoint/requires_grad保护及原dev选择保持。两臂原12ten+4fresh+4raw+1pair两端及C1所有权重不变，pair仅交换z，无039保持项/teacher加载。
- `adapter.py/checkpoint.py/config.py/training.py/policy.py/evaluation.py`提供严格042身份、完整初始化/保存/恢复、两臂入口及单学生原180协议。初始化固定完整041 **R0**末1000字节SHA `d4e726a867531f655d28e11f358ce0af597d4ada0f4928f4597aeadb28d38397`、原040 index `8ef04d91…e6c7fe`；全量LoRA/context/残差/count复制前核验。祖代2000、本阶段新增1000、累计3000如实分开；新optimizer/scheduler/seed7 sampler/RNG/两账本，不继承旧余额。独立root保存base c1、exp f0/f1、完整source/index/attention合同和实际runtime，旧041 reader仍拒042。resume严格绑定原输出目录/配置类型/source/index/臂/合同/backend/runtime，恢复全部训练状态；账本先扣、失败不退、领先checkpoint拒恢复。浮点`photometric_probability: 0.0`按实际生成JSON测试，整数0拒绝。

最终定向CPU/fake **109 passed，0 failed/errors/skipped，16.45秒**：新attention20、layout22、identity28、evaluation7、entry8、training5，加共享旧model14/reference5；[机器证据及完整命令](../evidence/042_cpu_fake.json)、[JUnit](../evidence/042_cpu_fake.junit.xml)。测试实际primitive入参/输出/梯度，独立native双向公式、RoPE/GQA/dropout/Parameter身份；三层P→C→T反例，固定I/L时F1的T数值p非干涉与控制仍读p；变长u/v真实reentrant checkpoint保存各自mask，原reference后反向无污染。default共享预测还经过真实tiny SDPA与非reentrant checkpoint的一次完整更新/dev，核对8参考先于22学生、每条仅一次vision/P投影。完整续跑与不中断的学生tensor hash相同，两臂各fake180原来源/评分/视频/raw合同保持，推理无reference/GT/partner。

[独立集中审查](../evidence/042_independent_review.md)未发现可确认的阻断缺陷、信息泄漏或关键合同缺失；其另行90新测试和32旧受影响测试通过，**不叠加到上述109计数**。`git diff --check`通过。早期TDD缺实现、fixture不匹配及保护回归红灯均保留本地，不改成历史通过。当地CPU Torch2.12.0+cu130/float32，Transformers未安装；tiny测试只patch私有runtime inspector或合成源指纹，不提供生产绕过开关。未加载真实7B、教师/轨迹、MuJoCo或GPU，不声称生产数值/性能、物理rewind不变、目标身份正确、A硬保护、创新或SR保证。

完整常用conda配置、完整源SHA/固定index、两臂实际JSON、原041 eval派生、同run恢复、后台与日志命令见[042运行文档](../../docs/task042_usage.md)。无私有路径/凭证，无依赖升级。Codex验收隔离部署并填好配置后，**用户**可串行执行两训练；任一失败停止，不自动重试/退款/eval：

```bash
set -e
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task042-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
for arm in f0 f1; do
  python -u -m egrs.tcif042 train \
    --config "$LNA_ROOT/configs/task042/training.$arm.json" \
    --output-dir "$LNA_ROOT/runs/task042-$arm-train-001"
done
```

训练完成后用户另启原正式协议，**各180、总360新执行**，不继承旧分数：

```bash
set -e
for arm in f0 f1; do
  python -u -m egrs.tcif042 eval --experiment-arm "$arm" --mode run \
    --config "$LNA_ROOT/configs/task042/evaluation.$arm.json" \
    --output "$LNA_ROOT/runs/task042-$arm-eval-001"
done
```

每臂九任务10二元合规90、00官方90、H520/chunk8/seed7、全视频/raw/core/reporting/双bridge及端点保持。每臂新增1000、原参考≤9024含dev、学生≤24560；两臂合计参考≤18048/学生≤49120。未重跑旧基线或改物理判据，未生成新数据/索引或改冻结部署；历史035–041全部证据保留，精确待删`[]`。

无新增已知硬阻塞；真实初始化时的严格source/runtime准入与真实效果仍待用户正常作业验证，不另加GPU预跑门槛。下一步执行者：**Codex**审查新PR、验收后隔离部署与准备实际配置；**用户**亲启两训练和正式360；**Codex**分析匹配F1−F0。X不部署、不启动真实实验、不自动合并。
