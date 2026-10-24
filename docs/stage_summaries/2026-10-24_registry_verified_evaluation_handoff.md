# 027文本拆解真实通过与正式评测交接

用户已亲自启动027单次同3B/checkpoint-3调用。Codex读取registry和原文audit：image_count=0，prompt609/generated95 tokens；bare_json，wrapper/JSON/schema全部passed，error=null，model_loaded/adapter_loaded=true。

原指令`put both the alphabet soup and the tomato sauce in the basket`逐字保留；两个source_text分别为`the alphabet soup`、`the tomato sauce`；actor_text分别为`put the alphabet soup in the basket`、`put the tomato sauce in the basket`。内容正确，026已见的指令改写/人物角色误解故障在此真实调用中已解决；不是仅消除异常或改写返回结果。不外推其余指令拆解、视觉状态判断或方法成功率。

实现仍为[PR #6](https://github.com/No1dry/Learning-Not-to-Act/pull/6)的`a236454a50b20c06674afd8f63c8120c86c0289e`；原55项CPU/fake、三环境部署和文件token预算证据复用，无新增测试门槛、模型诊断、训练、仿真回放或来源重建。PR未自动merge；旧025技术暂停、026原失败、027首次修订记录及原始数据均保留，无清理/删除。

正式评测新配置仅指向已部署027 selector源码，固定eval core515e87d、checkpoint-3、原OFT及评分不变。新输出目录与旧运行隔离，尚未创建评测结果。完整conda/venv/python启动命令已在本地交给用户，前台tee日志、progress.json和双视角视频沿用原入口。

准备/部署100%，训练100%，正式方法评测完成0%。直接进入同旧基线80条可用来源的正式比较，计划100和20缺旧来源仍披露，不计20条为模型失败、不擅自补状态或重跑基线。80条全部完成时全计划进度为80%、状态completed_with_missing_sources，不能宣称100条真实执行。

下一步操作和执行者：用户启动正式评测；Codex在用户交回结果后读取日志、指标和视频。Codex本轮仅读取已有模型输出、准备/上传配置与归档，没有代启模型或实验，不要求X继续返修。
