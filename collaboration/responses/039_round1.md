# Task039 R1：软件与CPU/fake交付

2026-11-07，X。实现commit **`8a733d039aef69df1323bb34c896ed40895cff12`**。依赖accepted038 PR13固定`5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`，并合入main工单`d919233`（本地merge `e5ff4aa`）；新PR显式携带未merge依赖，不合并任何GitHub PR。

- `egrs/coverage039/`接通真实动作open≤10／竖直退离≤20且≤0.10m／hold≤10，总新增≤40、episode≤520；沿原V2准入及真实连续5帧释放证据，收尾动作与T+1观测全导出。动作算法独立版本`physical_release_clearance_v3`，不把unknown改True。
- 双壶仅新normal首帧前，按实际模型/object的freejoint地址互换指定两壶qpos7/qvel6；验证对象、尺寸、地址、quat、其他坐标不变并保存SHA。restore后重新取首帧，A/B、炉子K、语言、原父split及正式bank不改；新10相对新normal交接配对。
- 固定三任务first20，durable账本≤60普通／360次10，初始化失败与中断计入；已消费槽缺metadata只补失败记录，不退款重试。旧003的221ten＋75normal和180 raw按原SHA引用复用，不回放/重做资格。新来源逐项绑定算法/recipe/置换；显式两root、新schema与实际计数，旧严格默认不放宽。一次准备共享稳定stat哈希上下文、≤30秒进度，训练只简化日志，不改变完整采样/RNG状态。
- 一条`generate`完成新导出→合并引用→retention与task-control两索引；新入口消费039索引并复用**同一038网络、损失、训练/adapter/eval**。新增合格train10为0则在模型加载前拒绝训练；有新增即按实际量继续，无每任务N/MVP门槛。038模型、正式评分、旧035/036/038工件保持。

受影响CPU/fake **277通过、0失败/错误，2跳过**：[JSON与两条完整测试命令](../evidence/039_cpu_fake.json)、[文件组JUnit](../evidence/039_cpu_files.junit.xml)、[模型组JUnit](../evidence/039_cpu_model.junit.xml)。两项跳过均因本机Windows无真实文件symlink权限，模拟symlink/解释器保留回归通过。合成执行记录→export/merge/两索引→原038微型C0/C1训练、adapter严格身份与fake eval合同已接通，C0/C1观察顺序一致、compact日志前后模型tensor一致；独立审查2项Important已修复并定向复查闭合。初次同进程NumPy MKL/Torch出现OpenMP重复库错误，最终按真实worker架构隔离fake记录器及模型进程验证，原失败保留，未设置忽略开关或改依赖。

**完整运行命令模板**（本轮未执行）：Codex验收隔离部署后，先按[详细配置与部署说明](../../docs/task039_usage.md)填写三个JSON，保留原035 generation、旧003 export/036 index、原runtime/core/reporting/双bridge。下面占位路径须由部署者替换，两个worker环境均须安装同一新方法包。

```bash
set -e
source /path/to/miniconda3/etc/profile.d/conda.sh
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task039-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/accepted-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-sog10-runtime.json
cd "$LNA_CODE"
conda activate EXISTING_NATIVE_ENV
python -m egrs.coverage039 generate --config "$LNA_ROOT/configs/task039/generation.json" --out "$LNA_ROOT/data/coverage039/production-001"
conda activate EXISTING_OFT_ENV
for arm in c0 c1; do
  python -m egrs.coverage039 train --arm "$arm" \
    --config configs/task_control/task_control_factorization.json \
    --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
    --index-dir "$LNA_ROOT/data/coverage039/production-001/indices/task_control" \
    --output-dir "$LNA_ROOT/runs/task039-$arm-train-001"
done
for arm in c0 c1; do
  python -m egrs.coverage039 eval --arm "$arm" --mode run \
    --config "$LNA_ROOT/configs/task039/evaluation.$arm.json" \
    --out "$LNA_ROOT/runs/task039-$arm-eval-001"
done
```

显式训练续跑`--resume`、各环境安装和输出解释均见同一[运行文档](../../docs/task039_usage.md)，不自动重开生产/退款。预算已批准：60普通＋360次10，两组原SOG10新初始化各1000、reference合计≤18048/student≤49120，新模型各10/00各90共360；保持原评分/H520/chunk8/seed7/全视频，只用固定末1000。

实现/受影响CPU-fake交付100%，**待Codex验收**；真实生成/标签与索引生产、真实模型/仿真/训练/eval、服务器部署均0%，无自动merge或删除。无新增设计硬阻塞；真实成功率和覆盖仍待用户运行。下一步：**Codex**审查并隔离部署/填写实际路径，**用户**亲自启动已批预算内作业，**Codex**审查产物；不能把软件验证当真实恢复成功。
