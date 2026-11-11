# 036：三池训练与同底座原策略动作参考

按[036工单](../collaboration/tasks/036_policy_retention_distillation.md)，复用已验收035 `ac2ec431`，在独立036分支/PR增加原策略保持实验。当前只交软件与CPU/fake；真实索引准备、参考前向、训练和新模型评测由用户启动。035真实10合规54.44%/00官方73.33%及其全部工件保持，不据此保证036效果。

## 数据与入口

新模块 `egrs.retention` 使用三池：

| 池 | 来源 | train/dev轨迹或来源 | 原父组 |
|---|---|---:|---:|
| ten专家 | 003现有合格10 | 161/60 | 54/20 |
| fresh普通观测 | 003现有合格正常重放 | 55/20 | 55/20 |
| raw普通观测 | 原九任务各自然前20，共180父示范 | 136/44 | 136/44 |

`cli index`只绑定JSON/观测shape/语言及文件SHA，输出 `sources.json/rows.jsonl/report.json`；不生成、渲染/恢复环境或调用参考策略，不导出整库图片。原180先按既定逻辑验证分组，再与003所有parents匹配，不重分组或根据035模型成败筛来源。

ten沿原专家chunk8/尾mask，排除audit-only hold。fresh/raw只惰性读取同一行双图＋8维proprio及完整原指令，不读取原actions/states/未来帧作为条件或参考目标。raw独立标记 `official_recorded_observation`，不复制fresh动作时序或物理资格声明。raw双图各旋转180°一次，本体按固定原统计归一化并clip一次；其余JPEG/缩放/crop/processor沿原OFT helper。

raw/fresh同父必须同split，不当成独立父演示；物理祖源未知仍unknown。prefix为前 `max(1,ceil(T_obs/3))` 当前观测，不是由谓词筛“A未完成”。full箱包含prefix，训练有放回抽样不计新数据。

## 参考、损失和预算

从原完整合并SOG10重新注入新语言q/k/v/o native LoRA（r16/alpha32/dropout0），不继续035 adapter。底座/vision/projector/action head/proprio冻结，仅新LoRA可训练。

普通观测目标取原同底座策略：暂时旁路全部新增native LoRA residual，在no_grad/eval下复用 `training_prediction` 得到连续归一化1×8×7 action head输出并detach。没有第二个7B，没有PEFT假接口、unnorm/clip/二值夹爪或文本解码。每更新全部8个参考在任何学生图建立前完成，finally逐模块恢复原training标志和LoRA enable；非重入checkpoint重算发生时学生LoRA保持启用。异常也恢复；保存/加载后默认启用LoRA，评测仅一个适配VLA。

原策略可能保留原有错误，参考不是完美专家。输入仅RGB/proprio/完整指令，pool/time-bin/父组/真值不进入processor或策略。

| 固定配方 | 值 |
|---|---|
| 每更新 | 12ten＋4fresh-ref＋4raw-ref，micro1/accum20 |
| 普通每池 | 2prefix＋2full，task→父组→variant/当前窗口均衡 |
| 损失 | 各池独立按有效动作标量归一化，再`.50Lten+.25Lfresh+.25Lraw` |
| mask | ten沿原尾mask；普通参考8×7全部有效，不用专家尾动作 |
| 优化 | 1000更新，lr2e-5/warmup50/bf16/seed7/非重入checkpoint，无图像增强 |
| 保存/选权重 | 250/500/750/1000；固定末1000，不按dev/正式SR选点 |
| dev | ten固定≤256；fresh/raw各≤128（64prefix/64full），四次 |
| 参考硬预算 | train≤8000，dev≤1024，总≤9024单观测前向 |

`ReferenceBudget`在调用前持久化消耗，失败也计数；resume不可回退。恢复只允许原output目录中的同run checkpoint，读取原ledger，不能换新目录绕过预算。若恢复时先前失败已消耗额外预算，达到上限就停止，不自动追加许可。日志含三池L1/weighted、update百分比、实际参考次数/预算、elapsed/ETA及采样/有效动作分母，loss不是SR。

学生1000×20=20000次曝光，较035的16000多25%；ten仍12000。参考额外前向也占计算量，不声称同耗时/同计算。

## 036身份和新评测

`task036-oft-adapter-v1`/group `policy_retention_distillation` 绑定三份索引字节、参考视图/原底座、配方、参考次数、原组件/统计、LoRA参数形状和adapter字节；最终评测只接update=1000。原030/035身份读取保持。

036不接受旧035结果继承，没有continue-from。新模型原10/00各90必须全新执行，同一最终adapter、原来源/状态/输入/seed7/chunk8/H520、原旧/新bridge及双向proxy协调、原端点/评分与全视频/query/actions/raw保持。

运行中只读本单元完成ledger更新n/180及10/00百分比，正式SR标待核验，不每个单元重扫所有历史raw。退出时仅一次完整原reader核验（126调用覆盖180），显示验证百分比，再生成原10二元合规/00官方summary/report；同时保留原22/90、78/90及035的49/90、66/90参照，口径不混。

完整结果已写后policy.close警告仍单列 `cleanup_warning`，最终报告与progress可完成，软件退出仍非零并传播该异常；不能称无错退出或为清理警告重跑。若推理/物理/证据/ledger出错，保留 `execution_error/ledger_warning/verification_error`，主执行错误优先，未完成不标completed，不把技术错误变模型失败。旧035的-15事实不倒改，本轮不为它启动真实复现。

## 文件配置及常见命令

配置：[data.example.json](../configs/retention/data.example.json)、[固定训练配方](../configs/retention/policy_retention_distillation.json)、[评测模板](../configs/retention/evaluation.example.json)。由Codex在独立 `configs/retention036-*` 中绑定已有实际路径/SHA；模板不是已部署证据。不重下数据、模型或升级环境。

固定依赖仍是原SOG10 `638918f3d1c2e43a39a8a20772bdb8b91835e4b7`、干净OFT `e4287e94541f459edc4feabc4e181f537cd569a8`、原core `d8541ef4`、旧bridge `ac130177`及034报告包。原统计key=`libero_10_no_noops`，SHA=`6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3`。

下面是普通shell/conda/python入口，路径由Codex替换后交用户。本轮均未执行真实索引/参考/训练/评测：

```bash
source /absolute/path/to/anaconda3/etc/profile.d/conda.sh
conda activate /absolute/path/to/existing-oft-worker-env
python -m pip install --no-deps -e /absolute/path/to/method036

# 绑定既有数据的观测索引，不创建新仿真或调用教师。
python -m egrs.retention.cli index \
  --config /absolute/path/to/data036.local.json \
  --output /absolute/path/to/data/retention036/index-001

# 用户启动唯一一组训练。--checkpoint是原完整SOG10，不能填035 adapter。
python -u -m egrs.retention.training \
  --config /absolute/path/to/method036/configs/retention/policy_retention_distillation.json \
  --export-dir /absolute/path/to/data/retention036/index-001 \
  --output-dir /absolute/path/to/runs/retention036-train-001 \
  --benchmark-root /absolute/path/to/accepted-core-d8541ef4 \
  --oft-root /absolute/path/to/clean-oft-e4287e94 \
  --checkpoint /absolute/path/to/complete-SOG10-638918f3
```

如确需恢复，同一命令追加 `--resume /absolute/path/to/runs/retention036-train-001/update-000250`（或原run其他合法保存点），output-dir仍是原run；035 checkpoint拒绝。不要为了恢复修改索引/配方或复制ledger到新run。

训练结果回来后Codex绑定固定末 `update-001000` 的新036评测配置。实际eval-env仍原环境，必要方法包部署到新代码目录；不改变环境/权重：

```bash
conda activate /absolute/path/to/existing-libero-eval-env
python -m pip install --no-deps -e /absolute/path/to/method036

# 纯文件计划，可由部署方准备；不做模型/物理预检。
python -m egrs.retention.evaluation plan \
  --config /absolute/path/to/eval036.local.json --out /absolute/path/to/new-eval036-plan.json

# 用户启动全新180，不能继承035成功/失败。
python -u -m egrs.retention.evaluation run \
  --config /absolute/path/to/eval036.local.json --out /absolute/path/to/runs/retention036-eval-001

# 按需独立重验；正式run结束已生成报告，不自动再扫一遍。
python -m egrs.retention.evaluation report \
  --run /absolute/path/to/runs/retention036-eval-001 --out /absolute/path/to/new-retention036-report
```

CPU/fake软件验证及限制见[036交付回复](../collaboration/responses/036_round1.md)。真实参考耗时、显存、1000更新和SR效果仍待用户执行；零新增仿真，原003/004和全部历史数据/失败/权重保留，无自动merge或清理。
