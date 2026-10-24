# 021：兼容本批轨迹实际出现的历史BDDL名称和Mac XML资源前缀

状态：accepted/closed（原工单软件范围），见[021裁决](../reviews/021_round1.md)；Object名称补充另见[022](022_object_historical_name_coverage.md)。2026-10-24，Codex交X。修复范围是离线标注来源适配，不改模型、评分或原始数据。

## 运行证据

020r2方法实现 `dc4dfa97d131fcdf8c1cc116e18d529a9d4d0efb` 已改用完整annotation reference core `c6dc98de0c54517c976057598b60f4cedf7fa3e5`。缺模块问题已消失。用户启动的本轮日志快照：82/200来源已返回失败（41%尝试进度），其中42条在bddl_resolution、40条在source_xml_assets失败；3200查询processed=0、supervised=0（均0%），未进入物理标注。快照不是最终统计。

实际字段和错误片段见同目录[运行样例JSON](021_runtime_compatibility_examples.json)，来自已生成events，不是新读取HDF。旧的019、020、020r2结果均保留。Codex已建议用户停止无有效产出的本轮，但未代停；不假定用户已停止。

## A. BDDL历史命名：仅明确版本化映射，不放开任意冲突

现有“所有basename逐字一样”规则将下列**已观察到的来源命名差异**拒绝：

| 固定suite | env_args及env_kwargs内旧basename | data.attrs内canonical basename |
|---|---|---|
| libero_goal | `open_the_middle_layer_of_the_drawer.bddl` | `open_the_middle_drawer_of_the_cabinet.bddl` |
| libero_goal | `open_the_top_layer_of_the_drawer_and_put_the_bowl_inside.bddl` | `open_the_top_drawer_and_put_the_bowl_inside.bddl` |
| libero_goal | `put_the_bowl_on_the_top_of_the_drawer.bddl` | `put_the_bowl_on_top_of_the_cabinet.bddl` |
| libero_goal | `put_the_cream_cheese_on_the_bowl.bddl` | `put_the_cream_cheese_in_the_bowl.bddl` |
| libero_goal | `put_the_wine_bottle_on_the_top_of_the_drawer.bddl` | `put_the_wine_bottle_on_top_of_the_cabinet.bddl` |

批准在新兼容版本中维护这5对精确映射，前提及边界：

- 映射按固定dataset/revision、suite、源任务键锁定；canonical必须同时匹配冻结catalog/registry、来源data.attrs明确标识与原source instruction。env_args与kwargs中**实际存在**的旧名仅经上述准确表归一。缺失与冲突仍分开处理；不能忽略任意字段、作模糊语义/字符串匹配、全局改“drawer= cabinet”或依模型结果选择来源。
- 保留每个原标识、规范化结果、映射版本/来源、当前canonical BDDL hash。将历史命名兼容与“历史BDDL正文逐字相同”分开：后者仍unverified；这张表不是旧文件语义/物理一致性已经验证的声明。
- 仍用固定安装的canonical BDDL字节锁、独立目标原子/对象映射、源XML及原state/RGB对应核验；任一失败均保留gap。特别是cream-cheese的文字in/on不能通过改成功谓词来迁就名称，沿用既有native目标映射。
- 对未列出的名称差异或跨task/suite冲突继续报明确gap，不猜。不因个别未解来源阻止其他可靠来源产生监督，覆盖报告保留所有分母。
- 这是对020严格名称规则的**显式版本化修订**；保留旧结果与旧解释，不将过去的conflict倒改为通过。不要要求重新下载、inventory、抽帧或改写原HDF。

## B. Mac历史XML前缀：有界离线资源适配

已见实际XML：
```text
/Users/yifengz/workspace/libero-dev/chiliocosm/assets/scenes/../textures/light-gray-floor-tile.png
/Users/yifengz/workspace/libero-dev/chiliocosm/assets/stable_scanned_objects/akita_black_bowl/texture.png
```
同一数据作者的历史前缀；不是用户机器或服务器目录。c6 resolver只认识其已实现的home前缀，现报unknown asset root。

- 在**方法侧离线适配层**支持这一精确历史前缀到获准libero asset root；不热改固定参考core或robosuite/LIBERO环境，也不把文件复制到旧作者绝对路径。
- 仅变更XML直接asset mesh/texture/hfield的file定位；在识别固定根后规范化suffix中的 `.`、`..`，只允许始终留在根内的归一，例如scenes/../textures。继续拒绝根外遍历、symlink逃逸、未知/歧义根、缺文件、非允许XML外部依赖；不按basename搜索、下载或虚构资产。
- 尽量复用已有bounded resolver，方法包装层或明确固定来源的纯资源工具均可；若存在中间XML，区分真正source原文hash、中间变换hash和最终XML hash，保留原→规范化suffix→目标文件hash及所用rule，不能把中间文本冒充原文。
- 不改source相机、场景body/geom/joint、纹理/mesh内容、控制器、state/时间规则及RGB残差阈值；已存在的XML拓扑核验继续执行。安装资产hash仅说明当前使用字节，不冒称历史作者资产逐字相同。
- 建议错误reason直接展示阶段/未解引用数量及少量原因，不先塞入整段original_xml导致2000字截断看不到原因；完整审计仍保留。这是诊断建议，不因显示偏好再次返修。

## CPU/fake验证和交付

只跑受影响路径，直接使用随附已观察字段/路径片段：
1. 5个准确名称映射各通过解析，并完整记录原值；任意替换另一task、跨suite、未列别名仍拒绝；当前BDDL hash、原目标映射与RGB对应约束不放松。
2. Mac前缀＋scenes/../textures和实际对象后缀在**临时合成资产根**解析成功，真实bounded路径逻辑参与，不能在这些用例里把资源resolver完全mock成永远成功。原home/官方前缀兼容保持。
3. 根外遍历/symlink/未知前缀/缺文件仍失败；仅file属性变化、原XML/中间/最终hash及目标hash审计准确；诊断不进入student样本或history。
4. 原生边界仍fake，真实HDF、仿真加载/恢复/渲染、教师、训练和eval都不由X/Codex启动；不新增GPU预检、全库/多平台门槛。

X回复 `collaboration/responses/021_round1.md`：最终remote实现SHA、改动与受影响测试、兼容规则版本、剩余未证实项。Codex审查后部署新的方法目录/配置/输出，复用c6固定依赖及现有数据；仍由用户启动真实标注。不要让用户反复以全量作业代替这些已知样例的CPU验证；也不承诺CPU通过便保证后续物理对应成功。
