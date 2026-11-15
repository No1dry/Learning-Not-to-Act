# Task043-v2：Codex直接实现

用户2026-11-15明确“这次你自己改一下吧”，本轮实现/软件测试由Codex负责，X不需重复实现；已批准数值预算与用户亲启全部真实阶段的规则不变。实现以accepted PR17@7d28d515为依赖，不自动merge旧PR。

## 新入口

```bash
python -m egrs.hint043 prepare --index-dir ORIGINAL_040_INDEX --output NEW_STATUS_DIR
python -m egrs.hint043 train --config DEPLOYED_TRAIN_CONFIG --output NEW_TRAIN_RUN
python -m egrs.hint043 evaluate --config DEPLOYED_EVAL_CONFIG --arm h0 --output NEW_EVAL_RUN
```

上面是接口说明，不是已填路径的生产命令；部署后Codex提供具体conda/python命令。public训练模板需要session中的明确环境变量；eval配置由原accepted042配置复制，只改方法schema/group/arm和新末adapter，不重写来源或评分。

`prepare`只读原sealed040主索引及现成JSON。旧retention父记录是裁剪元信息，而lineage.source是完整原始父记录：按原source/hash/group/split/task/instruction核对身份，再验证lineage中原生active/invariant语义；不因字段裁剪而要求整字典相等，也不放宽谓词绑定。双壶集合化，释放未知不当负标签，逐帧facts不偷看未来。输出已存在则拒绝，错误保留；raw缺失不回放补齐。

H0/H1均从原始SOG10装新语言LoRA；无旧task_control、pair、TCIF、039教师或在线VLM。主训练每更新12ten/4fresh/4raw；最多复用其中4个eligible ten作辅助视图。H0辅助原prompt，H1辅助有当前事实，主分支/部署都无提示。8个原底座reference先于训练图；aux分批反向释放并保存detach目标，20个主输出只计算一次，最后一个optimizer.step。

原OFT函数仅增加可选`prompt_override` seam，默认调用字节/56动作隐藏路径保持。部署使用原native动作接口，额外观察真值字段不传入底座；不读sidecar或教师。新的独立adapter与完整训练state绑定原底座/索引/sidecar/配方/arm/预算，旧reader不误接。

每臂1000，reference≤9024，模型前向≤27072（主训练20000＋辅助≤4000＋主dev≤2048＋辅助dev≤1024）；两臂合计18048/54144。末1000正式180×2，原H520/chunk8/seed7/全视频与双bridge不变。软件测试不证明真实标签ready、模型SR或泛化有效。

顺序脚本`prepare_and_train_both.sh`在用户已激活既有OFT环境并source部署session后运行；CPU整理正常后H0→H1，不自动eval。eval脚本须用户另在原simulation环境启动。已有输出/原子launch marker拒绝重复，失败停止不退款/自动重开。

## 测试边界

测试只使用人工小数组、随机tiny CPU模型和假环境/假评分读写，未加载7B、读取真实HDF像素或启动仿真、真实sidecar、训练/eval。包括native提示长度变化的shifted56、共享反向/stop-gradient/前向计数、一次完整1000更新的tiny软件循环、保存恢复/旧账本防退款、两臂各180假接线。

初次本地新core fixture symlink建在错误cwd，导致2个setup error；已改成独立目录下的正确fixture链接，不改固定core/断言。该错误不是模型或真实数据失败，历史保留；最终以JUnit原始日志为准。源Git克隆发生HTTP2错误，改用此前SHA已验收的7d28d515归档建立独立副本；未触碰用户脏checkout。
