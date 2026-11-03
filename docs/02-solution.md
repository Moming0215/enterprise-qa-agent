# 方案与动态决策

实现时使用 LangGraph 1.2.19、langchain-openai 1.7.3；扩展索引使用 Qdrant Client 1.20.0、FastEmbed 0.9.1、pypdf 6.21.4、jieba 0.42.1。精确依赖版本见 `pyproject.toml`。

使用 LangGraph 1.x `StateGraph` 构建模型节点与工具节点的循环。模型根据历史消息决定调用 `search_documents`、`read_snippet` 或输出结果；工具结果作为消息回传后再次调用模型。工具异常与调用上限由运行代码控制，不由模型自行宣称成功。DeepSeek API 使用 OpenAI 兼容接口，`deepseek-flash` 非思考模式工具调用。

合成资料的轻量检索通过主题词和同义词映射召回同一主题的所有候选，以避免冲突资料仅出现一份；这是确定性的本地工具，不代表模型判断。模型负责决定查询、读取、补查与最终状态。引用校验器仅接受本轮成功读取过的片段及其逐字连续子串。若同主题候选有不同文本，程序阻止直接输出 `answered`。通过校验后，最终事实回答由已读取的原文生成，避免模型在合法引文旁附加未经证实的陈述。

Trace 记录实际模型动作、工具参数、返回摘要及下一轮动作；`previous_observations` 和 `decision_basis` 给出动作依据的可审阅工具观察，不包含模型内部思维。Mock 模式动作由代码预设，只能用于测试工具链和安全边界，不能作为模型决策证据。参见 [`src/agent.py`](../src/agent.py)。

新增 PDF/Markdown 路径先提取章节或页，切出可引用的父片段，再切小的检索子片段。FastEmbed 生成中文 dense 与 BM25 sparse 向量，Qdrant 本地索引分别查询，按 RRF 合并父片段候选。已标注主题的其他父片段补入候选，防止 top-k 只返回冲突的一方。`read_snippet` 返回父片段原文及文件位置；最终引用从实际读取结果补上来源、版本和范围。索引路径与 JSON 路径共用 LangGraph 决策环和引用校验器。

技术取舍：LangGraph 提供清晰循环和状态结构；本地 Qdrant 便于离线演示和复现，避免引入服务部署。父子片段让检索粒度与引用上下文分开。当前同主题补查依赖侧车元数据，对无标注主题无效；RRF 和 dense 阈值仅在小型合成集上检查。原文式回答较长；程序不能理解任意文档间的语义冲突，遇到同主题不同文本时保守请求确认。设计与实现计划分别见 [`superpowers/specs/2026-11-01-hybrid-retrieval-design.md`](superpowers/specs/2026-11-01-hybrid-retrieval-design.md) 和 [`superpowers/plans/2026-11-01-hybrid-retrieval.md`](superpowers/plans/2026-11-01-hybrid-retrieval.md)。

2026-11-03 改进：最终响应先严格解析 JSON（也接受完整围栏 JSON）；解析失败时，只追加一次没有工具权限的 JSON 格式修复请求，之后仍走原有引用和冲突校验，失败则 `incomplete`。最终可读回答不直接信任模型自由表述，而是从已验证引文中挑选最多两句相关原文，按文档 ID 列出并去重引用。对于已显式引用其他文档的资料，检索器扩展这些关联文档作为候选。词面选句可能遗漏复杂语义，跨文档答案仍以证据完整性为先。接口 HTTP 503 不属于格式错误，不会被伪装成成功。
