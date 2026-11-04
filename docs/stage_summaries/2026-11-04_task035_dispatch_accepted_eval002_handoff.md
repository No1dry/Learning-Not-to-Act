# Task035：严格双bridge修复验收与eval002交接

2026-11-04。用户交付后，Codex验收PR10@fb16a672（实现1387de38）的最小方法侧兼容修复，R9软件/部署/只读身份范围accepted/closed，无主体返修；不自动merge。

## 解决的具体错误

001用户真实启动已加载模型/adapter，但首环境前因指纹不匹配退出，0/180且无动作；原失败不改写。旧六120条绑定旧bridge fa85ae08/27939e2d...，新三60条绑定新bridge3a515ddd/e7d58f35...，方法入口此前统一用新bridge。训练权重验收始终保持，不重训/重建状态。

新environment_dispatch.py锁旧libero_env/compat/schema三文件，在私有命名空间执行实际原字节、保留真实__file__，因此旧身份函数读邻接旧bridge；测量/协议等依赖仍固定97文件core。新版走原标准类。原_run_task字节只在局部globals绑定factory，标准benchmark/workflow和冻结文件不改；没有伪造/替换fingerprint，不另写评分/恢复/runner。v2配置显式legacy_root，sidecar/batch/独立reader记录和核对真实实现及原完整环境锁，旧v1的001错误仍可读。

## 实际验收与边界

Codex三文件受影响CPU/fake34/34通过（100%，0skip，9.76秒），复用原core/reporting归档；Git fixture从独立对象库读取真实ac130177旧文件，不修改测试/实现，无全库或真实模型/场景。

服务器再由原旧/新environment_identity函数实际读取源码、资产、包版本与compat，完整字典两套均匹配：旧fingerprint `27939e2d2a9a592a7c788ab5c91021d83f4ba88831615ef86aff0fb03ea7942b`，新`e7d58f354d2b013b362d181f9af3ef48dca136cdff2801c7de68606c16ed4883`。仅导入类并计算元数据，不创建环境实例/场景、不reset/step、不加载模型；它直接核对001的根因，不代表真实轨迹或模型成功率已通过。

## 部署和下一步

- 新代码`code/task035-dispatch-fb16a672`、配置`configs/trajectory035-eval-002`；归档SHA73d4010c.../配置77332bac...核对。两环境只无依赖更新本方法，五个使用模块均匹配新源码，没有升级仿真/模型库。
- 原180文件计划通过（90+90、126调用），120旧/60新正确绑定；plan身份`48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b`。
- 同一固定update-001000、adapter SHA21b982e5...，base runtime与001相同。原指令/双图/本体、seed7/chunk8/H520、端点、10二元合规SR/00官方SR及两基线24.44%/86.67%、全视频/原始证据保持，真值不进模型。
- 准备/训练100%，新模型eval0。新输出`runs/trajectory035-eval-002`尚未创建，001和其错误/旧代码/配置保持。原180预算不变，无新生成、训练、真实诊断/MVP或基线重跑。

下一执行者用户按[完整eval002命令](../experiment_plans/2026-11-04_task035_dispatch_evaluation002_commands.md)直接启动，不重复plan/pip或试跑；Codex只分析用户交回结果。X本兼容任务无需返修，实时SR/去重复读仍非阻断open（未交不假闭环）、不热改运行目录。方法实际效果仍open。原始数据/运行refs/开放任务不清理，无删除，待删=[]。

本地`reports/task035_dispatch_review_2026-11-04/`保存固定源码归档、CPU XML、实际身份收据、部署收据与精确配置；阶段文档按精确GitHub commit/SHA本地备份。
