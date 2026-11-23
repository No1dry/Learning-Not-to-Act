# 044软件验收与部署完成：用户直接启动提示词正式180

2026-11-16。Codex R1接受PR19固定e8445b6ae640f21446533592326c645a6d42894b（实现8259a104、acceptedPR17@7d28d515依赖）软件/隔离文件部署，X无需返修/泛审，不自动mergePR19/17/18。

新prompt044六模块，仅模型predict语言边界改变：P1完整原指令＋静态初始A完成事实；P2仅B。原官方SOG10/归一化/native封装/两RGB/proprio/H520/chunk8/seed7不变，不研究adapter/FINISH/在线GT。评分source instruction和完整A+B目标/保持/错抓/释放保持。既有90个egrs生产源/JSON逐字节不变。

Codex新60项全过；旧1bridge/原reader2/A与炉子2也过，独立65个不同通过。另19项旧bridge/proxy因归档无Git历史在git show旧revision时setup error，原代码未变、保留JUnit，复用原accepted及X本轮20项兼容证据，不修断言/加历史恢复或真实MVP门槛，不冒称80全过。X80＋另4为其证据，不与Codex混计。

新code/config task044-e8445b6a，101源码/依赖/模板和3实际配置SHA一致；原worker/simulation仅no-deps editable映射，无升级。实际两JSON/模型来源和冻结reference SHA/提示表、所有保护根与输出marker分离、脚本语法及worker模块来源核对通过。原plan完整ten投影在现成metadata上也匹配ed9b5027，不新构造来源计划。运行文档worker键路径的小错误已由Codex准确部署命令规避，非阻断不返修。

软件/准备100%，真实模型/仿真/正式eval0；两个eval目录及marker不存在。下一用户按公开2026-11-16_task044_user_evaluation_commands及本地044完整命令，在原simulation环境source session044.sh，一条P1正式90正常后P2正式90，180全视频/≤11700predict。P0历史24.44%只引用，训练/00/新标签索引或状态数据/额外seed/提示搜索/基线/预检/MVP均0；不要重开043。

Codex本轮只CPU/fake/现成JSON元信息/文件部署，未代启停任何真实作业；PR19已关联本聊天。固定源tar/X原稿/测试JUnit/配置/私有收据及六关键文档精确commit读回SHA本地备份、manifest登记。保留dirty checkout及所有旧数据/中间权重/分数/失败署名，无删除待删=[]。软件closed，真实SR/研究解释open。本条覆盖此前044代码/部署0快照，不覆盖未来用户决定。
