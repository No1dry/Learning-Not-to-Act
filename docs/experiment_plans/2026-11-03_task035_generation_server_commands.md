> 历史001命令，勿再执行：首轮因解释器软链解析失败；已由[修复后的002命令](2026-11-03_task035_generation_retry002_server_commands.md)替代。以下原文保留作记录。

# 035｜九任务轨迹增强：服务器启动命令

2026-11-03，Codex。九个原始HDF文件共12,790,079,988字节已下载、上传并核验原始LFS SHA；180条种子清单与六份配置文件已准备并核验传输。**现在可由用户启动正式轨迹生成，不再增加MVP或仿真预检。** 本文命令没有由Codex执行。

这一步是**生成训练轨迹**，不是模型训练或评测：九任务各自然前20条普通示范，父来源分组为train136/dev44；最多180普通重放＋1080次10尝试，不保证成功生成量。原正式90/90测试状态和模型轨迹不进训练，普通示范与official init物理祖源未知，不声称物理独立。

## 1. 启动（只执行一次）

在服务器终端粘贴：

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate /HUBU-AI096/zp/ICML/Learning-Not-to-Act/envs/selector
cd /HUBU-AI096/zp/ICML/Learning-Not-to-Act/code/task035-564c91c9

export CUDA_VISIBLE_DEVICES=0
export LIBERO_CONFIG_PATH=/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/remaining_libero/libero_config
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

mkdir -p /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs
nohup python -u -m egrs.trajectory_augmentation.cli generate \
  --config /HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-564c91c9/generate.json \
  --output /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/generated-001 \
  >> /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs/generate-001.log 2>&1 &
echo "PID=$!"
```

`selector`环境只运行调度/数据索引；真实native子进程已在配置中绑定原OFT worker环境和固定仿真/core，不会加载VLA或旧selector。使用`egrs.trajectory_augmentation.cli`，不是没有`__main__`入口的包名。不要同时运行两份，也不要删除旧输出重跑；已存在输出会拒绝覆盖。

## 2. 看日志

```bash
tail -f /HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/logs/generate-001.log
```

每完成一个父来源，会显示`processed_sources / planned_sources=180`和`completion_percent`；这表示生成来源处理进度，不是模型SR，也不代表该来源已成功生成10。单来源内部日志在`generated-001/artifacts/source-000/worker.stdout.log`和`worker.stderr.log`等；不为看日志另跑仿真。

结束后保留并交回：`generated-001/generation_report.json`、`generated-001/export/report.json`及总日志。报告记录实际10/normal合格数、失败原因、任务/划分覆盖，失败分母不丢。每任务自然第一个父来源记录代表性视频（若该来源失败也保留诊断，不按成功筛选）。

下一步Codex根据实际生成报告给混训命令；一组1000更新已获预算批准，但此时没有启动训练。同adapter正式10/00各90条评测在训练后进行，复用原24.44%/86.67%两基线，不重跑原始模型。
