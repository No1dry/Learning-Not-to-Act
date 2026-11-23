# 047 Codex直接实现、自查与部署交付

用户“你直接完成吧”覆盖此前待X安排。软件/隔离文件部署accepted，X不重复实现/泛审。PR22固定bd871dea127a2049134be4fb0fa7f392061d28d5，依赖PR21@a1179099，源树dbff1510与本地测试树一致，未自动merge。

直接调用固定官方OFT的eval_libero原主体及run_task/run_episode，环境、观察、动作队列/夹爪、原生done与视频保存由原函数执行。只增加初始化H1加载、观察记账、输出隔离与六cell串行；旧生产egrs逐字不改。H1原rank16 LoRA只加一次，base不注入，官方cfg rank32保持。训练身份仍10统计，实际推理各suite正确归一化；没有为跨套改旧identity、旧restore或伪造metadata。

42个不同CPU/fake最终通过：31首轮＋8新增＋3个直接Observer测试cwd装配修正后补过。原追加JUnit中3失败保留，视频路径保护未放宽；不是生产行为失败后删断言。包括完整六组假500调用未改官方runner、普通horizon False与技术异常分开、严格tensor/RNG/统计、持久输出及汇总。是Codex软件自查，不独立第三方或真实7B/物理验证。

126源依赖模板与8实际配置/脚本按SHA部署到独立047目录，只显式PYTHONPATH，未升级依赖或全局editable重映射。实际六配置、固定H1字节、三套统计和60个BDDL/init路径通过文件核对；ML/物理未导入，真实初态/训练state未反序列化，未来run不存在。实际conda+simulation venv+session下read-only progress返回not_started。

准备100%，真实正式0。用户下一直接一条run-all，base/H1按Spatial→Object→Goal两两串行，各500总3000/自然动作块上限101000。官方seed7/env0/等待10/chunk8/两图proprio/crop/50默认初态与220/280/300保持，保存全原视频/live SR/百分比与最终逐任务/三套总体SR差值，不接Remain评分或新提示。不训练/新生成/标签index/教师/真实MVP或基线额外重测。

技术异常保留停止、不自动重试/删除/退款；原版论文分数不代现场baseline，旧九任务不拼成四套AVG。全部旧数据权重失败署名与脏研究checkout保持。源tar/原JUnit/实际配置/私有部署receipt与精确commit文档SHA本地归档manifest；无自动merge、删除或代启实验。软件closed、真实效果open。
