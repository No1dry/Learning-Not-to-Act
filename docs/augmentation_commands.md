# 030 v2：数据导出、两组续训与普通 adapter 评测

本页是交付入口，真实阶段由用户另行启动。本轮仅做 CPU/fake 软件验证；
没有下载新数据/权重、真实 HDF 导出、仿真恢复、训练或模型评测。
正式机器路径由 Codex 部署填写，尖括号为占位，不可原样运行。

## 固定依赖与文件

- 本方法 PR：安装 `learning-not-to-act-augmentation`，不依赖旧 selector PR。
- 原评测 core：[LIBERO-Remain@d8541ef4](https://github.com/No1dry/LIBERO-Remain/tree/d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9)。
  使用独立 checkout，不 merge PR14，不修改冻结目录。`core_files.json` 校验97个 Python 文件；
  允许文档不同，不允许静默换源代码。
- 034：独立报告 PR 的 `libero_remain_reporting`；最终交付 SHA 见回复030。
  `reporting_files.json` 固定报告包字节，方法库不复制评分器。
- 官方 [OpenVLA-OFT@e4287e94](https://github.com/moojink/openvla-oft/tree/e4287e94541f459edc4feabc4e181f537cd569a8)。
- 已合并的 [SOG10@638918f3](https://huggingface.co/moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10/tree/638918f3d1c2e43a39a8a20772bdb8b91835e4b7)：
  需要完整权重、processor/tokenizer、dataset_statistics、原 action head 与 proprio projector sidecar。
  不是重新套发布 LoRA，也不能只取 VLM 权重随机初始化 head。
- 原始普通演示来源：[LIBERO-datasets@147fa5eb](https://huggingface.co/datasets/yifengzhu-hf/LIBERO-datasets/tree/147fa5eb607bb696dd922c3518084a90954cd2f3)。
  已有20任务200来源/160:40复用；九任务最多新增180仅为候选，不能假称已搬运/验证。
- 原90初态、构造/回放审计、旧六 manifest/replay、新三 composite sources、冻结 SOG10 runtime
  继续从已有正式基线引用。旧六保留 legacy endpoint，新三保留 nine-mask10；统一034报告，
  不补建初态或重跑 baseline。C只取0/3/6/9，不能称全90结果。

数据字段、完整来源清单、封存旧 split、局部证据格式和回退见
[augmentation_data.md](augmentation_data.md)。模板中的空清单和占位不代表数据已齐备。

## 环境与安装

复用已具备官方 OFT 依赖的独立训练/模型环境与原 LIBERO 仿真环境，避免升级冻结环境。
可在隔离克隆的环境中安装本方法包；训练使用官方环境的 torch/transformers/timm 等版本。
本项目没有另写一套未经验证的 GPU 依赖组合。普通导出只需 numpy/Pillow/h5py。

```bash
source <conda-install>/etc/profile.d/conda.sh
conda activate <isolated-oft-environment>
python -m pip install --no-deps -e <method-checkout>
```

评测主进程在原 LIBERO 环境运行，OFT 子进程解释器来自原 `base_runtime.runtime.python_executable`。
**两个环境都安装本方法包**；core 的子进程会重设 PYTHONPATH，单靠 shell 的 PYTHONPATH 不能代替安装。
034可通过配置的目录读取，无需把 benchmark main 安装到覆盖冻结 core 的位置。
保持已有 `LIBERO_CONFIG_PATH`、`MUJOCO_GL=egl`、`PYOPENGL_PLATFORM=egl` 和离线模型设置。

## 一次数据导出

```bash
source <conda-install>/etc/profile.d/conda.sh
conda activate <data-environment>
cd <method-checkout>
python -u -m egrs.augmentation.export \
  --manifest <bound-ordinary-demo-manifest.json> \
  --base-inventory <original-200-source-inventory.json> \
  --evidence <trusted-local-evidence.json> \
  --output <new-export-directory>
```

`--evidence` 可省略，不可信/缺失增强证据回退 RAW并报告。需局部恢复时，同一入口可加
`--evidence-provider <hash-pinned-local-provider.json>`，仅传显式阶段/边界局部窗口；
本轮没有内置一套新的仿真标注器，不能把插件接口称为已完成真实物理标注。
PROGRESS/ATOMIC均为空时，增强训练会在加载模型前报错，普通续训仍可使用合格RAW。
不要求每项都有增强段，不全量重建旧200来源视觉标注。

产物：`sources.json`、`windows.jsonl`、`evidence.json`、`report.json`。
图片按索引从原HDF读取；有效尾 mask、字段/归一化映射、来源 SHA、split、排除原因和实际覆盖均保存。
完整轨迹先分组，所有视图继承组；正式评测初态、模型轨迹/分数与错误动作不进入训练。

## 两组训练（分别由用户启动）

```bash
source <conda-install>/etc/profile.d/conda.sh
conda activate <isolated-oft-environment>
cd <method-checkout>
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
python -u -m egrs.augmentation.training \
  --config configs/augmentation/raw_control.json \
  --export-dir <same-export-directory> --output-dir <new-control-run> \
  --benchmark-root <accepted-core-d8541ef4> \
  --oft-root <official-oft-e4287e94> --checkpoint <complete-sog10-638918f3>
```

```bash
source <conda-install>/etc/profile.d/conda.sh
conda activate <isolated-oft-environment>
cd <method-checkout>
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
python -u -m egrs.augmentation.training \
  --config configs/augmentation/progress_aug.json \
  --export-dir <same-export-directory> --output-dir <new-augmentation-run> \
  --benchmark-root <accepted-core-d8541ef4> \
  --oft-root <official-oft-e4287e94> --checkpoint <complete-sog10-638918f3>
```

两组：bf16、microbatch1、accum16、checkpointing、1000次更新、lr2e-5、warmup50、seed7、每250保存。
仅完整语言 attention q/k/v/o路径的 r16/alpha32/dropout0 LoRA训练，原视觉/base/head/proprio冻结。
使用标准原生 Linear LoRA实现，无需重复PEFT adapter；冻结head前向仍传梯度到LoRA。
RAW/PROGRESS/ATOMIC请求比例50/25/25，任务/来源均衡且逐来源回退；实际比例写入metrics。
双图共享轻微亮度/对比因子，无新增几何增强。L1按真实有效动作标量归一化。

控制台与 `metrics.jsonl` 保存更新步、百分比、loss、LR、耗时、实际采样；
`update-XXXXXX` 保存adapter、optimizer、scheduler、Python/NumPy/torch/CUDA及采样器RNG，
`identity.json`绑定底座/原组件/统计/目标层/参数形状/adapter SHA；`best_checkpoint.json`
只依同一完整指令RAW dev有效标量L1选择，禁止用测试SR选checkpoint。
恢复使用同一命令加 `--resume <this-run-update-directory>`；不同配置/导出身份拒绝，不能以发布step300000伪恢复。

24GB静态约束：冻结7B bf16权重本身约14GB，另有视觉/head/激活和LoRA优化器状态；
checkpointing不保证峰值低于24GB。未做GPU probe、未测时长/显存。真实OOM保留日志后由用户决定fallback，
不能自行量化或减少视角/proprio/chunk。

## 普通 adapter 评测：A90、C36

部署时填写 `configs/augmentation/eval_progress_aug.json` 和 `eval_raw_control.json` 的全部占位。
adapter路径取各组 `best_checkpoint.json` 指向的本轮update目录。
`base_runtime`继续描述原底座加载器；方法batch/worker/raw单独绑定实际adapter，不能与原始模型混算。

```bash
source <conda-install>/etc/profile.d/conda.sh
conda activate <libero-evaluation-environment>
cd <method-checkout>
python -u -m egrs.augmentation.evaluation run \
  --config <filled-eval-progress-aug.json> --out <new-A90-run>
```

```bash
source <conda-install>/etc/profile.d/conda.sh
conda activate <libero-evaluation-environment>
cd <method-checkout>
python -u -m egrs.augmentation.evaluation run \
  --config <filled-eval-raw-control.json> --out <new-C36-run>
```

入口内完成文件验证，不要求用户先重复跑preflight。可选纯文件计划入口为同模块
`plan --config ... --out <new-plan.json>`；不会加载模型/创建仿真。
每条视频、动作、query、RGB输入证据与raw由原core保存。仅完整原指令、当前双图与proprio送入OFT；
不送mask、谓词/接触真值、未来帧、原子oracle或评分。seed7/chunk8/H520及原物理终点保持。
技术中断保留已执行结果并停止，不自动重试。已有输出目录不能覆盖或隐式重跑。

`summary.json`/`report.md`复用034二元接口：完成合规success→1，其余已完成→0；
原UNKNOWN只在diagnostics。缺失/技术错误不伪装模型0。正式SR和任务等权宏平均要求完整分母，
未齐显示live completed SR与完成率；90与36分别报告。基线22/90来自既有验收，不在这里重新执行。
只读另存报告：

```bash
python -u -m egrs.augmentation.evaluation report --run <existing-method-run> --out <new-derived-report>
```

## 软件验证及交接

CPU/fake命令和实际结果见回复030；覆盖合成HDF、tiny LoRA/梯度/恢复、固定90/36来源选择、
原core fake视频/动作证据链及034不完整报告。不将软件检查称为真实动作正确、训练成功或模型提升。
下一步由Codex审查/隔离部署并填写来源与环境；用户另行确认候选最多180新增来源、
两次1000更新、A90+C36预算后，亲自启动真实阶段。
