# Task041 R1：040初始化的R0/R1旧10保持实现交付

2026-11-11，X。实现commit **`c51df70e597021d2c33a5bca013feabf723d879f`**；基于accepted PR15@`428c13585cebac1d6c90fd86a205e914caa2bb8f`，同步main工单`be43704`（本地merge `6fe4bb9`），新PR保留未merge依赖，不合并旧PR。

- **R0/R1基础均为C1**，完整加载040固定末1000的LoRA、context z、动作残差、count等全部可训练参数，原冻结SOG10/头/proprio/统计保持。新优化器/调度/seed7 sampler及三账本，各**新增1000**；祖代1000单独记录。R0不是C0、不恢复完成040的optimizer/RNG。仅R1增加`.10 * L_old10`，原C1所有loss/采样/dev保持。
- `retention041/reference.py`提供独立完整039教师分支，共享的只有原冻结骨干；教师LoRA为独立buffer、完整context独立，不进入学生optimizer/adapter。原SOG10与039参考均先于学生图，no_grad/eval且逐项恢复模式/hook/requires_grad/checkpoint/cache/Python-NumPy-Torch及已初始化CUDA RNG。旧`task_control/oft.py`仅增加显式可选modules参数，原默认不变，无活跃图内权重热换。
- `data.py/config.py`严格绑定现成040 index与输入，按040→039→old003明确祖源识别六任务train ten，原12ten按位置取前最多4个、保留重复；少于4按实际数、0则无teacher forward/精确0项，不重抽或fallback。每样本按实际有效mask对7维动作取均值，再按所选样本数平均；原专家BC保留，保持项加到对应学生同一图，仍22student/8base-reference/最多4old-reference。
- `adapter.py/checkpoint.py/policy.py/evaluation.py`是严格041根schema，保存`arm=c1`与`experiment_arm=r0/r1`、完整init/teacher/index/阶段身份、全学生/optimizer/scheduler/sampler/RNG及三账本。SHA/键/形状/基础lineage在复制前校验，教师保留039 index。前向前扣账（含R0显式0账本），失败不退款、领先checkpoint拒恢复，复制到异run亦拒。新eval仅一个学生，复用原180人口/来源/双bridge/二元评分/全视频；旧reader不放宽且拒041根。

最终定向CPU/fake **166 passed，0 failed/errors/skipped**：[JSON及完整测试命令](../evidence/041_cpu_fake.json)，[数据65](../evidence/041_cpu_data.junit.xml)/[参考32](../evidence/041_cpu_reference.junit.xml)/[身份评测43](../evidence/041_cpu_identity.junit.xml)/[训练接线26](../evidence/041_cpu_stage.junit.xml)。真实tiny autograd＋非reentrant checkpoint覆盖三路分支、所有参考先于学生、匹配基础batch/C1 loss、少于4的归一化、0选择R1与R0 tensor相同、三账本失败前扣和同run中断恢复全tensor一致；R0/R1各fake180单学生接线保持。独立集中审查**0 Critical/Important/Minor**；未用CPU证明真实显存/速度或SR，CUDA RNG实现未在GPU运行。早期TDD/本机temp setup/fixture红灯保留。

**完整常用命令模板**（均未在服务器执行）：Codex验收隔离部署后，按[运行文档](../../docs/task041_usage.md)安装既有OFT/worker方法包，填`configs/task041/training.r0/r1.json`与原040实际eval派生配置；路径/环境由Codex替换。串行训练失败即停，不自动评测：

```bash
set -e
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task041-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
for arm in r0 r1; do
  python -u -m egrs.retention041 train \
    --config "$LNA_ROOT/configs/task041/training.$arm.json" \
    --output-dir "$LNA_ROOT/runs/task041-$arm-train-001"
done
```

两臂正常训练完成后，用户另行启动正式评测（原固定末1000，各180；不继承039040分数）：

```bash
set -e
for arm in r0 r1; do
  python -u -m egrs.retention041 eval --experiment-arm "$arm" --mode run \
    --config "$LNA_ROOT/configs/task041/evaluation.$arm.json" \
    --output "$LNA_ROOT/runs/task041-$arm-eval-001"
done
```

原040/039模型路径与完整固定SHA、现成index、原core/reporting/runtime、各臂JSON、同run完整`--resume`、nohup/日志/进度命令均见[使用说明](../../docs/task041_usage.md)。预算已批准：两组新增2000、原参考≤18048＋039≤4000=22048、student≤49120、正式模型360；新数据/标签/索引/仿真/状态重建/S/C0/seed/系数搜索/基线/MVP均0。

**实现/定向测试交付100%，待Codex验收；部署、真实数据/模型/仿真/训练/eval为0%。** 无新增硬阻塞，不复制真实权重到GitHub，无自动merge/删除或SSH。下一**Codex**审查、验收后隔离部署并填实际普通命令，**用户**亲启全部真实作业，**Codex**分析R1−R0；不把跨版本保持当A硬保护/新颖性保证，也不把R1−040全归新项。
