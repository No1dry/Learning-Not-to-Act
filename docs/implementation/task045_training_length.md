# 045：043训练长度参数化，不改变方法

用户2026-11-16要求H0/H1续到3000、固定测试2000和3000，并明确本轮由Codex直接改代码。复用原040数据/043状态文字、模型与损失；不新增动作/标签/索引，不使用044推理期提示。X无需重复实现。

```bash
python -u -m egrs.hint043 train --config TRAIN_CONFIG --output NEW_RUN \
  --target-updates 3000 --init-from ORIGINAL1000
python -u -m egrs.hint043 evaluate --config EVAL2000 --output NEW_EVAL \
  --arm h1 --checkpoint-step 2000
```

目标步数支持1000的整数倍，budget由原每1000开销计算；本次实际计划只3000，不授权额外长度。旧v1/1000配置与权重保持兼容，新延长配置/权重/完整state使用v2。--init-from只能将已完成原1000完整状态导入新输出；不覆盖旧run，不从adapter-only重置优化器。相同新run的故障恢复仍显式--resume，旧checkpoint不能退款已消耗前向。

恢复原LoRA全部参数、AdamW、LambdaLR、采样器、Python/NumPy/Torch/CUDA RNG，source/sidecar/dev选取必须相同；学习率不重新warmup，transfer系数从1001继续0.10。旧账本只读，新账本累计继承父消耗并声明新上限；来源包含父adapter/完整state/identity/run_config字节SHA。训练日志同时显示累计与新增进度。

两组各追加2000，总新增4000；原参考新增≤36096、学生新增≤108288，祖代消耗不冒称新增或退款。保留250间隔dev/checkpoint与固定2000/3000评测节点；不按loss/SR挑checkpoint。四快照10/00各90，共720新episode，1000原结果复用。模型部署仍只有原指令/RGB/proprio，无状态文字/GT/教师。

用户先一条extend_train_both.sh串行H0→H1；训练正常结束后用户另在simulation环境启动eval_training_length.sh，固定H0@2000→H1@2000→H0@3000→H1@3000。全部真实阶段仍由用户亲启，代理不代跑；不做新prepare/index/plan/MVP、旧基线或提示搜索，不自动merge旧PR。

CPU软件测试覆盖原1000兼容、完整假1000→3000与两个节点、恢复Adam/scheduler/sampler/RNG/账本、父原件不变和显式评测step；没有真实7B/GPU/仿真。具体服务器目录和完整常用命令由Codex隔离部署后提供。
