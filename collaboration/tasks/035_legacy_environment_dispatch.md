# 035：正式评测首次初始化失败，仅修旧/新环境桥接分派

2026-11-04，Codex→X。基于PR10@44b6ca02。训练及生成主体保持accepted；这是评测执行兼容遗漏，Codex此前文件核对未覆盖，不要求重做主体或训练。

## 已定位的真实错误

用户启动`runs/trajectory035-eval-001`，SOG10四shard与本次adapter已加载，首单元`10_basket`在environment_initialize暂停：`ValueError: runtime LIBERO fingerprint differs from the frozen manifest`。attempts/results均空，没有创建真实任务场景或执行轨迹；完成0/180=0%，不是模型失败。TensorFlow/cuDNN/Gym前置消息不是根因。

只读比对确认：LIBERO源码、资产、robosuite1.4.0、MuJoCo2.3.7、20Hz、compat规则/源码均相同，唯一锁差异是`compatibility.bridge_source_sha256`。

| 来源 | 条数/调用 | 原bridge SHA | 原环境fingerprint |
|---|---:|---|---|
| 旧六任务10和00 | 120条/66调用 | fa85ae08e1a09fcab1b95f0d25880d4fcb6d0948088e1f49ca7e3746ab95d603 | 27939e2d2a9a592a7c788ab5c91021d83f4ba88831615ef86aff0fb03ea7942b |
| 新三任务10和00 | 60条/60调用 | 3a515dddc29311012180d4479dacd77511b510de44021ab6bc09516ca9a51efa | e7d58f354d2b013b362d181f9af3ef48dca136cdff2801c7de68606c16ed4883 |

旧六为basket/basket_cheese_butter/stove/dual_mugs/mug_pudding/basket_soup_cheese。当前固定core d8541ef4只带第二版bridge，不能直接实例化第一版manifest。对比旧ac130177与新bridge，变动仅为新增task_semantics字段及新九任务谓词分支/goal_facts；不能因看起来相近就伪造旧指纹。

## 需要的最小实现

1. 方法侧显式支持这两套已有环境实现的分派。优先对旧指纹加载**字节固定的旧bridge和它的兼容依赖**，对新指纹用现有d8541ef4实现；按输入源的完整环境锁选择，不按模型成败或人为task oracle选择动作。共用同一已训练policy，不改变模型输入。
2. 不修改任何冻结core/manifest/state/replay/RGB审计；不跳过fingerprint检查、不将expected覆盖为actual、不伪造旧bridge SHA。只换env类但仍调用新compatibility_identity也不够：该函数按自身文件邻接的libero_env.py计算SHA，必须保证真实对应依赖和__file__。旧实现可用隔离模块命名空间加载，避免污染标准benchmark包与方法的core字节校验；无需新建通用跨环境框架。
3. 旧源码固定为[LIBERO-Remain@ac1301779cf6ae4c34ebc80c20936a4f7a4953be](https://github.com/No1dry/LIBERO-Remain/tree/ac1301779cf6ae4c34ebc80c20936a4f7a4953be)，服务器`/HUBU-AI096/zp/ICML/LIBERO-Remain-task031-prep-ac130177`；另有a23a8116相同bridge。已确认旧libero_env SHA见表，旧libero_compat.py SHA=`d7519cd0817b99b6178370d3e1d64915bf2a14bd6c465a8e76b6c73983517555`，旧schema.py SHA=`3b554f4e913b587d59238287c8b2830d2c99598e0688519c0a2db8ae7236ec20`。实际需要的传递依赖须锁定，不能读任意未固定包；路径用配置，Codex部署填写。
4. 不另写评分器/runner/状态恢复，不为兼容改变goal_values/native success/释放/端点。保留旧六00与新三00原协议，10二元合规和00官方SR保持原口径。reader/报告记录真实使用的环境实现/锁与来源，不借适配改变模型/证据身份。
5. 仅补必要的新配置字段/明确版本化入口，旧001计划、错误、旧报告继续可读，不原地热改已运行目录。用户后续用新代码/配置和新输出eval-002直接执行同180；001零episode，不需设计续跑或追加实验预算。原1000更新权重不变，不重训、不重建初态、不重跑baseline。

## 受影响CPU/fake即可

- 两类锁正确分派，分别能获得原完整fingerprint；只读文件/包版本身份核对不创建场景、不reset/step、不加载模型。
- 未知bridge/改变的源或资产/版本/compat被拒绝；不能只放行两个字符串。
- 同一队列旧六120＋新三60完整、同一adapter/原policy输入；异常仍技术错误、未执行不计模型0，原10/00评分不变。
- 独立reader绑定实际版本，旧001仍报告初始化错误/0动作，不回填为成功。

复用R7已通过的训练权重/配置与来源证据，不加全库、多平台、GPU试推理、物理回放或模型MVP。本修复按方法侧部署，不改benchmark仓库。真实新评测仅用户启动。

已有实时SR/去重复读取小增量仍可并行，若顺手完成请单列提交/测试；不要把它扩成此修复的依赖或拖延必要兼容修复。

交付`collaboration/responses/035_environment_dispatch_round1.md`，给commit/PR、实现选择、明确锁/实际分派清单、精简CPU/fake与新的配置示例。Codex审查部署给用户命令，X不启动真实作业。
