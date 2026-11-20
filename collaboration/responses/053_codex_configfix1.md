# 053 configfix1勘误交付

Codex初始化顺序错误已修：run在validation.identity之前调用原old.activate(cfg)。v2启动没有到parent或模型阶段，零新轨迹，新run未创建，旧marker与失败日志保留。

PR28最新8fc4a041ebc58fa4d83b059899c99749c5593724，树c87d06086b9383a3f64ea99c211f3949e84a29ad。生产只此一调用＋注释，原数据/源/评分/继承/预算保持。受影响16项CPU/fake过，新增独立进程实际CLI冷启动回归；服务器同conda/venv/session实际CLI在parent前CPU哨兵通过，没有导入torch/native env或启动真实作业。

v3隔离147源依赖/测试文档＋3配置SHA一致；新marker/log为configfix1，不删旧marker，原未创建run ID沿用。原11＋新439＋H1 450仍900。先前38索引/证据/续跑验收保持，本次不重跑23旧测试或旧真实trace。软件/部署closed，真实新889待用户亲启；X无需返修，不自动merge/删除。详细证据053_startup_configfix1.json。
