# Task035：eval004只续跑剩余120条

R11接受PR10@ac2ec431软件与部署，63/63受影响CPU/fake通过；父003配置/模型/依赖与六组完成索引轻量核对通过。实际仍完成60/180=33.33%，10阶段合规30/60=50%，00未执行；本次新120尚未启动。

**先释放GPU占用，再由用户启动一次。** 不重跑60、不重训，不执行额外plan/pip/MVP。正式入口会先完整读取核验003父工件，核验失败就不加载模型/执行动作；这段可能没有新task日志。不要把它当成已经在跑新的模型轨迹，也不要重复启动。

## 普通完整命令

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-resume-ac2ec431

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HOME=/HUBU-AI096/zp/ICML/Learning-Not-to-Act/models/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export PYTHONPATH="/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/LIBERO-8f1084e3132a39270c3a13ebe37270a43ece2a01${PYTHONPATH:+:$PYTHONPATH}"

nohup python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-eval-004/evaluation.json \
  --continue-from /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-003 \
  --out /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-004 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-004.console.log 2>&1 &
echo "PID=$!"
```

看日志（Ctrl+C只退出tail）：

```bash
tail -n 30 -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-004.console.log
```

## 进度与报告

核验后只加载同一最终模型，继承60条成功/失败，新执行120＝10剩30＋00全90。运行中progress.json记录inherited_completed=60、new_runtime_completed=n、new预算120；总体进度是(60+n)/180，新增进度n/120。控制台按任务记录状态，完整SR在退出时独立核验父/子工件后写summary.json/report.md，不使用缓存分数绕过原始证据。

原180人口与各90分母、10二元合规SR/00官方SR及24.44%/86.67%基线、同一update-001000、原完整指令/双图/本体/端点、seed7/chunk8/H520、全部视频/原query/actions不变。新视频在eval004/tasks/<key>/videos/；继承60的视频仍在003，报告明确引用旧来源，不伪装为新执行。

**003整个目录必须保留且不修改**，包括summary/report/原始工件：独立reader会核对父引用。不要删除、覆盖或在其中另写派生报告；0步技术attempt保留历史而非模型失败。新输出存在会拒绝，不自动重试。

配置仅schema改v3，仍引用原002/base-runtime.json以保持父合同；SHA `05a010c8b9f344054e8a51110820f5085d30f2cd701149950e6d0b6809dc95dc`。源归档SHA465036ff...，最终adapter SHA21b982e5...。完整父工件核验由本命令内置执行；取消的额外准备扫描不计为已通过，也不需要用户重新跑。

下一步操作和执行者：用户释放显存后启动本命令；Codex在用户交回后分析结果。X本次修复无需返修；不追加模型预跑、真实诊断或实验预算。
