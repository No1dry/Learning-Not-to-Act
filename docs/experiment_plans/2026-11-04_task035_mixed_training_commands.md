# 035｜003数据完成，启动一组1000更新混训

2026-11-04，Codex。003实际完成100%，技术错误0，合并75normal/221个10轨迹，train/dev四池非空；[R6结果审查](../../collaboration/reviews/035_round6.md)允许按既定预算直接训练。没有额外MVP、GPU预试、追加数据或原始模型基线重跑。以下训练仅由用户启动，Codex未执行。

## 在服务器执行一次

训练需要原OFT环境，不使用selector环境。第二行激活原Conda底座，第三行激活其已有OFT venv；不安装/升级包，也不解析替换其Python软链。代码仍为已部署44b6ca02，OFT用同commit的独立干净副本，旧本地改动目录完整保留。

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/activate
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-v2-44b6ca02

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HOME=/HUBU-AI096/zp/ICML/Learning-Not-to-Act/models/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export PYTHONPATH="/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/LIBERO-8f1084e3132a39270c3a13ebe37270a43ece2a01${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs
nohup python -u -m egrs.trajectory_augmentation.training \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-v2-44b6ca02/configs/trajectory_augmentation/robot_rewind_mix.json \
  --export-dir /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/generated-003/export \
  --output-dir /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-mix-001 \
  --benchmark-root /HUBU-AI096/zp/ICML/LIBERO-Remain-task033-r7-d8541ef4 \
  --oft-root /HUBU-AI096/zp/ICML/external/openvla-oft-task035-e4287e94 \
  --checkpoint /HUBU-AI096/zp/ICML/checkpoints/openvla-7b-oft-libero-sog10 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-mix-001.console.log 2>&1 &
echo "PID=$!"
```

不要改用有旧Python改动的`external/openvla-oft`，现有训练器会拒绝它；干净副本已准备，不需要用户自己清理或clone。输出为新目录，勿重复启动。发生错误保留日志/已保存checkpoint，不删除目录或自主另开一组训练。

## 查看进度

```bash
tail -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-mix-001.console.log
```

启动先读取数据身份并加载7B底座，第一条update不会立即出现；之后每个update打印`update`、`completion_percent`、`loss`及学习率。`runs/trajectory035-mix-001/metrics.jsonl`也保存每次更新。训练日志不是SR；SR在训练后正式评测得到。

配方保持：1000次更新，10/normal损失0.7/0.3；每有效batch16样本含12个10/4个normal（采样75/25不等于损失比例）；bf16、microbatch1、累积16、lr2e-5、seed7、LoRA r16/alpha32，只训练语言attention q/k/v/o，底座/视觉/head/proprio参数冻结。每250更新保存及有界dev诊断（每域最多256窗口），正式固定末1000权重，不按正式测试或dev择优改成别的权重。

结束后交回总日志、metrics.jsonl、run_config.json、selected_checkpoint.json、update-001000/identity.json。不要现在就运行旧eval配置；Codex据实际训练产物给同一个adapter的原10/00各90命令，并将新eval runtime指向同一干净OFT副本，保留旧runtime和基线记录。00保持与10提高均需实测，训练数据ready不代表方法已有效。
