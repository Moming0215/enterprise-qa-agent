# 企业知识问答 Agent（题号 3）

框架版本：LangGraph 1.2.19、langchain-openai 1.7.3；索引使用 Qdrant Client 1.20.0 与 FastEmbed 0.9.1（完整依赖见 `pyproject.toml`）。

使用合成制度和产品资料演示模型选择检索、读取原文、补查或结束的工具循环。CLI 输出回答、引用、资料缺口、状态和 Trace。真实模型为 DeepSeek `deepseek-flash`；Mock 模式仅验证流程，不能证明真实模型决策效果。

确定答案要通过已读原文的逐字引用、同主题竞争资料检查和保守的问答相关性检查；与问题无关或只说明“未规定”的证据会转为 `needs_clarification`。这降低无依据回答风险，但不构成通用语义正确性证明。

## 环境与安装

Python 3.11+。在 PowerShell 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
Copy-Item .env.example .env
```

在 `.env` 中填写 `DEEPSEEK_API_KEY=`。`.env` 已加入 `.gitignore`，不要提交密钥。在线接口默认 `https://api.deepseek.com`，模型默认 `deepseek-flash`。

`requirements.lock` 记录本次运行的完整 Python 依赖版本。需要按锁定版本复现时，先执行 `pip install -r requirements.lock`，再执行 `pip install -e . --no-deps`。

## 运行

```powershell
.\.venv\Scripts\python.exe -m src.cli --input examples/inputs/clear.json --mode online --output examples/online/clear.json
.\.venv\Scripts\python.exe -m src.cli --input examples/inputs/conflict.json --mode online --output examples/online/conflict.json
.\.venv\Scripts\python.exe -m src.cli --input examples/inputs/tool_failure.json --mode online --fail-tool read_snippet --output examples/online/tool_failure.json
.\.venv\Scripts\python.exe -m src.cli --input examples/inputs/clear.json --mode mock --output examples/mock/clear.json
.\.venv\Scripts\python.exe -m pytest -q
```

`--max-steps` 限制工具调用数，默认 8；达到上限返回 `incomplete`。`--corpus` 可指定替换后的合成资料 JSON。CLI 的未完成任务返回退出码 2。

## PDF/Markdown 混合检索入口

`data/source_docs/` 是合成资料原文件；同名 `.meta.json` 提供文档 ID、主题、版本日期和适用范围。首次运行会下载中文向量模型和 BM25 模型，需网络及模型缓存空间。索引只在本机生成，`data/index/` 不入库。

```powershell
.\.venv\Scripts\python.exe -m src.ingest_cli --source data/source_docs --index data/index
.\.venv\Scripts\python.exe -m src.cli --input examples/inputs/conflict.json --mode online --index-dir data/index --output examples/hybrid/conflict.json
.\.venv\Scripts\python.exe -m src.evaluate_retrieval --dataset data/eval_queries.json --index-dir data/index --output examples/hybrid/retrieval_metrics.json
.\.venv\Scripts\python.exe -m pytest -q
```

该路径按标题/页码切分父片段，再切子片段建立中文 dense + BM25 sparse 索引，融合候选并读取父片段。来源定位和版本信息随引用返回；同一已标注主题的其他资料会补入候选，避免 top-k 隐藏冲突。无侧车元数据也能入库，但主题为 `unknown` 时无法做同主题冲突扩展。扫描 PDF、DOCX、权限过滤和增量索引尚未支持，详见 [`docs/06-enterprise-rag-extension.md`](docs/06-enterprise-rag-extension.md)。

## 短视频工具企业模拟知识库

[`data/video_tool_kb/`](data/video_tool_kb/) 包含 44 份跨产品、内容安全、发布、客服、数据和安全流程的合成资料，以及 70 条标注检索题。它以“小影科技（模拟）”为背景，**不代表该公司的真实产品、政策或承诺**。K13/K14 故意给出相互矛盾且未说明优先级的草稿保留期限，用于验证冲突处理。

```powershell
.\.venv\Scripts\python.exe -m src.ingest_cli --source data/video_tool_kb/sources --index data/index/video_tool_kb
.\.venv\Scripts\python.exe -m src.cli --input examples/video_tool_kb/inputs/retention_conflict.json --mode online --index-dir data/index/video_tool_kb --output examples/video_tool_kb/retention_conflict.json
.\.venv\Scripts\python.exe -m src.evaluate_retrieval --dataset data/video_tool_kb/eval_all.json --index-dir data/index/video_tool_kb --output examples/private/retrieval-check.json
.\.venv\Scripts\python.exe -m pytest tests/test_video_tool_kb.py -q
```

扩充后的检索指标见 [`examples/video_tool_kb/retrieval_metrics_extended.json`](examples/video_tool_kb/retrieval_metrics_extended.json)，早期在线 Trace 见 [`examples/video_tool_kb/`](examples/video_tool_kb/)；首次在线字幕问答出现两次 `invalid_model_json`，失败记录也保留在目录内。最终输出现在支持严格 JSON 与围栏 JSON，在线格式无效时最多追加一次无工具的 JSON 格式修复。接口不可用或修复失败仍返回 `incomplete`。该目录下的资料用途与边界详见 [`data/video_tool_kb/README.md`](data/video_tool_kb/README.md)。

70 题评估输出中的 `hybrid` 才对应本知识库；`legacy` 固定使用旧 JSON 基线，语料不同，不作横向比较。2026-11-03 DeepSeek API 返回 503，新增格式修复尚未完成真实接口的重复成功率验证；本地模拟测试与失败 Trace 见 [`examples/video_tool_kb_v2/`](examples/video_tool_kb_v2/)。

## 评审入口

- 资料：[`data/documents.json`](data/documents.json)
- Agent 与工具：[`src/agent.py`](src/agent.py)、[`src/knowledge.py`](src/knowledge.py)
- 引用校验：[`src/validation.py`](src/validation.py)
- 六场景测试：[`tests/test_scenarios.py`](tests/test_scenarios.py)
- 输入与实际记录：[`examples/`](examples/)
- 需求、设计、评估、AI 使用与复盘：[`docs/`](docs/)
- 混合检索代码与评估：[`src/hybrid_knowledge.py`](src/hybrid_knowledge.py)、[`src/evaluate_retrieval.py`](src/evaluate_retrieval.py)、[`examples/hybrid/`](examples/hybrid/)
- 企业杂乱文档后续扩展：[`docs/06-enterprise-rag-extension.md`](docs/06-enterprise-rag-extension.md)

项目借鉴 [LangChain ReAct Agent 模板](https://github.com/langchain-ai/react-agent)的模型—工具循环模式，未直接复制其源文件。使用 LangGraph 1.x 的 `StateGraph`、消息 reducer 和条件边负责循环；资料检索、引用验证、状态边界和 Trace 为本项目代码。

索引路径借鉴 MIT 许可的 [agentic-rag-for-dummies](https://github.com/GiovanniPasq/agentic-rag-for-dummies) 的父子分块和 dense/sparse 混合检索思路，代码按本题证据定位与冲突规则重新实现，未复制其源文件。
