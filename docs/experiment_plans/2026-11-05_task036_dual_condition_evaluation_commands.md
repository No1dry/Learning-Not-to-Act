# 036：固定最终1000权重，正式评测10/00各90条

2026-11-05，Codex。用户已完成036一组1000更新；最终权重/预算/来源核对完成。训练100%，新模型评测0%。本次是**新模型全新180条**，不继承035分数或轨迹，不重训/重建状态/重跑原模型。配置与必要方法包已准备，无需再pip/plan/MVP，**真实评测由用户启动**。

## 完整启动命令（服务器执行一次）

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task036-205d6530

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HOME=/HUBU-AI096/zp/ICML/Learning-Not-to-Act/models/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export PYTHONPATH="/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/LIBERO-8f1084e3132a39270c3a13ebe37270a43ece2a01${PYTHONPATH:+:$PYTHONPATH}"

nohup python -u -m egrs.retention.evaluation run \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/retention036-eval-001/evaluation.json \
  --out /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/retention036-eval-001 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/retention036-eval-001.console.log 2>&1 &
echo "PID=$!"
```

只启动一次，不加`--continue-from`，不运行旧035命令。新输出存在会拒绝，不自动重试；报错保留日志和原目录。检查时GPU空闲约81GB；共享资源状态会变化，不自动停止其他进程。

## 查看进度

```bash
tail -n 30 -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/retention036-eval-001.console.log
```

先做内置文件计划并加载一个最终VLA，随后打印model_completed/180和百分比、两条件各90进度；正式SR在全部工件独立核验后输出。最终核验同样显示百分比，不再每完成单元重扫所有旧raw。结束写summary.json/report.md/progress.json并打印**10二元合规SR、00官方SR**。loss不是SR，不用缺证据推测临时成功率。

全部视频保存在`runs/retention036-eval-001/tasks/<任务或episode>/videos/`，双视角全轨迹，query/actions/raw同存。每任务10条、九任务、00/10各90；原完整指令/双图/本体、seed7/chunk8/H520、旧/新bridge与各自端点/评分不变。

实际绑定036最终adapter SHA `b110901c2e0f85c2e012647d9fb6994da5d71d0e4ddf728b559d8d016ce36050`，不是035的21b982e5。eval仅单个适配VLA，没有原策略教师/FINISH/规划器。对照原模型10 24.44%/00 86.67%，以及03510 54.44%/00 73.33%，不混用评分口径。

下一步操作和执行者：用户启动正式180；结果交回后Codex统计逐任务SR、与原模型/035比较并取回代表视频。Codex未启动/停止/重跑任何真实轨迹，X当前无需返修。
