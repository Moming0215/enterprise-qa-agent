# 评估记录

## 离线流程测试

`python -m pytest -q`：18 passed（2026-11-01，本机 Python 3.12.4；实际输出见 [`examples/test-results.txt`](../examples/test-results.txt)）。测试覆盖六个验收场景、引用越界、超限、资料替换后输出变化、Windows 控制台编码，并校验在线记录的状态与逐字引用。CLI Mock 实际输出位于 [`examples/mock/`](../examples/mock/)，输入位于 [`examples/inputs/`](../examples/inputs/)。Mock 结果仅证明流程，不证明真实模型决策。

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

检索是针对合成小语料的确定性主题词匹配；未知表述可能漏召回。冲突检查对同主题不同文本采取保守处理，可能把兼容但措辞不同的资料判为待确认。模型输出 JSON 及引用若不合法，将返回 `incomplete`，不会自动修复。工具故障注入仅用于可复现验证。

当前没有人工标注的检索评测集，也没有向量检索，因此不报告召回率。企业文档摄取与评估扩展见 [`06-enterprise-rag-extension.md`](06-enterprise-rag-extension.md)。
