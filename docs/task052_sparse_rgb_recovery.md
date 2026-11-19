# Task052：仅3项来源的显式稀疏RGB准入修订

用户2026-11-19明确批准：不排除3个初态，新增RGB通道差≤2、每幅图最多max(1,floor(H×W×0.0001))个差异像素（256×256为6）；物理/非RGB/状态对应、两次独立回放和动作评分不变。该规则是项目数值准入定义，不是已校准的GL误差界，也不保证VLA对差异不敏感。原图不滤波、不改色、不编辑。

## 固定来源与预算

051原报告SHA：`8657805313b12d384d6252011b46fb3008eedda45706d3db60a712339deb1eef`。

- 447个ready条目逐字段引用，来源/状态/图像/plan SHA不变，继续使用原051严格读取和归档路径，不重建/回放。
- `stove_s021_10`：原旧六的匹配构造方法再做一轮，仍同官方索引21；只改私有验证器的明确RGB配置，placement/控制/150步/候选上限与原bridge保持。伴随00/01/11仅原构造技术产物，不增加VLA评测。
- `two_pots_s011_10`、`two_pots_s045_10`：复用原已通过v6构造的manifest/state/初始图，不重新搜索壶位置；只增加新版独立回放。
- 新预算仅1个source build＋最多3个独立source replay（各2×150控制步），原内部有界构造开销保持。只一轮，不循环失败重试、不换容易索引，不退款或覆盖049/051失败与原账本。
- 全450就绪才继续原已认可原版450→045 H1@3000 450，共900条；没有新模型预算、训练、额外seed、prompt或MVP。

## 版本与隔离

`egrs.remain052`新增独立入口，不修改049/051生产文件或固定core。`named-uint8-rgb-sparse-two-level-task052-v1`将实际2档/面积上限写入新audit、replay及外层source extension；audit还绑定实际方法源码SHA。不是让旧v4/v6的1档记录伪装通过。

只在私有命名空间重编译两处精确RGB guard：producer允许固定(2,0.0001)，记录读取器允许error≤2且仍检查原面积上限/状态hash/非RGB/完整物理trace。所有其他算法代码保留；原canonical模块和文件仍1档。

新current helper允许明确的新profile，同时保留原v6构造读取（两个壶不重构）；legacy producer继续原legacy桥接/构造/回放模块，仅其私有RGB常量改变。旧447用完整051路径；新3项用052路径；归档后的snapshot仍按相同源ID路由、重新核对原件和版本，不依赖修改全局模块或降低动作评分。

新报告/配置和run必须独立目录。父报告完整性与精确447复用在入口检查；continuation只继续pending，failed不自动重试。技术异常保留并停模型阶段，不计入模型失败。真实作业只用户启动，Codex只CPU/fake、上传代码和给命令。

## 用户入口（环境与路径由实际session固定）

~~~bash
python -u -m egrs.remain052 recover --config "$CONFIG/evaluation.json" --parent "$PARENT051" --output "$BANK052"
# 仅450/450成功返回后：
python -u -m egrs.remain052 run --config "$CONFIG/evaluation.json" --model base --output "$RUN052/base"
python -u -m egrs.remain052 run --config "$CONFIG/evaluation.json" --model h1 --output "$RUN052/h1"
python -u -m egrs.remain052 compare --base "$RUN052/base" --h1 "$RUN052/h1" --output "$RUN052/comparison.json"
~~~

日志补救前缀`[052]`，动作评测沿原代码`[049]`，每条实时任务/总体合规SR和百分比。具体完整conda/Python与一键串行命令由Codex隔离部署后写入本地命令文档。

CPU/fake只证明软件路径和边界，不代替实际3项补救或真实SR；本轮不自动合并PR，不删除旧文件。
