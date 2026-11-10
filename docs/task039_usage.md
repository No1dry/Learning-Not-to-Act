# Task039：教师收尾、双壶置换与覆盖恢复

本轮预算**已批准**：最多60次普通回放、360次10尝试，两组各1000更新；reference合计≤18048、student≤49120，两个新模型各10/00各90共360。实际生产、训练和评测仍由用户启动。X本轮只实现和CPU/fake测试，未执行这些真实步骤或服务器部署。

基于accepted038 PR13固定`5a6452ab73ee31cd1afbe1cdc08e88e2d963ac04`，新代码在`egrs/coverage039/`。038的网络、LoRA、z残差、计数、自用/交换/align系数、三池采样、原策略旁路、adapter和正式评分保持。039是新数据功能，不是038返修；旧035/036/038数据、失败、权重、视频和报告不覆盖。

## 部署及配置

Codex验收后部署**新checkout**，保留所有旧目录。复用现有OFT与native环境及原模型，不升级依赖、不下载新示范/模型。训练及runtime中policy-worker、generation配置中native-worker的解释器，均须能导入同一新方法包；不要只在父进程设临时PYTHONPATH。

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task039-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/accepted-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-sog10-runtime.json
cd "$LNA_CODE"
python -m pip install --no-deps -e .
python -m egrs.coverage039 --help
```

上面是后续部署模板，本轮未在服务器或既有环境执行。原SOG10 checkpoint/统计、官方OFT commit、core/reporting/双bridge与controller绑定继续使用原配置。

复制`configs/coverage039/generation.example.json`到新配置目录，替换占位值：

```json
{
  "format": "task039-coverage-recovery-config-v1",
  "generation_config": "/path/to/unchanged-original035-generation.json",
  "old003_export": "/path/to/deployment-root/data/trajectory035/generated-003/export",
  "old_retention_index": "/path/to/deployment-root/data/retention036/index-001"
}
```

`generation_config`是原035完整180父清单、原始演示root、统计和native绑定所在配置；不是旧002失败报告或正式eval bank。其native python入口保留venv symlink，不resolve成base解释器。039从原180中选择stove/mug_pudding/two_pots各demo0…19，不按模型成败筛选。父源、136/44划分与语言不变。

## 一条生产入口：生成→合并引用→两索引

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_NATIVE_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task039-ACCEPTED_COMMIT"
cd "$LNA_CODE"
python -m egrs.coverage039 generate \
  --config "$LNA_ROOT/configs/task039/generation.json" \
  --out "$LNA_ROOT/data/coverage039/production-001"
```

调用前在同一流程检查原JSON身份、221/75与原036计数/来源、文件存在性；不读取RGB做推理、不重判旧资格。之后每父普通一次、合格后3机器人起点×最多2桥接，成功起点不额外重试。初始化失败、中断也消耗slot；总量和逐task/split失败明细均与durable ledger对账。丢失metadata的已消费槽位只补拒绝记录，不重试或改为成功。

教师动作算法版本为`physical_release_clearance_v3`，**准入仍是原V2**。原生全目标已真才补收尾：固定实际EE anchor/姿态张手最多10步，必要时最多20步竖直撤离≤0.10m，再最多10步保持；原真实released连续5帧满足即停。全部控制和下一观测进入HDF，T动作/T+1观测，不附audit-only释放尾巴；新增≤40、总episode≤520，A/K回退、重抓、侵入或原违规仍失败。

仅two_pots新normal初始化互换实际对象自由关节qpos7/qvel6，核对类型/尺寸/地址/quat，其他坐标不变。真正restore后拍首帧并验证原A/B均false、炉K真；两壶名称、目标、标签和正式bank不变。new10相对**新normal交接帧**rewind，不与原state0伪配对。原始父HDF路径/文件SHA不改。

输出是全新目录；已有输出拒绝覆盖，不自动续跑/退款或无限追加生成。完成后有：

| 路径 | 内容 |
|---|---|
| `generated/` | 本轮60父源范围的实际新尝试、账本、HDF/audit/lineage、普通/10失败和export |
| `merged-export/` | 旧221ten＋75normal与实际新合格记录的引用合并；不复制大HDF、不创建可写hardlink |
| `indices/retention/` | 动态三池，原180 raw不变 |
| `indices/task_control/` | 同038语义计数、实际记录state配对和039身份 |
| `preparation_report.json` | 新增合格train10数量、训练是否可继续、路径、进度及hash文件/字节量 |

生成工件仅允许old003/new039两个明确root；原raw仍绑定其既有root。每源保留原资格、teacher、SHA和新增算法/transform来源。新release不能仅加一个format字符串把旧轨迹算新增。报告按任务/split/domain列尝试、成功、窗口、失败、实际新增与复用量，不保证三任务全部恢复。

同一次准备和两split构造共用canonical path＋稳定stat的哈希上下文，同一文件只算一次；变化拒绝。独立进程重新验证，不持久化“免校验通过”。source/attempt、文件字节及metadata/index阶段有≤30秒进度/百分比/耗时。子进程首次验证仍严格执行。

当`new_qualified_train10=0`时报告未恢复，039训练入口在加载模型前拒绝；不为凑N追加生成，也不训练与旧数据相同的一轮。有新增则按实际合格量继续，不另加每任务数量门槛。

## 同一038算法重新训练C0/C1

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task039-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/accepted-core-d8541ef4
export LNA_RUNTIME=/path/to/unchanged-sog10-runtime.json
cd "$LNA_CODE"
python -m egrs.coverage039 train --arm c0 \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/coverage039/production-001/indices/task_control" \
  --output-dir "$LNA_ROOT/runs/task039-c0-train-001"
python -m egrs.coverage039 train --arm c1 \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/coverage039/production-001/indices/task_control" \
  --output-dir "$LNA_ROOT/runs/task039-c1-train-001"
```

两组依次由用户启动；都从原SOG10新初始化，不续旧C1。相同新索引、seed7、采样顺序、22观测/更新、固定1000；参考各≤9024、student各≤24560。每250保存/dev且只选末1000，原dev512普通＋≤64pair上限不变。新增日志只输出紧凑采样计数，完整层级/RNG仍保存checkpoint，不每update打印巨型字典。

新保留索引用039独立kind/contract，旧038默认reader拒绝；策略输入和物理窗口仍与038兼容。adapter继续038 schema，**index_identity绑定039来源、置换、实际数量与标签/pair字节**。网络/损失没有换一套；正式eval仍用038共享predict。

显式恢复仍用同arm、原输出/账本与新索引：

```bash
python -m egrs.coverage039 train --arm c0 \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/coverage039/production-001/indices/task_control" \
  --output-dir "$LNA_ROOT/runs/task039-c0-train-001" \
  --resume "$LNA_ROOT/runs/task039-c0-train-001/update-000250"
```

原038的strict恢复及前向前记账保持：若已消费账本超前于checkpoint，明确拒绝精确续跑，不删除账本或自动补额度。生产中断同样保留已消费尝试与原始工件，不隐式重启。

## 新模型正式评测

Codex用`configs/coverage039/evaluation.c0.example.json`及c1模板，填原六10/00、新三10/00来源、固定core/reporting与双bridge，adapter各指向本轮`update-001000`；其余保持原协议。两模型各新180，不继承旧模型分数，所有九任务继续完整报告。

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task039-ACCEPTED_COMMIT"
cd "$LNA_CODE"
python -m egrs.coverage039 eval --arm c0 --mode run \
  --config "$LNA_ROOT/configs/task039/evaluation.c0.json" \
  --out "$LNA_ROOT/runs/task039-c0-eval-001"
python -m egrs.coverage039 eval --arm c1 --mode run \
  --config "$LNA_ROOT/configs/task039/evaluation.c1.json" \
  --out "$LNA_ROOT/runs/task039-c1-eval-001"
```

`--mode plan`为可选纯文件计划，不是正式作业前额外MVP要求；正式run本身绑定输入。评测模型只有当前双图/原完整指令/proprio，无teacher、真值路由或FINISH。10二元合规/00官方、H520/chunk8/seed7、原reader/双bridge-proxy与全视频不变；报告沿038算法schema，数据阶段由adapter/index身份区分。

## 本轮验证边界

仅受影响CPU/fake。合成记录器→真实文件export/merge/两索引→同038微型训练/严格adapter合同已接通，两arm观测顺序一致；compact日志前后所有训练tensor一致。两项独立审查Important已集中修复、对应复查闭合。

本机NumPy MKL与Torch同时执行SVD时存在OpenMP重复库错误，因此最终验证分记录器/文件组和模型组；端到端fake记录器在独立子进程运行，符合实际worker架构，未设置不安全的duplicate-lib忽略开关。没有改生产依赖或证明真实效果。完整命令、结果及未执行项见[039回复](../collaboration/responses/039_round1.md)与[测试证据](../collaboration/evidence/039_cpu_fake.json)。
