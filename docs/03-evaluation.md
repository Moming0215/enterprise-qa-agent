# 评估记录

## 离线流程测试

原有基线测试为 18 passed，实际输出见 [`examples/test-results.txt`](../examples/test-results.txt)。加入 PDF/Markdown 摄取、混合检索、元数据溯源、检索评估和索引 Agent 测试后，全套结果见 [`examples/hybrid/test-results.txt`](../examples/hybrid/test-results.txt)。测试覆盖六个验收场景、引用越界、超限、资料替换后输出变化、损坏 PDF、同名文件、部分摄取失败和混合检索。CLI Mock 实际输出位于 [`examples/mock/`](../examples/mock/)。Mock 仅证明流程，不证明真实模型决策。

## 在线模型评估

2026-11-01 用 DeepSeek `deepseek-flash` 在线运行。每个输出 JSON 内含实际 Trace，输入和输出路径如下：

| 场景 | 输入 | 实际输出与 Trace | 观察结果 |
|---|---|---|---|
| 明确答案 | [`clear.json`](../examples/inputs/clear.json) | [`online/clear.json`](../examples/online/clear.json) | `answered`，引用 D03 原文；模型读取后回答 |
| 文档冲突 | [`conflict.json`](../examples/inputs/conflict.json) | [`online/conflict.json`](../examples/online/conflict.json) | `needs_clarification`，读取并引用 D01、D02，列出 30 天与 15 天的冲突 |
| 资料外问题 | [`out_of_scope.json`](../examples/inputs/out_of_scope.json) | [`online/out_of_scope.json`](../examples/online/out_of_scope.json) | `needs_clarification`，多次检索无结果后说明缺口 |
| 改写相似问题 | [`paraphrase.json`](../examples/inputs/paraphrase.json) | [`online/paraphrase.json`](../examples/online/paraphrase.json) | `answered`，引用 D03 |
| 上下文追问 | [`followup.json`](../examples/inputs/followup.json) | [`online/followup.json`](../examples/online/followup.json) | `answered`，结合历史明确远程办公主题并引用 D03 |
| 工具失败 | [`tool_failure.json`](../examples/inputs/tool_failure.json) | [`online/tool_failure.json`](../examples/online/tool_failure.json) | 首次 `read_snippet` 注入失败，模型随后重新检索和读取，成功后才回答 |
| 资料替换 | [`clear.json`](../examples/inputs/clear.json) + [`replaced-documents.json`](../examples/replaced-documents.json) | [`online/replaced.json`](../examples/online/replaced.json) | D03 从“两天”改为“一天”后，在线回答和引用同步改变 |
| 仅有 D01 | [`conflict.json`](../examples/inputs/conflict.json) + [`d01-only-documents.json`](../examples/d01-only-documents.json) | [`online/d01_only.json`](../examples/online/d01_only.json) | `answered`，仅引用 D01 的 30 天原文；无 D02 候选 |

不同观察后的动作对照：正常路径在 `search_documents` 返回 D03 后读取 D03 并结束；冲突路径在检索到 D01、D02 后读取两份原文并请求确认；故障路径在读取返回 `injected_failure` 后重新检索和读取。上述动作来自在线模型实际工具调用，非 Mock 的预设日志。资料外问题第一次在线运行被模型标为 `incomplete`，与请求确认的语义不一致；收紧状态提示后重跑为 `needs_clarification`。首次输出未保存，当前文件为修正后的运行结果。

## 已知限制

原有 JSON 基线检索仍是针对合成小语料的确定性主题词匹配。新增索引使用中文向量与 BM25，引用带原文件位置；但语料仍小，主题元数据仍需人工提供。冲突检查对同主题不同文本采取保守处理，可能把兼容但措辞不同的资料判为待确认。模型输出 JSON 及引用若不合法，将返回 `incomplete`。工具故障注入仅用于可复现验证。

### 混合检索实测（2026-11-01）

使用 [`data/source_docs/`](../data/source_docs/) 的 4 份合成 Markdown、[`data/eval_queries.json`](../data/eval_queries.json) 的 16 条人工标注合成查询（12 条有相关文档、4 条无答案），运行 `src.evaluate_retrieval`。实际逐题结果见 [`examples/hybrid/retrieval_metrics.json`](../examples/hybrid/retrieval_metrics.json)，建索引报告见 [`examples/hybrid/index_manifest.json`](../examples/hybrid/index_manifest.json)。

| 指标 | 混合检索 | 原 JSON 基线 |
|---|---:|---:|
| Raw Recall@3（12 条有答案查询） | 1.0000 | 0.8333 |
| Delivered Recall@3（含同主题冲突补查） | 1.0000 | 0.8333 |
| 冲突双方召回（标注的冲突查询） | 1.0000 | 1.0000 |
| 无答案查询仍返回候选的比例 | 0.5000 | 0.2500 |

“无答案仍返回候选”只表示有相关候选进入 Agent，不能直接等同于虚假回答。员工卡和 4K 导出这两条无答案问题触发了候选，但在线模型仍返回资料不足（[`badge_online.json`](../examples/hybrid/badge_online.json)、[`four_k_online.json`](../examples/hybrid/four_k_online.json)）。这个小样本上的 Recall@3 不能外推到真实企业文档，阈值也未在独立数据集校准。

索引路径的真实模型 Trace 分别见 [`clear.json`](../examples/hybrid/clear.json)、[`conflict.json`](../examples/hybrid/conflict.json)、[`out_of_scope.json`](../examples/hybrid/out_of_scope.json)、[`tool_failure.json`](../examples/hybrid/tool_failure.json)。结果依次为 `answered`（D03）、`needs_clarification`（D01+D02）、`needs_clarification`（无引用）、`answered`（首次读取注入失败后补查成功）。冲突引用含原 Markdown 文件、标题、版本日期和适用范围。扫描件、DOCX、ACL 和增量索引尚未实现，后续方案见 [`06-enterprise-rag-extension.md`](06-enterprise-rag-extension.md)。

### 短视频工具企业模拟知识库

新增 [`data/video_tool_kb/`](../data/video_tool_kb/) 的 14 份合成业务资料、20 条标注查询（15 条有答案、5 条无答案，其中 2 条标注冲突）。建索引报告见 [`index_manifest.json`](../examples/video_tool_kb/index_manifest.json)，逐题检索结果见 [`retrieval_metrics.json`](../examples/video_tool_kb/retrieval_metrics.json)。本机实际 Raw/Delivered Recall@3 均为 1.0000，冲突双方召回为 1.0000；无答案查询仍有候选的比例为 0.6000。这些数字只反映本组由同一套资料设计的合成题，存在明显同源偏差，不代表真实企业效果。

真实模型输入在 [`inputs/`](../examples/video_tool_kb/inputs/)：字幕校对最终返回 `answered`（[`subtitle.json`](../examples/video_tool_kb/subtitle.json)）；草稿保留冲突返回 `needs_clarification` 并引用 K13/K14（[`retention_conflict.json`](../examples/video_tool_kb/retention_conflict.json)）；4K HDR 无依据时返回 `needs_clarification`（[`four_k_unknown.json`](../examples/video_tool_kb/four_k_unknown.json)）；一次读取故障后成功补查（[`read_failure.json`](../examples/video_tool_kb/read_failure.json)）。字幕问题前两次模型最终输出无法解析的 JSON，Agent 正确返回 `incomplete`，记录见 [`subtitle_first_attempt.json`](../examples/video_tool_kb/subtitle_first_attempt.json) 和 [`subtitle_second_attempt.json`](../examples/video_tool_kb/subtitle_second_attempt.json)。这说明在线成功不稳定，后续应增加受约束的输出格式及有限修复机制。

Mock 在较大语料下会顺序读取全部候选，可能引用无关文档；其测试只证明冲突双方不会被漏掉，不能证明模型筛选证据的质量。在线记录和实际原文核对由 [`test_video_tool_kb.py`](../tests/test_video_tool_kb.py) 执行。所有业务制度与数值均为虚构设定。
