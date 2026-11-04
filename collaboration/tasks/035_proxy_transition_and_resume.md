# 035：修复同进程双bridge共享代理冲突，只续跑剩余120条

2026-11-04，Codex→X，基于PR10@fb16a672/实现1387de38。生成/训练、两套源码与完整环境身份及原评分保持，不返工主体。此次只修连续切换遗漏，并增加明确续跑以复用已完成60条。

## 已有事实与可复现根因

用户eval003已完成六组10各10条，共60/180=33.33%；10进度60/90=66.67%、合规30/60=50.00%，00尚未执行。全部60（含30成功、30失败）必须保留，不能按成败筛选或重跑。原始目录：

`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/runs/trajectory035-eval-003`

首个新三任务`bowl_drawer_close_s000_10`在原reset链上报：`unexpected LIBERO utils.collections binding; refusing to hide a foreign patch`，n_steps=0。环境构造和完整fingerprint已通过；不是显存、模型动作或训练错误。

旧/新compat源码同为SHA d7519cd0...，但分别在私有与标准模块命名空间执行，产生两个不同的_CollectionsProxy类对象。共享的`libero.libero.envs.utils.collections`在跑旧六时已被旧proxy占用；新apply_libero_compat的isinstance不认旧class，继而当成foreign patch拒绝。两个profile单独测试通过不代表同进程切换通过，这是Codex和X漏掉的覆盖。

Codex已用两份固定原源码、一个合成utils对象纯CPU重现：old→old通过，old→current触发完全相同错误，未导入LIBERO、创建场景或模型。X可用现有固定compat源码和SimpleNamespace(utils.collections=stdlib collections)复现；不需要真实仿真。

## A. 最小共享状态修复

1. 只在方法侧协调两套已锁兼容实现共享的代理状态。可以统一为同一个已锁代理类型，或显式管理/清理**本方法确知拥有**的代理；请选最小稳妥实现并说明实际运行绑定。不改冻结core/旧文件，不把环境expected改为actual，不伪造fingerprint，不把未知foreign patch一律放行，也不要按任务名单跳过校验。
2. 必须覆盖同一utils对象上的old→new→old、new→old→new和同版重复reset式调用。不要只让“新任务冷启动”过关：剩余队列先新三10，后00内又多次旧/新交替。
3. 不修改全局stdlib collections模块；不另起通用兼容框架、重写物理恢复/测量/runner/评分或改策略输入。记录此次方法侧代理协调协议/实现来源，原旧/新源与资产/版本/compat完整锁继续严格核对；不能将旧003的60条追认成新修复代码执行。

## B. 显式续跑：继承60，新增只执行120

1. 新增明确`--continue-from <eval003>`，新输出例如eval004；默认仍拒绝已有输出，不覆盖/热改003。不能把重新跑180当作修复后的启动方案。
2. 用各父run自己的冻结plan/batch、原reader、source/archive/观测/query/actions/video与环境sidecar核对**已完成**记录，再完整继承60条成功和失败。核验同一最终adapter/实际组件/统计/原指令与来源/seed7/chunk8/H520及原端点；有改动或不兼容就报错，不默默换样本。不要因父run还有120未完成和一个已知0步技术attempt就要求父run先跑满180。
3. 父003固定v2计划身份`48d230e753dfc844ba79cd04fd850982d01d2bcbafc2c40a22fdc348100c573b`，配置仍`configs/trajectory035-eval-002/evaluation.json`。最终adapter仍`runs/trajectory035-mix-001/update-001000`，SHA `21b982e5b1e7eaf8fe5f65fa8d2b461859dd11a5a0aea247ca87fa8618b745d8`。父run、parent plan/报告和各已完成工件引用必须冻结绑定并可独立复核。
4. 原180人口/90+90分母不变：继承旧六10共60，新执行新三10共30＋全部00共90=120；保持原队列相对顺序，仅跳过有效已完成项。首个抽屉0步技术尝试保留，在新run按原初态执行这条尚未完成episode，不中段恢复、不把技术错误算模型失败。
5. 新目录明确区分inherited与new_execution及代码/父来源lineage，不能复制后改raw身份假装60条是本轮新执行。汇总统一调用原评分，10合规/00官方分别全90；正式结果只有所有180有效完成才齐备。独立report必须能复核继承工件，改变父文件不能靠缓存/复制分数混过去。
6. 仍只加载同一个最终policy服务新增120；不重新训练、构造状态、跑baseline、加载GPU做旧结果核验，或自动重试任何episode。全部真实续跑由用户启动，Codex只审查、部署与命令。技术attempt与实际继承/新增预算分列。

## 精简CPU/fake与交付

- 同一合成utils对象双向切换、重复调用都通过；陌生代理仍拒绝，源码/实际身份锁不降级。
- fake父003包含六组60条已完成（成功/失败都保留）和一条0步技术错误；新队列准确只执行120（10=30、00=90），一policy，旧60零重跑。
- 父adapter/来源/工件/sidecar改动拒绝；原v2父reader仍可读，不因新代理协议重写旧真实身份。新最终聚合180、各90与原指标一致，部分/技术暂停仍不伪造最终SR。

不要新增真实GPU/物理预检、模型MVP、全库或多平台门槛。复用R9与已有通过证据；仅运行受影响CPU/fake。实时SR/去重复读可单列并行，但不要成为此次修复/续跑的前置。

交付`collaboration/responses/035_proxy_transition_resume_round1.md`，给commit/PR、共享状态选择、继承核验/实际120队列、受影响CPU/fake及普通配置/命令示例。Codex验收隔离部署后给用户eval004准确命令。旧001/002/003、原数据/权重/源码/失败全保留，无自动merge或清理。
