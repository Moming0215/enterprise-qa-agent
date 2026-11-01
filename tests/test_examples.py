"""Check that committed online evidence matches the claimed outcomes."""

import json
from pathlib import Path

from src.knowledge import KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]


def load_case(name):
    return json.loads((ROOT / "examples" / "online" / f"{name}.json").read_text(encoding="utf-8"))


def test_online_records_cover_required_paths():
    expected = {"clear": "answered", "conflict": "needs_clarification",
                "out_of_scope": "needs_clarification", "paraphrase": "answered",
                "followup": "answered", "tool_failure": "answered"}
    for name, status in expected.items():
        case = load_case(name)
        assert case["mode"] == "online"
        assert case["status"] == status
        assert case["trace"]
    assert {c["doc_id"] for c in load_case("conflict")["citations"]} == {"D01", "D02"}
    assert any(event.get("result", {}).get("error") == "injected_failure"
               for event in load_case("tool_failure")["trace"])


def test_online_citations_are_exact_source_text():
    for name in ("clear", "conflict", "paraphrase", "followup", "tool_failure", "replaced"):
        corpus = ROOT / "examples" / "replaced-documents.json" if name == "replaced" else None
        kb = KnowledgeBase(corpus) if corpus else KnowledgeBase()
        case = load_case(name)
        for citation in case["citations"]:
            source = kb.read_snippet(citation["doc_id"], citation["snippet_id"])
            assert source["ok"] and citation["quote"] in source["text"]
    assert "两天" in load_case("clear")["answer"]
    assert "一天" in load_case("replaced")["answer"]
