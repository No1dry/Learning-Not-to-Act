# Task043-v2：两组训练完成，用户直接正式360评测

2026-11-16。H0/H1均连续1000更新、末1000固定选择，正常结束、无043残留进程。原始SOG10新LoRA，新增/祖代1000/0，不是042续训。两末adapter SHA前缀371f9f13/1479edd4，完整状态8f39bca3/32c4768d已核对。所有真实阶段仍由用户亲自启动。

## 当前操作

按本地`docs/043-v2_正式评测命令_2026-11-16.md`切换到既有simulation环境，source部署的pathfix1 session。然后只运行：

```bash
nohup bash "$LNA043_CONFIG/eval_both_sequential.sh" \
  >> "$LNA043_ROOT/runs/task043-eval-launch-001.console.log" 2>&1 &
echo "PID=$!"
```

先H0正式180，原正式报告正常结束后H1正式180；每模型10/00各90，共360，全视频。两臂推理都无状态提示/sidecar/教师，完整原指令与原传感输入保持；原九任务状态bank、H520/chunk8/seed7、双bridge、10二元合规/00官方不变。

不重训、重做prepare、选其他checkpoint、加seed、新plan/MVP/预检或重测旧基线。正式入口自己绑定真实末权重创建计划。已有run/marker则拒绝，不删失败/预算文件、不自动重试；交回日志判断。

## 实时进度

```bash
watch -n 5 "tail -n 3 '$LNA043_ROOT'/runs/task043-*eval*.console.log"
```

Ctrl-C只退出watch。执行完成后仍有原正式核验，最终SR在各summary.json/report.md中给出；不把训练loss或未核验执行比例当SR。

## 已核对与解释边界

原始metrics各1000行，连续更新/三池数量及每步记录batch-key摘要一致，同底座/index/sidecar；不是全tensor/RNG审计。每组参考9024、模型27072，两组合计18048/54144恰等批准上限。末权重/完整训练状态按字节核对，无模型/状态反序列化或GPU前向。当前正式评测0%，启动器只bash语法/原部署SHA核对，没有替用户执行。

最终无提示dev10 L1 H0=.1234438700、H1=.1230172414，不当闭环成功率/显著提升/方法机制结论。主比较H1−H0；10第一优先、00保持其次。原权重、中间checkpoint、旧失败和署名保留，X无需返修或泛审，PR18不自动merge。
