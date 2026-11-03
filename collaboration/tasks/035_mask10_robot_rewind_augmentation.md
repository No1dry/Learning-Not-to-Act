# 035｜实现机器人起点重置的10轨迹增强与10/正常混训

2026-11-03，Codex交X，状态open。用户优先级：**提高10 SR第一，保持00第二，泛化第三**。

权威[035方案](../../docs/experiment_plans/2026-11-03_mask10_robot_rewind_augmentation_v1.md)。本任务是研究方向变更后的新实现，不推翻030 R2验收，也不要求重写其训练/adapter/native/报告主体。请直接交完整实现PR，不先增加纯可行性审阅/MVP/真实预检轮。

从已验收PR9固定`5bb32713a5451b7df8cb38c9a8e168d2c4a7e97d`复用实现，在独立035分支/PR合并最新main文档，不自动merge PR9。实现放方法库；benchmark保持固定依赖，不能改正式90来源、物理判据或评分代码。

## A．实际生成器，不交空插件

建议新增`egrs.trajectory_augmentation`或等价隔离模块，交付纯文件`plan`和用户启动的`generate`，两者分开。

1. **种子manifest**：支持固定九任务每任务自然前N≤20来源，不再强制包含旧200任务。字段/语言/父文件hash/原控制器/目标绑定明确；来源先按完整父demo成组分train/dev，已知重复同组。原200及030原schema/旧split不改，不按基线成绩选来源，不读正式90初态或模型轨迹生成数据。
2. **种子实际重放**：复用固定native初始化/历史XML/名称/BDDL组件，从原完整初态实际执行专家动作，重新记录本次实时观测/状态、原控制目标位姿和夹爪序列。成功标签由本次执行判定，不信原文件success。新数据不混配旧RGB或套旧原图对齐passed；失败分母/原因保留。该重放也提供normal域数据。
3. **交接点选择**：本次实时记录中A已成立、B未成立、保持约束真、夹爪打开、未持自由物体，A运输物已释放。预设几何规则取安全交接点，不以VLA成败选择。没有候选只记gap。所有源子任务顺序按真实谓词，不假造A先做。
4. **机器人起点变换**：只在新生成episode开始前改机器人qpos/qvel与打开夹爪，非机器人分量包括物体速度原样保留，实际joint布局定位，写变换/非改分量hash。3个预设候选：同来源名义初始robot state＋seed7两组≤0.05rad的小扰动，限位/初始明显穿透/目标错误则拒绝。不要把状态跳变当动作。
5. **两种有界桥接**：直接SE(3)插值和抬升—平移—下降备用，最多2尝试/起点，总H520，每阶段步数有限。默认交接末端误差5mm/3°。使用原OSC_POSE7维动作实际执行，bridge不抓物体；不换关节控制、不mid-trajectory set_state/set_goal/改控制频率救轨迹。不能用一个假的callable占位让部署方自写控制器。
6. **B段续接**：跟踪本次种子实际执行记录的世界系controller目标位姿及gripper序列，从新轨迹实际受控末端状态换算新env.step动作。不得直接粘贴旧7维动作或用原图配新状态。对固定robosuite OSC_POSE明确取`controller.goal_pos/goal_ori`等真正控制目标，不把实际到达位姿误当原控制命令；按原input/output缩放与世界旋转约定转换/限幅，末端坐标系一致。B段动作、图像、proprio、状态均重新记录。
   全部实际动作（含种子重放/桥接/B跟踪）先按原SOG10 stats、原夹爪映射和env.action_spec投影到当前策略可监督范围，再env.step并记录实际值；保存raw→projected变更。只读stats不加载模型。禁止teacher执行大动作成功、loader却裁标签后声称对应正确；动作normalize→unnormalize须还原实际执行值。原演示动作若被投影，不宣称新重放逐动作相同。
7. **资格**：复用固定core已有目标/释放/确认/违规/保持约束函数；10必须真实完成、保护A，额外拒绝再抓已完成A运输物。A为机制时不要把放壶对炉子的正常接触误判成抓A。释放/违规证据不确定不能宣称成功。确认用附加HOLD只存审计，不变成停车监督。严禁读truth改变正式评测策略，teacher离线可用truth。

   normal种子的真实初态可能有“抽屉原本关闭、任务中需打开再关闭”等已真谓词；不能谎填mask00或套10的初始成果保留条件误拒它。normal资格按真实完整任务完成及必要释放/错物体证据，原初始事实保留；正式00评测仍独立复用其固定source/protocol，不能因此改benchmark。

实现可用现有原生组件和小型位姿跟踪器，不要求安装完整MimicGen或新通用规划平台。参考[MimicGen接口](https://github.com/NVlabs/mimicgen/blob/main/mimicgen/env_interfaces/robosuite.py)及[数据生成机制](https://mimicgen.github.io/docs/modules/datagen.html)，不能声称它已有本九任务现成支持。不同实现若满足完整行为与边界可接受，不因文件组织返工。

## B．数据/索引格式

- 新schema明确`counterfactual_generated_from_demo`与`ordinary_reexecuted`，不伪装原官方`ordinary_expert_demo`。身份含parent/demo/split/task/recipe/variant/attempt、实际初态、控制器/数据源/依赖hash、成功资格与排除原因。
- 保存T+1实时观测/状态、T实际动作，`o_t→a_t→o_(t+1)`对应明确；loader兼容此格式，chunk8只在episode尾mask，不把padding当动作。
- 输出仍仅当前双图、8维proprio、原完整指令、动作目标与mask。物理状态、谓词、contact、domain/完成位、parent metadata只用于离线生成/采样/审计，不能进入模型输入、历史或eval终止决策。
- 成功轨迹保存完整RGB/proprio/actions；所有失败尝试至少保留初态/动作/逐步目标与失败原因，不能把失败源从生成分母删除。每task固定保留代表视频，正式模型eval仍全视频。
- 导出按task/split/domain列来源组、尝试、合格轨迹/有效窗口/动作数；540候选不写成540成功或独立来源。第一次真实生成直接正式有界批处理，不先做1条/5条滚动MVP。零池报gap，任务部分缺口如实报告，不静默退回普通BC假称完成增强。

## C．复用训练器：独立两域损失，不让关键域被回退稀释

新增035配方和数据kind，不动030旧配置语义。第一组模型`L=0.7 L10+0.3 Lnormal`。有效batch16可取12个10和4个normal，**两域分别按有效动作标量归一化再加权**，避免padding/轨迹长度把7:3变形。各域内均衡task→父来源→变体/窗口，实际抽样和有效动作占比均写log。

原SOG10已合并底座、原head/proprio/processor/stats与语言q/k/v/o-only LoRA、bf16/micro1/accum16/lr2e-5/seed7沿030，候选1000更新；不重新套发布adapter或随机头，不改norm key。模型/adapter身份记录035配方与数据版本；恢复与旧adapter兼容不能静默混算。

dev先按父来源留出，域内固定最多256窗口、按task/source均衡，在250更新点报告，不能扫全量重复dev拖慢。首轮固定1000-update末权重评测，不用正式90 SR挑checkpoint；只一组混训，普通续训对照/消融后置。真实1000更新是否充分尚未证明，不自动追加。

## D．同一模型同时评10和00，复用固定评测器

035新增条件配置，**同一adapter**各评固定九任务10/00各90条。原90/90状态、指令、seed7/chunk8/H520、相机/proprio/crop、动作接口不变。10按034二元合规SR，00按固定normal00原生目标成功端点/评分，不误套10释放与保留初始成果条件。

复用原00状态源读取及已有00 protocol，不在方法库复制评分器；原adapter身份桥可扩展新recipe，但不能把条件传入策略或据10/00换checkpoint/改指令。配置写清训练组/测试condition，统计分别与24.44%和86.67%比较，所有视频/query/actions/raw保留。新180条预算未启动，不重跑原始模型。

## E．只做本轮必要CPU/fake

覆盖：父来源先分组/变体不跨split；robot-only初始化分量与限位；无合法交接点/持物/保持约束失败；同source正常重放动作/控制目标/实时观测索引；SE(3)与原缩放/限幅/夹爪转换；真bridge执行而非瞬移；失败排除/尝试分母；T+1与chunk mask；7:3域独立L1梯度；不读truth的训练item；同adapter双条件来源/endpoint/报告。用tiny状态机/fake native边界，不启动真实仿真、回放、渲染、VLA或训练。

另用非对称q01/q99、环境更紧限幅、真实夹爪符号的合成用例，证明记录动作就是投影后实际env.step动作，动作标签往返还原，且没有二次归一化。

原head/LoRA等未变路径复用030已验收证据，不把全库、多平台/发布完整性/通用规划器作为前置。发现会破坏真实动作、原控制器或评分的硬问题，一次给证据和最小修订；非关键偏好不阻塞。不是要求只给可行性报告。

## F．交付与权限

新独立PR＋`collaboration/responses/035_round1.md`：精确commit、实际CPU/fake、依赖/改动、功能入口、配置模板与完整普通conda/python命令。必须交实际native生成路径、训练与双条件eval，不留部署方自写恢复/控制器的空插件；准确私有机器路径由Codex填，不提交凭证或服务器绝对路径。

旧030软件closed保持，旧native数据不倒改，不自动merge。**本轮只授权X实现与CPU/fake**；候选180种子重放＋最多1080次新10轨迹尝试、一组1000更新与180新模型episode需用户另行确认并亲自启动；不能套旧预算回答或借“预检”偷偷运行。Codex准备/部署与一次集中审查，不把用户变成文件搬运和反复检查执行者。
