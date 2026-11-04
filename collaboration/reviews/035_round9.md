# 035 R9：双bridge兼容验收与eval002部署通过

裁决：**accepted/closed限环境分派软件与隔离部署/只读身份核对；正式reset/step与180条模型效果仍待用户运行。** PR10 HEAD `fb16a672bd69dc9565e9efc41adafb4e4af7993b`，实现 `1387de381126176312a08d4c2b967c948d2fc541`；未自动合并。本轮无已证实阻断，不要求X返修主体。

## 审查与必要证据

- 完整阅读新增environment_dispatch.py、evaluation改动、新两测试文件及原评测测试增量。旧三文件以固定字节和真实__file__在私有命名空间执行，原compat确实读取邻接旧bridge；测量/runner/协议/评分复用固定core，没有把expected改成actual或关闭指纹。
- 原_run_task bytecode以FunctionType的局部globals绑定factory，标准workflow/benchmark模块和冻结文件不改；同一policy仍服务126调用/180条，分派锁不进模型输入。侧车/batch/独立reader绑定实际实现和完整环境身份，v1错误仍可读。
- Codex受影响CPU/fake **34/34通过，100%、0skip、9.76秒**。仅三文件测试，无全库/真实模型/场景；fixture路径适配用只读归档目录别名与独立Git对象库读取固定ac130177源码，未修改实现或测试。
- 服务器通过真正的原身份函数独立读取源码、资产、包版本与compat，旧完整fingerprint `27939e2d2a9a592a7c788ab5c91021d83f4ba88831615ef86aff0fb03ea7942b`、新 `e7d58f354d2b013b362d181f9af3ef48dca136cdff2801c7de68606c16ed4883` 均与实际来源全字典一致（2/2=100%），分别120/60条。只导入类/调用身份函数，**没有实例化环境、创建场景、reset/step或加载模型**。该项直接防止001同一指纹错误复发，不是GPU/物理预检。

## 部署与交接

独立code/task035-dispatch-fb16a672、configs/trajectory035-eval-002已部署；归档SHA `73d4010cad9ad0b9062d6cbd76e78202e4a40d6c3b996ec81c52ea4df625a7ab`，配置SHA `77332bac746797b2f45ed5145ddd990e63b69ef7b4a4059b9945191f9482d558`。两执行环境只无依赖更新方法包，5个必要模块均与部署源码匹配，其他环境库/权重不变。

v2纯文件计划原10/00各90、126调用通过，plan身份 `48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b`。同一update-001000/SHA21b982e5...，base runtime与001字节相同（仅新配置引用路径）；旧、新来源及10合规/00官方评分、端点、seed7/chunk8/H520、全视频/原query/actions不变。不重训、不重建初态、不重跑基线，不追加真实预算。

准备100%、训练100%、新模型eval0%。**下一执行者用户：按[eval002完整命令](../../docs/experiment_plans/2026-11-04_task035_dispatch_evaluation002_commands.md)直接启动原180条**；不再plan/pip/试跑/MVP。旧001和错误/旧代码/配置保持，不覆盖或自动重跑。R8历史失败不改写；当前结论不冒称已验证真实轨迹成功。

X本兼容任务无需返修；既有实时SR/去重复读仍非阻断open（未交付不伪闭环），不热改新运行目录。研究效果待实际10/00结果。[阶段总结](../../docs/stage_summaries/2026-11-04_task035_dispatch_accepted_eval002_handoff.md)。无删除或自动merge，待删=[]。
