# 023首轮审查：两处生产入口误拒绝，需小修

2026-10-24。固定PR HEAD `9c0429d590f40bcef83570c85ced1ee0fc10b8dc`，**needs-fix，仅下列两项明确错误**。Codex独立53/53定向CPU/fake通过（100%，12.93秒、无skip），17变更blob吻合；不据此宣称真实输入可启动。尚未验收部署、未运行真实诊断或改原数据。

## P1：把目录basename当作固定Git版本身份

`egrs/offline/sim_diagnostics.py::_historical_inputs` 第49—51行要求：
```python
Path(native['core']['root']).name == 'LIBERO-core-c6-reference'
```
旧作业封存的生产配置实际basename为 `LIBERO-Remain-reference-c6dc98d`；revision正是固定 `c6dc98de0c54517c976057598b60f4cedf7fa3e5`，allow_reference=true，backend文件hash与manifest一致。该字面目录名校验会确定拒绝获准输入，与版本身份无关。

修复：移除任意目录名要求，保留固定revision、allow_reference、原manifest/config/file身份和既有core激活时Git身份/干净状态核验。**不要把常量改成另一个服务器目录名，也不要改/重封旧manifest、重命名旧目录或复制依赖来迁就此条件。** 更新指南中将目录名当身份的表述。新增通过production分支的纯fixture回归：合法固定版本换不同目录basename仍可消费；错revision/allow_reference仍拒绝。可mock身份常量或边界，但不能仅测试绕过该分支的synthetic模式。

## P1：将计划schema与已验证source descriptor作完整字典相等

同函数要求 `planned == sources`。真实inventory中：
- planned记录只有7个计划身份字段：sample_id、source_id、file、episode、group_ids、task_group、ancestry_known；
- sources记录保留这些字段，另有读取后确定的instruction、instruction_id/origin/mapping、T、orientation、split。
- 已核对两条固定案例均符合此结构，公共字段无矛盾。source与旧requests、registry、native config、train split、complete结果也一致。

因此即使修正目录名，合法输入仍会在下一项条件失败。当前测试的 `sealed_input` 用 `planned_sources=deepcopy(sources)` 构造相同字典，掩盖了生产schema差异。

修复：两边都要求唯一记录，按**计划schema的上述7项身份投影**验证一致；对已验证descriptor继续保留完整request source相等、instruction/registry、T/PNG/相机/split等现有绑定，不退化成只比source_id。补合法“计划基础字段＋来源扩展字段”fixture和相应负例（改变file/episode/group等、缺计划或重复计划仍拒绝）；不要改原inventory或要求重做prepare。

## 其余审查结论与权限

两来源/原probe/相机预算、RGB分量、真实state codec分组、独立旧/新identity、未知原子处理、PNG审计、无标签输出、部分失败保留及CLI非零状态路径已有53项定向证据。已读取的12个PNG元信息均与请求/旧measurement相符；没有新打开HDF/图像、加载仿真或渲染。没有发现需要扩大改动或新增GPU检查的其他阻塞。

只需修上述生产消费层和针对性CPU回归，不重构诊断器、不重跑全库、不改0.03/1e-6、数据划分、原标签或预算。修复指示已追加到[023工单](../tasks/023_bounded_alignment_diagnostics.md)，[封存JSON证据](../tasks/023_production_input_compatibility.json)。

下一步操作和执行者：X小修并交付；Codex复核生产输入的只读解析后部署/给完整命令；用户再启动实际两来源诊断。当前用户无需启动或重跑任何实验。
