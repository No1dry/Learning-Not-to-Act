# 030 v2 round1｜代码交付与 CPU/fake 结果

2026-11-02，X，submitted / 待 Codex 审查。已先 fetch main `da34ff4`，按030 v2工单与九任务方案直接实现；未复活旧selector。

- 方法 [PR9](https://github.com/No1dry/Learning-Not-to-Act/pull/9)，分支`x/task030-v2`。
- 实现提交：`46dac7c7f7af23c6052b5890ce3b2d32c1886274`；本回复随后作为文档提交附在同PR。
- 034独立 [PR15](https://github.com/No1dry/LIBERO-Remain/pull/15)，报告实现固定`d2afce4eb074b777364daddea2c08bd70731865f`，
  交付head `cb8aca6aca0864bb9a304bdf2471b5025b371479`，两者报告包字节相同。
- 执行/source/物理core继续固定`d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9`，未merge PR14或修改冻结目录。

## 已实现

| 文件/入口 | 行为与边界 |
|---|---|
| `egrs/augmentation/data.py`, `export.py` | 一个导出入口、原HDF索引与RAW/PROGRESS/ATOMIC三视图；显式字段/时间/图像方向/动作/夹爪/归一化映射，整轨分组、已知重复合组，固定原200/160:40，新增每任务前N≤20、九任务精确scope绑定；尾mask不跨原子边界、不复制末动作。 |
| `data_scope.json`, `configs/augmentation/data*.json` | 固定九任务官方名称/目标/双壶保持约束的纯数据摘录，来源与可信证据模板；模板未填，不冒称已有380来源。 |
| `training.py`, `oft.py`, `adapter_identity.py` | 两个固定1000-update配置，原SOG10已合并底座及原head/proprio/processor/stats；仅语言完整q/k/v/o路径原生r16/alpha32/dropout0 LoRA，原head梯度可回传；bf16/micro1/accum16/checkpointing；有效动作标量L1；同RAW dev选checkpoint，完整adapter/optimizer/scheduler/RNG恢复。 |
| `evaluation.py`, `dependencies.py` | 普通adapter worker入口、A90/C36固定选择、原完整指令/RGB/proprio白名单，原core执行/证据/视频/评分复用；新adapter身份与基线lineage分开，读回校验adapter、视频及动作/query证据；不接受既有输出重跑。 |
| `core_files.json`, `reporting_files.json` | 明确依赖路径和源文件SHA锁，不复制评分器，不假定main含未合并实现；准确绑定包避免034 checkout旧benchmark遮蔽冻结core。 |
| `docs/augmentation_commands.md` | 环境、依赖/模型链接、一个导出、两组训练、A90/C36评测与另存报告的实际命令，所有flag存在。 |
| `docs/augmentation_data.md` | 数据/证据契约、已具备与待提供项、回退和覆盖限制。 |

RAW-control与Progress-Aug使用同一来源/分组和RAW dev。请求50/25/25，缺证据按来源回退RAW并记录实际采样；
PROGRESS仍输入完整指令，只离线均衡真实pending阶段；ATOMIC必须有整段动作归属证据，false→true不足以证明。
两增强池均空时，增强入口在加载模型前明确拒绝，普通RAW仍可使用。双图共享轻微photometric，无几何/物体换位增强。
数据集建立时一次校验每个选中HDF文件的SHA，防止导出后或恢复前替换数据却保留同一run身份。

原六任务继续使用原legacy初态协议/endpoint，新三使用已验收nine-mask10；C只选择0/3/6/9，A选择0..9。
legacy batching bridge允许明确固定四条子集，但仍调用原runner/schema/evidence/source验证，未另写物理评分。
每条全视频、动作、query与输入证据保存。正式二元映射仅来自034；completed unknown→0时保留未知释放诊断，
不编造违规。技术/缺失/损坏保留作业错误，完整分母未齐不输出正式全量SR。

## 实际软件验证

最终root定向运行 **49/49通过（100%，0skip，11.61秒）**：数据27、训练13、评测9。
独立审查运行同49项也全部通过（11.76秒）。034独立root运行 **12/12通过（100%，0skip，0.94秒）**；
独立审查12项通过（0.98秒）。没有跑全库、多平台或任何真实实验。

```bash
# 方法库；core checkout还提供既有的CPU synthetic测试夹具
export TASK030_TEST_CORE=<accepted-core-d8541ef4>
export TASK030_TEST_REPORTING=<task034-reporting-checkout>
python -m pytest tests/test_augmentation_data.py tests/test_augmentation_training.py \
  tests/test_augmentation_evaluation.py -q --basetemp <new-test-temp-directory> \
  --junitxml <new-test-results.xml>

# benchmark034分支
export LIBERO_REMAIN_ACCEPTED_CORE=<accepted-core-d8541ef4>
python -m pytest tests/test_binary_compliant_reporting.py tests/test_binary_compliant_loader.py \
  -q --basetemp <new-test-temp-directory> --junitxml <new-test-results.xml>
```

合成HDF防时间错位/夹爪/双重归一化/跨split重复/原子边界/padding错误；tiny模型证明仅语言LoRA可训练、冻结head可传梯度、
保存加载输出一致，以及完整入口恢复到相同adapter；只用fake官方边界验证原双图预处理/56动作hidden选择。
原core fake运行真实验证四条固定来源的视频/动作/query档案，篡改视频/adapter会拒绝。
034覆盖22/90合成用例、不等样本宏平均、unknown诊断、重复/缺失/技术错误/源hash变动/adapter混算。

审查发现并已修复：外部包遮蔽冻结core；224px输入仍需官方JPEG/Lanczos resize；HDF替换绕过恢复身份；
纯文件adapter身份读取不应要求评测主进程装PyTorch。对应回归已包含在上面结果。
早期fixture默认Windows临时目录权限、测试环境相对路径解析及开发中的红测试失败均已解决；不把早期运行计为通过。
CLI三入口`--help`通过，wheel构建和data_scope/core/reporting/纯identity模块清单检查通过；`git diff --check`通过。

官方OFT接口直接对照固定revision源码，不下载模型/data。使用官方输入/labels/动作mask helper、forward及原head；
只把推理的detach/NumPy输出替换为训练的可微L1链。源码审读参考：
`finetune.py` SHA256 `1400729cd444559dd914f9c3551868708592c79cbab96462cf80ad8c2bb0699c`，
`modeling_prismatic.py` SHA256 `b5431a074c0025a12e46dc954a5e18d1d73477babb5ae42e3a12ab4b907f33a6`。

## 真实阶段硬前提与未验证项（集中说明）

本轮软件实现无已知未解决阻断；**不等于已经可以用未填写模板直接开真实训练**。

1. 项目记录已有普通20任务200来源和旧split；本轮没有读取真实HDF。需部署原sealed inventory、实际HDF及
   经确认的字段/时序/动作/统计映射。新增九任务最多180来源仅候选，实际数量/文件hash/搬运状态未验证；
   不下载、不猜文件名、不造380来源就绪率。
2. 增强需要至少一个可信PROGRESS或ATOMIC池。已实现可信文件读取及同次导出的hash锁定局部provider接口，
   **没有内置或验收新的仿真恢复/技能归属标注器**。已有可信局部证据可直接用；缺失按RAW回退。
   若部署侧没有可信证据且无已审provider，真实Progress-Aug被阻塞，不能把RAW运行改名成增强实验。
3. 评测需填写原六manifest/replay、新三composite sources、原冻结runtime和本轮选定adapter路径；
   方法包必须安装在主评测环境及runtime指定的OFT worker环境。034依赖是本轮提交，仍待Codex验收部署。
4. 24GB实际显存和时长未知；仅说明冻结7B bf16权重约14GB加视觉/head/激活/优化器等静态组成，未做GPU probe。
   真OOM后由用户决定fallback，不擅自减少视角/proprio/chunk或量化。真实训练/效果完成率本轮均0%，没有提升结论。
5. 034完整实际基线派生报告仍需原结果/来源工件路径；本轮只交单一报告实现与合成22/90测试。
   已验收基线22/90=24.44%、不成功68/90=75.56%的事实保留，未称已重新读取真实90条。

真实完整命令集中在[augmentation_commands.md](../../docs/augmentation_commands.md)，由Codex填准确部署路径后交用户。
没有重跑基线、改物理阈值/判据、改旧失败/raw、启动下载/真实导出/仿真/训练/eval、自动合并或清理旧数据。

下一步操作和执行者：Codex审查PR9/PR15并隔离部署、补齐上述文件与证据/路径；用户另外确认候选数据及
两次1000-update、A90+C36预算后亲自启动真实阶段。软件提交状态为submitted，不能自行标accepted/closed。
