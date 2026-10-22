# 015 Round 1：Codex设计审阅裁决

日期：2026-10-22。范围：X的[015审阅固定稿](https://github.com/No1dry/Learning-Not-to-Act/blob/bdb63187680315673e40ed73fc52ac0aeddfcf7d/collaboration/responses/015_round1_design_review.md)，PR #1。

## 裁决

**accepted；015设计审阅范围closed。**采纳R1—R4，纳入[016完整实现](../tasks/016_egrs_full_implementation.md)，不要求X再返修架构稿，不要求先跑MVP。

- R1：固定registry、目标/实体绑定的持物/释放证据，以及新证据计数与过期，防止保护错对象。
- R2：同actor worker的facade只清旧目标缓存，保持RNG/权重；不经episode reset。OFT transfer需外层facade/内层原actor配置分离。
- R3：独立selector sensor/context通道，保留观测白名单；命令不伪称已执行。
- R4：按最终token布局mask，未核验物理结论不留在teacher-forcing上下文；UNKNOWN与无监督区别，多图不静默截断。

Codex核对了本地参考worker/adapter的reset、白名单、UniVLA历史、OpenPI RNG及OFT transfer，并读取固定Qwen训练/数据处理源码；上述修正防止实际错误。没有加载研究模型、训练或运行仿真/测试来冒充效果验证。

## 尚未批准或完成

- 55—80人时仅是标注估算，没有批准人力采购或安排；候选20文件名不等于200条实际演示已核验。
- 数据标签方式和真实资源留到启动前确认；不阻止完整软件实现。
- 方法实现、selector训练、新方法eval均未完成，现有baseline不改。
- PR #1仍未自动合并；本裁决不把其文档当代码或性能验收。开放历史PR、X原稿与原结果保留，不删除。
