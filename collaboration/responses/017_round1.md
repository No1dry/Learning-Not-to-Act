# 017 round1：离线候选与人工确认管线交付

日期：2026-10-23。执行者：X（本轮实现代理）。范围：在已验收016实现上增量开发；不改在线选择器、训练器、actor或评分规则，不放宽学生3B pin。

准备100%；017软件实现100%；本轮定向CPU/fake验证100%（59/59）；内部独立代码审阅已通过，外部协作Codex验收仍待执行。真实来源处理0、真实教师调用0、真实人工确认0；训练0%、模型评测0%。合成fixture中的确认事件仅用于软件测试，不能算人工研究标签。

## 交付内容

- `python -m egrs.offline` / 安装后的 `egrs-offline`：独立的plan、inventory、registry候选/审核导出/导入、prepare、视觉候选、审核导出/导入与build命令。
- 固定catalog的20文件×`demo_0..demo_9`，先冻结全部200计划来源的seed0 grouped split，再记录缺失/错误gap。原始指令精确保留；仅缺失时允许显式人工映射。相机长度/uint8 RGB格式错误不截短或替换；固定clamp/dedupe窗口与原frame sidecar。
- 独立本地缓存7B教师loader与`configs/teacher_offline.json`。一次命令一个backend、bf16/batch1/确定性生成，原schema/prompt/encoding预算。不下载、不LoRA、不自动重试/换模型；超过输入预算明确失败，不裁剪后假装原payload。原始输出、实际payload/messages、token/耗时/尝试均保留。
- 窗口内按连续query生成，只有过去合法候选进入原EvidenceMemory，commands始终为空。失败保持null/error，后续同窗query标unattempted，独立下一窗继续。全部机器候选weak，最终payload冻结。
- 可携带离线HTML审核包：双相机合法过去/当前图、表单字段、可编辑normalized box与overlay、完整evidence item确认、null候选人工draft、显式reviewer、跳过、导出/恢复。显示图映射不改训练路径；实体/证据变化清除依赖确认，后端拒绝stale确认及immutable输入/source/split变更。
- 复用annotation import/build与最终mask；仅增加可选`fixed_source_splits`，原默认行为保留。已确认子集与全候选/未审/部分字段未确认/gap/audit并列；候选和已确认字段分布、来源/窗口/query及train/dev覆盖分开报告。任何缺失来源、未审query或未确认字段/item都不声称全量ready；仍允许构建部分监督子集。排除声明默认unset，需外部显式true与basis；未知祖源披露保留。

所有入口、必要文件、固定revision、完整逐阶段命令和人工操作见[offline_pipeline.md](../../docs/offline_pipeline.md)。静态plan/help不读HDF5、不导入模型/native。视觉候选CLI显式要求`--core-config`并调用原core激活校验，不依赖测试conftest的路径注入。

## 验证证据

仅运行新017测试与受影响`test_data_training.py`，没有全库/runtime suite、真实HDF5/processor/weights、教师forward、VLA、仿真、render、训练或模型评测。

```text
EGRS_CORE_ROOT=<固定core参考checkout>
python -m pytest tests/test_offline_pipeline.py tests/test_offline_review.py tests/test_data_training.py -q --basetemp=.work/task017-tests-final2
59 passed in 4.45s
```

RED→GREEN证据覆盖首次缺失API，以及两处自审回归：已确认registry envelope被改后须拒绝；每条query只确认一个字段时不能报告全量ready。中断测试验证append-only候选partial journal和backend关闭；现有最终编码器测试验证evidence改项/压缩索引能进入正确token mask。

Wheel以`pip wheel --no-deps --no-build-isolation --no-index`构建并本地安装到新目录。隔离导入安装副本后：静态plan不导入h5py/torch/transformers/benchmark，catalog与原文件一致，HTML模板与两幅portable fixture图正常导出。没有网络包下载。该wheel检查早于最后的报告逻辑修复，仅证明当时安装副本的打包/资源路径可用；它不是最终发布产物。

浏览器交互验证**未运行**：控制器浏览器工具拒绝`file://`本地页面，未绕过工具限制。合成包保留在`.work/task017-ui/{prediction,registry}/index.html`供人工打开；软件测试/打包检查不能替代视觉交互验收。真实模型显存、吞吐、标签准确率、人时节省与数据分布尚未测量，不作承诺。

## 下一步操作和执行者

X／控制器：交付原PR #2增量及归档记录，不自动merge。外部协作Codex：审阅017交付并准备隔离部署，不热改运行树；另按2026-10-23用户明确授权的网络例外，本地下载固定20个原始文件后经SSH传输，仅做字节搬运和完整性校验，不含HDF5轨迹读取或后续处理。传输状态以独立日志为准，不据此宣称200来源或训练集ready。用户：之后分别启动真实inventory/抽帧、registry候选与人工确认、窗口/视觉候选、人工字段审核、build、训练及模型评测。各阶段不会自动串起后续真实工作；X本轮真实处理、模型调用、人工标签、训练和评测仍均为0。

## 内部独立审阅记录

2026-10-23，内部独立审阅代理检查`5a77f158..ad69afd38a41b6195e92b918b9dfbdb14fef26c0`完整增量，spec和代码质量均为PASS，未发现有具体失败路径的阻塞缺陷。结论基于代码检查和本实现方提供的59/59定向测试证据；审阅者没有重跑测试。此内部审阅不替代外部协作Codex验收，不表示浏览器交互、真实模型、发布或部署已验证。浏览器交互QA仍明确未运行。
