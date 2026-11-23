# 044 R1：软件及隔离文件部署accepted，用户直接正式180

2026-11-16，Codex。PR19固定**e8445b6ae640f21446533592326c645a6d42894b**（实现8259a1040b0a83551678db5cbb7849c836bac090，依赖accepted PR17@7d28d515）。软件/实际配置与文件部署accepted，X无需返修/泛审；PR19/17/18不自动merge。CPU/fake与静态文件核对不证明真实SR。

## 核对结果

- 六个新prompt044模块隔离；既有90个egrs生产源/JSON与accepted042固定快照逐字节一致，未改原模型/训练/评分/bridge。完整原指令仅在模型base.predict语言边界变成冻结P1/P2，底座直接官方SOG10，无研究adapter、FINISH或训练。原source/goal_specs与完整A+B评分保持。
- 固定9任务语言表字节SHA e648ef20...一致；双壶集合化，无在线GT更新或隐藏ID。真实模型入口字符串及SHA持久审计，原生封装/分词/forward不变。独立native ten-only90，未以假adapter/空00进入旧036；原bridge/proxy/reader与二元计分复用。
- 新60项CPU/fake全部通过。另1项旧bridge、2项原reader、2项A/炉子约束通过，Codex独立共65个不同通过。首次同次80项中19项旧bridge/proxy因本地归档无Git历史、git show旧commit失败而setup error；其生产源未变，复用既有accepted证据及X本轮20项原bridge结果，不改源码/断言、不恢复Git历史或追加真实MVP作门槛。原JUnit保留，**不声称Codex80全过**。
- 101个源码/依赖/模板和3实际配置SHA本地/服务器一致。原worker/simulation两环境仅no-deps editable映射新目录，无升级。两实际JSON严格解析、模型runtime与reference文件不变、实际输出/marker与所有保护根不重叠、冻结提示及脚本语法核对通过。未来两eval和marker均不存在。
- 原reference plan全文件SHA固定，X对“ten projection定义未详述”的披露不构成阻断；Codex对现成实际metadata计算完整ten tasks投影，确为批准ed9b5027...，无需新来源生产或full build_plan。未新加载真实模型/仿真或构造完整源计划。

## 非阻断说明

X运行文档取worker解释器的示例将python_executable按顶层读取，而实际文件位于runtime.python_executable。Codex部署使用已确认的原worker绝对路径，用户收到的完整命令无需执行该示例。只作后续文档建议，不要求X返修或再交一轮。X历史TDD/fixture失败与署名保留。

## 下一步与边界

软件/部署100%，真实eval0。用户按2026-11-16_task044_user_evaluation_commands及本地044完整命令，在原simulation环境一次启动P1正式90→P2正式90。原H520/chunk8/seed7/双bridge/完整10二元合规/全视频保持，原官方SOG10，不H0/H1。P0历史22/90仅aggregate引用，不重跑；无00、训练、额外seed/提示搜索或前向probe。

不新prepare/index/plan/资格/MVP/GPU预检；正式入口自然核对原来源。失败保留原输出、audit及预算，不删marker/自动重跑。X暂无实现待办，真实结果由用户交回后Codex审查。已备份固定X原稿/源码归档、原测试JUnit、实际配置/收据与本阶段六文档；原dirty checkout、全部旧数据/权重/失败保持，无删除待删=[]。
