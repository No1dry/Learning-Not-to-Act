# Task055 Round1 Codex验收：accepted并隔离部署，下一用户启动150构建

日期：2026-11-23。

## 验收结论

接受PR30固定head `6d9d0111881727f8765fce0c6affc881db949985`（实现`2f3bc7718ddc9bfa9324224322ef2e01b49776e7`），依赖已验收PR29，不自动merge，X本工单无需返修。范围仅软件、CPU/fake和隔离文件部署；真实预完成状态构建与模型评测均为0。

三个SCENE2新组合及每任务50个预完成来源、总150人口与最新工单`6e650887`一致；没有普通状态库、训练、教师轨迹、模型入口或按模型成败选源。实现保持旧九任务、450bank、训练数据、sidecar、评分及旧结果不变。

## 独立审查与测试

- 通过GitHub API固定commit源码，未切换到其他版本；`catalog.py`、`native.py`、`preparation.py`的Git blob SHA与PR分别一致。
- 审查覆盖A-only状态移植、派生BDDL/目标、固定150顺序、释放与双独立恢复、失败证据/控制账本、输出保护和冷启动激活。
- Codex独立运行`test_composition055_catalog.py`、`test_composition055_native.py`、`test_composition055_preparation.py`：**54 passed，0 failed，0 skipped，11.13秒**。本地JUnit保存在`reports/task055_acceptance_2026-11-23/cpu-fake.xml`。
- 首次本地复验因Codex相对core路径写错及系统Python无pytest未进入测试，随后使用现有固定core和Anaconda Python完成；不计为X源码失败，也不伪称真实物理通过。

## 隔离部署

代码：`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task055-composition150-v1`。配置：`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task055-composition150-v1`。

源包SHA `8eb64567b73a5675fae9c243aa0fe0dbb2b0f0d08254361f20afc3cc315ad4b7`；实际build配置SHA `30f9702a571d8e2bddfa26bd592008eb317461887408445dcc617cd6d58740d4`；启动器SHA `caed7cadf60c0c43fad63000905355f16a454bf2f878f05f9d9c7b3d461cd4d0`。官方BDDL/init SHA与固定值一致；环境身份由服务器固定bridge只读生成，未手写fingerprint。静态配置、CLI和`bash -n`通过，未实例化仿真或加载模型。

下一用户只启动一次：

```bash
nohup bash /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/task055-composition150-v1/build_150.sh > /HUBU-AI096/zp/ICML/Learning-Not-to-Act/logs/task055-composition150.console.log 2>&1 &
echo "PID=$!"
```

输出：`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/composition055/production-001`。脚本在构建成功后自动做只读全bank inspect；失败或不完整保留现场，不覆盖、退款、换目录或自动重试。普通状态仅在后续结果难解释时另行讨论，不是本轮门槛。真实通过率、剩余可完成性和泛化结论仍open。
