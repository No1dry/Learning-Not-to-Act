# EGRS软件阶段总结

日期：2026-10-23。范围：015设计审阅与016完整软件实现；不是方法效果报告。

## 已敲定的方法

③独立实体/目标关系选择器＋④可撤销证据历史。只训练Qwen2.5-VL-3B选择器的语言LoRA，冻结原VLA；选择器通过稳定子目标语言调度actor。图像框仅用于感知/选择，不是机械臂空间约束；不加FINISH，不改benchmark主指标。

## 本阶段交付

- 目标registry、实体/区域/query绑定、UNKNOWN与关系/释放证据。
- 两次新查询确认、反证/换实体/过期撤销，以及在途保持和原指令回退。
- 独立双worker、sensor/context隔离、保留actor RNG的目标切换、原OFT配置与归一化继承。
- 标注导入导出、字段来源、整来源分组切分、弱证据中性化、最终多模态token监督。
- 真正的LoRA优化、验证、保存/恢复、推理和消融入口；本轮用toy/fake验证，不以假训练替代生产入口。
- 调用固定eval core的薄桥接、原计分与query对齐日志；没有另造评分器。

固定交付：[PR #2 / 5a77f158](https://github.com/No1dry/Learning-Not-to-Act/tree/5a77f158229442d9a9ee95ba828b371dfc4c995a)。[X原始交付](https://github.com/No1dry/Learning-Not-to-Act/blob/5a77f158229442d9a9ee95ba828b371dfc4c995a/collaboration/responses/016_round1.md)和[最小修正回复](https://github.com/No1dry/Learning-Not-to-Act/blob/5a77f158229442d9a9ee95ba828b371dfc4c995a/collaboration/responses/016_round2.md)保留署名与历史。

## 验收证据与一处修正

首轮Codex独立复现47项CPU/fake全部通过，同时发现测试未覆盖的明确错误：逐项人工确认的evidence会因父列表未确认而被静默清空。X只做局部修正，按条目解析有效来源，并重映射删除前项后的监督索引。

第二轮Codex独立复现受影响30项（原24＋新6），100%通过；其余23项复用首轮证据。没有重复物理检查或把全库测试变成研究门槛。016软件范围已接受并关闭，见[最终裁决](../../collaboration/reviews/016_round2.md)；PR未自动合并。

## 能说明什么、不能说明什么

能说明：完整方法已实现，可转入实际数据与运行准备。不能说明：选择器已学会识别剩余任务、真实依赖已兼容，或新方法成功率已提高。

真实数据准备、标注、真实processor校验、研究forward、训练和新方法评测均为0；既有原模型baseline不因软件验收改变。

## 下一阶段

Codex准备隔离的固定版本部署与具体命令；数据候选仍是Goal10＋Object10、200来源/最多1,200窗口/约3,600查询的预算草案，实际数量据清单统计。标签来源、审核投入和真实资源尚需用户决定；55—80人时全人工估算从未获批，不能默认执行。物理真值不进模型输入，冻结eval来源及其派生帧不补train/dev。

014通用批处理在评测侧另行对接，不回头阻塞已完成的方法本体。用户亲自启动真实数据准备、标注推理、训练与eval；Codex/X不代跑。后续研究阶段不以扩benchmark、训练FINISH或先跑MVP为前提。

本次只归档，不删除任何交流文件、源码或实验数据。

## 2026-10-23部署补充

用户确认新项目目录后，Codex已部署固定实现5a77f158及干净eval core 515e87d，并安装独立Python3.10.22 selector环境（Torch2.6.0、Transformers4.51.3、PEFT0.15.2）；原VLA环境、权重和旧实验目录未改动。只注册固定core的轻量源码，不混装controller/actor依赖。

安装后仅核对解释器/包路径、Qwen类导入、core Git身份及CLI help/配置dry-run，全部通过。没有加载研究权重、真实processor或演示图像，没有forward/训练/仿真/eval；配置dry-run正确返回ready:false，缺少train/dev/output。

代码部署与独立环境安装100%；真实数据准备、标注、训练和新方法评测仍为0%。私有路径、安装日志和完整进入环境命令保存在本地部署档案及服务器配置目录，不上传公开库。下一步转入真实数据与标签方案确认，不再重复016验收。
