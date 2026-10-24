# 018 Round1验收裁决（2026-10-24）

结论：**accepted/closed，仅018软件修复范围**。固定交付 `119cd50bde04a53f41ddac47871d0f688276b146`，来自[PR #2](https://github.com/No1dry/Learning-Not-to-Act/pull/2)，未自动合并。X当前无返修要求。

Codex独立复跑`tests/test_teacher_wire.py tests/test_offline_pipeline.py`：55/55通过（100%，1.61秒）；20个交付变更文件的Git blob吻合。原contracts与共享student prompt逐字节不变。未跑全库、真实tokenizer/GPU预检或额外模型调用。

已核对两层修复：整份裸JSON/单外层代码块解析，原raw与分阶段失败审计保留；字段仍经原schema，错误不被自动修成UNKNOWN/合法ID/完整goal。教师专用提示明确目标、实体、运输/机构release及绑定证据，给出合法例子且纳入原token预算。学生提示不变。CPU诊断仅生成独立派生报告，不改历史答案/计数、不补后续查询。输入末行损坏与模型错误分母有回归覆盖。

已隔离部署新版源码；不重装或修改原selector依赖，用户从新代码目录运行模块。传输archive SHA256为`e997848ecf5d0c321e3df2796de83f2dffc8976f8a907dcdb9789ad847794b00`；远端静态导入和help确认加载新版parser/prompt，未加载模型。macOS archive扩展属性在解包时被tar忽略，不涉及Python内容或验收失败，不设返工门槛。

复用已有200来源、1200窗口、3200查询及160/40分组，不重建。原候选失败证据保持原状。读取旧PID时已不在运行；没有由Codex/X执行停止。新推理尚未启动，实际schema通过率、UNKNOWN比例及视觉正确性待用户运行验证；不能将软件验收冒称有效监督已准备完成。无需另跑CPU诊断才能启动新轮。

下一步操作和执行者：用户按新配置亲自启动新目录的视觉候选生成（最多3200次，旧/新预算另记）；Codex审查交回结果。X本轮无需返修；不自动训练或merge。
