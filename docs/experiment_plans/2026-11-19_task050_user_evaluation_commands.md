# 050：用户启动H0@3000官方LIBERO-10单500

准备100%，真实500尚未启动。完整实际服务器路径、普通conda/python、nohup及绝对路径watch命令已交到本地`docs/050_H0官方LIBERO10评测完整命令_2026-11-19.md`，公开库不复制服务器路径或凭证。

在原peft-openvla＋仿真venv中，source新session050，然后：

~~~bash
python -u -m egrs.official050 run --config CONFIG/h0-10.json --output NEW_RUN
~~~

后台用nohup；简洁实时进度每5秒watch：

~~~bash
python -m egrs.official050 progress --output NEW_RUN --brief
~~~

050仅H0@3000一个模型，官方十任务（含书/caddy任务5）各50默认初态0..49，共500。与048的原版/H1完整1000同官方pipeline、原语言/原生done、seed7/env0、H520/wait10/chunk8、两图/proprio/crop和10统计。全视频、逐条实时SR、最终十任务summary与episodes.jsonl。不是Remain九任务450，不生成状态或训练，不改变权重强度，也不重跑原版/H1。

现成H0的固定字节经文件核对，64CPU/fake一次全过，真实预跑0。直接启动正式500，不必MVP/额外GPU推理/索引/资格流程。旧047/048/049保持，不启停用户作业；输出存在即拒绝覆盖。正常500完成后由Codex读取summary、逐条索引并同原版94.80%、H1 88.80%做配对分析。预计空闲卡约2–3小时，仅基于前轮500历史，不作保证。所有真实阶段由用户启动，PR25不自动merge。
