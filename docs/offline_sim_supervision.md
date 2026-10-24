# 现有观测的离线仿真监督

019提供两个独立入口：`label-sim`在隔离LIBERO worker中读取指定旧来源、恢复状态并渲染标注证据；`export-sim`校验封存产物后，通过既有selector数据构建器导出可用子集。两个入口都不启动teacher、特征抽取、训练、eval、下载或后续任务。真实标注及后续模型作业由用户分别启动；必要渲染可能使用GPU。

固定范围：20任务、200来源（160 train / 40 dev）、1200窗口、3200查询、21目标。生产配置固定dataset `yifengzhu-hf/LIBERO-datasets`、revision `147fa5eb607bb696dd922c3518084a90954cd2f3`、inventory `3f550e7736ba5428dad789a307e2c18b32f25ec51dcc763e1fb8e65db563bb33`、windows `bb453b047946179eb1ec68eb4c9ab884f9b2564b5173e849836a5caa56988cdd`、registries `ec058064453e996175bebfca449d427b240d762a08d33c01f383164dc16a8095`。原RGB、窗口、来源划分、别名、ancestry披露、registry、提示预算及history规则保持不变；旧候选和结果保留在原目录。

## 配置独立运行环境

复制[sim_backend.example.json](../configs/sim_backend.example.json)到新的本地配置文件，将通用绝对路径示例替换为选定解释器、原生库导入根目录、BDDL目录、固定core及获准asset目录。`module_paths`按顺序只传给独立worker。控制器使用本实现的绝对bootstrap脚本，在导入worker前将方法包绝对根目录放到`sys.path`首位，并核验包实际路径及控制器冻结的`egrs.sim.code.v1`源码字节identity；随后核验worker实际路径才启动协议服务。工作目录中的旧`egrs`不能覆盖本实现。identity不符时在原生工作/事实输出前失败，诊断留在worker失败audit。控制器封存前再次核对同一identity，运行中代码变化不生成manifest。工作目录保持继承，已支持的相对`core.root`、`bddl_root`和`asset_roots`仍相对调用者工作目录解析；不改变为相对配置文件解析。请求、事件、事实和manifest版本格式不变。不会安装依赖或热改现有环境。

worker需要现代`mujoco`绑定、兼容LIBERO/robosuite、Pillow、NumPy、h5py及正常离屏渲染依赖。控制器需要方法包、Pillow、NumPy；导出复用现有CPU数据/监督代码。示例显式使用annotation reference core `c6dc98de0c54517c976057598b60f4cedf7fa3e5`并设置`allow_reference:true`，不改变评测要求的core版本。core原有版本及shadow保护照常执行；必要时可配置`core.git_executable`。源场景/控制器/相机元信息不兼容时记录gap，不猜默认参数。

示例的`versions`、`module_sha256`为空，**必须采集后填写，否则入口拒绝启动**。用所选worker解释器运行下面的标准库脚本。保存为新的本地`collect_sim_lock.py`，设置三个明确源码路径，使它们对应配置导入根目录实际解析的文件，再执行`WORKER_PYTHON collect_sim_lock.py > sim-runtime-lock.json`。脚本只读distribution元信息与源码字节，不导入原生包、不打开HDF/图片。不要填任意hash，也不要为了找路径导入仿真模块。

```python
import hashlib
import importlib.metadata
import json
from pathlib import Path

sources = {
    'libero.libero.envs.bddl_base_domain':
        Path('/absolute/path/to/LIBERO/libero/libero/envs/bddl_base_domain.py'),
    'libero.libero.envs.predicates.base_predicates':
        Path('/absolute/path/to/LIBERO/libero/libero/envs/predicates/base_predicates.py'),
    'robosuite.environments.robot_env':
        Path('/absolute/path/to/robosuite/environments/robot_env.py'),
}
resolved = {name: path.resolve(strict=True) for name, path in sources.items()}
print(json.dumps({
    'versions': {name: importlib.metadata.version(name)
                 for name in ('numpy', 'h5py', 'robosuite', 'mujoco')},
    'module_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                      for name, path in resolved.items()},
    'resolved_sources_for_review': {name: str(path)
                                  for name, path in resolved.items()},
}, indent=2))
```

将`versions`、`module_sha256`原样复制进`native`，单独保留`resolved_sources_for_review`为准备依据。LIBERO源码checkout无需伪造distribution版本，必需模块按字节锁定；允许增加其他distribution/源码锁。真实作业内核对已导入模块路径/hash及安装版本，写入独立audit。采集成功不能代替环境兼容与对齐验证。

`asset_roots`只接受`libero`、`robosuite`获准前缀。worker在对应根目录内解析源XML资源并审计文件hash；不下载缺失asset，也不宣称与无法访问的历史路径字节相同。缺失资源使该来源失败。

## 分别启动标注与导出

在固定部署checkout运行，每次输出使用新目录；已有目录拒绝覆盖。以下交给用户的命令未在实施阶段执行：

```sh
CONTROLLER_PYTHON -m egrs.offline label-sim \
  --inventory /absolute/path/to/original/inventory.json \
  --windows /absolute/path/to/original/windows.json \
  --registries /absolute/path/to/original/registries-confirmed.json \
  --backend-config /absolute/path/to/new/sim-backend.json \
  --output /absolute/path/to/new/sim-annotations
```

先检查`progress.json`、stderr进度回执、`coverage.json`、`audit.jsonl`及`manifest.json`。导出直接接受原`build_dataset`的三个显式true排除布尔项（`six_composites_excluded`、`semantic_equivalents_excluded`、`eval_sources_excluded`），不要求新增`basis`；若原文件包含`basis`或额外依据，原样保留。导出是另一步文件操作，有用的部分覆盖可以保持`ready:false`：

```sh
CONTROLLER_PYTHON -m egrs.offline export-sim \
  --annotations /absolute/path/to/new/sim-annotations/manifest.json \
  --windows /absolute/path/to/original/windows.json \
  --attestation /absolute/path/to/original/exclusion-attestation.json \
  --output /absolute/path/to/new/sim-selector-data
```

`train.jsonl` / `dev.jsonl`可直接交给既有训练CLI；本入口不启动训练/抽特征。`report.json`披露可用查询及gap。`usable:true`表示存在真正可观察的状态监督子集；`ready:true`还要求来源/查询/字段完整、worker全部完成，导出时train/dev均有可用记录。部分数据诚实保留`ready:false`，不因此阻止有用子集导出；全UNKNOWN及只有身份/框的产物拒绝作为可用训练集导出。

Task3审查后的兼容性修正：`label-sim`启动前仍要求配置的worker解释器文件和导入目录存在；`export-sim`只核对这些历史路径的结构及已封存配置identity，不要求原worker环境仍安装或可访问，也不会启动worker。原图路径/字节、来源/样本绑定、manifest/config/code/mapping/hash检查照常执行。此规则及上面的原三布尔attestation契约取代首轮交付中“导出须保留worker路径、须非空basis”的额外前置条件。

## 设置与有界操作预算

| native设置 | 默认值 | 范围与作用 |
|---|---:|---|
| `probe_count` | 3 | 2..5个固定已有且可核对的帧 |
| `rgb_threshold` | 0.03 | 0..0.1；整图/可见前景MAE最大值除以255 |
| `min_visible_pixels` | 16 | 1..65536个组件可见像素 |
| `max_reset_attempts` | 3 | 1..10次既有RandomizationError有界reset |
| `max_physics_substeps` | 100 | 1..1000；replay前拒绝超限action步进 |
| `replay_state_atol` | 0.000001 | 0..0.1诊断容差；等价认证单独上限1e-6 |
| `seed` | 0 | 32位无符号初始化seed |
| `surface_inset_m` | 0.002 | 0..0.01目的支撑区域内缩 |
| `surface_normal_z_min` | 0.7 | 0.5..1可见向上支撑法线 |
| `surface_neighbor_m` | 0.03 | 0.001..0.05深度邻域不连续阈值 |
| `surface_vertical_margin_m` | 0.005 | 0..0.01原生支撑容差 |
| `table_vertical_margin_m` | 0.025 | 0..0.03桌面区域容差 |

示例`worker.timeout_seconds=600`为每来源总超时，须有限、正数且<=86400，覆盖检查、导入、初始化、对齐和所有请求帧。没有来源重试、自适应选帧、settle、hold、新视角或模型调用。超时/崩溃保留已完成事件和有效标签，后续帧显式UNKNOWN/gap。

采用Task2最终修正预算：每来源F<=18个固定请求帧、P<=5个固定probe（默认3）、C=2相机、G=1或2目标、M<=配置的action物理substeps。next-state/replay等价路径还需检查probe以外E个请求known-next帧，E<=F-P；其他路径E=0。跨分支保守上限为restore `N<=3P+2E+F`、replay action `S<=P+F`、action物理步`<=M*S`、直接标注render `<=2C*N+CF`。等价核对最多增加2E次restore、E次action、4CE次直接render；等价分支自身S<=P+E。两个方向假设复用渲染。

core的restore/action/观测刷新还会触发相机渲染。初始化之外，源码保守相机render API上限为`C*[3N+(M+2)S+2F]`。默认最大值P=3,F=18,E<=15,M<=100时：**N<=57、S<=21、action物理substeps<=2100、直接标注render<=264、总相机render API调用<=4698/来源**；等价分支自身S<=18。这些同时取最大值的数字是保守API上限，不是实测GPU kernel次数。200来源按同样松上限合计<=11400 restore、4200 replay action、420000 action substeps、52800直接render、939600相机render API调用，另加初始化。每来源一次原生构造、<=配置次数的有界reset、一次源XML reset/compile及初始化渲染另计，墙钟时间仍受source超时约束。显式目标求值<=G*F；内部success-refresh只是额外bookkeeping，不作为标签。不增加独立GPU预检。

## 对齐、可观察性及覆盖限制

精确映射20条instruction / 21个独立atom。抽屉Open与碗In分开；top-drawer Open为annotation-only原生子目标；cream-cheese-in-bowl使用原生On；plate-front使用`main_table_stove_front_region`。不广播总success，不用reward/done、演示结尾或teacher输出造标签。

对齐保留所有声明规则及两个方向的原图比较。`alignment.v2`仅在显式`equivalence.v1`提供`next_state`代表、且每个获准请求known-next帧均通过状态/RGB核对时合并next-state/replay。RGB相似但状态不同、缺检查、方向歧义及未认证final replay均保留gap。**next-state末帧没有下一state时保留边界gap，绝不clamp或静默换replay**。这是可观察覆盖的真实限制，不是保证实际全覆盖的软件承诺。原存储RGB从不变换或替换。

| 目标家族 | 支持条件与保守限制 |
|---|---|
| Drawer Open | 同相机活动抽屉部件与固定reference均可见；handle不足以证明活动面；固定柜体本身不能监督开合 |
| Stove Turnon | 活动knob视觉geom与固定炉体reference；仅炉体或不可见/透明指示物不足以监督状态 |
| Basket / drawer In | 可见目标及目的内部支撑，深度落在内缩native区域且法线向上；外壁、遮挡或内部底面隐藏时UNKNOWN |
| Stove / cabinet / rack On | 可见目标及对应native支撑面、同样深度门控；仅父对象mask不足 |
| Plate-front | 实际native区域内局部桌面、plate及stove landmark；不能用整桌/整个stove框替代 |
| Bowl-on-plate / cream-cheese-in-bowl | upright目的物、可用原生边界与可见向上支撑面；倾斜、仅侧面或遮挡时UNKNOWN；cream cheese谓词仍为On |
| Transport grasp / release | 同相机目标和手可见，配合dual-pad或既有保守手/捏持净空释放证书；单接触、闭指、隐藏或不确定证书均UNKNOWN |

HELD不推出RELEASED；机构release为NOT_APPLICABLE。稳定合法实体别名跨同来源窗口复用。bbox包围原RGB坐标中的实际可见像素，原生names/IDs只在audit。只有有证据的非UNKNOWN字段/证据项获得`sim_supervised`，该来源不进入合法history provenance。原有合法过去预测/可见证据历史原样保留，无历史则空，不用前面GT答案补造。state、contact、mask、depth、alignment与额外相机不进入payload、prompt、actor或eval策略，不放宽输入白名单与预算。

## 不可变产物与失败保留

`manifest.json`格式`egrs.sim.annotations.v1`，以规范JSON identity封存，包含五个输入identity、config identity、mapping identity、代码字节identity、原`source_splits`、来源状态/错误、`coverage`、`ready`、`usable`及下表所有文件的字节SHA-256。代码identity覆盖全部方法Python源码及打包offline JSON。部署commit另用`git rev-parse HEAD`采集；提交不能自引用最终SHA，Codex发布后再提供remote SHA。导出要求同一实现字节及映射。

| 文件 | 内容 |
|---|---|
| `inventory.json`、`registries.json`、`backend-config.json` | 原输入/配置快照，独立核验identity |
| `image-bindings.json` | 原source/frame/camera路径、尺寸、PNG字节hash |
| `requests.jsonl` | 每来源一次有界worker请求，native config只在操作侧 |
| `events.jsonl` | 所有有序事件，包括构造阶段、重复inspection、facts、audit、error、最终result；控制器失败另有版本化记录 |
| `audit.jsonl` | 独立native/inspection/alignment/失败及逐query字段gap、history可用性 |
| `annotations.partial.jsonl` | frame返回立即flush标签，之后补显式缺失帧UNKNOWN行 |
| `annotations.jsonl` | 按原query顺序整理，仅改变answer/provenance的样本副本 |
| `progress.json` | 原子替换的`egrs.sim.progress.v1`及当前coverage |
| `coverage.json` | 总体/逐任务/train-dev的planned、processed、有意义supervised、gap、UNKNOWN、字段分母/监督数、自然分布及来源/history披露 |

事件同步flush后才继续处理。`processed`统计有有效frame返回的query，即使字段仍有gap；`supervised`必须在既有mask后至少有一个relation/interaction/release状态监督，身份/role/框及NOT_APPLICABLE不计。`gap`统计任何适用状态字段未解决的query，可与supervised重叠；`unknown`统计含UNKNOWN状态字段的query，`unknown_fields`为字段数。自然分布保留UNKNOWN/null/NOT_APPLICABLE，不平衡类别或挑来源。无窗口来源、原inventory/windows gap仍披露。

协议损坏（source/frame/request错绑、重复/多余fact、schema或stream/result不一致）停止标注，留下partial及失败audit，不生成成功封存manifest。worker超时、崩溃、来源运行失败可利用先前有效事件封存诚实的部分产物。中断作业保留journal，缺最终manifest时不可导出；不自动resume/retry。后续获准重跑也需新目录，保留旧失败。

导出核验manifest、全部文件hash、实现/映射、输入identity及request集合、PNG字节、payload/history/group/ancestry/查询顺序、原split及排除attestation；由保留frame facts重建answer/provenance并重算coverage，再调用`build_dataset(..., fixed_source_splits=original_splits)`。输出只有train/dev样本、独立聚合报告与`export-manifest.json`，truth/audit侧车不进入train/dev。未知ancestry仍披露，不宣称来源物理独立。

真实HDF字段、保存场景与native兼容、对齐残差、可见支持及实际监督覆盖仍待用户真实作业验证。CPU/fake通过证明软件边界，不能代替物理标注成功。

下一步操作和执行者：Codex审查、固定实现与配置并隔离部署；用户启动标注、检查coverage，再分别决定导出及模型作业。
