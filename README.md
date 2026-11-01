# 企业知识问答 Agent（题号 3）

框架版本：LangGraph 1.2.19、langchain-openai 1.7.3（完整依赖见 `pyproject.toml`）。

使用合成制度和产品资料演示模型选择检索、读取原文、补查或结束的工具循环。CLI 输出回答、引用、资料缺口、状态和 Trace。真实模型为 DeepSeek `deepseek-flash`；Mock 模式仅验证流程，不能证明真实模型决策效果。

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

## 评审入口

- 资料：[`data/documents.json`](data/documents.json)
- Agent 与工具：[`src/agent.py`](src/agent.py)、[`src/knowledge.py`](src/knowledge.py)
- 引用校验：[`src/validation.py`](src/validation.py)
- 六场景测试：[`tests/test_scenarios.py`](tests/test_scenarios.py)
- 输入与实际记录：[`examples/`](examples/)
- 需求、设计、评估、AI 使用与复盘：[`docs/`](docs/)

项目借鉴 [LangChain ReAct Agent 模板](https://github.com/langchain-ai/react-agent)的模型—工具循环模式，未直接复制其源文件。使用 LangGraph 1.x 的 `StateGraph`、消息 reducer 和条件边负责循环；资料检索、引用验证、状态边界和 Trace 为本项目代码。
