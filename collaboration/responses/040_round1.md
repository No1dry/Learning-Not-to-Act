# Task040 R1：train父源覆盖软件交付

2026-11-10，X。代码基线为已验收PR14 **`113ded21434a06e2cdc156e5d6283a11c3f15488`**，同步main工单`3d92223`的本地merge `fef4a95`；未merge依赖显式保留。首实现`ea3c48b95ed538abdd0e2c5c5beabac32fc86657`，**最终实现/修复commit `0f24e9d46bfbc33edd001facf19d2c1c40ffc166`**，新PR交付，不自动合并。

- 新`egrs/coverage040/plan.py`从原035配置与固定039索引绑定生成**三任务各demo_20..39共60候选**；原180父组/split不变，seed7已知alias组件继承旧锚点、冲突拒新、只选新增train自然代表，新dev仅封存元数据。三字段配置支持环境变量展开，未解析变量/占位符拒绝。
- `generation.py`复用039真实控制、双壶仅normal初态freejoint置换、V2准入与5帧释放；正常1次/3起点×2桥、60/360、H520保持。040 plan/ledger/sidecar/recipe独立绑定，失败和中断不退款；新输出拒覆盖，不提供隐式生产续跑。独立审查发现的**父中断时worker可能继续写**已修复：040 launcher先停止并wait，再恢复/封存；无法确认清理则拒封存。原039实现不改。
- `index.py/data.py`引用冻结039，旧源对象及rows/labels/pairs原字节前缀保留；仅追加合格新train ten及pair。**新normal只在独立pair_sources，无主池/pseudo-fresh样本**，各端读自己的实际出站动作；缺pair只记缺口，不踢合格BC。原105fresh/180raw及全部旧dev记录/稳定选择键/顺序严格保持，共享新的040外层identity与真实计数，旧入口不放宽。
- `pipeline.py`一条生产命令完成候选→生成→增量索引，不启动训练。`training.py/__main__.py`只允许本轮C1，复用原038固定1000 preset、网络/loss、12+4+4及pair两端、save/resume/adapter与正式180评测；没有新合格train父组ten时加载模型前拒训，无N/MVP门槛。原SOG10新初始化，不续039，不加S/C0。

定向CPU/fake **162通过、0失败/错误/跳过**：[完整命令/JSON](../evidence/040_cpu_fake.json)，[来源43](../evidence/040_cpu_sources.junit.xml)、[未改数据组77](../evidence/040_cpu_data.junit.xml)、[模型/接线42](../evidence/040_cpu_model.junit.xml)。合成实际动作记录→040导出/索引→原C1微型训练，真实seed7抽到新pair，每更新22学生/8参考，中断恢复全tensor等值，严格新index/adapter与末1000评测合同通过。独立审查0 Critical/1 Important已修复且定向复查闭合；原失败和测试红灯保留，未以真实效果冒称通过。

**完整常用命令**（本轮均未执行）：Codex验收隔离部署后，按[详细运行文档](../../docs/task040_usage.md)安装到既有native/OFT/worker环境并填配置；生成JSON从原035/039绑定推导，eval JSON复制原039 C1实际配置、只换本轮末1000 adapter。下列路径/环境名由Codex替换：

```bash
set -e
source /path/to/miniconda3/etc/profile.d/conda.sh
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task040-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/unchanged-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-original-sog10-runtime.json
cd "$LNA_CODE"
conda activate EXISTING_NATIVE_ENV
python -u -m egrs.coverage040 generate \
  --config "$LNA_ROOT/configs/task040/generation.json" \
  --output "$LNA_ROOT/data/coverage040/production-001"
conda activate EXISTING_OFT_ENV
python -u -m egrs.coverage040 train \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/coverage040/production-001/indices/task_control" \
  --output-dir "$LNA_ROOT/runs/task040-c1-train-001"
python -u -m egrs.coverage040 eval --mode run \
  --config "$LNA_ROOT/configs/task040/evaluation.c1.json" \
  --output "$LNA_ROOT/runs/task040-c1-eval-001"
```

独立环境安装、配置展开/原eval复制、完整`--resume`命令、nohup/日志与精简进度模板均在[运行文档](../../docs/task040_usage.md)。父生产进程及train/dev共用稳定stat哈希上下文；独立native worker仍首次严格复验原HDF/统计，未采用跨进程免验缓存。缺字段/来源真实性错误在生产前明确拒绝，不从40以后补；真实覆盖和物理多样性仍未知。

已批准预算：≤60普通＋360次10、单C1 1000（reference≤9024/student≤24560）、原九任务新模型10/00各90共180；算法、评分、全视频及全部035/036/038/039权重/数据/失败不变。**实现/定向测试交付100%，待Codex验收；部署、真实元数据/标签/索引生产、真实模型/仿真/训练/eval全部0%。** 无新增设计硬阻塞，无自动merge/删除。下一**Codex**审查并隔离部署/填实际命令，**用户**亲自启动已批作业，**Codex**审查结果；软件交付不代表SR提升。
