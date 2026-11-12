# 042软件验收、隔离部署与用户直接训练交接

2026-11-12，Codex。[R1](../../collaboration/reviews/042_round1.md)接受固定PR17@7d28d515（实现03e0efcd，依赖accepted PR16@e8dcf879），X无需返修，不自动merge；[机器证据](../../collaboration/evidence/042_codex_acceptance.json)。

## 软件事实

F0 native OFT双向padding-only、F1仅逐层禁T query读C key，同SDPA/参数/loss/data/完整R0初始化，祖代2000＋新增1000。最终mask/shifted56首个A/P/逐样本checkpoint与原SOG10 reference旁路、全参数保存/同run恢复/前扣预算/float0.0/原180评测接线通过审查。原80部署源依赖79不变，仅共享oft加可选forward seam，新12模块独立命名空间，无全局包改动。

109独立不同CPU/fake最终全过；首次103过＋6因Codex cwd链接错误的setup error保留，复用既有固定core/reporting补6通过，未改源码/断言或重复旧全库。另用服务器已安装HF4.40.1/Torch2.4.1构造随机2层hidden16 CPU软件模型验证actual类/source准入、native-F0一致、F1非干涉/控制p路径、变长checkpoint反向；没有预训练模型/真实轨迹、GPU或optimizer更新，不计入109，不代表真实VLA/GPU/SR结论。原deprecation warning保留。

## 部署与命令

新code/config task042-7d28d515已上传，92源/依赖与8配置/脚本SHA一致，两份实际训练JSON在本地及原worker严格读取通过、float0.0未被转成整数。R0初始化源d4e726a8字节SHA匹配；原runtime复制字节不变，eval仅042封装/实验臂/未来末权重变更，原来源/评分/双bridge等不变。两原venv仅no-deps editable映射新方法，core cwd静态模块定位正确，HF源SHA3aac24ce仍原字节、依赖未升级。脚本只语法检查，未执行；未来train/eval/launch均不存在。

**准备100%，真实训练/正式eval0%。下一用户直接一条train_both_sequential.sh执行F0→F1各新增1000，正常末1000后另启正式360。** 不等待新Codex预检、不generate/index/plan/MVP/旧资格/GPU试跑或基线，不重开041。完整常用conda＋python、后台、5秒自动刷新的简洁训练进度见本地docs/042_服务器完整运行命令_2026-11-12.md；公开[脱敏说明](../experiment_plans/2026-11-12_task042_user_training_evaluation_commands.md)。一键脚本自激活原环境，失败保留/停后续臂、不退款或自动重试/eval，原子marker拒重复。

已批两组新增2000、reference≤18048/student≤49120/新模型正式360不变；source祖代2000＋新增1000累计3000，不假resume。主比F1−F0，旧R0差还混新增训练/backend，不保证更高SR/成果硬保护/新颖性。真实预训练实例类/布局准入留在用户正常作业初始化，无额外forward。

软件closed、训练/SR/研究open，X暂无修改任务，用户亲启全部真实阶段。六关键文档与固定X六原稿精确GitHub commit读回SHA本地manifest；源tar/独立JUnit/随机CPU及私有收据保存。旧dirty checkout、全部039040041权重/数据/分数/失败/署名不改，无merge/删除/代启停，精确待删=[]。
