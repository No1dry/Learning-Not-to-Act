# 035教师v2｜003正式恢复启动命令

2026-11-03，Codex。已通过[R5软件审查](../../collaboration/reviews/035_round5.md)，68项受影响CPU/fake全过；实际73/旧8引用与配置纯文件核对完成，不再增加真实预检或让用户先重复plan。不需要pip安装/升级或重新下载数据。

本次用户已批准：**复用旧8条合格轨迹，只重建指定73来源（53train/20dev）**，最多73普通重放＋438次10尝试、H520。原001/002和原资格保留。正式benchmark评分/原状态/split、训练1000更新7:3、同adapter90+90评测不变；合格量不保证。这是轨迹生成，不是模型训练或评测。

## 启动一次

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate /HUBU-AI096/zp/ICML/Learning-Not-to-Act/envs/selector
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-v2-44b6ca02

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config

mkdir -p /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs
nohup python -u -m egrs.trajectory_augmentation.recovery recover \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-v2-44b6ca02/recovery.json \
  --output /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/generated-003 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs/generate-003.log 2>&1 &
echo "PID=$!"
```

这是已实现的`recovery recover`入口，不再使用旧的`cli generate`。调度在selector环境运行，实际native子进程沿已绑定原OFT worker venv；没有加载旧selector模型。输出必须是不存在的新目录，勿重复启动。

## 日志与完成判定

```bash
tail -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs/generate-003.log
```

作业先做文件引用核验并复制旧8条，再处理73个来源；因此刚开始可能尚无第一条完成进度，不能另开一份。每来源完成会报`processed_sources/planned_sources=73`、百分比、技术错误、新normal/10合格数、旧复用量及实际新attempt数。处理百分比不是成功率。

结束后给Codex：`generated-003/recovery_report.json`、`generated-003/export/report.json`和总日志。`new_execution`是本轮新增实际尝试，`reused`是旧8条，不能把上限438当已执行分母。`pools`与`training_ready`表示train/dev×10/normal四池是否非空，不代表模型已有效。

teacher v2仅让table_drop未知留诊断；已确认违规、其他关键未知、完成/释放/A保护等仍检查。新失败观测保留但不进训练，ready=false不会自动改split、追加尝试或训练。结束后Codex按实际结果给原一组1000更新混训命令；本次所有真实作业仍由用户启动，Codex未运行。
