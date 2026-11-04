# Task035：最终模型正式评测，10/00各90条

> 2026-11-04暂停：用户已启动001，首场景前因旧六与新三绑定不同bridge指纹而退出，0/180、无动作。不要重跑本页旧命令或覆盖001。训练权重验收保持；下一执行者X按[兼容分派任务](../../collaboration/tasks/035_legacy_environment_dispatch.md)修复，Codex验收部署后另给新eval002命令，仍由用户启动。见[R8](../../collaboration/reviews/035_round8.md)。下方为原交接历史，不代表当前运行就绪。

准备100%、训练100%、新模型评测0%。用户直接启动，不先跑plan、pip、MVP、GPU预检、重训或重建初态。使用同一固定update-001000，10合规SR对原24.44%（22/90），00官方SR对86.67%（78/90）；不混成一率。原九任务、完整指令、双图/本体、seed7/chunk8/H520、原端点与全部视频/原始query/actions保持。

## 启动（只启动一次）

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-v2-44b6ca02

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HOME=/HUBU-AI096/zp/ICML/Learning-Not-to-Act/models/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export PYTHONPATH="/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/LIBERO-8f1084e3132a39270c3a13ebe37270a43ece2a01${PYTHONPATH:+:$PYTHONPATH}"

nohup python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-eval-001/evaluation.json \
  --out /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-001 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-001.console.log 2>&1 &
echo "PID=$!"
```

看日志（Ctrl+C只退出tail，不停止nohup）：

```bash
tail -n 30 -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-001.console.log
```

结果在新输出的`summary.json`/`report.md`；视频在`tasks/<key>/videos/`，原始记录同任务目录。当前入口按任务单元更新报告，控制台主要为condition/task/status；旧六10任务每单元10条，内部没有新增逐episode实时SR。未齐时formal SR=N/A是预期，不把缺失记模型失败。X的实时SR/去重复读小增量仍open，不等它、不热改运行目录。技术中断保留证据，不自动重跑；已有输出目录会拒绝。

## 已完成的部署与文件核对

两环境已无依赖安装必要方法包，7个关键方法/依赖清单字节匹配部署源码、factory可导入；未升级其他库。纯文件计划通过90+90=180、126调用，模型/仿真未创建；不要求用户重复核对。

- adapter SHA：`21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8`
- plan身份：`d6ab87244f873199e1ab560320af3d343b92175355b7797ffb484348187ac2fd`
- evaluation配置SHA：`78a639f661d59f7c35249552255d409860fa8540e8d38e44b5083de4f409a2f9`
- 新runtime SHA：`3c03ffb2422e10c253143fef601fcf5a79f34be56060b54b455ace2c0bfe6e1e`

新runtime仅repo_path改为与训练相同的干净OFT副本，原脏目录/runtime/基线保留。新三00指向实际已构建`task033_nine_aedfe169/preparation/normal00/sources.json`；旧`configs/sources00.json`是空模板，首次文件计划因此报错已保留，仅纠正配置引用，没有重建状态或修改评分。

下一步操作和执行者：用户启动正式180条评测；Codex在用户交回后分析两类SR、任务分解和视频，不代启动/监督实验。
