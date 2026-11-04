# Task035：双bridge修复后，用户启动eval002

准备/训练100%，新模型评测0%。R9已接受PR10@fb16a672的兼容修复并隔离部署，两套真实源/资产/包版本/compat完整指纹只读核对2/2通过；没有实例化环境或运行模型/仿真。无需再等X、plan、pip、GPU预跑/MVP、重训或重新生成状态。

本页替代已暂停的eval001启动命令。固定同一最终update-001000，原10/00各90，共180，九任务各10，完整原指令/双图/本体，seed7/chunk8/H520和原端点/评分。10二元合规SR对原24.44%，00官方SR对86.67%，不混分。旧六120条用原ac130177 bridge，新三60条用原d8541ef4 bridge，均严格原环境身份；分派不进策略。全部视频/原始query/actions保存。

## 直接启动一次

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate peft-openvla
source /HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/venv/bin/activate
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-dispatch-fb16a672

export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export HF_HOME=/HUBU-AI096/zp/ICML/Learning-Not-to-Act/models/huggingface
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export PYTHONPATH="/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/LIBERO-8f1084e3132a39270c3a13ebe37270a43ece2a01${PYTHONPATH:+:$PYTHONPATH}"

nohup python -u -m egrs.trajectory_augmentation.evaluation run \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-eval-002/evaluation.json \
  --out /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-002 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-002.console.log 2>&1 &
echo "PID=$!"
```

看日志（Ctrl+C只退出tail，不停止nohup）：

```bash
tail -n 30 -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-002.console.log
```

输出下的summary.json/report.md按任务单元更新；控制台仍主要为condition/task/status，旧六10每单元10条，内部暂不逐条打印SR。未齐formal SR=N/A是预期，可看报告live completed SR；不是缺失算失败。独立实时SR/去重复读小增量仍非阻断，不热改运行目录。

视频为`tasks/<key>/videos/`；环境版本证据另在每task的environment_dispatch.json，原始轨迹/输入/动作仍由原core保存和核验。技术中断保留证据，队列不会自动重跑；已有输出会拒绝，勿再次执行旧001命令或改旧结果。

## 身份记录

- 最终adapter SHA：`21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8`
- eval002配置SHA：`77332bac746797b2f45ed5145ddd990e63b69ef7b4a4059b9945191f9482d558`
- base runtime仍`3c03ffb2422e10c253143fef601fcf5a79f34be56060b54b455ace2c0bfe6e1e`，与001相同
- plan身份：`48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b`
- 分派descriptor身份：`186087e7321b6b5e672a1d0c8e76ddd08b63a9797f24e049223f0a02d926f889`

下一步操作和执行者：用户启动上述原180条评测，Codex在用户交回后分析两类SR、各任务和视频；X本兼容修复已验收，无返修。所有旧失败/训练权重/状态保持，不重跑基线或追加实验预算。
