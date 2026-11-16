# Task044：官方SOG10的P1/P2初始语义提示诊断

本轮位于方法库`No1dry/Learning-Not-to-Act`，基于accepted PR17@`7d28d515be610f33f959f36d25623e86796671ce`。只使用原官方SOG10，没有H0/H1、042或其他研究adapter。P1在原完整指令后附加固定的初始A已完成事实；P2仅给冻结的B指令。两者都使用原九任务90个10初态和完整A+B评分，A保护/错抓/释放/放置判据保持。P1/P2是获得额外初始语义信息的诊断，不是自主RGB识别结果、公平无提示主方法或理论上界。

软件交付包含独立`egrs.prompt044`、两个配置模板和串行脚本。X仅做定向CPU/fake，未SSH、部署、下载/加载真实7B、运行物理或启动真实评测。以下是Codex验收隔离部署、填好现存路径后，**用户**执行的命令；预算许可不表示代理代跑许可。

## 冻结输入

- 官方模型：`moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10@638918f3d1c2e43a39a8a20772bdb8b91835e4b7`；OFT源码`e4287e94541f459edc4feabc4e181f537cd569a8`，`libero_10_no_noops`。沿原base-runtime与官方动作头/proprio投影，双RGB、中心裁剪、proprio8、native封装/分词、chunk8、seed7、H520、不量化。
- [九任务冻结语言表](../collaboration/evidence/044_prompt_manifest.json)，文件SHA `e648ef202c31e6e99e14478f6ec36952a1791d2187bf023a224b25974f669566`。逐字节验证，不改换行/重新序列化；Git为该文件关闭文本换行转换。原instruction须精确命中，未知/冲突/错variant拒绝。P1为`original_instruction + '. ' + p1_added_initial_fact`，P2为`p2_instruction`。双壶只用集合语义，无隐藏实例编号。
- 现存043 H1正式plan仅作任务/来源/runtime/core协议元数据，原文件SHA `bafc7238da1ed94e8a1b6d4b98ce7f9d41bb59bad887be2d7de9e1d2ce5d68df`，不加载其研究权重或继承结果。抽取原36个10执行单元/90episode，原source/完整goal_specs/初态保持。expected10投影SHA `b53418726b09cf533bff06a162a2407bd6316bc0df6e909a4801bac72e73c7a5`。
- 原core revision `d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`、reporting `d2afce4eb074b777364daddea2c08bd70731865f`及旧bridge依赖按参考plan/原manifest核验，不按文件夹名字猜版本。原reader验证源、动作、视频及环境；直接使用原二元评分，不构造假adapter/空00通过036入口。

批准证据还给出了ten task input projection摘要，但没有列出其具体字段投影。程序以**完整原plan文件SHA**硬绑定元数据，记录本实现完整ten任务投影及批准声明；未获得可核对定义时不冒称二者已匹配，也不猜测字段制造准入失败。完整plan及原source一致性验证保持严格。

## 配置准备（Codex验收后）

沿现有simulation与policy worker环境，不升级依赖，不编辑全局安装包/冻结core。部署方法包需在两环境指向同一验收044源码。现有输入路径保持，不移动初态或更改参考plan字节。配置支持明确环境变量或相对配置目录路径，未展开变量/多余字段/错误类型拒绝。

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate EXISTING_SIMULATION_ENV
export LNA_ROOT=/path/to/Learning-Not-to-Act
export LNA_CODE="$LNA_ROOT/code/task044-ACCEPTED_COMMIT"
export LNA_REFERENCE_PLAN=/path/to/unchanged-043-h1-evaluation/plan.json
export LNA_CORE=/path/to/accepted-core-d8541ef4
export LNA_REPORTING=/path/to/accepted-reporting-d2afce4e
export LNA_LEGACY_CORE=/path/to/unchanged-legacy-bridge-checkout
export LNA_RUNTIME=/path/to/unchanged-official-sog10-runtime.json
cd "$LNA_CODE"
```

由后续部署人在上述**既有的两个环境**中接线方法包（本轮未执行这些部署命令）：

```bash
# simulation环境已激活；worker解释器取自原runtime，保留venv symlink原路径。
export LNA_WORKER_PYTHON="$(python -c 'import json,os; print(json.load(open(os.environ["LNA_RUNTIME"]))["python_executable"])')"
python -m pip install --no-deps --no-build-isolation -e "$LNA_CODE"
"$LNA_WORKER_PYTHON" -m pip install --no-deps --no-build-isolation -e "$LNA_CODE"
```

原子进程从core目录启动并设置自己的PYTHONPATH，仅改变外层工作目录不足以让worker导入044。两环境必须通过既有方法包安装机制指向同一验收源码；不修改全局包源码或升级依赖。这里不加载模型、不运行额外前向，也不改原runtime的解释器字段。

将库内`configs/prompt044/evaluation.p1.example.json`与`evaluation.p2.example.json`填写为`$LNA_ROOT/configs/task044/evaluation.p1.json`与`evaluation.p2.json`。复制时把`prompt_manifest`改为`$LNA_CODE/collaboration/evidence/044_prompt_manifest.json`的实际绝对路径；两个配置仅variant不同。reference_plan指向现成已批准JSON，base_runtime指向原官方模型runtime，不指向H0/H1的worker runtime。`adapter_options`是原官方loader已有选项，不能添加研究adapter参数。

新输出及marker应在独立`runs`/`launches`树，不能在旧data根、旧run、模型权重、源码/依赖或配置输入目录内部。已有输出/marker拒绝覆盖；失败现场保留，不自动清理重试。

## 用户一条命令串行P1→P2

在上述既有环境与目录中配置新路径：

```bash
export LNA_P1_CONFIG="$LNA_ROOT/configs/task044/evaluation.p1.json"
export LNA_P2_CONFIG="$LNA_ROOT/configs/task044/evaluation.p2.json"
export LNA_P1_OUTPUT="$LNA_ROOT/runs/task044-p1-eval-001"
export LNA_P2_OUTPUT="$LNA_ROOT/runs/task044-p2-eval-001"
export LNA_044_MARKER="$LNA_ROOT/launches/task044-p1-p2-001"
bash scripts/prompt044/run_both_sequential.sh
```

脚本调用`python -u -m egrs.prompt044 run-both`。两个独立新进程/worker，各90条，P1进程正常退出且正式报告完整后才启动P2。每组原始predict最多5850次，两组合计11700；只按原正式rollout执行，没有额外观察probe。marker独占创建并记录配置SHA、开始/完成/失败；首组失败、返回非零或报告不完整都停止，不重试、不启动次组。完成后再次执行也拒绝。真实恢复或重跑需交回用户决定，不支持隐式继承其他run结果。

需后台时，使用下列**替代启动**，不要与前台命令重复执行：

```bash
mkdir -p "$LNA_ROOT/logs"
nohup bash scripts/prompt044/run_both_sequential.sh \
  > "$LNA_ROOT/logs/task044-p1-p2-001.console.log" 2>&1 &
tail -n 10 "$LNA_ROOT/logs/task044-p1-p2-001.console.log"
```

单组独立入口供明确需要时使用；不在串行组启动后重复运行：

```bash
python -u -m egrs.prompt044 evaluate \
  --config "$LNA_P1_CONFIG" --output "$LNA_P1_OUTPUT"
# P2：替换为LNA_P2_CONFIG与LNA_P2_OUTPUT
```

正式入口自带必要原来源/身份/计划核验，无需用户先另跑plan、MVP、预检或评分进程。训练、新初态/回放、标签/索引、00、P0重测、新seed、额外提示搜索均为0。P0仅历史22/90=24.44%引用；当前没有可绑定的P0逐episode输入时报告aggregate-only，不编造配对。

## 语言审计、进度及正式结果

wrapper在实际`base.predict`调用前持久记录`source_instruction`、`model_instruction`及各自SHA、variant/manifest SHA、episode/query序号；调用失败已计账，不退款。固定初始提示整episode不变，不根据A后续破坏或逐帧GT更新；底座仅收到原允许RGB/proprio字段。实际native formatting/tokenization由原官方predict执行，日志记录的是其输入字符串，不声称这些字符串等于tokenizer最终token序列。

独立prompt audit与原task_run attempts/raw queries绑定，包括零query的初态失败；原完整任务instruction/goal_specs保留给评分。actual加载的base组件/统计/推理来源metadata保持，并增加`prompt_variant`、manifest SHA及`deployment_initial_semantic_information=true`，不会冒充H0/H1或无提示策略。逐episode仍保存原RGB/proprio/actions/raw及全视频。

每组逐episode记录`episode_started`，`progress.json`的完成数量/90与百分比在原执行单元完成后更新（旧六任务为每单元10条，新三任务为每单元1条）；正式核验前不把执行100%称正式100%。最终`summary.json`/`report.md`给固定90分母的完整性、总体与每任务正式SR和P0历史引用；技术错误/缺工件使报告不完整，不伪造成功。底层UNKNOWN保留原诊断，按原binary-compliant-success-v1算不成功，不能删分母。P2下A破坏或错抓仍失败。

本轮CPU/fake证据及完整命令见[044回复](../collaboration/responses/044_round1.md)。下一步Codex验收并隔离部署/填配置，用户亲启正式180；所有旧数据、模型、分数、视频及失败保留，无自动merge或删除。
