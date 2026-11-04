# 035 R8：eval001首场景前暂停，环境桥接双版本兼容待修

训练完成/权重身份验收保持；**撤回R7“可直接执行180”这一运行就绪结论**，保留当时纯文件计划通过事实，不冒称已测真实环境初始化。

用户真实启动eval001，模型与adapter已加载；首单元10_basket在environment_initialize因`runtime LIBERO fingerprint differs from the frozen manifest`失败。attempts=[]、results=[]，0/180=0%，无任务轨迹/动作；不是低SR、OOM或训练错误。未由Codex停止/重启作业，程序自行退出。

实际sim版本/源码/资产/控制频率/compat规则均与旧manifest一致，差别仅bridge文件SHA。原180来源静态分组：旧六120条/66调用绑定fa85ae08/指纹27939e2d；新三60条/60调用绑定3a515ddd/指纹e7d58f35。当前d8541ef4是第二版；旧六原baseline使用第一版。Codex漏审执行分派，责任不推给用户或训练。

已向X提交[精确最小任务](../tasks/035_legacy_environment_dispatch.md)：方法侧保持两套实际原实现与严格锁分派，不伪造/绕过指纹、不改core/评分/初态、不重训或回放。先精简CPU/fake与只读身份核对，Codex隔离部署后用户直接新eval002；不新增模型MVP或实验预算。原001零episode，全部180仍未执行。

旧命令页已加暂停说明，原001/config/权重/源码/错误保留，不覆盖/自动重跑。实时SR小增量仍非阻断open；本修复open、方法效果open，不伪造闭环。无自动merge或清理，待删=[]。
