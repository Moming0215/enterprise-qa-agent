from langchain_core.messages import AIMessage, ToolMessage

import src.agent as agent


class FakeModel:
    def __init__(self, **kwargs):
        pass

    def bind_tools(self, tools):
        return self

    def bind(self, **kwargs):
        return FakeRepairModel()

    def invoke(self, messages):
        observed = [message for message in messages if isinstance(message, ToolMessage)]
        if not observed:
            return AIMessage(content="", tool_calls=[{"name": "search_documents", "args":
                {"query": "远程办公"}, "id": "search-1"}])
        if len(observed) == 1:
            return AIMessage(content="", tool_calls=[{"name": "read_snippet", "args":
                {"doc_id": "D03", "snippet_id": "S1"}, "id": "read-1"}])
        return AIMessage(content="not valid JSON")


class FakeRepairModel:
    def invoke(self, messages):
        return AIMessage(content='''{"status":"answered","answer":"每周两天",\
"citations":[{"doc_id":"D03","snippet_id":"S1","quote":"员工每周最多可申请两天远程办公"}],\
"gaps":[],"clarifying_question":null,"error":null}''')


def test_invalid_online_json_gets_one_bounded_format_repair(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setattr(agent, "ChatOpenAI", FakeModel)
    result = agent.run_agent({"question": "每周远程办公几天？"}, mode="online")
    assert result["status"] == "answered"
    assert result["trace"][-1]["format_repair"] == "success"
    assert "两天" in result["answer"]


def test_failed_format_repair_returns_incomplete(monkeypatch):
    class BrokenRepair:
        def invoke(self, messages):
            return AIMessage(content="still invalid")

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setattr(agent, "ChatOpenAI", FakeModel)
    monkeypatch.setattr(FakeModel, "bind", lambda self, **kwargs: BrokenRepair())
    result = agent.run_agent({"question": "每周远程办公几天？"}, mode="online")
    assert result["status"] == "incomplete"
    assert result["error"] == "invalid_model_json"
    assert result["trace"][-1]["format_repair"] == "failed:JSONDecodeError"


def test_model_api_error_is_not_reported_as_answer(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setattr(agent, "ChatOpenAI", FakeModel)
    monkeypatch.setattr(FakeModel, "invoke", lambda self, messages: (_ for _ in ()).throw(RuntimeError("503")))
    result = agent.run_agent({"question": "每周远程办公几天？"}, mode="online")
    assert result["status"] == "incomplete"
    assert result["error"] == "model_error:RuntimeError"
