# 036：直接启动一组1000更新训练

2026-11-05，Codex。[R1软件/部署验收](../../collaboration/reviews/036_round1.md)通过；元数据索引已备好，不需用户再运行index/plan/pip或真实MVP。用户已批准的一组1000更新、参考≤9024含dev及随后新180预算不变，**以下真实训练仅由用户启动**。当前训练0%、评测0%，准备100%。

## 在服务器执行一次

沿用035实际训练的Conda底座＋已有OFT venv，不使用selector环境，不升级包。已有venv必须正常激活以保留原依赖；不是再建新环境。新目录运行本轮代码，无需改变旧环境editable映射或pip安装。

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/activate
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task036-205d6530

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HOME=/HUBU-AI096/zp/ICML/Learning-Not-to-Act/models/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export PYTHONPATH="/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/LIBERO-8f1084e3132a39270c3a13ebe37270a43ece2a01${PYTHONPATH:+:$PYTHONPATH}"

nohup python -u -m egrs.retention.training \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task036-205d6530/configs/retention/policy_retention_distillation.json \
  --export-dir /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/retention036/index-001 \
  --output-dir /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/retention036-train-001 \
  --benchmark-root /HUBU-AI096/zp/ICML/LIBERO-Remain-task033-r7-d8541ef4 \
  --oft-root /HUBU-AI096/zp/ICML/external/openvla-oft-task035-e4287e94 \
  --checkpoint /HUBU-AI096/zp/ICML/checkpoints/openvla-7b-oft-libero-sog10 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/retention036-train-001.console.log 2>&1 &
echo "PID=$!"
```

只启动一次，不覆盖旧目录；显存请保持可用，不自动终止其他人进程。`--checkpoint`是原完整SOG10，不能换成035 adapter；本轮不继续035训练。无需额外GPU预跑。若报错保留日志/预算ledger/目录，不删除后重开run或自主增加参考预算。

## 看日志与进度

```bash
tail -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/retention036-train-001.console.log
```

先读取已有数据身份并加载原7B，第一条update不会立即出现；此时不是评测。开始更新后每轮打印update/1000、completion_percent、三池pool_l1/weighted_l1、reference_calls及elapsed/eta_seconds，同时写metrics.jsonl。loss不是SR，SR在后续原10/00各90正式评测得到。

每轮12ten/4fresh-ref/4raw-ref，普通各半prefix/full；损失.50/.25/.25按池有效标量均值，lr2e-5/warmup50/bf16、语言LoRA r16，其余冻结。参考仅训练/dev使用、共享底座旁路新增LoRA，不加载第二7B；总最多9024单观测前向（8000train＋1024dev）。比035多25%学生样本并增加无梯度参考前向，当前未实测用时，不能承诺与035相同。

250/500/750/1000保存，固定最终`update-001000`评测，不按dev或正式SR选权重。结束后把完成消息交回Codex，由Codex核对实际训练产物并给同一新模型10/00各90命令；不要运行035 eval配置或继承035分数。若需恢复，先交回错误/日志；原预算ledger不回退，不能假设额外失败调用可免费重算。
