# 045 Codex交付：043训练长度参数化与完整状态续训

2026-11-16。用户明确本轮由Codex直接修改，不交X重复实现。PR20固定10531b626998d02f6168d23df02501ce64d36969，依赖PR18@1edc6e0；不自动merge。13文件，实际生产改动限hint043八模块的参数/状态格式/评测step；未改数据、网络、loss或原core/reporting。

--target-updates参数按原每1000配方推导预算，--init-from将原已完成1000完整状态导入新输出，保留AdamW/LambdaLR/sampler/Python/NumPy/Torch/CUDA RNG。源账本/权重只读，累计消耗继承，不退款、不重新warmup；相同新run恢复仍显式--resume。旧v1/1000兼容，新延长v2记录父adapter/state/identity/run_config字节SHA。--checkpoint-step显式选择固定2000/3000，无提示部署与完整原评分保持。

90项不同CPU/fake通过：原71、新续训15、policy step2、脚本2，零failure/error/skip；包含tiny1000→3000、两个milestone、旧父文件不变、优化器/采样/RNG恢复和防旧checkpoint退款。不把tiny软件循环称真实7B训练。GitHub新源码树与本地git树一致，PR已关联聊天。

已隔离部署110源码/依赖/模板和9配置SHA一致；两原venv仅no-deps editable映射，原runtime/父1k状态SHA/数据来源/评测来源和实际JSON0.0类型核对，旧输出保持。未加载/反序列化真实模型state或运行任何真实阶段，未来两train/四eval/两marker均不存在。

实际计划两组各新增2000步，共4000、原参考新增≤36096/学生≤108288，之后固定四快照10/00各90共720，零新数据/index/标签/基线。用户先一条串行train，两组结束后用户另启720，不额外prepare/plan/MVP/资格；完整常用命令已填本地，公开脱敏说明见同日commands。X暂无任务，真实效果open，所有旧结果/失败署名保持，无删除待删=[]。
