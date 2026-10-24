# 018 round1：教师输出包装与 schema 对齐

执行者：X。日期：2026-10-23；定稿：2026-10-24。基线：已验收`c6840ae6c27429c8a6eb27a4e937927f4f934202`。本轮只修018，不重开016/017；已同步main最新工单、文本规格/实际进度和授权记录。

准备100%；018实现100%；受影响CPU/fake验证100%（55/55）；外部Codex验收待执行。本轮X真实数据处理、原397份raw重读、教师调用、人工视觉标签、训练和模型评测均为0。已有GPU作业未停止/继续/重启；原数据、图像、规格、来源分组和历史结果未改写。

## 修复及机制

1. `egrs.teacher-wire.v2`只接受裸JSON或单个完整外层json/无语言代码块。原raw保留，wrapper/JSON/schema分别记状态和错误；额外说明、多块、截断仍拒绝。不截取大括号，不改ID/枚举/字段，不补目标。
2. 包装解析后仍调用原`validate_registry`/`validate_prediction`，没有修改契约。运输release、实体ID、目标集合、非UNKNOWN绑定证据、角色枚举、关联/null与supports问题都仍严格失败，answer保持null。
3. 教师专用`egrs.offline-teacher-guidance.v2`补充明确约束和合法UNKNOWN/有证据完整示例；固定目标不扩出目的地goal，不用真值ID，不虚构实体或框。学生训练/推理继续共享原提示及同一契约；仅教师增加补充提示，版本/完整hash及实际messages均审计。全文连同图像/上下文进入原4096/1024等预算，不增预算或删图。
4. `python -m egrs.offline diagnose`只分析已有manifest/journal的单次字节快照，写入新目录，报告包装/JSON/schema通过数、首错类别、有证据非UNKNOWN覆盖与all-UNKNOWN数量。保留原错误/答案/计数和来源SHA；新增模型调用0，未生成query仍unattempted，不补历史、不升级旧答案。原generation标志按yes/no/unknown单列，避免把attempted当GPU调用数。

完整CPU诊断、新推理命令和解释见[teacher_wire_diagnostics.md](../../docs/teacher_wire_diagnostics.md)。原图像、窗口、20条文本任务规格和160/40来源划分直接沿用，无需重建。

## 验证证据与限度

```text
EGRS_CORE_ROOT=<既有固定core参考checkout>
python -m pytest tests/test_teacher_wire.py tests/test_offline_pipeline.py -q --basetemp=.work/task018-final2
55 passed in 3.30s
```

39项018用例＋16项受影响离线管线回归。首次RED25失败（新解析/提示API缺失及旧包装拒绝）；实现后25通过。诊断入口RED4失败、25通过，完成后45/45通过；原调用标志汇总另有一次KeyError的RED→GREEN。一次预算测试fixture遗漏两幅假图导致先触发image-grid校验，补齐合成图后实际验证完整提示超预算会在forward前失败；不冒称真实tokenizer适配。

覆盖裸JSON/单层包装与拒绝路径、七类严格schema失败、合法运输/机构及完整多goal、实体/相机/快照/框绑定、原raw及历史/调用边界、诊断源字节不变、旧成功计数不变、部分journal输入错误、未知与证据覆盖区分。CLI合成子进程验证不导入torch/transformers/h5py/teacher/PIL.Image，帧路径不存在仍可诊断。未运行全库、runtime/多平台或真实GPU预检。

工单已有397份raw的事实基线仍是“原解析0通过”；工单记录的去包装JSON397通过、严格schema0通过是先前CPU诊断，本轮未复跑。提示改进的实际有效率、完整真实tokenizer预算和视觉正确性尚未验证；不将全部UNKNOWN或schema通过称为有用监督已ready。

## 独立审查后的修正

独立审查对实现提出两项P2，均已修复：JSONL按换行字节分帧、逐行严格解码，末行截断UTF-8字符只计输入错误，保留前面的合法记录；原registry/query/snapshot引用先独立校验，损坏上下文计输入错误并排除于模型失败和attempted分母。只允许文件开头BOM，不读取像素，也不修改预测契约。新增10项回归先有9失败、1通过，修复后受影响集55/55通过。

执行者确认两项具体缺陷已覆盖并修复。审查未判断真实tokenizer适配、视觉正确性或397份真实raw效果；这些属于后续真实阶段，当前没有用CPU/fake通过替代实证。内部审查不等于外部Codex验收。

方案取舍：教师增加专用提示而学生提示不变，语义仍由同一契约约束；诊断只代表所读字节快照，不能充当仍在运行作业的最终统计。

## 下一步操作和执行者

X交付原PR #2增量并保留旧结果；Codex对固定head作建议式审查，接受后隔离部署和准备命令；用户决定旧作业停止/继续，并以新目录亲自启动修复后的真实推理。旧实际预算与新运行预算分别记录，不自动训练或合并PR。
