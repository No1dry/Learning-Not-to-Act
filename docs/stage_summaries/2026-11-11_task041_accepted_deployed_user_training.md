# 041软件验收、隔离部署与用户训练交接

2026-11-11，Codex。[R1裁决](../../collaboration/reviews/041_round1.md)接受固定PR16@e8dcf879（实现c51df70e，继承accepted PR15@428c1358），不自动merge，X无需返修。用户已批两组正式预算，实施与真实效果分开。

## 本轮确认

两组均以040末1000全部可训练模块初始化，基础都是C1、新优化器/调度、各新增1000；R0不是旧C0。只有R1对历史old003六任务train ten的已有最多4个位置增加0.10的完整039动作软保持。原BC/loss/采样/dev/040数据不变，teacher独立新增分支、只共享原冻结底座，所有参考先于学生图并恢复模式/路由/checkpoint/cache/RNG。完整初始化/严格041身份、同run恢复、三账本前扣及单学生原180/臂接线通过审查。

Codex独立定向CPU/fake166通过、0失败/错误/skip，四组65/32/43/26；复用原固定fixture、未改源码或断言，没有真实VLA/MuJoCo/GPU验证。70原部署源/依赖中69不变，旧OFT仅扩显式可选modules参数，新10模块独立命名空间。详细测试与SHA见[机器证据](../../collaboration/evidence/041_codex_acceptance.json)，不将CPU测试当SR/速度/显存证明。

## 文件部署完成，不代表实验已启动

新code/config名task041-e8dcf879，80源码/依赖和8配置/脚本服务器SHA一致，040/039权重实际SHA匹配批准值；原runtime逐字节复制，eval只改041包络/实验臂/未来adapter，原基础C1、来源/core/reporting/双bridge/评分/视频保持。两个原环境仅no-deps editable映射指向新包，在core cwd静态定位模块，没升级依赖或改旧代码/数据。脚本仅bash -n，没有执行。未来两train/two eval/launch marker目录均不存在。

**准备100%，真实训练和评测0%；用户下一直接启动R0→R1各1000，正常完成后再单独启动正式360。** 私有完整命令在本地docs/041_服务器完整运行命令_2026-11-11.md，公共脱敏[运行交接](../experiment_plans/2026-11-11_task041_user_training_evaluation_commands.md)。启动器自动激活既有环境，内部是两条普通python；失败即停，保留现场/账本、不自动重试/退款/评测。无需generate/index/新资格、额外Codex预检/MVP/基线。

## 预算、判读与归档

本轮新增2000更新，原SOG10参考≤18048＋039 R1 train-only≤4000＝全部参考≤22048，student≤49120，新模型正式360；新数据/仿真/标签/index生产0，未增加seed/系数搜索。祖代1000与新增1000分记，R1−R0主比较，R1−040还包含额外训练和优化器重启。策略保持不等于episode内成果硬保护，也不是ICML创新保证。

软件closed、真实训练/eval/研究open，X暂无修改任务。旧03958.89%/85.56%、04058.89%/86.67%、全部原数据/权重/失败/视频与署名保留，不重开旧run、不merge/删除。六关键文档精确GitHub commit读回SHA本地备份，固定X8原稿按PR head另存与manifest登记，源tar/四独立JUnit/私有部署收据保留。原dirty checkout不改，待删=[]；Codex/X没有代启停任何真实作业。
