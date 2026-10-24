# EGRS 安装、运行与交付边界

本次交付是 016 的软件实现。独立选择器在 query 边界读取双相机观测，维护可撤销的目标证据，通过稳定语言调用冻结 actor。目标框用于选择和反馈，不能约束机械臂空间。合法但错误的预测是方法失败；非法 schema、进程或日志错误保留为 technical/partial。

真实数据、标注、Qwen/VLA forward、训练和模型评测均未执行。下面的真实运行入口供用户后续启动。CPU 测试不证明研究方法有效，也不证明 CUDA/真实 processor 已兼容。

## 1. 依赖及解释器隔离

推荐使用已复现模型的各自环境：controller/eval、selector、每个 actor 保持独立。要求 Python >=3.10。安装方法包到**实际加载 factory 的所有解释器**；只在父 shell 设置 `PYTHONPATH` 无效。

```sh
git clone https://github.com/No1dry/Learning-Not-to-Act.git
cd Learning-Not-to-Act
# 切换到本次交付 PR 的提交后安装。
/path/to/controller/python -m pip install -e .
/path/to/actor/python -m pip install --no-deps -e .
# actor 保留已验证的 NumPy/Pillow/模型依赖，不安装 selector requirements。
/path/to/selector/python -m pip install -r requirements-selector.txt
/path/to/selector/python -m pip install --no-deps -e .
```

也可 `python -m pip wheel . --no-deps` 后在各解释器安装相同 wheel。wheel 只分发 `egrs`，不覆盖 `benchmark`，不包含测试、权重或原始数据。固定候选 catalog 随包安装。公开仓库没有替研究项目追加许可证；eval core/官方模型代码和权重继续使用其原许可。

依赖清单：

| 内容 | 身份 / 要求 |
|---|---|
| eval core | [LIBERO-Remain-Eval](https://github.com/No1dry/LIBERO-Remain-Eval)，固定 `515e87d9b93ab838428791273a0f3020d6f56e9c` |
| 本次实际核对的可读参考 | [LIBERO-Remain](https://github.com/No1dry/LIBERO-Remain/tree/c6dc98de0c54517c976057598b60f4cedf7fa3e5)，固定 `c6dc98de0c54517c976057598b60f4cedf7fa3e5` |
| selector base/processor | [Qwen2.5-VL-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/tree/66285546d2b821cf421d4f5eb2576359d3770cd3) |
| selector LoRA | 用户后续训练得到 `checkpoint-N/adapter`；需要同级 `state.json`、`COMPLETE` |
| actor | 原环境、官方代码、对应 suite checkpoint/normalization、原完整配置；方法不替换这些身份 |
| eval assets | 固定 core 所需状态包、XML/BDDL、模型资源及视频/evidence 配置；本库不分发 |

本次无法读取新 eval 私有库，不能宣称核验过该 pin。静态检查严格核对本地 Git HEAD、benchmark 修改/影子源码和所用核心文件哈希。需要参考导出时，必须显式使用参考 revision 加 `"allow_reference":true`；运行身份标为 `reference_only:true`。不要把参考目录冒称新库。

把 [core.example.json](../configs/core.example.json) 复制到本地 `core.json`，填写实际 checkout 根目录。也可设置 `git_executable` 为 Git 可执行文件。新 core 按其自身安装文档安装 controller/native 依赖；selector 只通过原 whitelist/transport 的轻量 API 校验 sensor。

## 2. 组合原 actor 配置

`egrs compose` 读取完整原 actor JSON，保留原 factory、suite、checkpoint_source、adapter_options、execution 和 runtime。路径按原 actor JSON 所在目录解析。不要重新手填一个只含模型名的伪配置。

| actor | `--capability` | 原 factory（前缀 `benchmark.remaining_goals.adapters.`） |
|---|---|---|
| OpenVLA | `openvla` | `openvla:make_policy` |
| OpenVLA-OFT | `openvla_oft` | `openvla_oft:make_policy` |
| π0 | `pi0` | `openpi:make_policy` |
| π0.5 | `pi05` | `openpi:make_policy` |
| GR00T N1.7 | `groot_n17` | `groot:make_policy` |
| UniVLA | `univla` | `univla:make_policy` |

OFT/OpenVLA/OpenPI/GR00T 已按固定参考适配器静态核对无目标缓存，目标变化时显式 no-op；不调用会重建 OpenPI RNG 的 episode reset。UniVLA 只清 `_history` 与 decoder 聚合缓存。新适配器必须明确提供 `custom_hook` 和 `on_goal_change(old,new)`，不能回退到全 reset。

原 OFT SOG10→LIBERO90 的 `suite_transfer` 留在嵌套 actor 原配置中；facade 外层不携带它。worker 内按原 factory 验证 transfer，再检查实际 normalization/provenance。单独保留每个 suite 的配置、解释器、checkpoint 和视频/core 输出。

```sh
python -m egrs compose --actor actor-oft-libero90.json --core core.json \
  --selector configs/selector.json --selector-python /path/to/selector/python \
  --adapter /path/to/selector-run/checkpoint-3/adapter \
  --capability openvla_oft --variant full \
  --run-dir /path/to/new-run/method --output local-method.json
python -m egrs inspect --config local-method.json
```

`compose` 只写新 JSON；不下载、加载模型或运行评测。`inspect` 只检查配置和本地文件，缺依赖返回码 2；存在文件不等于模型/CUDA/014 联调已就绪。除 selector model/processor 的 Hugging Face ID 外，运行路径填本地路径。方法配置中的相对路径按该 JSON 目录解释，解释器符号链接不被解析成 base Python。

消融配置通过同一命令生成，避免复制后错改底座配置：

| `--variant` | selector 配置 | `--adapter` | 实际行为 |
|---|---|---|---|
| `baseline` | 不传 selector 相关参数 | 不传 | 原完整指令，跳过选择器 |
| `no_lora` | `configs/selector.json` | 不传 | 相同 Qwen base，未训练任务 LoRA |
| `full` | `configs/selector.json` | 完整训练 checkpoint | 完整方法 |
| `no_history` | `configs/selector_no_history.json` | 对应训练 checkpoint | 同时去过去图像、文本、命令和规则历史 |
| `no_role` | `configs/selector_no_role.json` | 独立消融 checkpoint | 训练时去角色/绑定监督，按该 checkpoint 推理 |

`no_role` 不接受仅配置为 false、实际用完整训练权重的声明。推理检查保存配置的 role/use_history、base/processor pin 和 adapter 文件哈希。所有训练/推理默认关闭 packing。训练与数据命令、字段 provenance、最终 token mask 和预算规则见 [data_training.md](data_training.md)。

配置字段与默认值：

| 字段 | 意义 |
|---|---|
| `policy_factory` | `egrs.policy:make_policy` |
| `core` | 显式依赖路径与 revision，可选 `allow_reference`、`git_executable` |
| `output_dir` | 必须不存在的新方法 sidecar 目录 |
| `variant`, `history` | 上述消融身份；禁用 history 必须用 `no_history` |
| `memory` | `sat_queries:2, expiry_queries:3, max_records:12` |
| `actor` | 原完整配置，嵌套传入原 worker |
| `goal_change_capability` | 上表值，必须匹配原 factory |
| `selector` | selector 配置、`adapter`/`lora_path`、独立 `runtime` |
| `runtime.python_executable` | 已安装方法包的实际 Python 文件 |
| `runtime.startup_timeout_seconds` | 默认 1200；正有限值 |
| `runtime.predict_timeout_seconds` | 默认 180；包括管道发送与响应等待 |
| `runtime.cuda_visible_devices` | 可选，独立传给各 worker |

## 3. 与原 core 对接

接口是普通 Python factory，不是新评分器。调用者可以直接传入 `load_config()` 的返回值：

```python
from egrs.configuration import load_config
from egrs.policy import make_policy
from egrs.core import run_episode

config = load_config("local-method.json")
policy = make_policy(config)  # 用户启动真实阶段时才调用：会启动模型 worker
try:
    # env、episode、recorder、evidence、identity 均由固定 core 原流程创建。
    # 原 run_episode 负责 policy.reset；这里不另重置环境或模型。
    result = run_episode(env, policy, episode, horizon=520,
        confirmation_steps=4, max_chunk_steps=8,
        recorder=recorder, evidence=evidence, identity=identity)
finally:
    policy.close()
```

此片段是现有 core 驱动程序的集成点，变量由驱动程序提供，不能独立作为批处理命令。`egrs.core.run_episode` 只调用原 runner 后结束方法 sidecar；若调用原 runner，调用者必须显式执行 `policy.finish_episode(result)`。忘记 finalize 或发生技术错误会留下 partial。finalize 写入失败抛出 `SidecarFinalizationError`，其中 `partial_result` 保留原 core 返回值。

**014 仍需评测侧对接**：通用批处理接收自定义 method factory、每 suite runtime、嵌套 method/selector/actor 身份；保存原 core JSON、evidence 和完整视频，调用 finalize，保留 close 异常。目前不提供一条未经验证的“全模型批量评测”命令。冻结的 H520、20Hz、K4、sticky 事件、实际路径与主指标均由 core 保持。core 参考仍限制 chunk<=8；其他 actor 的实际 chunk 配置由 014 与冻结协议确定，不擅自扩大。

actor 仅收到原 whitelist 后的当前传感器和所选语言，输出动作交回原 core 处理。方法不改裁剪、归一化、解码，不向 actor 提供 bbox、mask 或物理真值。命令/夹爪闭合不能当作执行或抓取证据；选择器不能读取未来帧或 core 逐步指标。

SAT 两次和不可见三次均按 **query** 计数，不能宣称等价于每种底座相同的物理时间或 K4。运输完成信念需要新关系和释放证据；新反证、换实体或到期撤销。当前可信持物目标优先，否则选当前可见 UNSAT；无可靠目标时原指令回退，没有 STOP/零动作替代。

## 4. 日志与离线审计

每次运行写 `metadata.json`，每 episode 写独立 JSONL：registry、query 开始、调用尝试/结果、预测、短历史、选择/回退原因、实际 actor 文本、返回 chunk、观测哈希。开始即新文件、每条 flush/fsync，不覆盖旧结果。不把失败重跑成 baseline。

`supplied_snapshot_ids` / `supplied_image_count` 是方法提交量；`selector_input_audit` 是选择器预算裁剪后的实际保留/丢弃快照、图像数和 token 数。无实际计量时写 null，不把提交量冒称模型使用量。失败调用也计 attempted calls；未响应的调用保留 unfinished。输入预算裁剪不删除当前图像/完整目标/完整答案。

```sh
python -m egrs sidecar --method /path/to/run/method/episode-000001.jsonl \
  --core-result /path/to/run/core-result.json
```

join 使用 query ID、返回 chunk 和观测哈希；实际步数仅从 core `executed_steps` 汇总。方法没有读取这些量作为策略输入。`complete` 仅指日志/core 执行记录完整，**不等于任务成功**。主指标仍为原合规成功率与成功条件路径；selector 准确度或 SFT dev loss 不替代它们。

partial、日志损坏、worker 崩溃、加载和 schema 错误保留，不静默重试。`close()` 异常必须由驱动程序保留为运行失败；即使已有完整 episode，也不能据此把整个运行报告成成功。

## 5. 定向 CPU/fake 验证

测试依赖 controller 的 pytest、NumPy、Pillow，以及单独 CPU toy 测试的 torch/h5py。测试没有加载真实研究模型。设置固定参考 checkout 后运行；Git 不在 PATH 时设置 `EGRS_GIT`。

```sh
export EGRS_CORE_ROOT=/path/to/LIBERO-Remain-at-c6dc98d
export EGRS_GIT=/path/to/git
python -m pytest tests/test_runtime.py tests/test_policy.py tests/test_rpc_config.py tests/test_delivery.py -q
python -m pytest tests/test_data_training.py -q
python -m pytest tests/test_core_integration.py -q
python -m pytest tests/test_installed_workers.py -q
```

Windows PowerShell 用 `$env:EGRS_CORE_ROOT='...'`，若系统临时目录权限有问题，给每次 pytest 不同的 `--basetemp=.work/pytest-<run-id>`。本次 Anaconda 中把 Torch 与 core 的 NumPy/MKL 几何测试混在同一进程曾发生原生退出，分进程执行均通过；不能把该退出说成全部单进程测试通过。

installed-workers 测试构建并安装实际 wheel 到临时环境，从仓库外启动真实两个 RPC，使用明确的 CPU fake backend；检查目标变化 hook 和 sidecar，且没有临时父 `PYTHONPATH`。core 集成测试直接调用原 headless runner/environment/evidence/metrics，以合成 env 驱动，不复制成功判据；需要固定参考 checkout 中的原 CPU fixture。

下一步执行者：X 提交本轮软件 → Codex 集中审查与 014/部署命令对接 → 用户确认标签/资源后启动真实阶段。软件准备与实现可以交付，真实数据准备、标注、训练、方法评测目前全部 0%。
