# 048：用户启动LIBERO-10官方500×两模型

已部署，53项CPU/fake过（含047旧42与048新11），代码PR23@4d8762c4504a09f7d9efac099137a7ce8ff35a3b。准备100%、正式0。不是实际模型/物理效果验证，不需要X实现或新MVP。

在原peft-openvla＋simulation venv中source新部署的session048.sh后：

~~~bash
cd "$LNA048_ROOT"
nohup python -u -m egrs.official048 run-all \
  --config-dir "$LNA048_CONFIG" \
  --output "$LNA048_ROOT/runs/task048-official-libero10-001" \
  >> "$LNA048_ROOT/logs/task048-official-libero10-001.console.log" 2>&1 &
echo "PID=$!"
~~~

完整实际conda/venv/session路径及绝对路径watch命令见本地048_LIBERO10官方评测完整命令_2026-11-19.md。

原版联合OFT500正常完成后自动H1@3000 500，每模型全部10任务×50官方初态，含task5书/收纳盒；新H520/等待10/chunk8/seed7/env0/两图proprio/crop和libero_10_no_noops均沿官方，仍无完成提示。成功按官方done，不用Remain评分，全部视频保存。

同一shell实时只读：

~~~bash
watch -n 5 "python -m egrs.official048 progress --output '$LNA048_ROOT/runs/task048-official-libero10-001'"
~~~

简洁日志：

~~~bash
watch -n 5 "grep '\[048\]' '$LNA048_ROOT/logs/task048-official-libero10-001.console.log' | tail -n 3"
~~~

新开shell不要依赖未设置的ROOT变量，请用本地完整文档的绝对路径命令。加载阶段0%正常。最终root下comparison.md/json给两模型官方500成功率、10任务和配对得失；两组目录保留summary、episodes.jsonl、官方日志和rollouts视频。

一条正式1000，不重训/prepare/index/旧047、额外MVP或GPU预检；自然请求上限65000。技术错误保留停止，不自动删目录/重试/退款，部分live SR不当满额正式结果。旧047原三套3000及所有旧权重/分数/视频保持，用户亲启，Codex待结果分析，PR23不自动merge。
