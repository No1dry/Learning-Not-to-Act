# Task035：九任务正式结果、最终权重和视频保留

2026-11-05，Codex。复用已完成正式报告，未新增评测/统计物理核验或重新计分。模型180/180=100%，10/00各90；原始成败全部保留。

| 任务（官方task_id） | 原10合规SR | 03510合规SR | 原00官方SR | 03500官方SR |
|---|---:|---:|---:|---:|
| 0 字母汤罐＋番茄酱入篮 | 0.00% | 90.00% | 70.00% | 70.00% |
| 1 奶酪＋黄油入篮 | 20.00% | 60.00% | 100.00% | 60.00% |
| 2 开炉并放摩卡壶 | 0.00% | 0.00% | 90.00% | 70.00% |
| 3 黑碗入下层抽屉并关屉 | 0.00% | 100.00% | 90.00% | 100.00% |
| 4 白杯放左碟、黄白杯放右碟 | 100.00% | 50.00% | 90.00% | 80.00% |
| 6 白杯上盘、布丁放盘右 | 0.00% | 0.00% | 90.00% | 70.00% |
| 7 字母汤罐＋奶酪入篮 | 90.00% | 100.00% | 80.00% | 40.00% |
| 8 两个摩卡壶都放炉上 | 10.00% | 0.00% | 80.00% | 80.00% |
| 9 黄白杯入微波炉并关门 | 0.00% | 90.00% | 90.00% | 90.00% |
| **总体（各90条）** | **24.44%** | **54.44%** | **86.67%** | **73.33%** |

每任务各10条。10增加27成功、+30.00个百分点；00净少12成功、-13.33个百分点。新模型10专家覆盖六任务49/60=81.67%，未覆盖三任务0/30，仅分组观察、不证明因果或泛化。00配对有20条原成新败/8条原败新成，两个篮子任务00各降40pp；双杯10也下降50pp，036旨在干预能力保持，效果尚未知。

## 已保留的内容

本地长期归档：`research_archive/Learning-Not-to-Act/task035_results_weights_videos_2026-11-05/`。

- `results/`：现成summary.json/report.md/batch.json/progress.json/console，复制前后SHA一致；summary SHA `56bf8718a592ff6f87d15b9014b876fa01e40e1d0b0b23cc873bd34a7df9222c`。
- `weights/update-001000/`：完整最终adapter.pt、identity.json、training_state.pt及其sha256；权重和优化器/RNG续接状态均从服务器复制并逐文件SHA匹配。另存run_config、selected_checkpoint、完整metrics。adapter SHA **`21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8`**。未重新训练/选择checkpoint，原7B固定底座保留在服务器、不再重复下载，来源及两组件hash在identity/manifest。
- `videos/`：18个原始双视角完整视频，各任务10/00各取1个；SHA与已有raw视频证据一致，无裁切/重生成。10通常展示成功、双杯优先失败、全失败任务取首个；00优先展示失败、无失败取首个。**这是定向展示，不是新随机抽样或SR统计分母**。任务名/instruction/episode/步数/帧数/原来源/sha在videos.json；README可直接查看视频。
- `task_metrics.json`、`preservation_manifest.json`：逐任务统计、每文件SHA/原路径、完整底座身份与保留范围。preservation manifest SHA `c9c709ea06c9a1f6514aac8ca601823adb87aa182be7e04c6ecc6f8d9a341472`。

服务器`runs/trajectory035-mix-001`的全部250/500/750/1000 checkpoint保持；`runs/trajectory035-eval-003`与004的完整父/子raw/query/actions/video/source archive及原代码/配置不删不覆盖。本次本地复制最终checkpoint，不宣称全部中间权重/180原始视频已另做第二份本地备份；003仍为004继承证据所必需。旧技术失败和`035_teacher_v2_recovery_refs.json`保持。

## 退出异常与可用性

最终policy.close有worker-15警告，发生于全部轨迹写完后，finally正式报告仍完整；两类完整性/兼容错误0，00官方信号覆盖100%。不称程序无错退出、不把关闭警告计模型失败或为此重跑。旧progress pending滞后事实保留，以正式报告为准；本次未为展示视频重跑原reader或物理检查。

## 下一步操作和执行者

用户可直接看本地README及18段原视频；036软件/部署/索引已完成，按[036命令](../experiment_plans/2026-11-05_task036_training_commands.md)由用户启动一组训练。Codex负责后续结果核对和评测命令，不自动启动/停止真实作业；X本轮无需返修。归档summary提交后精确commit读回并本地SHA备份，manifest更新；本轮待删=[]，没有合并/删除或改分。
