# 022：补充固定Object十任务的准确历史BDDL名称表

状态：accepted/closed（软件范围），见[022裁决](../reviews/022_round1.md)；下一步由用户启动真实标注。2026-10-24，Codex交X。**这是Codex原021工单样例范围遗漏的后续补充，不否定021按原5对名称范围的验收。** 不改模型、评分、原始HDF、目标谓词或图像对应规则。

## 已有事实和范围

021交付固定 `3444ec744b9dea413a70fdfc3faa16b2c3a4ddda` 的247/247受影响CPU/fake独立通过，5个Goal历史名称和Mac XML规则已实现。Codex在实际worker用已生成audit/request文本核对：10种Goal元信息均可解析；5种已有XML的495个引用均能找到安装资产。没有读取HDF/图像、加载仿真或生成标签。

同一020r2旧事件在此前提供的82来源快照之后，又记录了4种Object任务的历史名称；当前明确观察到以下表中的前四个。使用021解析这些旧事件字段仍报BDDL identifier conflict。不是新模型实验，也不是数据任务的语义冲突已经获证。

## 批准的准确兼容表

保持同一个固定dataset/revision和十任务catalog，不增加训练任务或数据。本表列出10个**独立精确条目**；其中4个有旧事件直接证据，6个是同一命名约定下明确声明的预期兼容，**不是已观测或已物理验证**：

| suite | 来源文件 | env_args/kwargs兼容旧basename | canonical basename | 证据状态 |
|---|---|---|---|---|
| libero_object | `pick_up_the_alphabet_soup_and_place_it_in_the_basket_demo.hdf5` | `pick_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | 旧events已观察 |
| libero_object | `pick_up_the_bbq_sauce_and_place_it_in_the_basket_demo.hdf5` | `pick_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | 旧events已观察 |
| libero_object | `pick_up_the_butter_and_place_it_in_the_basket_demo.hdf5` | `pick_the_butter_and_place_it_in_the_basket.bddl` | `pick_up_the_butter_and_place_it_in_the_basket.bddl` | 旧events已观察 |
| libero_object | `pick_up_the_chocolate_pudding_and_place_it_in_the_basket_demo.hdf5` | `pick_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | 旧events已观察 |
| libero_object | `pick_up_the_cream_cheese_and_place_it_in_the_basket_demo.hdf5` | `pick_the_cream_cheese_and_place_it_in_the_basket.bddl` | `pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | 预期兼容，未观察 |
| libero_object | `pick_up_the_ketchup_and_place_it_in_the_basket_demo.hdf5` | `pick_the_ketchup_and_place_it_in_the_basket.bddl` | `pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | 预期兼容，未观察 |
| libero_object | `pick_up_the_milk_and_place_it_in_the_basket_demo.hdf5` | `pick_the_milk_and_place_it_in_the_basket.bddl` | `pick_up_the_milk_and_place_it_in_the_basket.bddl` | 预期兼容，未观察 |
| libero_object | `pick_up_the_orange_juice_and_place_it_in_the_basket_demo.hdf5` | `pick_the_orange_juice_and_place_it_in_the_basket.bddl` | `pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | 预期兼容，未观察 |
| libero_object | `pick_up_the_salad_dressing_and_place_it_in_the_basket_demo.hdf5` | `pick_the_salad_dressing_and_place_it_in_the_basket.bddl` | `pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | 预期兼容，未观察 |
| libero_object | `pick_up_the_tomato_sauce_and_place_it_in_the_basket_demo.hdf5` | `pick_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | 预期兼容，未观察 |

- 运行时按精确表查找，不能做全局pick→pick_up替换、模糊语言匹配或允许任意未知冲突。已验证绑定仍包含dataset/revision、suite、固定source_file/task_group、episode/source_id、完整instruction、strict registry/native目标映射。
- canonical仍须由data.attrs明确提供且与该固定source/catalog/registry一致；不因旧字段自身一致就推断通过。完整instruction从既有冻结registry/任务映射取得，不能只根据文件名猜文字。
- 保留原始字段、规范化字段、映射版本/证据状态与原当前BDDL hash锁；预期6条须明确未有旧事件证据，不伪造真实运行结果。
- 原021的5个Goal条目保持。可以把条目改为显式携带suite的精确记录；维护方式不限，不为结构偏好返修。未知别名、换物体/目的地、跨suite/任务、错dataset/revision、缺canonical、错误目标原子仍拒绝。
- 这只解决来源名称定位；历史BDDL/资产原字节仍unverified，原XML、实际native目标/物体、state/RGB对应、可观察性及输入白名单照旧，不能据名称表直接生成SAT标签。

## 精简验证及交付

只做名称解析、受影响fake构造/传输/导出路径的CPU回归，不重复完整XML套件或全库。至少覆盖这4个已见Object元信息样例、全部10个准确表条目绑定、suite/物体/指令等负例、原5个Goal条目不回退；原Mac修复及同一c6依赖复用，不为本次补表新加真实元信息读取/物理预检。

X在 `collaboration/responses/022_round1.md` 交付最终remote SHA、规则版本、受影响测试与真实阶段未验证项。不要自主启动/停止HDF处理、仿真、渲染、训练或eval。Codex审查后部署新代码/配置/输出并给完整命令，用户启动。

021当前实现已隔离部署且仍可处理其已支持来源；**不要求所有未知字段完美才能使用可靠子集**。但已知4个Object来源类会失败，Codex建议本轮先完成这项小补表再让用户启动全量200来源，避免已知错误及重复渲染。不是额外MVP或扩大模型轨迹预算。旧021实现、旧020r2失败与全部分母保留，不热改运行目录、不重建原数据。
