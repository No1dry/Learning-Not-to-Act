# 016 round1：完整 EGRS 软件交付

作者：X。日期：2026-10-22。状态：实现与定向 CPU/fake 验证完成，提交本仓库 PR，等待 Codex 集中审查；不自动合并。

基线：`891ef3605a389977e91e86871c2af89867776f33`。本地实现提交：`17d94eb2d8ac5bbd7fadadea281b1747b4bc2ffa`。GitHub 通过登录的网页会话发布，远程提交身份以本 PR 历史为准；本地开发提交与逐目录网页提交可能不同，交付后核对文件树。没有使用或提交会话里的旧 token。

## 1. 交付内容

| 模块 | 文件 | 已实现行为 |
|---|---|---|
| 固定目标/证据契约 | `egrs/contracts.py` | 指令生成一次 registry；完整目标集合、实体/区域/query 绑定、机制释放适用性；原 sensor whitelist；拒绝 GT/未来/非法字段 |
| 可撤销历史/调度 | `egrs/memory.py` | 两次新 SAT＋运输释放；反证/换实体/三次无支持撤销；在途保持、可见 UNSAT、原指令回退；无 STOP |
| 方法与双 worker | `egrs/policy.py`, `rpc.py`, `worker.py` | 独立 selector/actor 进程；sensor/context 分离；稳定语言；无隐式重试/真实动作修改 |
| 冻结 actor facade | `egrs/actor.py` | 原 factory/config/normalization 保留；目标变化专用缓存处理；OFT transfer 嵌套原验证；未知适配器需要明确 hook |
| core 接入 | `egrs/core.py` | 固定依赖/源码检查；原 headless runner 薄调用；原 evidence/metrics；无评分副本 |
| 方法日志 | `egrs/sidecar.py` | registry/预测/历史/选择/命令；调用尝试/成功/失败；真实输入预算审计；query 对齐及 partial 保留 |
| 数据与标签 | `egrs/data.py`, `datacli.py`, `data/catalog.json` | 固定 20 文件候选；已有 RGB 提取；外部标注导入导出、UNKNOWN/弱标签/provenance；同源组 split 与独立计数 |
| selector 训练/推理 | `egrs/selector/` | 显式固定 Qwen2.5-VL；语言 LoRA；真实优化/dev/save/resume 代码；最终多模态 token mask；预算裁剪与记录；推理 JSON/引用校验 |
| 安装/配置/入口 | `pyproject.toml`, `egrs/cli.py`, `configuration.py`, `configs/` | 可安装 wheel；compose/inspect/sidecar；五种消融；独立解释器；checkpoint 设置与文件身份检查 |
| 文档 | [runtime](../../docs/runtime.md), [data/training](../../docs/data_training.md) | 必需文件、环境、路径、全部入口/参数、真实运行命令及未联调边界 |

生产入口不是 fake 训练替身：真实入口调用 Transformers/PEFT 加载固定模型、语言投影 LoRA、AdamW、训练与 dev loop，保存 adapter、processor、optimizer/RNG/config/data identity 并恢复。本轮仅在测试中注入 CPU toy 网络和 fake processor，未调用真实模型。

## 2. R1—R4 和本轮审查闭环

- R1：registry 来源仅原指令，之后完整引用固定目标。合法但可能错误的语言分解/实体判断仍属于方法行为，不从 task_id 查答案。fresh 证据不能用 B 实体字段更新 A 的缓存信念；历史复述不能充当第二次新 SAT。运输完成所需释放支持长期不可见也会到期。
- R2：actor worker 内比较实际文本；UniVLA 清 latent/history 与 decoder 聚合，不重置 RNG/权重；固定无缓存路径 no-op。原 OFT transfer 不带到 facade 外层，并在内层验证原 factory 和实际 metadata。
- R3：selector sensor 每帧走原 whitelist；context 只含原指令、registry、过去预测/命令。安装到实际 worker 解释器，真实 wheel 的仓库外双进程 fake 检查通过。
- R4：弱/未确认结论及其证据在 teacher forcing 前中性化；确认 UNKNOWN 保留监督。完整 chat template＋视觉 token 展开之后核对最终 input IDs，再用精确 token offset 形成字段 mask；不按字符长度估 token。no_role 真正去角色/绑定监督，checkpoint 训练身份必须匹配，不能仅改运行日志。

独立代码审查指出并已修复：跨实体记忆更新、选择器 close 异常吞掉、未跟踪/忽略源码遮蔽固定 core、失败调用未计数、裁剪前图像数误当实际输入数。针对这些错误补了定向检查并复审；最终没有剩余 Critical/Important 阻塞意见。只审查软件正确性，不将其当研究效果验证。

## 3. 定向验证结果

2026-10-22 最终运行，Python 3.12.7，Windows CPU：

| 检查组 | 结果 | 防止的具体错误 |
|---|---:|---|
| runtime / policy / RPC / delivery | 20 passed | 错目标/实体记忆、GT/未来泄漏、错误重置、静默 baseline、partial 假完整、transfer/config 改写、core 影子源码 |
| data / selector training | 24 passed | 弱标签伪真值、teacher forcing 泄漏、token mask 错位、历史/答案静默截断、同源 split 泄漏、保存/恢复和消融身份错误 |
| 原 core fake 集成 | 2 passed | 评分漂移、命令长度冒充执行长度、视频/evidence/query 不对应、技术错误被算成功 |
| 安装后的双 worker | 1 passed | 只在仓库 cwd/PYTHONPATH 下可用、实际 worker 找不到 factory、跨目标缓存 hook 未执行 |
| **合计** | **47 passed** | 分进程定向验证 |

命令见 [runtime §5](../../docs/runtime.md#5-定向-cpufake-验证)。最终四组实际结果分别为 20/24/2/1，全为退出码 0。wheel 构建/安装成功；新目录内运行双 worker，原 core actor worker 与 selector worker 都能导入安装后的 `egrs`。CLI help/静态 inspect 和 train dry-run 不加载 native/模型；缺 train/dev/output 时明确 `ready:false`。

core 集成使用原 `HeadlessMeasurements`、runner、evidence schema/validator 和 scorer，加显式 synthetic env/视频 recorder。返回 10 条动作、core 接受 8 条并实际执行 6 步的用例核对原路径/帧数和 sidecar；没有制作真实 mp4 或仿真。

训练测试贯穿生产 `train.main` 的 toy CPU 梯度、三轮 train/dev/save，再从 checkpoint1 恢复到新目录；这些 toy epoch **不是实际研究训练量**。

一次把 Torch/h5py toy 测试和 core 几何测试混在同一 Anaconda 进程时，NumPy/MKL 原生退出；已保留事实，四组分进程执行通过，没有宣称该混合执行通过。没有安装/切换真实 GPU 软件来掩盖问题。

## 4. 核验边界与实际完成数

| 项目 | 本轮实际数量 / 状态 |
|---|---|
| 真实公开 demo 下载/读取/恢复/render | 0 |
| 真实标签、人工作业、教师调用 | 0 |
| 真实 tokenizer/processor 校验 | 0；本地未安装 Transformers/PEFT，fake processor 不能替代其证明 |
| Qwen/VLA 权重加载、forward、特征提取 | 0 |
| 真实 LoRA 训练/训练 epoch/完成 checkpoint | 0 |
| 新方法模型评测 episode | 0 |
| 20 文件 catalog | 静态候选模板；不是 200 条来源或 1,200 窗口已齐备 |

实际读取的 core 是 `LIBERO-Remain@c6dc98de0c54517c976057598b60f4cedf7fa3e5` 参考导出。所要求的 `LIBERO-Remain-Eval@515e87d9b93ab838428791273a0f3020d6f56e9c` 此环境仍不可匿名访问；代码支持其显式依赖身份，但本轮没有核验它。`allow_reference:true` 必须显式设置，metadata 保留 reference_only。

## 5. 交给 Codex 的对接项

1. 审查本 PR；之后由 Codex 合并/部署决策，X处理有依据的修正。原015 PR、历史独立稿/比较稿与原结果不改、不自动合并。
2. 014 批处理接受 `egrs.policy:make_policy`、独立 suite runtime 和嵌套身份；沿用原 H520/20Hz/K4/sticky/视频/路径指标；调用 `finish_episode` 并保留 `close` 异常。方法不新增评分器或伪造批处理命令。
3. 取得可读 eval pin、真实资产、各 actor 的原完整配置和对应 checkpoint。静态 inspect 不替代 package/CUDA/真实 processor 兼容验证。
4. 标签来源、排除六个复合任务/语义等价/eval 同源的外部 attestation、真实物理祖先未知、source/window/query 覆盖均需真实清单支持。缺标签时不补造或随机替换。不以 55—80 人时承诺作为当前软件交付门槛。
5. 确认设备和预算；Codex准备后续真实数据/训练/评测命令，用户亲自启动。本轮不启动任何真实阶段。

进度：**软件准备100%，软件实现与定向验证100%（待Codex接受），真实数据准备/标注0%，训练0%，新方法评测0%。** 下一步操作和执行者：Codex集中审查与014部署对接；X按审查修正；用户另行确认并启动研究运行。
