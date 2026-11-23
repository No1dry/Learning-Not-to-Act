# Task055 Round1：三个未见组合、仅预完成150的软件交付

日期：2026-11-23；角色：X。依据用户指定工单 `6e650887ba43b7fff81c24e8491442a8337de252`，直接实现软件与定向CPU/fake。代码提交：`2f3bc7718ddc9bfa9324224322ef2e01b49776e7`，分支 `x/task055`，[新PR #30](https://github.com/No1dry/Learning-Not-to-Act/pull/30)以最新已验收PR29分支 `codex/task054-h0-remain450` 为依赖，不自动合并。

软件已交付，真实构建 **0/150**。部署0、SSH0、模型加载/训练/评测0。没有普通状态库，也没有将普通或剩余操作诊断设置为门槛；当前无必须补数据、换模型或先做真实MVP的软件硬阻塞。真实物理通过率及泛化结论未验证。

## 实现范围

新增 `egrs/composition055`，包含纯任务catalog、strict config、单来源原生构建、原始证据读回、固定150编排及 `build/inspect` CLI。另交配置模板、三组测试、JUnit、内部实现复核及[完整使用说明](../../docs/task055_usage.md)。没有向旧catalog注册新任务，没有训练/模型执行接线。

| 顺序 | task key | A 已完成 | B 剩余 | 固定数量 |
|---|---|---|---|---:|
| 1 | `composition_soup_butter` | alphabet soup | butter | 50 |
| 2 | `composition_tomato_cheese` | tomato sauce | cream cheese | 50 |
| 3 | `composition_tomato_butter` | tomato sauce | butter | 50 |

完整语言逐字沿工单；每个任务只含其A/B的两个原生 `in ... basket_1_contain_region` 目标。派生官方Scene2 BDDL只改语言、目标物体列表和goal三段，其他资产/初始化不变。官方task0 `.pruned_init` 固定索引0..49，同一顺序供未来Base/H0/H1读取。源ID和episode ID确定生成，不开放数量、普通状态、模型或重排序参数。

祖源资产SHA固定：BDDL `2e661058917f683a25bce480015197f0a2c1911bcbc2b9dd9d947199069c9618`；50×123初态 `1899fe54c51e24a41d5f9e32254730d6777f4894ab68e0e873f1fa7ae2062030`。已通过纯文件读取核对真实资产、派生BDDL及50×123 float64布局，没有实例化环境或推进物理。每条再次绑定原始向量、环境、编译拓扑、物体关节和篮子region所有者，防止把旧任务改名冒充新组合。

构建直接调用固定core `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9` 的几何、恢复、观测、物理和释放函数。内部base settle80，最多24个A几何候选各settle80，保留实际速度；只移植A自由关节，B/第三物体/机器人和其他状态相对内部基准逐位不变。内部基准不导出为普通状态库。原150步构建审计加两个独立150步恢复回放；A释放取原5观测窗口，B全程false，`None`不是通过。

原 `.005/.01/.002/.002` 物理阈值、原观测检查保持。RGB使用旧篮子路径 V4 一档加稀疏面积上限，不套用052针对旧来源的两档例外，不误称为V6。两个RGB相机缺失、非RGB字节不符、恢复观测不符、未释放、不稳定、穿透、B误完成或场景close异常均拒绝。初态准入不伪造B=true，不新写完整任务评分；未来模型评测须继续保持原完整评分与A保护。

## 记账、证据与旧内容保护

固定150人口在native工作前落盘；每个控制步调用前保存已消耗计数。文件持久化失败停止当前和后续来源，不能因原validator捕获异常而继续消费。Windows已观察到的短暂共享锁仅重试同一已fsync文件的rename，不重做物理步骤或来源。

新输出拒绝覆盖、拒绝与代码/core/输入/旧bank/训练/结果目录重叠。成功保存状态、typed观测、原物理/释放trace、两次回放和祖源SHA；失败保存原因、已产生文件及账本，不替换、退款或重新排序。离线reader对成功证据重算原判据，对失败文件核验完整清单和SHA，缺失不能被读成完整证据。报告分任务ready/50和总ready/150，不将pending或失败计为成功。

旧生产源码没有本轮修改。基于accepted PR29 `9bb9bfc92d4a8632223567261d99f0162cc469a0`，同步main最新文档的合入点为 `17de860`；PR中来自main的历史报告是已有文档同步，不是本轮运行或改分。本轮实现增量只新增055文件，另更新README/STATUS入口。旧九任务、450bank、训练ten/fresh/raw、sidecar、dev、checkpoint选择、旧结果和冻结core均未写入或重跑。

## 定向CPU/fake结果

最终 **54 passed，0 failed，0 skipped，32.37秒**：catalog21、native9、编排24。证据：[JUnit](../evidence/055_cpu_fake.junit.xml)、[机器交付记录](../evidence/055_implementation.json)、[内部实现复核](../evidence/055_internal_implementation_review.md)。内部复核不冒充另行Codex验收。

实际命令（Windows本地，只运行Task055）：

```powershell
$env:LNA_CORE='C:/Users/robot/Desktop/Learning_Not_to_Act/Learning_Not_to_Act/.release-work/LIBERO-Remain-task033-r2'
& 'C:/ProgramData/anaconda3/python.exe' -m pytest `
  tests/test_composition055_catalog.py `
  tests/test_composition055_native.py `
  tests/test_composition055_preparation.py `
  -q --tb=short --show-capture=no `
  --basetemp=../../.release-tools/t55/final54 `
  --junitxml=../../.release-tools/t55/final54.xml
```

覆盖精确任务/角色/第三物体隔离、canonical SHA、固定150顺序/重复/缺失/越界拒绝、真实core函数配CPU场景双独立恢复、释放/速度/穿透/B误完成/缺相机/旧观测/close失败、输出保护、失败保留、全新解释器先activate、控制账本中断和篡改拒绝。fake150只是编排测试；不是实际150物理状态通过。

首轮缺模块红测、Windows rename失败及修复回归原件均本地保留。内部复核指出失败来源文件/账本被删时旧reader未拒绝，已补失败artifact清单和全状态账本核验；3个对应红测失败后全部转绿，最终包含在54项内。另修正了fake对官方桌面fixture加载方式的假设，并对照源码确认篮子site归属；未通过真实环境试跑掩盖问题。没有扩到全库测试。

## 后续完整命令与限制

配置见 `configs/composition055/build.example.json`。下面构建命令仅由用户在Codex审查、隔离部署后运行；本轮没有执行。完整路径设置和所需冻结环境JSON见[使用说明](../../docs/task055_usage.md#配置和后续用户命令)。只需原LIBERO环境与固定core，无模型下载。

```bash
export LNA055_CODE=/absolute/path/to/isolated/task055-code
export LNA055_PYTHON=/absolute/path/to/existing/environment/bin/python
export LNA_CORE=/absolute/path/to/frozen/eval-core
export LNA_LIBERO_ASSETS=/absolute/path/to/LIBERO/libero/libero
export LNA_ENVIRONMENT_CONFIG=/absolute/path/to/existing/frozen_environment_manifest.json
export LNA_EXISTING_DATA_ROOT=/absolute/path/to/existing/data
export LNA_EXISTING_RUNS_ROOT=/absolute/path/to/existing/runs
export LNA055_OUTPUT=/absolute/path/to/separate/task055-output/composition150-001
export LNA_CANONICAL_BDDL="$LNA_LIBERO_ASSETS/bddl_files/libero_10/LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket.bddl"
export LNA_CANONICAL_STATES="$LNA_LIBERO_ASSETS/init_files/libero_10/LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket.pruned_init"
cd "$LNA055_CODE"
"$LNA055_PYTHON" -m egrs.composition055 build \
  --config configs/composition055/build.example.json --output "$LNA055_OUTPUT"
# 构建结束后的只读证据核验，不推进状态或模型：
"$LNA055_PYTHON" -m egrs.composition055 inspect --bank "$LNA055_OUTPUT"
```

仍存限制：真实runtime解析、物理通过数量和剩余任务可完成性待用户运行；没有跨机器对renderer作未经验证的保证。bank绑定原输入/代码路径和字节，需保留冻结源包；150限制及防覆盖是单输出级别，不授权用户换目录重跑。中断/失败须保留现场，后续补救另议，本轮无自动resume。检查完整bank后再决定Base/H0/H1同源配对评测，分任务报告；必要时另议少量诊断，不改150正式来源，不声称未见场景泛化或预定正结果。
