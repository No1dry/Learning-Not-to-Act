# 036 Round1｜三池原策略保持完整实现

2026-11-04，X。按[036工单](../tasks/036_policy_retention_distillation.md)直接交实现与定向CPU/fake，无先行方案或真实预跑。独立分支 `x/task036`，[独立036 PR11](https://github.com/No1dry/Learning-Not-to-Act/pull/11)，不更新/合并035 PR10。

基于已验收035 `ac2ec431aa7e1c3c7096baf978878d20ef458e9b`（实现 `918db35b`），已fetch最新main `3a26a7c` 并合入为 `c458a7d`。**036实现commit `8b9399a940b45db7e3089aaad9f25c6509fd7c5a`**。035尚未合入main，故本PR包含其未合并祖先；本次036增量从 `c458a7d` 查看，不把035主体当本轮重写。

软件实现100%；最终分进程定向CPU/fake **120/120通过（100%，0skip/error/failure）**。真实036参考前向/1000训练/新模型180评测本轮均0%，新增仿真0。035已完成的54.44%/73.33%、003/004父子工件与close-15警告保留，不重计分、不以软件测试冒称036效果。

## 数据与三池训练

新增 `egrs.retention`，不重构035主体。`data.build_index(config_path, output_dir)` 与 `RetentionDataset(export_dir, split=None, pools=None)` 封存三份索引 `sources.json/rows.jsonl/report.json`：

| 池 | train/dev来源 | train/dev父组 | 行为 |
|---|---:|---:|---|
| ten | 161/60 | 54/20 | 原003合格10、chunk8/尾mask与原归一化专家动作 |
| fresh | 55/20 | 55/20 | 原003同一时刻普通观测、完整原指令，不用普通专家动作 |
| raw | 136/44 | 136/44 | 原九任务180父示范全部保留，仅同一行双图/本体 |

原180先按原逻辑验证/分组并与003 parents对照，source/group/split/语言/映射/SHA保持；不能按035成败过滤raw。fresh/raw同父同split，合并父组不重复算独立演示，祖源unknown仍unknown。

raw两图各旋转180°一次、同一行8维proprio按原统计归一化/clip一次；JPEG/缩放/crop/processor仍原OFT helper。raw单列 `official_recorded_observation` 和仅观测的basis，不照搬fresh T+1/T动作时序或物理资格声明。索引只读shape/语言/文件身份，普通item只惰性读取当前观测，不读actions/states/未来帧。模型item仅images/proprio/instruction；ten另外有离线动作target/mask，训练前 `_sensors` 也明确排除目标/池/父组/真值。

`training.ThreePoolSampler` 固定每更新12ten＋4fresh＋4raw，各普通池2prefix/2full。task→父组→variant/窗口均衡；prefix为前 `max(1,ceil(T_obs/3))`，不是谓词标签，full自然包含prefix。`batch_weights`预取本更新各池有效标量分母，再 `.50Lten+.25Lfresh+.25Lraw`；ten尾mask保持，普通参考完整8×7有效，不固定平均12个不同尾长或增加普通专家loss。

训练从原SOG10新注入q/k/v/o native LoRA r16/alpha32/dropout0开始；不加载035 adapter/优化器。其他参数冻结，micro1/accum20、bf16、lr2e-5/warmup50/seed7、非重入checkpoint、无图像增强，固定1000更新。保存250/500/750/1000，固定末1000评测，不按dev或正式SR选点。学生20000次曝光比035多25%，ten仍12000，不称同计算量。

## 同底座参考与预算

`reference.shared_base_reference` 暂时禁用所有新增native `LoRALinear.enabled` residual，只走原base_layer；no_grad/eval，逐module保存并finally恢复training标志及每个LoRA enable，原requires_grad/梯度/优化器不改。`reference_prediction`复用 `training_prediction`，返回detach/clone的有限1×8×7连续归一化动作，未unnorm/clip/二值夹爪/解码。不是PEFT或第二个7B。

每更新8个参考全部先于任何学生图；参考退出后学生LoRA已启用，checkpoint重算不会取到旁路状态。原vision/head/projector等冻结模式不被root.train(True)错误恢复。异常路径、nested flags、checkpoint梯度及加载后默认启用均有tiny回归。参考可能保留原策略错误，不是完美专家，仅训练/dev使用；评测只有一个适配VLA。

`ReferenceBudget`在forward前持久化消耗：train≤8000、dev≤1024、合计≤9024，失败亦计数。dev四次，每次ten≤256、fresh/raw各≤128（64prefix/64full）。036 resume仅允许checkpoint所在原output目录，原ledger取max且不回退，不能换新目录绕预算；达限直接拒绝，不自动追加。日志分三池loss、weighted、update百分比、有效标量、参考实际/预算、elapsed/ETA，loss不称SR。

## 新身份、加载与评测

`task036-oft-adapter-v1`/group `policy_retention_distillation` 绑定三份索引SHA、配方/参考视图/原底座/参考计数、原统计/组件、LoRA形状与adapter字节；参考视图是 `shared_frozen_base_without_added_lora`。读取纯stdlib，不为计划加载模型。共享OFT只加native enable和036严格身份分支；030/035默认读取保持。restore/attach默认启用LoRA，不把参考旁路带到评测。

`retention.evaluation`使用独立schema/group，复用原035人口验证的显式参数、严格双bridge/proxy协调、原 `_run_task`、原archive/query/actions/video reader及034/00评分。原035 GROUP/validator未全局改，未复制评分器。036无continue-from、拒绝继承035结果，原九任务10/00各90全部新执行，同一新末1000 adapter、原来源/初态/输入/端点/seed7/chunk8/H520和全视频不变。

每单元只读本单元完成ledger更新n/180与两条件百分比，不做逐单元历史全量reader扫描。退出仅一次正式完整核验（126 reader调用覆盖180），显示验证百分比，最后打印两类正式SR并把progress标completed；没有自动第二次完整report。报告另列原22/90、78/90与035的49/90、66/90参照，口径不混。

close警告在全部结果写出后仍捕获为 `cleanup_warning`，完整报告/完成进度可保存，软件仍非零传播该异常，不称无错退出。推理/物理/证据/未完成错误不吞；final ledger IO也受保护，单列 `ledger_warning` 并优先保留主执行错误。软件退出状态与模型完成分别记录；坏证据/缺失仍技术未解决，不能填模型0。

## 定向CPU/fake证据

| 最终独立进程 | 结果 | 覆盖 |
|---|---:|---|
| data | 16通过，1.65秒 | 三池/父split、same-row、一次变换/prefix、普通不读states/actions、身份篡改 |
| reference＋training及受影响旧训练 | 53通过，6.59秒 | 新参考12/训练16＋原共享13/035训练12；模式/梯度/checkpoint、预算、池损失、严格resume/旧身份兼容 |
| evaluation及受影响旧评测/桥接 | 50通过，47.00秒 | 新036七项、原035 reader/双bridge/proxy；新180、一policy、reader仅最终一次、实际reader坏视频拒绝、close/推理/ledger错误 |
| 保存→加载→评测链 | 1通过，7.20秒 | 明确合成998完整状态→实际tiny CPU两更新999/1000→严格保存/attach→全新180 fake队列 |
| 合计 | **120通过，0skip/error/failure** | 无真实模型/仿真/数据作业 |

链测试的前7984 train/768 dev调用是明确记录的合成fixture历史，不是真实教师前向；实际只做两次tiny CPU优化，最后train8000/dev832/total8832是fixture计数。它验证末1000身份/字节/接口，不声称真实1000训练或9024参考已跑。

最终命令在036工作目录，四行分别独立进程：

```powershell
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_retention_data.py -q --tb=short --show-capture=no --basetemp=.work/task036-final-data --junitxml=.work/task036-final-data.xml

& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_retention_reference.py tests/test_retention_training.py tests/test_augmentation_training.py tests/test_trajectory_training.py -q --tb=short --show-capture=no --basetemp=.work/task036-final-training --junitxml=.work/task036-final-training.xml

& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_retention_evaluation.py tests/test_trajectory_evaluation.py tests/test_trajectory_environment_dispatch.py tests/test_trajectory_proxy_transition.py -q --tb=short --show-capture=no --basetemp=.work/task036-final-evaluation --junitxml=.work/task036-final-evaluation.xml

& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_retention_end_to_end.py -q --tb=short --show-capture=no --basetemp=.work/task036-final-chain --junitxml=.work/task036-final-chain.xml
```

三个CLI help均exit0；最终暂存diff whitespace检查通过；独立窄审查提出的跨目录resume预算、普通clip parity及ledger主错误覆盖已修，未发现剩余已证实阻断。开发阶段新功能红灯、一次Windows高频原子文件占用/tmp遗留与fixture缺protocol整合失败XML全部保留，未改core/加环境绕过或冒称旧命令通过；上表仅最终新目录分组结果。不跑全库/多平台/发布级测试，没有额外真实warmup/MVP。

## 配置、命令和交付边界

完整命令与依赖：[retention036.md](../../docs/retention036.md)。模板：[data](../../configs/retention/data.example.json)、[固定训练配方](../../configs/retention/policy_retention_distillation.json)、[eval](../../configs/retention/evaluation.example.json)。原SOG10/OFT/core/旧bridge/034依赖复用，无新下载/升级；统计key `libero_10_no_noops`、SHA `6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3` 严格绑定。

Codex在新隔离目录绑定实际源/索引/配置后交用户普通命令，例如：

```bash
source /absolute/path/to/anaconda3/etc/profile.d/conda.sh
conda activate /absolute/path/to/existing-oft-worker-env
python -m pip install --no-deps -e /absolute/path/to/method036

python -m egrs.retention.cli index --config /absolute/path/to/data036.local.json \
  --output /absolute/path/to/data/retention036/index-001

python -u -m egrs.retention.training \
  --config /absolute/path/to/method036/configs/retention/policy_retention_distillation.json \
  --export-dir /absolute/path/to/data/retention036/index-001 \
  --output-dir /absolute/path/to/runs/retention036-train-001 \
  --benchmark-root /absolute/path/to/accepted-core-d8541ef4 \
  --oft-root /absolute/path/to/clean-oft-e4287e94 \
  --checkpoint /absolute/path/to/complete-SOG10-638918f3
```

本轮未执行上述真实命令。训练结果回来后Codex固定新update1000再给原180的新评测命令；036不能继承035分数，指南含plan/run/report完整示例。

未覆盖实际GPU显存/耗时、真实参考数、1000更新收敛或SR改善；不承诺00恢复且10必保。下一步执行者 **Codex**：建议式集中审查、准备来源索引/新配置并隔离部署、交准确常用命令；**用户**亲自启动唯一真实训练及新180评测。本轮实现100%、真实训练/新模型eval0%，新增仿真0。原数据/split/评分/035权重与003/004/原失败和open日志事实保留，无自动merge或清理，待删=[]。
