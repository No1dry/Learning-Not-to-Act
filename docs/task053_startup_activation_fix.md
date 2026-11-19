# 053启动顺序勘误（configfix1）

用户启动v2后，在加载模型/读取父轨迹之前报`ModuleNotFoundError: No module named 'benchmark'`。原因是Codex在run入口先调用validation.identity，再到parent里激活固定core；此前CPU fixture和文件诊断已经激活core，遮住了全新CLI进程的初始化顺序错误。不是用户conda、权重、源数据或新实验失败。

修复只在run中、构造engine/identity之前显式调用原old.activate(cfg)，原依赖校验不变。除注释与这一调用，无模型、评分、源规则、继承逻辑或预算变更。新增独立Python进程CLI回归：从benchmark尚未导入开始，真实解析配置和激活固定依赖，抵达parent入口后用CPU-only异常截断；无真实父数据/模型/仿真。053受影响16项CPU/fake通过。

最终code/config短名改用task053-index50-continuation-v3，新的启动marker和console标configfix1。旧v2日志、task053-launch-001以及v1/v2代码均保留，不删marker。原正式run输出尚未创建，无新动作，仍使用原run ID；不退款、不重复补建或已执行11条。

用户新一条启动器先继承原11、base新439，再H1新450，共原900。旧450 bank/052源版本/父plan和partial summary SHA、全部权重/评分及原模型参数保持。Codex只做软件/CPU-fake/文件部署，不启动任何真实作业。先前38项覆盖的索引/证据/续跑数学部分不重跑，本次只跑16项受影响测试；不是声称已通过真模型完整评测。
