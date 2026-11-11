# 040 R1：软件验收及隔离部署通过

2026-11-10，Codex。审查[PR15](https://github.com/No1dry/Learning-Not-to-Act/pull/15)固定head `428c13585cebac1d6c90fd86a205e914caa2bb8f`，最终实现`0f24e9d46bfbc33edd001facf19d2c1c40ffc166`，依赖accepted PR14@`113ded21434a06e2cdc156e5d6283a11c3f15488`。

**裁决：accepted，限软件、定向CPU/fake与隔离文件部署；X本轮无需返修，PR不自动合并。** 不代表真实数据覆盖、训练或SR已通过。

## 审查依据

- 新实现集中于8个coverage040模块；与accepted039比较，60个原egrs生产.py/.json逐字节不变。不是用旧main代替实现，也未修改原评分/core/控制器或X源码。
- 计划固定三任务20..39候选、原分组锚点与train-only代表；新dev封存、旧180 split保留，已知旧重复不生成。原039教师、收尾/双壶初始化变换及V2/H520复用，不换标签或扩控制算法。
- 新normal仅在pair_sources，主池仍原fresh105/raw180＋旧ten305和新train10；旧主行、labels、pairs字节前缀保留，dev稳定source/observation/pair键及选择顺序检查存在。缺新pair不踢掉合格BC。
- 共享原038 C1网络/loss、22学生/8参考、1000更新、原统计/输入白名单、保存恢复与单VLA正式eval；新增索引真实绑定，零新train10在模型前拒训。没有新增S/C0/FINISH/外部教师或真值推理路由。
- 子worker异常/中断先stop/wait再恢复封存，无法确认清理则不导出；持久账本不退款，旧输出拒覆盖。父进程SHA去重不豁免独立worker首次原HDF/统计严格校验，不冒称全作业只读一次。

## 独立定向测试

162个独立用例最终全通过、无遗留失败/错误/skip：sources43、data77、model31＋固定core fixture后的11。包含fake实际动作记录→导出/索引→tiny C1真实新pair抽样、22/8计数、save/resume全tensor一致及末1000/180假执行合同。

初次model组11项因本地未链接既有固定core/reporting而setup error；Codex一次链接命令cwd错误又复现同11项。复用已有固定快照、只重跑这11项后通过，原错误日志保留，不计初次通过、不要求X改实现/补全库测试。没有真实模型、MuJoCo或任务小样。

## 部署与命令

新隔离目录名`task040-428c1358`，70源码/依赖文件与4配置SHA一致；原OFT worker与simulation两个既有venv无依赖升级地映射到新包，并在core工作目录静态核对模块来源。旧代码和数据目录保留，未启动原作业或新实验。

原runtime逐字节复制；原039 C1 eval JSON只改adapter到本轮未来末1000，来源、base_runtime/双bridge与原10/00评分保持。初次本地复制将原runtime末尾两个换行变成一个，字节守卫在任何服务器写入前拒绝；恢复原字节后成功部署，非算法/环境修复。

[机器验收证据](../evidence/040_codex_acceptance.json)、[用户命令说明](../../docs/experiment_plans/2026-11-10_task040_user_generation_training_commands.md)。具体服务器路径/配置及完整命令在用户工作区私有副本，未把服务器私有路径推到GitHub。

**软件与文件部署100%，040真实元数据/轨迹/索引生产、训练、eval均0%。** 当前没有创建production/train/eval输出；未调用真实plan/generate/train/eval，不把find_spec/文件hash核对冒充真实运行通过。

下一步：用户在原OFT环境启动一次generate。正常完成且training_ready=true后直接原一组C1训练，再由用户切原simulation环境正式180；不增加plan/MVP/基线/旧状态重复预检，不自动继续或启动。预算仍60普通/360ten、一组1000/9024/24560、正式180；失败保留交回，不删除退款重开。X无需新工单；研究效果open、软件范围closed，无merge/清理。
