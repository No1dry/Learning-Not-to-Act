# Task057：反事实指令数据与组合泛化干预

日期：2026-11-27  
状态：用户已批"先做 1"（056 分析第 7 节选项 B 的数据构建与训练预算）。本工单是该批复的落地规格。  
**本工单不授权任何真实阶段**：状态构建、rollout、训练、评测仍由用户亲启；X 只做软件与 CPU/fake。

---

## 1. 批复后的可行性核查（必须先读）

056 分析把失败机制定位为"配对补全"：模型用"预放物体在训练数据中的固定伙伴"替代"按指令选剩余实体"。原计划是加"配对多样化"训练数据。核查后发现三个硬约束，原计划不能直接执行：

1. **现有 ten 数据来自人类演示重放，不是 VLA rollout。** `egrs/trajectory_augmentation/generation.py` 的 `safe_handoff` / `bridge` / `track` 表明生成器把演示的末端位姿目标重新执行到机器人上；`TEACHER_V1/V2` 只是数据来源标签，不是策略网络。035 阶段总结原文："从普通演示重放找到安全 handoff……实际记录新的 RGB/proprio/actions"。
2. **新组合没有演示动作。** milk、orange_juice 只作为干扰物出现在场景里，从不是九任务的目标物体，因此没有任何"把牛奶放进篮子"的人类演示可供重放。
3. **四个原始物体的 6 个配对已被穷尽。** {汤罐,番茄酱}（任务 0）、{奶酪,黄油}（任务 1）、{汤罐,奶酪}（任务 7）已见；{汤罐,黄油}、{番茄酱,奶酪}、{番茄酱,黄油} 是 055 测试。**不存在"既非已见、又非测试"的配对。**

结论：要保留 055 作为 held-out，训练数据的剩余目标必须取 milk / orange_juice；而它们的动作只能来自合成或自生成。这不是预算问题，是数据来源问题。

---

## 2. 假设与判据

**H**：配对补全来自训练分布中"预放物体→固定伙伴"的一一映射。加入同一场景、不同指令目标（且目标不是该预放物体的训练伙伴）的反事实样本，可以迫使模型按指令选物，并迁移到 055 的未见配对。

**主判据**（相对同一新基线臂）：

- 055 三组合总体 SR 提升 ≥ +10pp（即 ≥ 约 15/150 条净增），且至少两个任务方向为正；
- 9 任务 10、00 均不退化超过 −3.33pp（3 条/90）。

**次判据**：

- 055 首选错抓从"配对伙伴"转向"指令点名物体"（例如 soup_butter 中抓番茄酱的比例从 86% 下降）；
- 不出现新吸引子（例如在 soup_butter 中改抓 milk）。

**反例即结论**：若 T 组无提升但错抓分布改变，说明模型学到了"多一个候选"却没学会"按指令"，属于有效负结果。

---

## 3. 数据来源与两道门槛（先做 G0，不训练）

### G0a：策略能力探针（决定能否"过滤式自生成"）

- 新任务 4 个：`probe_soup_milk`、`probe_cheese_milk`、`probe_soup_orange_juice`、`probe_cheese_orange_juice`（A 预放，B=milk/OJ，指令为完整 "put both the A and the B in the basket"）。
- 每任务建 15 个状态（复用 055 的 canonical sources，A 预放；**不新增场景、不改 055 bank**）。
- Base（原版，无 adapter）每任务 15 条 = 共 60 条，H520 / chunk8 / seed7 / 原评分。
- 判据：某任务成功率 ≥ 20% → 该 B 允许走"过滤式自生成"；全部 < 5% → 直接转 G0b；5–20% → 可加大尝试数（≤ 400 次/B 物体）。

### G0b：演示段重定向资格（G0a 失败时）

- 取现有 ten 演示的逐帧末端位姿目标（audit 已保存），把抓取段刚性平移到目标物体（milk/OJ）的位姿，再执行、按原 `qualify_frames` 校验。
- 每目标物体 20 次尝试；判据：合格率 ≥ 20% 才进入批量生成，5–20% 加大尝试，< 5% 停止并回到讨论。

### 数据标注（强制）

每条新 ten 记录 `provenance`：

- `policy_generated_filtered`：自生成成功片段，附模型 identity、尝试序号、过滤条件；
- `retargeted_human_segment`：演示段重定向，附来源 episode/frame 区间、偏移量。

不得写成"人类演示"，不得与旧 ten 混为同一来源。

---

## 4. 两臂与预算

| 臂 | 数据 | 训练 | 评测 |
|---|---|---|---|
| T（反事实） | 289 旧 ten + 6 个反事实任务 × 15–25 条 | Base 新 LoRA，1000 更新 | 9 任务 10（90）+ 9 任务 00（90）+ 055（150）= 330 |
| C（体积对照） | 289 旧 ten + 等量"原配对"重放 ten（现有 augmentation 多 variants） | 同上 | 同上 |

- 反事实任务：A ∈ {汤罐, 番茄酱, 奶酪} × B ∈ {milk, orange_juice}，共 6 个；全部与 055 三个测试配对无交集。
- 两臂同索引、同采样、同 seed、同更新数；不挑 checkpoint。
- 不重跑 Base/H0/H1 的 055（056 已有 450 条）；不重跑 9 任务基线。

**预算量级**：G0a 60 条 ≈ 2 GPU 小时；数据生成（自生成需 500–1000 次尝试，重定向约 120–200 次执行）≈ 8–15 GPU 小时；训练 2×1000 ≈ 6–8 GPU 小时；评测 2×330 ≈ 15–20 GPU 小时。合计约 **2.5–3 GPU 日** + 工程。

---

## 5. 实现要求（新隔离扩展 `composition057`）

1. 新建独立扩展，不修改 055/056 任何字节、不覆盖 `composition055/production-001`、`composition056` 结果、旧九任务 bank/index、评分 core。
2. 新 catalog：在 055 的 BDDL 派生方式上扩 6 个对象（加 milk/OJ），任务键与指令逐字固定；`obj_of_interest` 与 goal 精确对应。
3. 状态构建复用 055 的 canonical sources 与准入检查（A 预放、释放、稳定、无穿透）；B 只是场景中的物体，不参与构建。
4. G0a 复用 056 的 rollout/评分路径，只换 bank 与任务；输出成功率、首选错抓、n_steps、A 保持。
5. 数据生成（二选一）：
   - 自生成：策略 rollout → 过滤（B 入篮、A 保持、释放确认、**首次抓取=指令物体**）→ 按 ten 格式落盘；
   - 重定向：演示段位姿目标平移 → 执行 → 同一 `qualify_frames` → 落盘。
6. 训练入口：复用 040/045 的数据索引与训练配方；新 pool 只追加，不改旧索引；`provenance` 进入索引与报告。
7. 评测入口：复用 056 evaluator；输出逐任务、三组合、配对、`wrong_grasp`/`goal_regression`/`native`。
8. 控制台与报告必须能区分 T/C 与新数据占比；不得把反事实数据算进 055 或旧 450 的分母。

**定向 CPU/fake 验收（至少覆盖）**：

- 6 个新任务键/指令/物体/region/BDDL 派生正确，milk/OJ 不在旧任务里；
- canonical source 复用、A 预放、B 未完成、第三物体隔离；
- G0a 假 60 条分母、成功率与错抓统计；
- 过滤规则（首次抓取错误、A 回退、释放未确认）逐条拒绝；
- provenance 字段必填且不可伪装；
- T/C 数据量相等、采样同 seed、旧索引/旧 bank/旧结果字节不变；
- 评测 330 分母与 055 不重跑。

---

## 6. 执行边界

- 真实状态构建、G0a/G0b、数据生成、训练、评测全部由用户启动；Codex 只做规格、软件验收、隔离部署、完整命令与结果分析。
- 未通过 G0 之前不批量生成；未通过 T/C 主判据之前不追加训练、不加 seed、不改评分、不扩 benchmark。
- 任一阶段失败保留输出与账本，不删除重开、不换容易初态、不把技术错误记成模型失败。

---

## 7. 需要用户确认的一个决定

**已确认（2026-11-27）：用户回复"按推荐的来"，接受合成动作作为 ten 训练数据，provenance 如实标注（`policy_generated_filtered` / `retargeted_human_segment`），不声称人类演示。**

在 G0a 结果出来前，仍不生成训练数据、不训练。

---

## 附录 A：G0a 探针实现规格（已落地本地代码）

### A.0 实现状态（2026-11-27）

- 代码已在本地 `implementation/task056-codex/egrs/composition057/` 落地：`catalog`（4 任务 / 60 人口）、`contracts`/`evidence`/`native`/`preparation`（复用 055 构建与准入逻辑，150→60、50→15）、`source`/`evaluation`（只 base、60 人口、复用 056 rollout/证据/评分）、`__main__`（build/run/inspect）。
- 新增 `tests/test_composition057.py`：20 项全通过；055 既有 catalog/preparation 45 项回归通过；056 测试需服务器 `LNA_CORE`，本地未跑，但 056 包字节未改。
- 配置样例：`configs/composition057/probe_build.example.json`、`probe_eval.example.json`。
- 部署时按惯例隔离到新的 `task057-*` code 目录，055/056 包保持字节不变；真实 60 条仍由用户启动。

### A.1 实现路线：新建 60 个状态，不重绑冻结状态

两个可选路线，推荐前者：

- **推荐：新建 60 个探针状态**（4 任务 × 15），复用 055 已验证的 canonical source → A 预放构建逻辑。证据链完整、不依赖对 055 产物的二次改写；构建只跑仿真、不加载模型，量级约 15–30 分钟。
- 备选：重绑 055 已冻结状态（只换 BDDL/目标/指令、状态字节直通）。省 60 次构建，但需要额外写 `rebind + inspect` 并处理产物一致性，风险更高，不作为首选。

### A.2 新扩展模块（新 suite `libero_remain_composition057`，055/056 字节不改）

| 模块 | 来源 | 工作 |
|---|---|---|
| `catalog.py` | 新写（约 90 行） | 4 个任务档案；`render_bddl` 沿用 055 的派生方式（只改 language / obj_of_interest / goal），canonical BDDL SHA 校验保留；`SOURCE_COUNT=15`、`TASK_ORDER` 4 项 |
| `contracts.py` | 从 055 复制（约 110 行） | 仅改 `SCHEMA` 与错误文案；`CORE_REVISION` 不变 |
| `native.py` | 从 055 复制（约 571 行，逐字） | 只改 `from .catalog import ...`；构建/校验逻辑一行不动 |
| `preparation.py` | 从 055 复制（约 160 行） | 人口 150→60、每任务 50→15、报告文案 |
| `source.py` | 从 056 复制（约 90 行） | 只改 suite 常量与 task 注册表 |
| `evaluation.py` | 从 056 复制（约 500 行） | 人口 60、只允许 `--model base`、去掉 h0/h1 分派；plan 的 bank 身份改由 config 提供并在加载时校验 |
| `__main__.py` | 新写（约 25 行） | `build` / `run` / `inspect` |

### A.3 关键事实：不需要 bind / 环境身份重算

055 的 3 个任务目标不同，但共用**同一个** `environment` 记录（`_inputs` 从 config 读取，`build_source` 断言 `bridge.environment_identity(20)` 与之一致）。说明 environment identity 只覆盖场景/机器人/控制频率，不含目标谓词。因此探针任务沿用同一 `environment` 记录即可，不需要额外的 bind 步骤。

### A.4 任务与人口

| task key | A 预放 | B 剩余 | 用途 |
|---|---|---|---|
| `probe_soup_milk` | alphabet_soup_1 | milk_1 | 冲突语境（汤罐→本应番茄酱） |
| `probe_soup_orange_juice` | alphabet_soup_1 | orange_juice_1 | 同上，换目标 |
| `probe_tomato_milk` | tomato_sauce_1 | milk_1 | 冲突语境（番茄酱→本应汤罐） |
| `probe_tomato_orange_juice` | tomato_sauce_1 | orange_juice_1 | 同上，换目标 |

每任务 15 个状态（canonical source index 0–14），共 60；`initial_mask=[true,false]`；指令为完整 `put both the {A} and the {B} in the basket`；H520 / retention 150 沿用。

### A.5 运行与输出

- 只跑 `base`（原版 OFT，无 adapter），60 条，seed7 / chunk8 / 原评分与证据。
- 输出：逐任务成功率、首选抓取物体分布、`n_steps`、A 保持率、native 完整目标率；控制台实时完成数。
- 报告明确标注"能力探针，不是方法结果，不进入任何 450/900 正式分母"。

### A.6 定向 CPU/fake 验收

1. 4 个任务键/指令/谓词与 BDDL 派生正确，milk/OJ 在 canonical `:objects` 中；
2. 每任务 15、总 60，缺一/重复/错位在模型前拒绝；
3. `environment` 记录与 055 同源一致，不改 055 输入；
4. 假 60 人口、只 base、成功/错抓统计正确；
5. 评分使用新 goal_specs（milk/OJ），不是 butter；
6. 输出保护与失败保留，技术错误不记模型失败；
7. 055/056 文件、bank、结果字节不变。

### A.7 判定与后续

- 任一任务 ≥20% → 该 B 走过滤式自生成（G1a）；
- 全部 <5% → 直接进 G0b 重定向；
- 5–20% → 加大尝试数（≤400 次/B 物体）或直接重定向。

### A.8 命令模板（部署后由用户启动）

```bash
# 1) 构建 60 个探针状态（只仿真，不加载模型）
python -u -m egrs.composition057 build \
  --config "$LNA057_CONFIG/probe_build.json" \
  --output "$LNA057_ROOT/probe-bank-001"

# 2) 探针（只 base，60 条）
python -u -m egrs.composition057 run \
  --config "$LNA057_CONFIG/probe_eval.json" \
  --model base \
  --output "$LNA057_ROOT/probe-run-001"
```

> 变量与完整路径在部署阶段填好；本附录不含服务器私有路径。

### A.9 部署清单（隔离部署时执行）

1. 从当前已部署的 056 code 目录复制一份为新的 `task057-*` 目录，保持 055/056 包字节不变；
2. 将 `egrs/composition057/`、`configs/composition057/` 与 `tests/test_composition057.py` 放入该目录；
3. 填 `probe_build.json`：`benchmark_root`/`canonical_bddl`/`canonical_initial_states`/`environment_config` 直接复用 055 构建时的同一组路径（同一 canonical Scene2 资产）；
4. 填 `probe_eval.json`：`source_bank` 指向新 build 输出、`base_runtime`/`reporting_root` 复用 056 的原版路径；
5. 构建阶段在原 OFT 环境（只仿真、不加载模型）；探针阶段切原 simulation 环境（与 056 评测一致）；
6. 构建完成后先 `inspect` 确认 60/60 ready，再启动探针；失败保留、不重试覆盖。

预期：构建 60 状态约 15–30 分钟；探针 60 条约 1–2 小时（含视频/证据）。


---

## 附录 B：G0a 探针结果（2026-11-27，真实运行）

部署于 `/HUBU-AI096/zp/ICML/Learning-Not-to-Act` 的隔离 `code/task057-probe-v1`，真实阶段由 Codex 在用户提供访问后启动。

- 构建：**60/60 ready，失败 0**，`inspect` 通过。
- 探针：**60/60 执行完成，0 成功**（4 任务各 0/15），全部跑满 520 步；完整性错误 0。
- **Base 从未抓取指令点名的牛奶/橙汁：0/60**。首抓全部回退到训练配对伙伴：
  - 汤罐已入篮（应抓牛奶/橙汁）：首抓奶油奶酪 **11/15**、番茄酱 1/15，3 条无抓取；
  - 番茄酱已入篮（应抓牛奶/橙汁）：首抓字母汤罐 **13/15**，1 条无抓取。
- 结果与 056 的配对补全一致：同场景只换指令，模型仍按训练伙伴抓取；对未见目标连一次尝试都没有。
- **判定：<5% → 走 G0b（演示段重定向）**；过滤式自生成不可行。

---

## 附录 C：G0b 资格门结果（2026-11-27，真实运行）

脚本化抓放（privileged 位姿 + OSC 伺服 + 高位释放；释放前用物体自身对准篮心；成功 = A 保持 + B 在篮 + 篮筐位移 <1cm）：

| 目标 | 成功/尝试 | 合格率 |
|---|---|---|
| `milk_1` | 17/20 | **85%** |
| `orange_juice_1` | 2/20 | **10%** |

- 两个物体抓取均 **20/20 成功**；失败集中在释放落点砸在篮沿（milk 4 条、OJ 18 条）。
- **判定：milk 通过资格门（≥20%），OJ 不通过（<20%）**。v1 干预只使用 `milk_1` 作为反事实剩余目标；OJ 暂缓（需要不同抓取/释放策略或更大篮筐）。
