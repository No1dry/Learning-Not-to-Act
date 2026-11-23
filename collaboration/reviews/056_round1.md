# Task056 Codex验收：accepted并隔离部署，下一用户启动三模型450

日期：2026-11-23。

## 结论

接受PR31固定head `18e86284115c1005c753cab450c97dcfea4d7866`。本轮用户明确要求Codex直接完成，X无需实现或返修；PR不自动merge。范围为软件、定向CPU/fake、实际文件部署与只读计划/注册核验，真实模型评测0/450。

实现只读复用Task055完成的150个预完成来源，Base/H0/H1各150条。普通状态、状态重建、训练、额外seed均为0；旧九任务、450bank、训练数据、sidecar、冻结core和旧结果未修改。

## 独立验证

- 本地与服务器相同**10项CPU/fake通过，0失败、0跳过**。覆盖三个任务注册、manifest/artifact绑定、固定150、fake三模型450与配对、adapter分离、bank拒绝、输出保护、失败保留及冷启动帮助。
- Base完整只读计划为150，bank SHA `4a60ea3c25c379204353b0c5dfc167b16718f535426b918618f5a5221282ee0b`。
- H0/H1分别为冻结3000步及`e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20`/`78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d`，部署无提示。
- 实际`composition_soup_butter`原生benchmark注册、BDDL路径与完整指令通过；没有实例化真实策略或仿真环境。

服务器检查先发现`load_runtime`在bank激活前导入，已移至`read_bank`后；又发现原benchmark默认10任务重排与单任务注册表不兼容，已改为显式当前组合任务列表。均重新通过10项测试和实际注册核验，未进入模型/物理执行。早期本地测试的core激活、输出目录冲突及期望计数错误属于Codex fixture装配，保留并修正，不冒充源码通过。

## 部署

代码：`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task056-composition150-v1`。配置：`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task056-composition150-v1`。

最终源包SHA `3aba8cde6c43a3b06d091b78688dbb98c9503a51d28d771dc97463c052f6686d`；实际评测配置SHA `52b59ca1fb9199712579366d38d71942ecaf5b503eee58f7c70f354e2a7f9d33`；启动器SHA `e5c793fea0bd200c560783fa2582d3b9c8e0b43e9d7167d08126ac50a06cf6d9`。`evaluate_450.sh`语法通过，005输出`composition055-evaluation-005`尚不存在。

001在模型加载前报`libero_remain_reporting`缺失，002在首条rollout写结果时缺少`raw/`父目录，003前10条及`s010`均执行完成后被原core索引10上限中断，004续跑路径又绕过`plan→read_bank→activate_core`。已分别补充reporting激活、raw目录创建、053 index50验证、显式continuation和统一`run`路径的core激活。005继承003的11条、只新执行139条；`s010`已通过实际继承验证，`SubprocessPolicy`导入通过。旧001/002/003/004现场均保留，服务器12项测试通过，未重跑已继承episode。

下一用户只启动一次：

```bash
nohup bash /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task056-composition150-v1/evaluate_450.sh > /HUBU-AI096/zp/ICML/Learning-Not-to-Act/logs/task056-composition150-005.console.log 2>&1 &
echo "PID=$!"
```

顺序为Base→H0→H1，各150条，最后自动比较。失败或不完整保留现场，不覆盖、退款、换目录或自动启动后续模型。真实成功率与组合泛化仍open；普通状态诊断只在结果难解释时另议，不是门槛。
