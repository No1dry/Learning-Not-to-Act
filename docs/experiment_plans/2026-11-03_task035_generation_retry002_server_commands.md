# 035｜解释器修复后的002正式生成命令

2026-11-03，Codex。R2阻断已按[R3](../../collaboration/reviews/035_round3.md)验收、隔离部署。CPU/fake8/8通过（含两项真实symlink）、一次真实配置纯JSON路径核对通过；不做额外仿真预检。以下真实作业仍仅由用户启动，Codex未执行。

复用已下载/核验的9个HDF、180清单、原版本锁和配置，**不重新下载、不改split、不覆盖001**。只换新代码目录、输出目录和日志文件。原001处理100%但初始化错误100%，合格轨迹0；002尚未启动，不代表本方法已有有效训练数据。

## 启动一次

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate /HUBU-AI096/zp/ICML/Learning-Not-to-Act/envs/selector
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-eecd25f5

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config

mkdir -p /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs
nohup python -u -m egrs.trajectory_augmentation.cli generate \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-564c91c9/generate.json \
  --output /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/generated-002 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs/generate-002.log 2>&1 &
echo "PID=$!"
```

`selector`只调度/索引，native子进程在修复后保留原OFT worker venv入口。最大180普通重放＋1080次10尝试/H520不变，不保证合格轨迹数量。不要重复启动同一命令；已有输出会拒绝覆盖。

## 查看日志

```bash
tail -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs/generate-002.log
```

每处理完一个父来源显示处理百分比，不是成功率；单来源内的日志保存在`generated-002/artifacts/source-000/worker.stdout.log`、`worker.stderr.log`等。结束后以`generation_report.json`和`export/report.json`里的合格10/normal数量、错误、各task/split覆盖为准，不能只看处理100%。

用户交回报告后由Codex给出混训命令（预算一组1000更新，7:3损失保持）；不自动训练。原10/00各90正式测试与原基线不重跑。X本路径修复无返修，评测报告效率小增量仍为非阻断并行。
