from src.knowledge import KnowledgeBase


def test_conflicting_documents_are_both_recalled():
    hits = KnowledgeBase().search_documents("报销期限多久")
    assert {hit["doc_id"] for hit in hits} == {"D01", "D02"}


def test_paraphrase_recall_and_exact_read():
    kb = KnowledgeBase()
    assert kb.search_documents("在家办公一周能有几天")[0]["doc_id"] == "D03"
    assert kb.read_snippet("D03", "S1")["text"].startswith("员工每周最多")


def test_missing_and_out_of_scope():
    kb = KnowledgeBase()
    assert kb.search_documents("公司食堂几点开门") == []
    assert kb.read_snippet("D99", "S1")["ok"] is False
