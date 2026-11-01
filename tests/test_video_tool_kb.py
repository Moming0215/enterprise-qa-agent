"""Check the fictional short-video business corpus and its saved runs."""

import json
from pathlib import Path

from src.agent import run_agent
from src.evaluate_retrieval import score_retrieval
from src.hybrid_knowledge import HybridKnowledgeBase, build_index


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "data" / "video_tool_kb"
EXAMPLES = ROOT / "examples" / "video_tool_kb"


def test_business_corpus_has_unique_ids_and_source_metadata():
    sources = sorted((KB / "sources").glob("*.md"))
    assert len(sources) == 14
    metadata = [json.loads(path.with_name(path.name + ".meta.json").read_text(encoding="utf-8"))
                for path in sources]
    assert len({item["doc_id"] for item in metadata}) == len(sources)
    assert all(item["topic"] and item["version_date"] and item["scope"] for item in metadata)
    assert {item["doc_id"] for item in metadata if item["topic"] == "cloud_draft_retention"} == {"K13", "K14"}


def test_business_corpus_retrieval_and_conflict_agent(tmp_path):
    index_dir = tmp_path / "index"
    assert build_index(KB / "sources", index_dir)["indexed_files"] == 14
    kb = HybridKnowledgeBase(index_dir)
    try:
        cases = json.loads((KB / "eval_queries.json").read_text(encoding="utf-8"))
        scores = score_retrieval(kb, cases, limit=3)
    finally:
        kb.close()
    assert scores["total_queries"] == 20
    assert scores["raw_recall_at_3"] >= 0.9
    assert scores["conflict_pair_recall"] == 1.0
    result = run_agent({"question": "删除的云端草稿在回收站保留多久？"},
                       mode="mock", index_dir=str(index_dir))
    assert result["status"] == "needs_clarification"
    assert {"K13", "K14"}.issubset({citation["doc_id"] for citation in result["citations"]})


def test_business_online_records_match_sources_and_failure_state():
    expected = {"subtitle": "answered", "retention_conflict": "needs_clarification",
                "four_k_unknown": "needs_clarification", "read_failure": "answered"}
    for name, status in expected.items():
        result = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
        assert result["mode"] == "online" and result["status"] == status
        assert result["trace"]
        for citation in result["citations"]:
            source = KB / "sources" / citation["source_file"]
            assert citation["quote"] in source.read_text(encoding="utf-8")
    conflict = json.loads((EXAMPLES / "retention_conflict.json").read_text(encoding="utf-8"))
    assert {citation["doc_id"] for citation in conflict["citations"]} == {"K13", "K14"}
    unknown = json.loads((EXAMPLES / "four_k_unknown.json").read_text(encoding="utf-8"))
    assert unknown["clarifying_question"]
    failure = json.loads((EXAMPLES / "read_failure.json").read_text(encoding="utf-8"))
    assert any(event.get("result", {}).get("error") == "injected_failure" for event in failure["trace"])
    for name in ("subtitle_first_attempt", "subtitle_second_attempt"):
        attempt = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
        assert attempt["status"] == "incomplete" and attempt["error"] == "invalid_model_json"
