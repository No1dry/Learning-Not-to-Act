# 035双向代理切换＋003继承续跑｜Round1

2026-11-04，X，交[PR10增量](https://github.com/No1dry/Learning-Not-to-Act/pull/10)。按[任务](../tasks/035_proxy_transition_and_resume.md)及[R10](../reviews/035_round10.md)实现，未启动真实作业。

已fetch main `a98453d`，于 `1ff539f` 合入任务/证据并保留历史。基于已验收 `fb16a672`；**实现commit `918db35bd67c3b6a9e2cfb189528eff6352cb028`**，随后仅追加本回复与状态。

软件实现100%；最终受影响CPU/fake **63/63通过，100%，0skip/error/failure，47.16秒**。本轮真实续跑0条，003既有60条保持，实际总进度仍60/180=33.33%。原训练权重100%完成验收保持，不能把软件结果写成实际eval004或全量SR。

## 双向共享状态修复

`environment_dispatch.py`仅协调本方法知道的两个已锁compat模块的**精确proxy类型**。在构造边界和每次原实例reset前，若共享LIBERO utils.collections为这两个类型的实例，则仅将这个局部绑定复位为原stdlib collections，再调用原reset。陌生对象及proxy子类仍拒绝；stdlib模块、标准benchmark全局/类和旧/新冻结文件不改。

原shim、环境源码/资产/版本/compat完整指纹检查照旧；没有把expected改为actual、跳过检查、换初态、重写物理恢复/测量/评分或修改动作。reset包装只加代理守卫并委托原绑定方法。

`coordination_identity()`明确记录 `task035-exact-owned-proxy-reset-v1`、方法源文件SHA、原compat SHA及策略。新v3 plan与sidecar封存该协议；原v2 descriptor/父003侧证据保持，不将旧60追认为本次代码执行。测试同一合成utils对象覆盖old→new→old、new→old→new、同版重复及已有旧proxy；类型/陌生状态拒绝证据保留。

## 显式续跑与严格继承

新增配置版本 `task035-dual-condition-eval-v3` 和 `plan/run --continue-from <eval003>`。v3的run缺父run直接报错，默认仍拒绝已存在输出，不能隐式再跑180。

新增 `continuation.py`：`prepare_continuation(parent_dir,new_plan)`完整核验并封存父引用；`verify_continuation(descriptor,new_plan)`重新读取原工件、调用父原reader/原评分，不信存储分数。

固定父v2 plan：`48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b`；adapter：`21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8`。生产CLI不能覆盖这两个约束。核对完整adapter身份、实际组件/统计、runtime、原180人口/各90预算、来源/指令/初态/端点/完整环境锁，不能只比不含adapter的底座身份。

父六组60条必须都完成并由各自v2 plan/batch、原source/archive/观测/query/actions/video/sidecar reader验证，成功和失败全部继承，不按结果筛选。父plan/batch/summary/report、六个完成task及首个0步技术task的全部文件均封SHA/大小，核验前后还比对一致性。父未完成180和已知0步错误不是拒绝继承的理由。

子run不复制改写父raw，`new_execution=false`并保留父run/plan/原代码lineage。父003目录及工件需保留可访问；独立report会重新核验它们，改变video/raw/sidecar/报告等即拒绝。0步技术attempt单列历史，未作为继承模型结果或子run永久artifact issue。

队列保持相对顺序：跳过六个旧10任务60条，新执行120＝新三10的30＋全部00的90，只加载一个相同最终policy。子batch预绑定父实际loaded组件，原task回调仍严格核对；原60不会在新task目录再执行，首抽屉按原初态重新开始。父目录保护使用已经核验、expanduser后的规范路径。

运行中只写 `progress.json` 与原task/batch/sidecar，区分继承60和新增实际完成/120，标明正式报告待核验。**没有缓存分数的正式summary路径**：退出时和CLI独立report都完整重读父/新工件、重新评分后才写报告。若父工件运行中被改，核验失败，不残留缓存生成的正式SR。只做一次最终核验后返回同一报告，避免无意义重复扫描。

最终报告仍原10二元合规/00官方成功各90；缺失/技术暂停不填模型0。summary的continuation块包含父冻结引用、60继承、120新预算及原0步技术attempt。原初态/权重/评分、seed7/chunk8/H520和两基线不变。

## CPU/fake证据

| 受影响路径 | 最终用例 |
|---|---:|
| 双向/重复proxy、陌生对象/子类、原reset委托及协议身份 | 8通过 |
| 父003全60含成功失败、固定plan/adapter/来源/工件篡改、额外/不完整父结果、0步错误拒绝混入 | 12通过 |
| 仅120/单policy、无父拒绝、规范父路径保护、父变动不写正式报告、合成180按原90/90聚合 | 5通过 |
| 原双bridge身份、环境接线、四原协议reader的v1/v2/v3及原评分回归 | 38通过 |
| 合计 | **63通过，0skip，47.16秒** |

合成聚合用例显式保持继承60（30成功＋30失败）与新增120，原make_report得到10合规30/90、00官方90/90；缺失或技术错误正式SR=N/A。这只是合成软件证据，不是实际eval004结果。

最终命令（035工作目录）：

```powershell
& C:/ProgramData/anaconda3/python.exe -m pytest tests/test_trajectory_proxy_transition.py tests/test_trajectory_continuation.py tests/test_trajectory_continue_evaluation.py tests/test_trajectory_environment_dispatch.py tests/test_trajectory_environment_evaluation.py tests/test_trajectory_evaluation.py -q --tb=short --basetemp=.work/proxy-continue-final --junitxml=.work/proxy-continue-final.xml
```

`evaluation plan/run --help`均exit0，最终暂存diff whitespace检查通过，独立窄审查已收口。开发阶段一次高速fake循环在Windows原core原子写progress时遇WinError32文件占用，失败XML保留；未改core/加重试，换新测试目录后同代码最终63项通过。新功能红灯、早期fixture/API整合失败亦保留，不冒称先前命令都通过。没有全库、真实LIBERO场景/reset/step、GPU/模型/训练/物理预检。

## 配置与普通命令

完整配置：[eval_robot_rewind_continue.json](../../configs/trajectory_augmentation/eval_robot_rewind_continue.json)，[指南](../../docs/trajectory_proxy_transition_resume.md)。从原eval配置复制到隔离新位置，仅schema改v3；其余runtime/adapter/来源/legacy/core/reporting路径保持同一实际身份。继续标志在命令行显式给出，不塞进模型runtime。

```bash
conda run -p /absolute/path/to/libero-eval-env python -m pip install --no-deps -e /absolute/path/to/method035-continue

# 纯文件继承计划，无native/model；Codex准备准确路径。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation plan \
  --config /absolute/path/to/eval004.local.json \
  --continue-from /absolute/path/to/runs/trajectory035-eval-003 \
  --out /absolute/path/to/new-eval004-plan.json

# 本轮未执行；用户亲自启动剩余120。
conda run -p /absolute/path/to/libero-eval-env python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /absolute/path/to/eval004.local.json \
  --continue-from /absolute/path/to/runs/trajectory035-eval-003 \
  --out /absolute/path/to/runs/trajectory035-eval-004

# 独立复核父/子原工件，不依赖缓存分数。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation report \
  --run /absolute/path/to/runs/trajectory035-eval-004 --out /absolute/path/to/new-eval004-report
```

下一步执行者 **Codex**：集中审查、隔离部署、纯文件核对实际父003引用并交eval004准确命令；**用户**启动原剩余120。旧001/002/003、60条成功和失败、技术attempt、原数据/源码/权重全部保留。本轮真实续跑0，无重跑60/基线、重训、状态重建、新GPU预检、自动merge或清理，待删=[]；实际全量效果仍待用户结果。
