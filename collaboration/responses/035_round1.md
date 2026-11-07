# 035 Round1｜完整轨迹生成、7:3混训与同adapter双条件评测

2026-11-03，X提交，等待Codex审查。执行[035工单](../tasks/035_mask10_robot_rewind_augmentation.md)及其关联方案；本轮只做实现与CPU/fake，没有启动真实生成、仿真、训练或模型评测。

## 版本与结论

- 独立分支 `x/task035`，独立PR面向 `main`；不更新PR9，不自动合并任何PR。
- 复用已验收030 `5bb32713a5451b7df8cb38c9a8e168d2c4a7e97d`；已fetch并合入main文档 `cb026b3`，合并提交 `58a05f0`。
- 主体实现：`fda3c95ab5a95d7f3d7db388b3c4ad42cde46f46`；配置/命令复核修正：`e98ecc366cbb29eb1c3727cf17773cb851da379f`。后者只将示例单来源超时字段与实际worker对应，默认7200秒。
- 软件实现100%；最终定向CPU/fake **87/87通过，100%，0skip/0error/0failure**。真实数据获取/生成、训练、新模型评测本轮均0%。软件通过不等于生成成功率、显存适配或模型SR已验证。

PR9尚未合入main，因此独立035 PR携带其已验收祖先实现；035新增内容可从 `58a05f0` 起查看，不把旧030主体重新申报为本轮重写。

## 实际交付

新增 `egrs.trajectory_augmentation`，包含 `cli/data/control/native/generation/training/evaluation`。入口均有实际实现；fake只用于测试注入环境边界，不要求部署方补恢复器、控制器或训练主体。

### 完整生成与数据

1. 固定九任务自然前N≤20普通demo；最多180父来源。先按父demo及已知重复组分train/dev，变体继承split。已知正式测试同源/模型动作/编辑状态排除；未知物理祖源保留unknown，不冒称已证明无重叠。
2. 默认每来源启动独立native worker，复用030锁定的初始化/XML/BDDL/名称组件，从原完整初态真实重放。本次动作先投影到原SOG10统计与原环境可监督范围再 `env.step`；当前RGB/proprio/state与真实controller目标重新记录，不复用旧图/旧RGB对齐passed。
3. 按实时A真/B假、保持约束、必要开门、手开、无持物、A运输物释放筛交接点，选距同来源名义初始受控末端最近者。B先完成或无安全交接只记gap。机器人按实际joint布局在新episode起点恢复，非机器人分量及速度保留；名义起点加两组seed7的≤0.05rad扰动，越限/明显穿透/初态错误拒绝。
4. 直接SE(3)插值优先，抬升—平移—下降仅备用；每起点最多2次、每attempt总H520（含审计HOLD）。B段跟踪正常重放的真实 `controller.goal_pos/goal_ori` 与夹爪序列，根据当前受控末端、原OSC缩放和世界旋转计算新动作，不粘贴旧7维动作，不在中途 `set_state/set_goal`。
5. 复用固定core的事实/释放/确认/违规分析。10保护A并拒绝再抓A运输物；机制A不把放壶接触炉子当抓A。normal保留真实初始谓词，不谎称mask00或套10初始成果保护。必要释放必须已经由监督动作完成；确认HOLD仅审计，不靠未入标签HOLD补做释放，不生成FINISH监督。
6. 合格轨迹保存T+1双图/8维proprio/state和T实际动作；chunk8只在尾部mask。provenance分别为 `ordinary_reexecuted` / `counterfactual_generated_from_demo`，数据kind为 `task035-generated-trajectories-v1`。新数据集复用030读取/归一化，模型item不含truth、domain、父来源或阶段。
7. 初始构造前落正常slot，attempt开始前落元数据，动作送入环境前后分别写journal。超时、中断、初始化异常、拒绝和资格失败都保留；无状态/未执行动作明确缺失，不补写成功。成功才入监督，所有实际尝试仍入分母。每task固定首次自然来源代表视频，失败诊断保留。
8. 同次 `generate` 导出 `sources.json/windows.jsonl/attempts.json/report.json`，报告task/split/domain、父来源/组、实际尝试、合格轨迹、窗口/有效动作、缺口和失败原因。1080是10尝试上限，不是成功条数；输出目录不得覆盖。

### 混训与adapter

复用030完整SOG10加载、原head/proprio/processor/stats、语言q/k/v/o LoRA、前向、优化器/RNG恢复和保存。新配方 `robot_rewind_mix` 每有效batch16取12个10、4个normal，两域各自按有效动作标量归一化后 `0.7 L10 + 0.3 Lnormal`，padding不改变权重。域内按task→父来源→变体→窗口均衡，记录实际采样/有效动作；必需train/dev域为空在加载模型前报gap，无普通BC静默回退。

沿原bf16/micro1/accum16/lr2e-5/seed7、LoRA r16/alpha32/dropout0；候选1000更新，250间隔诊断。dev固定每域最多256唯一窗口；固定末1000权重写 `selected_checkpoint.json`，不由dev/正式SR选checkpoint。035不增加额外photometric。新身份 `task035-oft-adapter-v1` 绑定recipe、数据kind、export字节和update；旧030身份语义保留，续训/评测不能混算。

### 同adapter固定10/00评测

一个显式 `update-001000` adapter、一个隔离策略worker供两条件使用。固定九任务10/00各90，原来源/指令/seed7/chunk8/H520/相机/proprio/crop/action接口不变。六个旧10复用原full-ten reader；旧六00复用既有normal00-control来源及endpoint，新三分别复用nine-mask10/nine-normal00，后者00保持official-success endpoint。源协议差异保留，不重制初态。

完整视频、query、返回/执行actions、raw及source/adapter身份保存。10调用034二元合规报告，对比22/90；00调用固定core官方目标评分，对比78/90，preservation不适用，release诊断不误拒官方00成功。仅完整且兼容的90条证据生成正式SR差值；缺失/技术错误保留未解决，不能算模型失败或补写通过。两口径分开报告，不合并SR，不向策略传condition或切checkpoint/指令。

### 对030共享文件的最小扩展

| 文件 | 必要改动 |
|---|---|
| `egrs/augmentation/training.py` | 可选recipe钩子提供035域独立损失、dev和终点选择；旧默认路径保留 |
| `egrs/augmentation/oft.py` | 保存035 adapter附加身份；原模型/LoRA主体复用 |
| `egrs/augmentation/adapter_identity.py` | 验证独立035 schema、recipe/export/update，保留030身份 |
| `egrs/augmentation/evaluation.py` | 原native相机与eef/gripper平铺观测精确白名单传递；实际OFT `_raw_observation` 需要这些原传感器字段，仍排除truth |

没有修改benchmark、冻结部署、正式90来源或物理/评分判据；旧030及034验收结论不变。

## CPU/fake证据

本机Python3.12.7，最终由root分三个进程运行，仅合成HDF、tiny策略和fake native边界；0真实模型/仿真/渲染作业。

| 组 | 文件 | 最终结果 |
|---|---|---|
| 生成/控制/数据/CLI | `test_trajectory_control/generation/data/cli.py` | 38 passed，1.14秒 |
| 混训及受影响030 | `test_trajectory_training.py`、`test_augmentation_training.py` | 25 passed，3.88秒 |
| 双条件评测及受影响030 | `test_trajectory_evaluation.py`、`test_augmentation_evaluation.py` | 24 passed，18.32秒 |

覆盖非对称q01/q99和更紧环境限幅、真实夹爪符号往返、机器人分量/非机器人速度、真实step桥接、交接与持物/门约束、释放HOLD边界、中断分母、T+1/尾mask、父来源分组、输入隔离、域独立梯度、export→tiny训练/恢复/身份、完整180条fake队列和四种协议的实际证据reader。旧head/LoRA等未变路径沿用030已验收证据，没有要求全库重验。

在035工作目录复现下列三个独立进程；历史组件路径按部署同级目录解析，缺失时须绑定固定15文件原组件，不以skip替代：

```powershell
$env:EGRS_PROGRESS_HISTORICAL_ROOT=(Resolve-Path ../Learning-Not-to-Act-task016).Path
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_control.py tests/test_trajectory_generation.py tests/test_trajectory_data.py tests/test_trajectory_cli.py -q --tb=short --basetemp=.work/task035-final-generation-20261103 --junitxml=.work/task035-final-generation-20261103.xml

& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_training.py tests/test_augmentation_training.py -q --tb=short --basetemp=.work/task035-final-training-20261103 --junitxml=.work/task035-final-training-20261103.xml

& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_evaluation.py tests/test_augmentation_evaluation.py -q --tb=short --basetemp=.work/task035-final-evaluation-20261103 --junitxml=.work/task035-final-evaluation-20261103.xml
```

三入口 `--help` 均exit0；最终暂存diff whitespace检查通过。独立实现复核无剩余已证实阻断项，之后补正了评测adapter目录占位和生成超时配置字段；未更改已测试执行逻辑。

**保留失败记录：**一次单进程组合定向测试在NumPy矩阵乘法处进程中止。独立最小复现 `import numpy as np; import torch; print(np.eye(3) @ np.eye(3))` 得到本机Anaconda `OMP Error #15: libiomp5md.dll already initialized`。并行实现期间另误启动过一次全库CPU pytest，已要求停止，同类底层中止且无summary，不能记为通过。最终87项仅统计上表三个独立进程。没有设置 `KMP_DUPLICATE_LIB_OK`、安装/升级包或更改冻结环境；本地XML及 `.work/task035-openmp-diagnosis.txt` 保留，未把失败改写成通过。

## 配置、依赖和完整运行命令

详细说明：[生成/混训](../../docs/trajectory_augmentation.md)、[双条件评测](../../docs/trajectory_augmentation_evaluation.md)。模板位于 `configs/trajectory_augmentation/`：`seeds.example.json`、`seed_record.example.json`、`generate_robot_rewind.example.json`、`robot_rewind_mix.json`、`eval_robot_rewind_mix.json`。

固定依赖：原官方普通演示revision `147fa5eb607bb696dd922c3518084a90954cd2f3`；历史native `fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391`（15文件）；core `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`（97文件）；034报告包 `d2afce4eb074b777364daddea2c08bd70731865f`；官方OFT `e4287e94541f459edc4feabc4e181f537cd569a8`；完整合并SOG10 `638918f3d1c2e43a39a8a20772bdb8b91835e4b7`。沿用原版本/模块/资产/统计锁；不新增MimicGen安装或通用规划依赖。

Codex在隔离035目录一次性绑定实际HDF、字段/原控制器/语言/目标、真实SHA、原统计与native interpreter/module/资产配置，以及双条件封存source/runtime/reporting路径；模板中的占位符/空hash不是ready证据。原native环境需既有LIBERO/robosuite/mujoco、h5py及视频imageio/ffmpeg；OFT环境沿已验收030。下面是普通conda/python入口，路径由Codex替换后交用户，不让用户手填180条记录，不在冻结环境中热改。

```bash
# 独立方法目录与导出/评测主进程环境；仅安装本包，不解析升级依赖。
conda run -p /absolute/path/to/export-env python -m pip install --no-deps -e /absolute/path/to/method035
conda run -p /absolute/path/to/oft-env python -m pip install --no-deps -e /absolute/path/to/method035
conda run -p /absolute/path/to/libero-eval-env python -m pip install --no-deps -e /absolute/path/to/method035

# 纯文件生成计划，不创建仿真、不加载模型。
conda run -p /absolute/path/to/export-env python -m egrs.trajectory_augmentation.cli plan \
  --config /absolute/path/to/generate035.local.json \
  --output /absolute/path/to/new-generation-plan.json

# 下列真实阶段由用户确认035预算并亲自启动；本轮均未执行。
conda run -p /absolute/path/to/export-env python -u -m egrs.trajectory_augmentation.cli generate \
  --config /absolute/path/to/generate035.local.json \
  --output /absolute/path/to/new-generation-run

conda run -p /absolute/path/to/oft-env python -u -m egrs.trajectory_augmentation.training \
  --config /absolute/path/to/method035/configs/trajectory_augmentation/robot_rewind_mix.json \
  --export-dir /absolute/path/to/new-generation-run/export \
  --output-dir /absolute/path/to/new-mixed-training-run \
  --benchmark-root /absolute/path/to/accepted-core-d8541ef4 \
  --oft-root /absolute/path/to/official-oft-e4287e94 \
  --checkpoint /absolute/path/to/complete-SOG10-638918f3

# eval035.local.json adapter绑定 /absolute/path/to/new-mixed-training-run/update-001000。
# 以下plan只读配置/既有文件；run才是新180条模型评测。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation plan \
  --config /absolute/path/to/eval035.local.json --out /absolute/path/to/new-evaluation-plan.json

conda run -p /absolute/path/to/libero-eval-env python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /absolute/path/to/eval035.local.json --out /absolute/path/to/new-dual-condition-run

# 只读现有结果派生报告，不补跑缺失episode。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation report \
  --run /absolute/path/to/new-dual-condition-run --out /absolute/path/to/new-dual-condition-report
```

恢复同一训练run时在完整训练命令末尾加 `--resume /absolute/path/to/new-mixed-training-run/update-000250`（或该run已有的合法保存点）；不自动重跑旧批次。单来源worker总墙钟限额为 `native_backend.source_timeout_seconds=7200`，含初始化及来源全部尝试；H520仍是每attempt控制步上限，不因超时加候选或放宽资格。

## 边界与下一步

目前无已证实未修的软件阻断；真实输入绑定/依赖可用性、native实际生成成功率、24GB显存是否足够、1000更新充分性及SR变化均未验证。若真实生成池不足，报告gap交研究判断，不编造来源、不回退后冒称增强完成、不自动追加预算。

下一步执行者 **Codex**：对该固定实现集中审查、绑定实际文件与锁、在新目录隔离部署，交最终准确命令；不是重写控制器。随后 **用户** 确认035新预算并亲自启动最多180种子重放＋最多1080新10尝试、一组1000更新和同adapter180新模型episodes。当前无真实作业、基线重跑、自动merge或清理，待删=[]。
