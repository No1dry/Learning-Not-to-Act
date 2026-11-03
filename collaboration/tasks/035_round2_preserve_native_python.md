# 035 R2｜仅修复native Python被resolve丢失venv语义

2026-11-03，Codex→X。基于PR10固定HEAD `564c91c920a521c6c5ea909d69350e70d14a5e7e`。这是有真实结果支撑的单一阻断错误；035生成/训练/评测其余软件验收保持，不重开架构、数据方案或旧030，不重下任何数据。

## 已确认的失败链

用户按已发命令完成`data/trajectory035/generated-001`，180/180来源处理=100%，但180条均`ValueError: annotation library version lock mismatch`，合格normal=0、10=0，不能训练。这是初始化技术失败，不是180次有效物理重放失败或模型SR。

原`generate.json`正确指定：

```text
/HUBU-AI096/zp/ICML/LIBERO-Remain-normal00-stage02/.runtime/oft_worker/bin/python
```

实际`artifacts/source-000/request.json`却变成：

```text
/root/anaconda3/envs/peft-openvla/bin/python3.10
```

`egrs/trajectory_augmentation/cli.py:17-19,32-33`把`native_backend.python`交给`Path.resolve()`，解引用venv解释器软链，丢失`pyvenv.cfg`环境选择；后续`generate_source`原样调用这个已错误解析的值。只读`importlib.metadata`证实（没有import仿真/模型）：

| 包 | 原配置锁＝正确OFT worker | 被resolve后的base Python |
|---|---|---|
| numpy | 1.24.4 | 1.26.0 |
| h5py | 3.16.0 | 3.16.0 |
| robosuite | 1.4.1 | 1.4.1 |
| mujoco | 2.3.7 | 3.4.0 |

原版本锁正确，不得改为base环境版本“让检查过”。不得pip升级/降级、复制解释器、改物理判据/模块SHA或删除版本锁。

## 唯一必做修复

1. **只对解释器路径保留调用拼写，不解引用软链。** 可expanduser＋相对配置目录的绝对化；例如`os.path.abspath`或等价不follow-symlink处理。绝对路径`.../oft_worker/bin/python`必须仍以这个字符串进入plan/request和`subprocess`的argv[0]。相对的`venv/bin/python`也正确基于config目录绝对化，不能解析到软链目标。其他数据/目录的现有resolve可保留。
2. 检查035生产链后续没有再次resolve解释器；不要顺手全库重构。原生core/native依赖、统计、种子/分组、3×2尝试、H520、训练、计分均不变。
3. 精简CPU/fake回归覆盖**真实symlink文件布局**：`venv/bin/python`链接到base interpreter；对绝对及相对配置调用`build_plan`，断言plan保留venv路径；fake subprocess边界进一步捕获argv[0]仍为venv路径。不要只测一个不存在的`unopened-python`字符串。不创建真实NativeSession/仿真、加载模型、HDF回放或启动GPU。无symlink权限的平台可在支持机器补该项，不能把skip冒称通过；无需全库测试。

非阻断建议：生成结束控制台直接打印`source_errors`、合格normal/10数量，避免用户只看到处理100%而误认有训练数据；不为日志风格扩返修。原评测实时报告小增量可并行，不成为本修复/数据生成前置。

## 交付与执行边界

在PR10上交小增量或独立PR，回复`collaboration/responses/035_round2.md`，给HEAD、受影响文件、精简测试命令/结果和argv示例。Codex审查后只做一次真实配置的纯JSON路径核对，隔离部署新代码，复用全部9个HDF/180清单/固定版本锁，并给新输出`generated-002`的普通conda/python命令。**仍由用户启动，Codex/X不运行真实生成/训练或新预检。**

保留`generated-001`全部失败、原plan与日志；不原地覆盖、不改写已失败180条为成功。用户原预算中的真实种子物理重放与10桥接尚未开始，不自动新增来源或改变科学预算。R1其余验收保持，研究与本阻断项open，不自动merge或删除交流。
