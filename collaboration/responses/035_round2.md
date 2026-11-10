# 035 R2｜保留native解释器的venv软链路径

2026-11-03，X。按[最小修复工单](../tasks/035_round2_preserve_native_python.md)及[R2审查](../reviews/035_round2.md)交付[PR10](https://github.com/No1dry/Learning-Not-to-Act/pull/10)增量，等待Codex验收。

已fetch最新main `203a1b1`，文档合并提交 `f9f5355`；保留双方历史STATUS。**代码实现HEAD：`e56e3e7031e96308c3e723734944b45166c2f0f7`**，其后仅追加本回复及状态记录。原已验收主体 `564c91c9` 不返工。

## 唯一生产修复

`egrs/trajectory_augmentation/cli.py`：只将 `native_backend.python` 从通用 `Path.resolve()` 分离，改为 `expanduser()`＋基于配置目录的 `os.path.abspath()`，不解引用解释器软链。绝对配置仍调用venv入口，相对配置正确绝对化。`historical_root`、数据及其他目录继续原有resolve。

只读追踪确认：`generation.generate_source`原样将该配置写入 `request.json`，并直接放入 `subprocess.run` 的 `argv[0]`；native入口没有再次resolve解释器。无需修改后续生成器、版本锁或环境。

示例（非实际服务器路径）：配置文件 `/work/035/config.json`，解释器绝对值 `/work/envs/oft_worker/bin/python`，或相对值 `../envs/oft_worker/bin/python`，均得到：

```text
plan.config.native_backend.python = /work/envs/oft_worker/bin/python
request.config.native_backend.python = /work/envs/oft_worker/bin/python
argv = ['/work/envs/oft_worker/bin/python', '-m',
        'egrs.trajectory_augmentation.native', '--request', '<new-output>/request.json']
```

即使该入口链接到base解释器，也不替换成base目标路径。原版本锁继续执行；不是改锁以迁就错误环境。

## 精简CPU/fake回归与限制

只改一个测试文件 `tests/test_trajectory_cli.py`。绝对/相对各一项真实文件symlink布局：`venv/bin/python`链接到当前base interpreter，走实际 `build_plan`、实际 `generate_source` 写request，只在subprocess边界fake，断言plan/request/argv[0]三处保留venv路径及版本锁不变。不启动NativeSession或模型。

本机Windows创建真实文件symlink返回 **WinError1314（缺少所需权限）**，两项如实skip。另两项明确标记 `simulated_resolve`，模拟文件系统解引用边界，保留其余生产链不变，用于本机红绿验证；**它们不是实际symlink通过证据**。

| 运行 | 结果 |
|---|---|
| 修复前，仅新路径回归 | 2 failed、2 skipped、4 deselected；两失败均因plan路径被换成base Python，符合故障 |
| 修复后，整个受影响CLI测试文件 | **6 passed、2 skipped，0 failure/error，0.40秒** |
| 最终diff whitespace检查及独立窄审查 | 通过；无额外已证实阻断 |

实现100%；本机已执行CPU/fake 6/6通过，8项中另2项真实symlink尚无执行通过证据，**不能写8/8或全通过**。没有安装WSL、修改系统权限或Python环境来绕过限制，没有运行全库/训练/评测回归。原红灯和skip XML保留。

本机精简复现命令，在035工作目录执行：

```powershell
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_cli.py -q -rs --tb=short --basetemp=.work/task035-r2-green --junitxml=.work/task035-r2-green.xml
```

支持文件symlink的机器补验命令（纯CPU/fake，不需要真实数据/仿真/模型）：

```bash
python -m pytest tests/test_trajectory_cli.py -k 'native_python_venv_path and real_symlink' \
  -q -rs --tb=short --basetemp=.work/task035-r2-symlink \
  --junitxml=.work/task035-r2-symlink.xml
```

预期这两项均执行通过；若仍skip，继续标记验证缺口，不能当成通过。

## 保留内容与下一步执行者

本轮生产差异仅上述解释器字段处理。版本/模块/资产/统计锁、9个HDF、180清单与split、3×2尝试、H520、生成方案、训练、物理判据和评分均不改。`generated-001`的180项初始化错误、原plan、raw和日志全部保留；合格normal/10仍为0，不倒改失败，不声称已可训练。非阻断日志/评测报告优化未纳入本修复。

下一步 **Codex**：在支持symlink的机器补跑两项CPU/fake，做一次实际配置的纯JSON路径核对，审查后隔离部署本增量，复用全部原文件/清单/锁，给新输出 `generated-002` 的普通命令。**用户**按已确认预算亲自启动；本轮X没有真实生成、仿真、训练、模型评测或新增预检。没有自动合并PR、覆盖旧输出、扩大来源预算或清理，待删=[]。
