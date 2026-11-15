# 043-v2：软件已实现部署，用户直接准备＋训练

## 最新：pathfix1替代首次启动命令

首次用户启动因sidecar输出位于旧输入声明的宽data根目录内，被防覆盖检查正确拦截；这是Codex部署路径配置错误，不是模型或数据失败。写入首条标注之前退出，状态输出和两个训练run均未创建，模型前向0。保留旧日志/空launch marker；不删marker、不放宽保护规则。

Codex已新建`configs/task043-codex-pathfix1`七份配置，仅训练配置的sidecar路径改为data树外的`annotations/task043/status-001`，session绑定新配置目录，启动marker/prepare日志独立版本化。模型源码/配方/评测配置不变。实际服务器两个严格配置及全部保护根不相交检查通过；新增两项CPU/fake最终通过（首次fake参数索引错误保留，不算生产失败）。没有代启prepare/训练/eval。下一用户source本地完整命令中的**pathfix1 session**后启动下方命令；预算不变。

2026-11-15。用户明确本轮由Codex直接改代码，X无需重复实现/泛审。PR18固定head `da666bc4a5d1aaa04381d64c29dbc0412fee6628`，依赖accepted PR17@7d28d515；两个PR均未自动合并。

71个不同CPU/fake最终通过，108源码/依赖/模板和7实际配置SHA一致；两原有环境无依赖升级映射新隔离副本。实际训练配置严格解析及正式来源保持已核对，不构造数据/模型，真实状态文字生产、训练和评测0%。

具体服务器路径/环境激活命令在用户本地`docs/043-v2_服务器完整运行命令_2026-11-15.md`及聊天中，不把凭证或私有路径放公开文档。

## 1. 用户启动准备→H0→H1

先按本地完整命令激活既有OFT环境并source实际部署的session043.sh，再运行：

```bash
nohup bash "$LNA043_CONFIG/prepare_and_train_both.sh" \
  >> "$LNA043_ROOT/runs/task043-launch-pathfix1.console.log" 2>&1 &
echo "PID=$!"
```

脚本先CPU读取既有JSON产生状态文字，通过后从原始OFT先训H0 1000、再训H1 1000。它不续042，不重建旧索引，不做MVP/GPU预跑，也不自动评测；不等额外Codex人工门槛。输出/marker已存在则拒绝，失败不自动重开或启动下一臂。

## 2. 实时进度

```bash
watch -n 5 "tail -n 3 '$LNA043_ROOT'/runs/task043-*.console.log"
```

prepare日志为当前键数和百分比，h0/h1日志为`043 h0/h1 train N/1000 (百分比)`；初始加载时可看hash/分片进度。Ctrl-C只退出watch。固定末1000，开发loss不是闭环SR。

## 3. 两臂训练完成，用户另启正式评测

切换到既有simulation环境并重新source同一session，然后：

```bash
nohup bash "$LNA043_CONFIG/eval_both_sequential.sh" \
  >> "$LNA043_ROOT/runs/task043-eval-launch-001.console.log" 2>&1 &
echo "PID=$!"
```

H0正式180正常报告后H1正式180，两模型10/00各90、共360、全视频。正式入口自己绑定实际末权重与原人口，不另跑plan/MVP或旧基线。部署始终无状态提示/sidecar/教师，不改原core/reporting/双bridge/评分。正式SR在原末尾证据核验完成后给出。

## 4. 固定预算与保留

一次真实CPU sidecar≤143960主键，零新仿真；两个1000更新，原策略参考≤18048、含辅助/dev训练模型前向≤54144，正式360。超限/缺失不伪造、不退款重跑。原状态、权重、失败、署名和42结果保持。

若启动器报告已有数据或run，不删除marker/失败文件。将日志交回，按同run完整checkpoint规则判断恢复；正常整套流程不叠加手动命令。
