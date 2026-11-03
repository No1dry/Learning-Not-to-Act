# 2026-11-03｜035原始文件与种子配置准备完成

本阶段仅文件准备完成，不代表真实轨迹生成、训练或新模型成功率已完成。用户已批准最多180种子重放、1080次10尝试、一组1000更新及同adapter10/00各90评测，仍由用户亲自启动全部真实作业。

九个固定LIBERO-10复合任务的原始HDF共12,790,079,988字节，固定`yifengzhu-hf/LIBERO-datasets@147fa5eb607bb696dd922c3518084a90954cd2f3`。9/9文件已本地下载、核验官方LFS SHA、上传服务器并再次SHA核验，文件准备100%。原网络/DNS/SSH失败日志和部分文件保留；最后微波炉文件通过分段续传后核对完整SHA `1cef1974f76176214dfd1d983a1961507c2b23d54be9dbf9abb2f243f3efacef`，没有把旧失败结果改成成功或从头重下所有文件。

原始文件位于`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/data/trajectory035/raw/147fa5eb/libero_10/`；原始整文件可能含更多demo，但本轮清单严格仅各任务自然demo_0..19，共180父来源。按已验收固定分组得到train136/dev44，变体继承父分组。普通演示与官方测试初态的物理祖源仍unknown，不冒称物理独立；正式90测试状态/模型轨迹没有进入清单。

只读取HDF属性与shape，绑定原完整语言、OSC_POSE控制器及env_args身份、原SOG10动作/8维proprio统计、opengl相机与原OFT旋转/裁剪、九任务BDDL/A/B/invariants；未提取图像帧、动作或状态值用于生成标签，未创建仿真或加载模型。统计原文件SHA `6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3`，key `libero_10_no_noops`。

六个配置文件已上传并逐文件核验，目录`/HUBU-AI096/zp/ICML/Learning-Not-to-Act/configs/trajectory035-564c91c9/`：

| 文件 | SHA-256 |
|---|---|
| seeds.json | 9b3ea9f56ad23b4da7a53f1eff04525b570b9fad7f22caefd28ee804acf4093b |
| generate.json | ddbd43d93592fda89ee0a620b7c132116d9d524cbf8675fe15371b8c4063cff5 |
| recipe.json | b751abf1d5b9cf71cbd88d36961bc095f09136ecffb3fa7f5302f44dccfa0584 |
| evaluation.json | 3bbf2c8d81ba2d01c8f1e31fb4266e7f55d23b33c018c615f29c48e1cc5a8c25 |
| hdf_metadata.json | 11af24f3c786ad3f2e049be2b2bbd30d0e187f0fda793a0492646e5320e323a8 |
| preparation_receipt.json | 8a533ce9c63bbbb6f4caec8134a3afdcb8133721b5d57241df6f1be3d0e6c295 |

生成代码保持PR10固定`564c91c920a521c6c5ea909d69350e70d14a5e7e`的隔离目录`.../code/task035-564c91c9`，不热改代码、升级包、自动merge或重跑基线。先前软件验收证据87个CPU/fake通过、118个依赖锁保持，不重复耗时检查。X的评测实时SR/去重复读取小增量仍为非阻断open，不卡生成或混训。

[用户启动命令](../experiment_plans/2026-11-03_task035_generation_server_commands.md)直接启动正式生成。真实native步数、生成合格10轨迹、训练更新、新模型eval均0，下一执行者为用户；不是“训练数据已合格”或方法已提高SR。研究未闭环，无交流清理，待删=[]。本总结按GitHub来源commit/SHA备份到本地方法研究归档。
