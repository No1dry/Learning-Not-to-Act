# 035：双向兼容切换与003继承续跑

本入口执行[035代理切换与续跑任务](../collaboration/tasks/035_proxy_transition_and_resume.md)。003已有旧六10任务60条有效完成（包含全部成功和失败）；新输出eval004只运行新三10的30条及全部00的90条。原权重、180人口/各90分母、初态、指令、seed7/chunk8/H520、环境锁和评分不变。

## 受控代理协调

两份原compat虽然文件SHA一致，但不同模块命名空间创建的 `_CollectionsProxy` 类型不相同。方法侧在环境构造后、每次原实例reset前检查共享LIBERO utils的局部collections绑定：只对两套已锁实现的**精确代理类型**复位为原stdlib collections绑定，再完整委托原reset。陌生对象/代理子类仍拒绝，不修改stdlib模块或冻结文件，不改物理恢复、动作或原shim实现。

新plan/sidecar记录 `proxy_coordination`：`task035-exact-owned-proxy-reset-v1`、方法实现文件SHA、原compat SHA及策略。旧003的v2 plan/sidecar不补此字段，不将其60条追认为新代码执行。旧/新bridge仍独立计算并严格比较完整指纹。

## 显式父run与严格继承

配置版本新增 `task035-dual-condition-eval-v3`，其余字段沿原v2。模板：[eval_robot_rewind_continue.json](../configs/trajectory_augmentation/eval_robot_rewind_continue.json)。v3的run必须提供 `--continue-from`，缺失直接报错，不能默认重跑180。

父003固定plan身份为 `48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b`；最终adapter SHA为 `21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8`。生产CLI不提供放宽这些值的选项。

`continuation.prepare_continuation`用父run自己的plan/batch/runtime、原reader、source/archive/观测/query/actions/video及环境sidecar核验全部60完成条目，成功和失败一并保留。核对完整adapter、实际加载组件/统计、原来源/端点/预算及同一指令；不是只比底座身份。原summary/report与六个完成task、首0步技术task的全部文件按SHA/大小冻结。它不要求父run完成180。

子plan封存父目录、父plan/batch/报告/工件引用、技术attempt和原代码lineage。继承raw不复制改身份，报告引用仍指向父run且 `new_execution=false`；原文件必须保留可读。首抽屉0步技术attempt仅保留历史，不当作已完成继承、模型失败或子run永久评分错误。新run按原初态执行该尚未完成项。

队列保留原相对顺序，只跳过六个有效completed任务：继承60；新增120（10=30、00=90），仅一个相同最终policy。父实际加载组件身份预先绑定到子batch，后续每task继续原检查；不一致在动作执行前拒绝。原输出仍默认拒绝覆盖，不能把eval004放入父003目录内。

## 报告与进度

运行中只更新 `progress.json`（继承60、新运行已完成数、新预算及正式报告待复核）和原task/batch/sidecar。不会用缓存分数写完整formal summary。

退出时及独立 `report` 都重新读取父冻结文件、调用父原reader/原评分，并验证子工件后合并180条；没有序列化score缓存可绕过父工件变动。父raw/video/sidecar/报告等变化直接拒绝。正式10合规SR与00官方SR仍分别按各90计算；缺失/技术暂停继续保留未解决，不能填模型0。`continuation`报告块明确继承量、新预算和旧技术attempt，父目录与代码来源保留。

独立报告依赖原父目录及其冻结文件可访问；不清理003，也不把父60的视频/原始工件悄悄替换成分数副本。

## 普通命令

Codex在新隔离代码/配置目录部署。新配置从原 `evaluation.json`复制，仅schema改v3；runtime、adapter、全部来源、core/reporting/legacy路径保持。以下占位路径由Codex绑定后交用户，不重训或增加MVP/预检：

```bash
conda run -p /absolute/path/to/libero-eval-env python -m pip install --no-deps -e /absolute/path/to/method035-continue

# 可选纯文件计划及继承核验，无模型/场景/动作。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation plan \
  --config /absolute/path/to/eval004.local.json \
  --continue-from /absolute/path/to/runs/trajectory035-eval-003 \
  --out /absolute/path/to/new-eval004-plan.json

# 本轮未执行；用户亲自启动，只执行剩余120。
conda run -p /absolute/path/to/libero-eval-env python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /absolute/path/to/eval004.local.json \
  --continue-from /absolute/path/to/runs/trajectory035-eval-003 \
  --out /absolute/path/to/runs/trajectory035-eval-004

# 独立复核父/子全部所需工件，不加载模型。
conda run -p /absolute/path/to/libero-eval-env python -m egrs.trajectory_augmentation.evaluation report \
  --run /absolute/path/to/runs/trajectory035-eval-004 \
  --out /absolute/path/to/new-eval004-report
```

保留旧001/002/003、60条成功和失败、原技术错误与训练权重；不自动合并、清理或追加真实作业。下一步Codex审查部署并交实际命令，全部真实续跑由用户启动。
