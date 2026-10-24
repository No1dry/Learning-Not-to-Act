# 020：修复019真实数据的元信息兼容错误

状态：accepted/closed（软件范围），见[020首轮裁决](../reviews/020_round1.md)。真实标注待用户启动。2026-10-24，Codex交接X。仅修明确运行错误，不重开016/017/018设计或软件验收。

## 已有证据与影响

用户启动的019实现 `b38526d57d858fdfdb410752f0ae0d6db3085e2f` 已结束。最终manifest identity为 `2cd2df5f78b7148b1f490f31c56ce5b55df6bad15c6131dc88172b756bc7b82d`：
- 200/200来源失败（100%），共同首个错误为 `source inspection gap: "Unable to synchronously open attribute (can't locate attribute: 'bddl_file_content')"`。
- 3200查询实际processed=0、supervised=0（均0%）；ready=false、usable=false。
- 尚未进入状态恢复、原图对应核验或谓词标注；UNKNOWN是来源失败后的占位，不是已经确认图像无法对齐，更不是模型失败。
- 位置：`egrs/offline/sim_native.py::SourceEpisode.__init__` 将生产脚本可选的嵌入BDDL正文当作必有属性；`NativeAdapter._initialize` 随后还强制正文哈希相同。因此不能只把一次KeyError吞掉。
- 当前成功读过env_args和episode model_file才遇到此错误；其他尚未读到的属性是否存在未知，不能声称也缺失。
- 独立156项CPU/fake通过没有覆盖本次真实元信息差异；保留既有软件证据，不冒称真实兼容已通过。

## 实现要求：一次修完整个元信息入口

1. 不要求每种数据生产版本都内嵌BDDL正文。先独立记录已有元信息键、字段来源及缺失项，再解析必要字段；后续失败仍保留已完成的inspection与明确失败阶段。不要因为一个可选字段缺失而丢失所有诊断信息。
2. 有内嵌正文时继续校验其与实际使用BDDL的一致性；正文缺失时，可以使用来源env_args内的明确BDDL路径标识（及存在时的其他属性），按**固定suite＋精确basename**解析固定LIBERO版本的本地BDDL。规范化历史绝对路径仅用于定位，不要求旧机器路径存在；禁止模糊搜索、按模型成败挑任务、任意默认任务或扫描候选后择优。
3. 处理各BDDL元信息字段“存在/缺失/冲突”的情况，不继续把可选的bddl_file_name等生产属性无条件当必有。同一来源中实际存在的多个任务标识冲突必须报gap；没有足够唯一标识也报gap，不猜。源instruction、目标原子映射、原XML与已有RGB对应规则继续核对。
4. 正文缺失的路径采用显式版本化来源说明，例如 `metadata_resolved_installed_bddl`：记录源字段、固定LIBERO版本、解析文件身份与SHA-256，并明确 `source_embedded_bddl_present=false`、历史原始BDDL字节一致性未证实。不得伪造source正文、source哈希或“原件逐字一致”；本地文件身份锁定、任务语义核对及既有原图对应通过之后才允许生成标签。正文缺失本身不再全量拒绝，真正任务歧义或对应失败仍如实保留。
5. 对其他生产版本元信息也采用“已有来源证据优先、缺失与矛盾明确区分”；不得默默默认控制器、机器人、相机约定或state/RGB时序。原始已确认inventory/RGB/窗口/文本规格/160:40划分不重建，对应阈值与可观察性约束不放宽。
6. inspection失败信息不得将XML、状态数组或谓词真值混入student输入、历史或训练prompt。完整元信息诊断只留离线audit。

以上检查直接防止错配任务BDDL、错误来源声明及本轮全量入口失败，不新增通用工程门槛。

## 验证、交付与权限

- 只做受影响CPU/fake回归：缺少内嵌正文但有唯一合法路径可解析；其他可选属性缺失；多标识冲突/无法唯一解析拒绝；内嵌正文存在且不一致拒绝；失败仍保留partial inspection；已有对齐/可观察性/无真值输入约束不变。不要求全库、多平台或新增GPU预检。
- fixture需要覆盖本次缺失字段；没有真实元信息证据的字段必须写明假设，不把fake当真实数据读取成功。若确实需要本批原始键值才能确定解析，交付一个**用户执行的只读元信息命令**，不在X/Codex侧自主启动真实HDF处理、恢复、渲染或模型作业。
- X在PR #2或明确新PR交付实现SHA、受影响测试、来源模式与尚未验证项，在 `collaboration/responses/020_round1.md` 回复。
- Codex验收后部署新代码目录和新输出目录；原019失败manifest/日志/数据保持不变，不热改b38526d5，不用新结果覆盖或倒改旧统计。
- 仍由用户启动修复后的真实标注，不自动重跑、训练、扩数据或调用7B教师。没有新增模型轨迹预算。
