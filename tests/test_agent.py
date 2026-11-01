from src.agent import run_agent


def test_mock_clear_answer_has_read_trace():
    result = run_agent({"question": "每周可以在家办公几天？"}, mode="mock")
    assert result["status"] == "answered"
    assert result["citations"][0]["doc_id"] == "D03"
    assert any(event.get("tool") == "read_snippet" for event in result["trace"])
    finish = result["trace"][-1]
    assert finish["decision_basis"]
    assert finish["previous_observations"]
    assert "text" not in next(e["result"] for e in result["trace"] if e.get("tool") == "read_snippet")


def test_mock_conflict_prompts_clarification():
    result = run_agent({"question": "报销期限多久？"}, mode="mock")
    assert result["status"] == "needs_clarification"
    assert {c["doc_id"] for c in result["citations"]} == {"D01", "D02"}


def test_mock_missing_and_tool_failure():
    missing = run_agent({"question": "食堂几点开门？"}, mode="mock")
    failure = run_agent({"question": "每周可远程办公几天？"}, mode="mock", fail_tool="read_snippet")
    assert missing["status"] == "needs_clarification"
    assert failure["status"] == "incomplete"
    assert any(event.get("result", {}).get("error") == "injected_failure" for event in failure["trace"])


def test_step_limit_and_bad_question():
    assert run_agent({"question": "报销期限多久？"}, mode="mock", max_steps=1)["status"] == "incomplete"
    assert run_agent({"question": " "}, mode="mock")["status"] == "incomplete"
