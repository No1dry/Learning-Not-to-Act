# Task038：037-v2 使用与交付

本入口实现单个原SOG10底座上的C0/C1任务上下文学习。依赖已验收036 PR11固定`205d6530e1ba389f74166a2e9520a3db7ae0edbf`；新PR包含该依赖实现并合入最新main文档，不自动合并任何GitHub PR。035/036训练、权重、报告、视频、原失败和旧037审阅保留。

**本页命令均是待授权模板，不是本轮已启动或已部署的实验。** 两组1000更新、参考最多18048、学生最多49120、正式新模型360条的预算尚待用户批准。真实文件索引也由用户在批准后启动；本次只运行合成CPU/fake测试。

## 文件与环境

- 新方法包：`egrs/task_control/`。所有训练和评测都调用`oft.prediction`，交换上下文只调用`oft.decode`，不额外调用VLA。
- 固定训练配方：`configs/task_control/task_control_factorization.json`。
- 评测配置模板：`configs/task_control/evaluation.c0.example.json`、`evaluation.c1.example.json`。替换所有占位路径，保持各自arm与最终adapter匹配。
- 模型、原始统计、官方OFT commit与036相同：SOG10 `moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7`；OFT源码`e4287e94541f459edc4feabc4e181f537cd569a8`。复用现有本地模型，新增LoRA和小模块从头初始化。
- 复用现有OFT环境、固定eval core及034 reporting依赖，不升级依赖。索引读取现成JSON/HDF结构及SHA，不读取图像像素、生成仿真或推理标签。
- 原指令prefix通过tokenizer offset与processor实际token ID核对；固定官方默认加载链使用Fast tokenizer。自定义慢tokenizer或不一致的offset明确拒绝，不能猜文本位置；本轮未实例化真实tokenizer/模型。
- Codex验收后的部署须让训练解释器和原runtime中实际policy-worker解释器都能导入同一新方法包；worker会隔离环境变量，不能仅依赖父进程临时PYTHONPATH。下面的`pip install --no-deps -e`是**未来部署模板**，本轮未执行、不会修改已冻结035/036运行目录。

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task038-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/accepted-core-d8541ef4
export LNA_RUNTIME=/path/to/original-sog10-runtime.json
cd "$LNA_CODE"
python -m pip install --no-deps -e .
python -m egrs.task_control --help
```

若policy worker使用另一既有环境，由Codex在该解释器中单独完成同一方法包部署并核对来源，不改变原模型、core或环境bridge。正式运行仍用原runtime JSON中的执行设置：seed7、chunk8、H520、原双图/原完整指令、8维本体。传入训练的`--runtime`就是评测使用的原完整SOG10 runtime，而非另造简化checkpoint配置。

## 一次文件索引（批准后由用户运行）

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task038-ACCEPTED_COMMIT"
cd "$LNA_CODE"
python -m egrs.task_control index \
  --generated-export "$LNA_ROOT/data/trajectory035/generated-003/export" \
  --retention-index "$LNA_ROOT/data/retention036/index-001" \
  --out "$LNA_ROOT/data/task038/index-001"
```

输出新目录的`sources.json`、`labels.jsonl`、`pairs.jsonl`、`report.json`、`identity.json`；已有目录拒绝覆盖。labels从父源active谓词绑定的既有facts计数0/1/2，不取official列表前两项；raw标签为缺失。缺标签mask，不改变正式二元结果。

pair取同父normal交接帧与ten0，分别保留自己的真实outgoing动作与尾段mask；比较实际audit记录state，排time0和真实rewind layout机器人索引后，非机器人差≤1e-8且机器人确有变化。还核验来源、split、语义、环境、释放/空手及原约束。构造hash不能代替记录比较；confirmation不进训练。report逐九任务/split记录候选、通过与剔除原因。无pair仍保留原BC源；零有效pair明确数据不可用、训练拒绝，不放宽或自动补数据。

新身份绑定原036索引、所有源JSON/HDF及audit/lineage SHA和labels/pairs字节。索引不会成为可迁移复制的数据包：源文件仍须存在于已部署位置。移动/修改源路径或内容需明确重新准备新索引，不能编辑已绑定文件后沿用旧identity。

## 两arm训练（批准后，由用户分别启动）

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task038-ACCEPTED_COMMIT"
export LNA_CORE=/path/to/accepted-core-d8541ef4
export LNA_RUNTIME=/path/to/original-sog10-runtime.json
cd "$LNA_CODE"
python -m egrs.task_control train --arm c0 \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/task038/index-001" \
  --output-dir "$LNA_ROOT/runs/task038-c0-train-001"
python -m egrs.task_control train --arm c1 \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/task038/index-001" \
  --output-dir "$LNA_ROOT/runs/task038-c1-train-001"
```

两组相同新LoRA/小模块初始化、三池与pair序列、父划分、expert/reference和标签；均不加载035/036成品adapter。每更新12ten＋4fresh-ref＋4raw-ref，再加一个pair的两端，总22学生观测。参考8次先于学生图计算，旁路全部新增LoRA/任务上下文/残差及其hook；不加载第二个底座。

`L_main=.5 BC_ten+.25 ref_fresh+.25 ref_raw`，计数CE按出现类均值。C0为`main+.1 count+.1 self`；C1为`main+.1 count+.05 self+.05 swap+.01 align`，align为128维归一化MSE、epsilon1e-6。swap仅换z，接收端H/proprio/真实动作/mask不变，两个z都有梯度。辅助计数不用于硬路由或停止；无GT/pair/时间/任务ID策略输入。

固定1000、lr2e-5、warmup50、bf16、每250保存/dev，选择末1000；不按测试SR挑checkpoint。每组参考≤9024；学生train22000＋dev≤2560＝≤24560。dev每次普通≤512和pair≤64，不足用全部，不再补观测。日志包括进度、pool/count/self/swap/align、dev计数分组和配对/置零z诊断、ETA/显存；loss不是SR。

### 显式续训模板

```bash
# 与原arm、原索引、原输出目录和原budget账本相同。
python -m egrs.task_control train --arm c0 \
  --config configs/task_control/task_control_factorization.json \
  --benchmark-root "$LNA_CORE" --runtime "$LNA_RUNTIME" \
  --index-dir "$LNA_ROOT/data/task038/index-001" \
  --output-dir "$LNA_ROOT/runs/task038-c0-train-001" \
  --resume "$LNA_ROOT/runs/task038-c0-train-001/update-000250"
```

checkpoint严格保存全部LoRA/新模块及逐tensor SHA、base/统计/arm/recipe/index身份、优化器、调度器、Python/NumPy/Torch/CUDA RNG、三池与pair sampler和双budget。缺/多/错形/错dtype/错hash拒绝。

预算在前向前落盘；若中断前已消费的durable账本超前于所选checkpoint，**拒绝精确续跑**，不退款或重置计数。不能擅自删账本继续；交Codex集中说明恢复点与已消费量后，再决定是否另有获批恢复预算。本轮不承诺任意中间位置无损恢复。完成1000的目录拒绝再续训。

## 同一adapter的10/00评测（批准后由用户启动）

先由Codex将两个example复制到新配置目录，填入原六10、原六00 composite、新三10/00来源、固定core/reporting/旧bridge root、同一原runtime；arm各指自己的`update-001000`。保留旧所有配置和run。

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_OFT_ENV
export LNA_ROOT=/path/to/deployment-root
export LNA_CODE="$LNA_ROOT/code/task038-ACCEPTED_COMMIT"
cd "$LNA_CODE"
# 可选文件计划；无模型/仿真。新输出不得存在。
python -m egrs.task_control eval --arm c0 --mode plan \
  --config "$LNA_ROOT/configs/task038/evaluation.c0.json" \
  --out "$LNA_ROOT/configs/task038/plan.c0.json"
python -m egrs.task_control eval --arm c1 --mode plan \
  --config "$LNA_ROOT/configs/task038/evaluation.c1.json" \
  --out "$LNA_ROOT/configs/task038/plan.c1.json"
# 以下为真实作业，必须另获预算并由用户启动。
python -m egrs.task_control eval --arm c0 --mode run \
  --config "$LNA_ROOT/configs/task038/evaluation.c0.json" \
  --out "$LNA_ROOT/runs/task038-c0-eval-001"
python -m egrs.task_control eval --arm c1 --mode run \
  --config "$LNA_ROOT/configs/task038/evaluation.c1.json" \
  --out "$LNA_ROOT/runs/task038-c1-eval-001"
```

eval默认为文件`plan`模式，真实执行必须显式`--mode run`。每arm新执行10/00各90，合计两arm360；原正式来源/九任务/评分不变，全部视频和raw证据沿原runner保存。不能继承旧模型轨迹/分数，已有输出拒绝覆盖。worker工厂是`egrs.task_control.policy:make_policy`，当前帧自己算z并走与训练同一`oft.prediction`；无pair、标签或reference推理。

`summary.json`保留034二元10和00官方指标及完整性诊断；`report.md`标明038与arm，原始模型及035数值仅作历史参考。C1−C0才检验本轮约束包，不能将align/swap各自效果分开归因。未增强三任务仍是“已知任务、未见该任务10增强”的探索性迁移，不是未见任务zero-shot。

如需对已执行038生成独立报告（无模型、原目录不改）：

```bash
python -m egrs.task_control eval --arm c0 --mode report \
  --run-dir "$LNA_ROOT/runs/task038-c0-eval-001" \
  --out "$LNA_ROOT/reports/task038-c0-eval-001"
```

## 本轮软件验收

只运行受影响CPU/fake，测试在合成文件和微型网络上执行；未运行本页任何真实索引、训练或评测。命令与最终结果见[038回复](../collaboration/responses/038_round1.md)及[CPU/fake记录](../collaboration/evidence/038_cpu_fake.json)。软件验收不代表真实pair覆盖、训练收益、SR或新颖性已经验证。
