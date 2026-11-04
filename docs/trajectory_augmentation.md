# 035：机器人起点变换轨迹、7:3混训与双条件评测

035在已验收030上增加真实轨迹生成的数据kind、混训配方与双条件评测。当前交付是软件与CPU/fake验证；真实数据获取、生成、训练和模型评测由用户另行确认并亲自启动。优先目标为10合规SR，其次00保持；不承诺生成成功率或SR增益。

## 固定来源与部署输入

实现基于030 PR9固定 `5bb32713a5451b7df8cb38c9a8e168d2c4a7e97d`，不自动合并PR9或本PR。原模型、LoRA、head/proprio、归一化、checkpoint/RNG恢复及评测证据主体复用，旧030配置含义保留。

| 输入 | 固定身份/作用 |
|---|---|
| 官方普通演示 | `yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`，九任务自然前N≤20 |
| 目标绑定 | `egrs/augmentation/data_scope.json`，scope `191eabf1dad8bebc1cf2a39d26a98308ed4d6338` |
| 历史native组件 | `Learning-Not-to-Act@fc1b49906b8b4e5b3bf9994c139ac3f61ec7b391`，沿用030的15文件字节锁 |
| 执行/资格core | `LIBERO-Remain@d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`，沿用030的97文件字节锁 |
| 10二元报告 | 已验收034包 `d2afce4eb074b777364daddea2c08bd70731865f`，原字节锁不变 |
| 官方OFT | `moojink/openvla-oft@e4287e94541f459edc4feabc4e181f537cd569a8` |
| 完整合并SOG10 | `moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7`，包括原head/proprio/processor/statistics |

路径由Codex在隔离目录中绑定，模板不包含真实服务器路径、模型或数据。
复用既有native backend的interpreter、module_paths、native版本/模块/BDDL/XML资产锁；不要求用户重写恢复器或控制器。
035隔离worker在明确校验d854 core后，为历史初始化器提供该固定core的activate桥接，原15文件不改，实际core和历史组件身份都入审计。不能将示例路径或空hash表当作已部署配置。

种子模板：[seeds.example.json](../configs/trajectory_augmentation/seeds.example.json)、[seed_record.example.json](../configs/trajectory_augmentation/seed_record.example.json)。
生成配置：[generate_robot_rewind.example.json](../configs/trajectory_augmentation/generate_robot_rewind.example.json)。
原始字段/normalization绑定规则沿用[030说明](augmentation_data.md)，本轮不要求旧200来源加入新manifest。

种子记录必须包含真实文件SHA、`data/demo_N`、完整原语言、长度、固定任务目标、原控制器和字段映射。
`controller_binding.env_args_sha256`是解析原HDF env_args JSON后经030 `identity(...)`所得的canonical SHA；`type=OSC_POSE`、`control_freq`必须与实际原环境一致。
既有未知物理祖源继续标记unknown；已知测试同源、评测状态/轨迹、编辑状态和模型动作不得进入种子。
来源先按完整父demo和已知重复组以seed7分train/dev，约80/20而不强凑数量；变体和全部窗口继承该split。

新执行记录保存原环境action，因此035要求官方部署的坐标符号全+1、原夹爪open=-1/closed=+1；监督映射open=1/closed=0。原始SOG10 q01/q99/mask与统计文件SHA均须绑定，不能以自定义逆变换伪造“往返一致”。这只限定035新数据，不改030旧schema。

## 生成行为与边界

`plan`只读JSON元数据，输出来源组、缺失任务、最多180正常重放、540机器人起点和1080新10尝试；这些都是候选上限，不是成功数量。它不读HDF内容、不创建仿真、不加载模型，不能据此声称真实数据已通过。

`generate`默认调用本库实际native worker。每来源最多一次正常重放；从原完整初态出发，所有source/bridge/continuation动作先与原统计可监督范围、夹爪映射及`env.action_spec`求一致投影，再实际`env.step`。保存raw、projected、normalized和变更，正常回放被投影后不冒称与原动作逐值相同。

所有RGB/proprio/state来自本次实时执行，不复用旧图像或旧RGB对齐passed。正常数据保留真实初始谓词，不假称mask00；其完成、释放和违规证据由固定core分析，不套初始成果保留要求。

交接点须A真/B假、保持约束和所需门打开条件真、手打开、无持物且A运输物已释放；取合法候选中距同来源名义初始受控末端最近者，按时间打破平局。B先完成或无合法候选如实记gap。

新episode初始化仅按实际编译joint布局替换机器人qpos/qvel和打开夹爪，保留全部非机器人分量及其速度，记录改动索引与未改分量hash。三个预定起点为名义起点及seed7的两组≤0.05rad扰动；越限、明显穿透或错误初始事实拒绝。初始化跳变不记作动作，随后不再set_state/set_goal救轨迹。

每起点先直接SE(3)插值，失败再试一次抬升—平移—下降；默认每阶段40步，另有最多40步末端收敛，总控制步含确认HOLD不超过520；初始化/编译耗时另计。默认交接误差≤5mm/3°。
`native_backend.source_timeout_seconds`限制单个父来源worker的总墙钟时间，默认7200秒，允许1至86400秒；包括初始化及该来源全部尝试，不是每步或每次attempt的超时。超时保留已写的尝试/journal，不算成功或自动重试。
B段使用正常重放记录的**真实controller.goal_pos/goal_ori和夹爪序列**，依据当前受控末端位姿及原OSC缩放计算新动作，不复制旧七维动作。保持原控制频率和世界旋转约定。

成功10必须完整任务成功、保持A和不再抓A运输物、满足释放/连续确认且无违规；A为炉开机制时不把B正常放壶接触当成抓A。
必要释放须已在监督动作内完成；只有最后监督状态已释放且手打开时才追加仅供审计的确认HOLD，不能靠未入训练标签的HOLD完成释放。
终局确认不会生成FINISH或停车监督。

机制参考：[MimicGen数据生成](https://mimicgen.github.io/docs/modules/datagen.html)、[官方robosuite接口](https://github.com/NVlabs/mimicgen/blob/main/mimicgen/env_interfaces/robosuite.py)、[robosuite v1.4.1 OSC](https://github.com/ARISE-Initiative/robosuite/blob/v1.4.1/robosuite/controllers/osc.py)。
本实现采用其位姿连接/控制转换思路；没有安装完整MimicGen或声称它原生支持本九任务。

## 产物和失败记录

`generation_plan.json`封存来源和候选预算；`artifacts/source-NNN/`保存来源级报告和每次attempt的元数据、lineage、qualification、初态/状态事实与逐步journal。动作发给环境前先记请求，完成后记实际controller目标/事实；中断不能删除已开始attempt。初始化尚未得到状态时明确记录缺失，不伪造初态或成功。

正常首次自然来源的代表视频按任务预先固定，视频失败保留错误。成功轨迹另存HDF，双图/8维proprio/state为T+1，实际动作和控制目标为T，明确`o_t→a_t→o_(t+1)`。失败attempt不进成功监督，但留在分母和审计。无交接点意味着10池缺口，不能补写成功候选。

`export/`包括 `sources.json`、`windows.jsonl`、`attempts.json`、`report.json`。报告区分父来源/组、实际尝试、合格轨迹、窗口/有效动作、task/split/domain覆盖与失败原因。540个起点不等于540个独立来源或成功轨迹。

新provenance为`ordinary_reexecuted`和`counterfactual_generated_from_demo`，数据kind为`task035-generated-trajectories-v1`。
`GeneratedTrajectoryDataset`复用030的图像/动作/proprio处理，输出仍只有双图、proprio、完整指令、chunk8动作目标和有效mask；只在episode尾padding。数据hash、谓词、contact、domain、父来源和阶段不进入策略输入/历史/终止决策。

## 完整入口命令

以下路径均为部署占位；Codex一次性绑定后交用户，不要求用户手填180/200条记录。复用隔离的原生环境与OFT环境，不升级冻结部署。native需要原有LIBERO/robosuite/mujoco、h5py和代表视频所需imageio/ffmpeg；统计仅文件读取，不加载7B。方法包安装到导出/训练/评测主进程与原OFT worker所用解释器。

```bash
conda run -p /absolute/path/to/export-env python -m pip install --no-deps -e /absolute/path/to/method035

conda run -p /absolute/path/to/export-env python -m egrs.trajectory_augmentation.cli plan \
  --config /absolute/path/to/generate035.local.json \
  --output /absolute/path/to/new-generation-plan.json
```

用户确认新预算并亲自启动正式有界批处理，不增加1/5条滚动MVP：

```bash
conda run -p /absolute/path/to/export-env python -u -m egrs.trajectory_augmentation.cli generate \
  --config /absolute/path/to/generate035.local.json \
  --output /absolute/path/to/new-generation-run
```

`generate`已在同次操作中导出合格数据索引，不需要部署方自写恢复插件。新输出目录不能覆盖；不自动重试既有整批或增加来源/候选预算。实际不足/错误由报告交研究决策。

## 混训与同adapter双条件评测

配置：[robot_rewind_mix.json](../configs/trajectory_augmentation/robot_rewind_mix.json)。
一组模型，batch16取12个10和4个normal；两域各自按有效动作标量归一化，再加权`0.7L10+0.3Lnormal`。
各域按task→父来源→变体→窗口均衡，记录实际抽样与有效动作比例，不将空10池偷偷回退normal。
任一必需train/dev域空，在模型加载前报gap；部分任务缺口在数据报告中明示，不强迫全部任务完美覆盖。

沿用SOG10原底座、训练好的head/proprio、原统计与语言q/k/v/o LoRA r16/alpha32/dropout0；bf16/micro1/accum16/lr2e-5/seed7，固定候选1000更新。035关闭额外photometric，避免引入未指定新配方变量。dev以元数据固定抽每域≤256唯一窗口，每250更新诊断；固定末1000权重写`selected_checkpoint.json`，不以dev或正式90 SR选点。

```bash
conda run -p /absolute/path/to/oft-env python -m pip install --no-deps -e /absolute/path/to/method035
conda run -p /absolute/path/to/oft-env python -u -m egrs.trajectory_augmentation.training \
  --config /absolute/path/to/method035/configs/trajectory_augmentation/robot_rewind_mix.json \
  --export-dir /absolute/path/to/new-generation-run/export \
  --output-dir /absolute/path/to/new-mixed-training-run \
  --benchmark-root /absolute/path/to/accepted-core-d8541ef4 \
  --oft-root /absolute/path/to/official-oft-e4287e94 \
  --checkpoint /absolute/path/to/complete-SOG10-638918f3
```

恢复加`--resume /absolute/path/to/this-run/update-000250`，原优化器/调度器/所有RNG与sampler恢复逻辑复用；配方、数据字节身份或update不一致拒绝。035 adapter身份为`task035-oft-adapter-v1`，包含recipe、数据kind、export身份和实际update，旧030身份不能静默混算。

同一个`update-001000` adapter同时评10/00各90，完整命令与固定来源配置见[双条件评测指南](trajectory_augmentation_evaluation.md)：

```bash
conda run -p /absolute/path/to/libero-eval-env python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /absolute/path/to/eval035.local.json --out /absolute/path/to/new-dual-condition-run
```

10复用034二元合规SR，对比22/90；00复用各来源既有normal00协议和原生目标评分，对比78/90。分别报告，不能混为同一成功口径或据条件切checkpoint/指令。原始模型两组基线不重跑，正式视频/query/action/raw均保存。

## 验证与下一步

软件验证只用合成HDF、tiny策略与fake native边界，覆盖数据→混训、生成→索引及双条件证据读取；不能证明生成成功率、24GB显存适配或SR提高。具体命令/结果见`collaboration/responses/035_round1.md`。
下一步Codex集中审查、绑定实际来源与锁、隔离部署并给最终命令；用户确认候选最多180种子重放＋1080新10尝试、一组1000更新与180新模型episode后亲自运行。没有自动启动真实阶段或合并PR。
