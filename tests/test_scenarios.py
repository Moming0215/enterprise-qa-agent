import json

from src.agent import run_agent


def test_six_acceptance_scenarios():
    cases = [
        ("员工每周可远程办公几天？", "answered"),
        ("报销期限多久？", "needs_clarification"),
        ("公司食堂几点开门？", "needs_clarification"),
        ("在家办公每周能安排几日？", "answered"),
    ]
    for question, expected in cases:
        assert run_agent({"question": question}, "mock")["status"] == expected
    followup = run_agent({"question": "那每周最多几天？", "history": [
        {"role": "user", "content": "远程办公有什么规定？"}]}, "mock")
    assert followup["status"] == "answered"
    failed = run_agent({"question": "远程办公规定？"}, "mock", fail_tool="search_documents")
    assert failed["status"] == "incomplete"


def test_replacement_document_changes_answer(tmp_path):
    from src.knowledge import DEFAULT_CORPUS

    docs = json.loads(DEFAULT_CORPUS.read_text(encoding="utf-8"))
    for doc in docs:
        if doc["doc_id"] == "D03":
            doc["snippets"][0]["text"] = "员工每周最多可申请一天远程办公，须提前一天获得直属主管批准。"
    replacement = tmp_path / "documents.json"
    replacement.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    original = run_agent({"question": "每周远程办公几天？"}, "mock")
    changed = run_agent({"question": "每周远程办公几天？"}, "mock", corpus_path=str(replacement))
    assert "两天" in original["answer"]
    assert "一天" in changed["answer"]
    assert changed["citations"][0]["quote"] != original["citations"][0]["quote"]
