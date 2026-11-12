# 041固定末1000两模型正式360评测

2026-11-12，Codex。R0/R1新增1000均已100%完成并通过[R2文件审查](../../collaboration/reviews/041_round2.md)，完整末权重/训练状态本地SHA备份；正式eval0%。以下真实作业仅用户启动。

直接运行已部署configs/task041-e8dcf879/eval_both_sequential.sh一次即可。实际绝对路径命令在聊天/本地docs/041_服务器完整运行命令_2026-11-11.md第3节，不在GitHub暴露私有路径/凭证。脚本自动激活原Conda和simulation venv，模型在原OFT worker执行；内部仍是两条普通python：

~~~bash
python -u -m egrs.retention041 eval --experiment-arm r0 --mode run \
  --config "$LNA_CONFIG/evaluation.r0.json" \
  --output "$LNA_ROOT/runs/task041-r0-eval-001"
~~~

R0正式summary.json/report.md生成并正常退出后才同样执行r1。一键与逐组命令互斥，不重复启动；原子marker/已有输出拒覆盖，失败保留、停止后续臂，不自动退款或重试。eval启动器SHA cbf69a1befe6d13bcbff367ec1b0ca51c930619e889685fe6420aaa1026b68e8，与原部署一致且仅语法核对，Codex没有执行。

每模型九任务10合规90＋00官方90，两模型共360；实际配置各自绑定末1000 adapter，SHA R0=d4e726a867531f655d28e11f358ce0af597d4ada0f4928f4597aeadb28d38397，R1=456801220a677f4dbde7b41e2bd7857b14eeee8d731510cae926c1e944879ae9。原H520/chunk8/seed7/全视频、来源/人口/runtime/core/reporting/双bridge与评分不变，不继承039040分数、不依据dev loss改checkpoint。

无需再generate/index/plan/MVP、来源物理资格重复扫描、GPU预检、新baseline或训练；正式入口自己绑定实际权重和输入创建plan。模型执行100%后原进程可能仍在正式核验，需等summary/report及正常结束，不另开第二个report作业。

启动器总console提供START/COMPLETE/FAILED；逐臂console、run/progress.json看运行，最终报告给10/00成功率百分比。本地完整命令给绝对路径和简洁日志命令。当前没有新SR；主比较R1−R0，R1−040还混有新增训练/优化器重启。原预算正式360已获批，不追加模型episode/seed/系数搜索。

下一执行者用户；X无需改代码，Codex只在结果交回后读取/归档分析。全部旧训练数据/权重/中间checkpoint/失败/分数和署名保留，PR16不自动merge，无删除。
