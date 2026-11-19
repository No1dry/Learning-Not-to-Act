# 053：修正结果/证据校验的索引范围，继承11条后继续

052的3项补救已经全部通过，450/450来源ready（100%）。新错误在第11条、官方初态索引10的结果校验：固定core headless/schema.py仍仅允许0..9。049/051/052之前只扩了source/构建/回放准入，遗漏了实际动作结果以及evidence内部复用的schema入口；这是Codex接线遗漏，不是模型或RGB修订失败。

父原版run有11条完整执行、视频与raw，task_run均completed/无cleanup错误；旧summary只接受前10条（0成功），第11条在动作结束后被索引guard拒绝，不能把它伪记模型失败或再执行一次。

## 软件修复

- 新053私有schema命名空间只将initial_state_index的整数上限9→49；保留非负/类型/源指令状态绑定/动作/事件/终点/模型/视频全部检查。
- evidence验证函数的嵌套schema调用也指向同一私有扩展。canonical core文件/全局函数不修改，旧0..9入口保留。
- 原049 verify_episode函数体只定向替换两处schema/evidence导入；原动作评分器、034二元mapper、runner/控制、052来源路由/版本/阈值及两模型权重不改。

## 继承与预算

父plan文件SHA：68a4e754f398c5abaaff96dc9f4f84aa3692ba7e08adae2d2fbdcf74f5c6a0d4。

完成来源bank SHA：54a225330e43bb88cd6299109798885ee2ac6af06d9492f8d5639f2d62e29747。

1. 纯文件重验父11条完整raw/视频/输入证据/源snapshot，原10条已报成功/失败必须逐条保持；第11条补的是校验/计分，不加动作。
2. 父源、原plan/summary/失败日志、全部11条视频/raw保持原地，不修改旧文件。新输出receipt绑定父SHA，明确11已执行/10旧计分/1条校验恢复，不声称旧run原本成功退出。
3. 新原版run只执行439条，继承11条；同资产/归一化/推理配置校验。H1新执行450条。总真实执行仍是原900预算：11+439+450，不是重跑900。
4. 不重建/回放任何初态，不新训练、生成、MVP或seed。新run必须独立目录，继承条目不能在新episodes目录重复出现；原全部源都保留。

用户一条脚本先base --continue-from原052/base，再H1，再comparison，实时合规SR沿原049输出（包含继承结果）；真实作业仍用户亲启，Codex只软件/fake、文件诊断/部署与命令。后续不得重开旧052脚本、删除旧marker/输出或重新补建。

本轮检查需覆盖实际core schema+evidence对索引10/49的CPU/fake完整trace，而不再只mock掉execute/verify；已有真实第11条也做仅读验证，不启动新模型/物理。源码测试不是对新439/450效果的承诺。
