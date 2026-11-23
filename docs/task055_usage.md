# Task055：三个未见组合的预完成初态构建

本入口只构建三个 held-out object combinations，各50条、总150条预完成状态。没有普通状态库、训练、教师轨迹或模型评测入口。软件和 CPU/fake 通过不表示真实150条已就绪，也不表示新组合一定可完成或方法已经泛化。

## 冻结任务与来源

| 顺序 / task key | 完整指令 | 已完成 A | 剩余 B |
|---|---|---|---|
| 1 / `composition_soup_butter` | `put both the alphabet soup and the butter in the basket` | `alphabet_soup_1` | `butter_1` |
| 2 / `composition_tomato_cheese` | `put both the tomato sauce and the cream cheese box in the basket` | `tomato_sauce_1` | `cream_cheese_1` |
| 3 / `composition_tomato_butter` | `put both the tomato sauce and the butter in the basket` | `tomato_sauce_1` | `butter_1` |

每行只使用这两个物体的原生 `in <object> basket_1_contain_region` 目标。派生 BDDL 只改变官方文件的 `:language`、`:obj_of_interest` 和 `:goal` 三段；场景、其他物体、region、初始化条件不变。不修改官方任务注册表或旧九任务注册表。

每个任务固定使用官方 `libero_10` task0 的索引0..49，按上表 task-major 顺序处理，不按模型成败选角色、换来源或重新排序。同一条 canonical index 用于三个不同任务身份；后续 Base/H0/H1 应共同读取同一批冻结状态。

官方祖源文件名主体：

```text
LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket
```

| 文件 | SHA-256 |
|---|---|
| `bddl_files/libero_10/<主体>.bddl` | `2e661058917f683a25bce480015197f0a2c1911bcbc2b9dd9d947199069c9618` |
| `init_files/libero_10/<主体>.pruned_init` | `1899fe54c51e24a41d5f9e32254730d6777f4894ab68e0e873f1fa7ae2062030` |

必须是50×123的 `.pruned_init`，不接受100条的 `.init`、重新保存的等值文件或其他 Scene2 任务的来源。解码固定 NumPy payload 不执行 pickle；每条另记录所选原始向量的 SHA、环境身份、派生 BDDL SHA、模型 XML SHA 和完整编译拓扑。

## 构建与准入

依赖沿用 `egrs/augmentation/core_files.json` 固定的 eval core `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`。先校验依赖文件再导入；不修改冻结 core，不新增评分器。

调用原 `placement_candidates` 为指定 A 产生最多24个几何候选，给 A/B 留位。canonical 内部基准 settle80步，候选 settle80步；候选只改变 A 位姿，保留实际速度。将候选 settle 后 A 的自由关节位姿/速度移植到内部基准，逐位核对其他分量，包括 B、第三物体、篮子及机器人，均未随候选被改动。内部基准来自原 settle 协议，不导出为普通状态库。

随后执行原 `validation.validate_candidate` 静态检查、150步构建检查和两个独立新环境的150步恢复回放。固定 `[true,false]`，不以第三物体替代目标；原位移、速度、机器人位姿、穿透阈值分别为 `.005/.01/.002/.002`，非RGB浮点观测容差仍为 `1e-8`。恢复起点的非RGB要求逐位一致；两路 uint8 RGB 复用旧篮子路径的 V4 `RGB_QUANTIZATION_AUDIT`（每通道差≤1，变化像素≤max(1,floor(HW×0.0001))，256²时每相机6像素），没有引入052针对旧特定来源的两档例外，也没有改成 V6 的纯诊断面积规则。

A释放调用原 `_release` 与 `release_measurement`，取原 runner 默认确认窗口：起点加后续4次、共5次连续观测。`None`/缺失不算释放，B始终必须为false。这里是初态准入，不把B伪造为true来调用任务终止评分。后续模型评测仍需保持原完整任务评分和A保护；本轮没有创建该模型运行入口。

每条成功来源保留所选状态、双RGB/proprio typed artifact、静态/动态物理trace、释放几何/trace、两次回放及谱系。离线 reader 重新调用原证据验证与观测绑定、重新计算释放事实，不只相信 `ready` 标志。失败候选、失败来源及已消耗控制步不删除；失败文件和控制账本也绑定哈希。

## 配置和后续用户命令

以下命令用于 **Codex审查、隔离部署后由用户亲自启动**。本次交付没有运行这些真实命令。使用原已验证 LIBERO/robosuite/MuJoCo 环境和 Python≥3.10；不升级依赖、不修改全局 editable 映射。无需下载或加载任何模型。

先把下面绝对路径替换成部署实际路径。`LNA_ENVIRONMENT_CONFIG` 指向已有冻结 JSON，必须包含完整 `environment` 对象（`name: libero`、`fingerprint`、`lock`，`control_freq:20`）；可以使用含其他字段的原 manifest。不要临时伪造 fingerprint；实际构建会核验整个环境身份相等。

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
  --config configs/composition055/build.example.json \
  --output "$LNA055_OUTPUT"
```

配置模板会展开这些环境变量；未替换变量、额外普通状态/model/count字段均拒绝。`protected_roots` 应列出所有旧bank、训练和结果根目录，可在独立配置副本中增加更多路径。输出必须不存在，且不能位于这些根、代码、core或输入目录内，也不能是它们的祖先。真实命令只运行一次，不换目录自动重开失败来源。

控制台每来源输出 processed和ready百分比，`sources.json` 固定保留150身份及逐来源 `ready/failed/pending/running`、失败原因和控制账本SHA；`report.md` 分任务显示 ready/50。只有150全部证据就绪，CLI才以0退出；不完整以1退出。中断记录已消耗来源，剩余保持pending；本轮不提供续跑/重试/退款入口。需要补救时先审阅原失败和账本，再由用户单独授权；不删除旧失败或把它改成通过。

真实构建后可只读核验：

```bash
cd "$LNA055_CODE"
"$LNA055_PYTHON" -m egrs.composition055 inspect --bank "$LNA055_OUTPUT"
```

`inspect` 不创建仿真、不恢复/推进状态、不执行策略；会读取固定来源资产、代码/core身份和已保存证据，缺失或篡改拒绝。保留原部署路径、输入配置和源包用于核验；它不是可任意搬迁的自包含数据格式。

## CPU/fake命令与结果边界

在仓库根目录执行下面定向命令。原生测试使用实际固定 core 的几何/物理/释放/证据函数，以假场景替代仿真IO；不导入真实 LIBERO 环境或模型。`LNA_CORE`仅需现有固定core源码；JUnit和tmp放到单独新目录。

```bash
export LNA_CORE=/absolute/path/to/frozen/eval-core
python -m pytest tests/test_composition055_catalog.py \
  tests/test_composition055_native.py \
  tests/test_composition055_preparation.py \
  -q --basetemp=/absolute/path/to/new/cpu055-tmp \
  --junitxml=/absolute/path/to/new/cpu055.junit.xml
```

此轮不重跑旧基线/450来源，不加入训练ten/fresh/raw、sidecar、dev或checkpoint选择。旧官方四套件普通能力证据仍沿用；普通或剩余物体操作诊断只在后续结果难解释时另议，**不是本轮门槛**。后续结果要分任务报告；本测试集是同场景、同技能下的未见物体组合，不声称未见场景或任意任务泛化。
