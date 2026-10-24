# 020部署更正：离线标注依赖必须使用完整参考core

2026-10-24，Codex记录。此说明更正019/020部署材料中“评测core515e87d已具备全部标注助手、可直接开标注”的错误判断，不倒改原始失败。

## 实际结果和原因

用户启动020实现 `dc4dfa97d131fcdf8c1cc116e18d529a9d4d0efb` 后，200/200来源（100%）在 `core_activation` 阶段因 `No module named 'benchmark.remaining_goals.finish.xml_assets'` 失败。最终manifest identity为 `766fcd5a13a1f05bb56ffde90222f369b0a4d3f98df3277d1a030bac6d6439d9`；3200查询processed/supervised均0%，ready=false、usable=false。作业已自行结束，不是Codex停止。此前读取元信息已通过，不再是019的缺少BDDL正文字段错误，也尚未进入渲染/对齐或证明模型成败。

评测裁剪core `515e87d9b93ab838428791273a0f3020d6f56e9c` 没有该XML助手。选择它用于离线物理标注是Codex部署核对遗漏；148项CPU/fake并未验证实际部署依赖的完整导入，不能把软件范围通过当成真实入口可用。X本轮元信息修复的软件证据保留，无需为此修改模型或方法实现。

## 已完成的配置纠正

使用019/020配置示例本就支持的annotation reference core `c6dc98de0c54517c976057598b60f4cedf7fa3e5`，`allow_reference=true`。固定Git checkout独立部署，不把xml_assets.py塞进或热改原评测core。方法代码、原环境、旧配置/输出与实际eval所用515e87d不变；后续评测仍使用其原固定core，不将reference-only状态冒称正式评测。

在实际worker解释器中，固定参考core身份/干净状态检查及8个所需助手的完整导入通过（100%），包括resolve_xml；未调用任何助手执行物理操作，未导入libero/robosuite/mujoco，未打开原始HDF/图像、恢复状态或渲染。三个新传输文件SHA-256一致。此检查仅防止刚发生的缺模块错误，不新增GPU预检。

新配置与输出独立命名为020r2；复用已上传方法实现、20个BDDL文件锁与3200个原查询。Codex未自动重跑，真实native/XML/原图对应与监督覆盖仍待用户启动验证；不声称一次导入通过就保证全部后续运行成功。

下一步操作和执行者：Codex提供020r2完整命令；用户亲自启动标注、运行和监督。X不需要因本次部署失配返修。旧019/020失败及日志保留。
