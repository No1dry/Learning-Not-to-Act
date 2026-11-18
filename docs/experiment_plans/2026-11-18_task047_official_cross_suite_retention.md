# 047：官方评测流程检验其他三任务集能力保持

2026-11-18。用户已明确采用官方OFT源码pipeline，并批准 `3×10×50×2=3000` 条，一次正式做完，不先MVP。

## 评什么

| 模型 | Spatial | Object | Goal | 合计 |
|---|---:|---:|---:|---:|
| 官方四套联合OFT原版 | 500 | 500 | 500 | 1500 |
| 045 H1@3000 | 500 | 500 | 500 | 1500 |

每suite全部10任务、每任务官方50初态。同底座/组件/原指令，唯一模型差异为H1的已训练LoRA。测普通任务原生成功率，不构造Remain任务；既检验能力保持，也能看到跨套负迁移，不能称底座未见任务的严格zero-shot。

## 怎么跑

直接调用固定官方 `run_libero_eval.py` 的环境、run_task/run_episode、图像与动作处理、成功done和保存视频。新增代码仅在模型初始化后为H1加载一次原adapter，以及串行、日志、结果收集。**不使用我们的Remain评分器，不改官方成功规则。**

三suite各按官方归一化选择与步数上限220/280/300，seed7、env seed0、等待10步、chunk8、两图/proprio、center_crop、task order0、init index0..49。它们不是LIBERO-10，不能继续固定10归一化或520步。H1训练记录仍如实绑定10统计，不为了运行修改旧身份文件。

一次命令串行执行六cell：原版Spatial→H1 Spatial→原版Object→H1 Object→原版Goal→H1 Goal。保存全视频、官方日志、轻量逐条JSON、实时百分比和live SR；六cell完成后输出逐任务/逐suite/总体SR及H1−原版差值。异常保留并停后续，不自动重试或悄悄换初态。

## 固定身份

- 官方底座：`moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10`，revision `638918f3d1c2e43a39a8a20772bdb8b91835e4b7`。
- H1@3000 adapter SHA：`78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d`。
- OFT源码：`e4287e94541f459edc4feabc4e181f537cd569a8`，与已验收原动作路径一致。[官方runner](https://github.com/moojink/openvla-oft/blob/e4287e94541f459edc4feabc4e181f537cd569a8/experiments/robot/libero/run_libero_eval.py)、[官方使用说明](https://github.com/moojink/openvla-oft/blob/e4287e94541f459edc4feabc4e181f537cd569a8/LIBERO.md)。

## 范围与交接

预算正式3000、动作块请求自然上限101000；新训练/数据生成/标签/index/教师/预检前向/额外seed或提示/其他任务集均0。旧10/00及权重视频全部保留，不将旧九任务结果拼成官方四套AVG。单seed50初态不冒称论文多seed复现。

X直接按 `collaboration/tasks/047_official_cross_suite_retention.md` 实现薄接线和定向CPU/fake；Codex审查后部署，用户亲启一条完整命令。无需先泛审或反复验证；当前交接100%、实现/部署/新正式0。原046已closed，不重跑。
