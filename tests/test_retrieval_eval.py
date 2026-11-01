from src.evaluate_retrieval import score_retrieval
import json
from pathlib import Path

from src.hybrid_knowledge import HybridKnowledgeBase, build_index


class StubRetriever:
    def search_documents(self, query, limit=3):
        if query == "conflict":
            return [{"doc_id": "D01", "expanded_for_conflict": False},
                    {"doc_id": "D02", "expanded_for_conflict": True}]
        if query == "missing":
            return [{"doc_id": "D03", "expanded_for_conflict": False}]
        return []


def test_metric_separates_raw_and_expanded_recall_and_negative_false_hits():
    cases = [
        {"query": "conflict", "relevant_doc_ids": ["D01", "D02"], "conflict": True},
        {"query": "missing", "relevant_doc_ids": [], "conflict": False},
    ]
    result = score_retrieval(StubRetriever(), cases, limit=3)
    assert result["raw_recall_at_3"] == 0.5
    assert result["delivered_recall_at_3"] == 1.0
    assert result["negative_candidate_rate"] == 1.0
    assert result["conflict_pair_recall"] == 1.0


def test_labeled_chinese_queries_retrieve_evidence_with_real_embeddings(tmp_path):
    root = Path(__file__).resolve().parents[1]
    build_index(root / "data" / "source_docs", tmp_path / "index")
    kb = HybridKnowledgeBase(tmp_path / "index")
    try:
        cases = json.loads((root / "data" / "eval_queries.json").read_text(encoding="utf-8"))
        result = score_retrieval(kb, cases, limit=3)
    finally:
        kb.close()
    assert result["total_queries"] == 16
    assert result["raw_recall_at_3"] >= 0.9
    assert result["conflict_pair_recall"] == 1.0
