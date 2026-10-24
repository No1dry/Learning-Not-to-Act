# 020 首轮交付：来源元信息兼容

本地实现提交：`d139812b7db73a7a7582aa977ed5161e3bff581e`（基线`edc317321469b80eced1d80bf918d899fef9b89c`）。本回复为后续文档提交；本地交付待X发布到既有PR #2并交接固定remote SHA，随后由Codex审查与隔离部署。此处记录的本地提交尚未推送，未合并；最终remote head由PR交接记录提供。

准备与实现完成度100%；本轮受影响CPU/fake用例148项，144通过（97.30%），4跳过（2.70%），失败0%。真实兼容验证/修复后标注/训练/评测均0%，未启动真实HDF读取、图像处理、状态恢复、渲染或模型作业。

## 修复与边界

- `SourceEpisode(root, source, *, emit=None)`先记录键、属性摘要、字段缺失及来源位置，再解析；异常附带partial inspection和精确阶段。worker保留同步inspection事件及最终失败信息，不再被未赋值的adapter inspection覆盖。
- `resolve_bddl_metadata(env_args, data_attrs, *, suite)`核对三个受支持标识：data属性`bddl_file_name`、`env_args.bddl_file`、`env_args.env_kwargs.bddl_file_name`。每一个存在值都必须有效且一致；允许仅一个标识，固定suite＋精确basename定位一个文件。旧Windows/POSIX机器前缀无需存在，不做模糊查找或候选择优。
- `resolve_installed_bddl(root, metadata, *, embedded, runtime_identity)`保留内嵌正文的严格字节摘要核验；缺正文采用版本化`metadata_resolved_installed_bddl`，明确`source_embedded_bddl_present=false`、历史原字节一致性`unverified`，不填写source-body hash。缺正文必须有`native.libero_source={revision,bddl_sha256}`；提供锁时两种模式都核验精确文件，构造前再查未变。revision是部署声明，显式记录`revision_verified_at_runtime=false`。失败仍保留已经观察到的文件hash及期望hash。
- 生产可选的`bddl_file_name`、`num_samples`可缺失；后者存在时仍校验整数和真实维度。源instruction缺失时仅允许原inventory已有的完整`explicit_human_mapping`；现有instruction仍核对。没有新增BDDL字面语言比对，避免官方“top drawer / top layer of drawer”表述差异误拒；既有native目标原子/对象映射继续核验。
- 源相机约定、机器人/控制器/相机设置缺失或矛盾仍报gap。源XML、compiled names、状态布局、原RGB绑定、对齐/可观察性及无真值输入规则均保持。诊断只在离线audit/events，实际pipeline测试核验annotations、train/dev和prompt不含新增元信息。

配置与标准库锁采集脚本见[运行指南](../../docs/offline_sim_supervision.md)。原生LIBERO示例revision为`8f1084e3132a39270c3a13ebe37270a43ece2a01`，不混作annotation reference core revision。脚本只读固定catalog精确BDDL和源码/git对象，记录版本建立依据，无native导入或HDF读取。示例digest映射为空，需要部署者从选定固定安装采集后填写，不能使用任意hash。既有内嵌正文配置可不加此锁。

## 验证证据

以下均使用`C:/ProgramData/anaconda3/python.exe`、已有固定`EGRS_CORE_ROOT`，native测试在前，无OpenMP绕过或依赖调整。

```text
python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py -q -k metadata --basetemp .work/task020/red-temp
30 failed, 37 deselected                         # 实现前RED：新接口/解析器缺失

python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py -q -k metadata --basetemp .work/task020/green-first
30 passed, 37 deselected

python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py tests/test_sim_pipeline.py -q --basetemp .work/task020/final
142 passed, 4 skipped

python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py -q -k "enumerates_nested or digest_failure" --basetemp .work/task020/red-diagnostics
2 failed, 111 deselected                         # 自查新增partial诊断RED

python -m pytest tests/test_sim_native.py tests/test_sim_metadata.py tests/test_sim_pipeline.py -q -rs --basetemp .work/task020/final-reviewed
144 passed, 4 skipped in 11.58s                   # 最终实现树
```

首次RED使用默认临时目录遭`WinError 5`（19 setup errors、11 failed），随后仅将basetemp移至忽略的工作目录，得到上面的有效RED。最终四个跳过均为`test_metadata_symlink_cannot_escape_fixed_suite`的`suite_outside`、`suite_other`、`file_outside`、`file_other`：Windows创建symlink返回`WinError 1314`，缺少所需权限；没有宣称本机验证了这四种路径。精确大小写与其他路径/摘要检查已通过。修改的六个Python文件`py_compile`及`git diff --check`通过。未运行全库或真实作业。

fixture假设是合成元信息、合成数组与fake原生边界，不是读取本批真实元信息成功的证据。实际只确认缺少内嵌正文，其他字段、native/XML/asset兼容、RGB/时序对应、可观察覆盖均待真实运行。已有019实现`b38526d57d858fdfdb410752f0ae0d6db3085e2f`及manifest `2cd2df5f78b7148b1f490f31c56ce5b55df6bad15c6131dc88172b756bc7b82d`保持不变：200/200来源失败（100%），3200查询processed=0/supervised=0（0%），ready=false/usable=false；不倒改旧统计，不将入口失败UNKNOWN解释成模型失败。

下一步操作和执行者：X发布到既有PR #2并交接固定remote SHA，Codex随后审查并准备新代码/配置/输出目录，保留旧019失败日志、manifest及数据；用户在获准的新目录亲自启动修复后标注，检查覆盖后再分别决定导出、训练和评测。本实现不自动重跑，不新增元信息预读或GPU预检门槛。
