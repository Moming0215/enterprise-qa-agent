"""Validate saved real-model runs against the source files and claimed paths."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_case(name: str) -> dict:
    return json.loads((ROOT / "examples" / "hybrid" / f"{name}.json").read_text(encoding="utf-8"))


def test_hybrid_online_records_and_source_provenance():
    expected = {"clear": "answered", "conflict": "needs_clarification",
                "out_of_scope": "needs_clarification", "tool_failure": "answered"}
    for name, status in expected.items():
        case = load_case(name)
        assert case["mode"] == "online" and case["status"] == status
        assert any("action" in event for event in case["trace"])
        for citation in case["citations"]:
            source = ROOT / "data" / "source_docs" / citation["source_file"]
            assert source.is_file()
            assert citation["quote"] in source.read_text(encoding="utf-8")
            assert citation["source_location"].startswith("section:")
            assert citation["version_date"]
    assert {citation["doc_id"] for citation in load_case("conflict")["citations"]} == {"D01", "D02"}
    assert load_case("out_of_scope")["citations"] == []


def test_hybrid_online_failure_is_observed_before_recovery():
    trace = load_case("tool_failure")["trace"]
    failed = next(i for i, event in enumerate(trace)
                  if event.get("result", {}).get("error") == "injected_failure")
    assert any(event.get("tool") == "read_snippet" and event.get("result", {}).get("ok")
               for event in trace[failed + 1:])
    assert any("injected_failure" in event.get("decision_basis", "") for event in trace[failed + 1:])


def test_no_answer_candidates_do_not_become_claims():
    for name in ("badge_online", "four_k_online"):
        case = load_case(name)
        assert case["mode"] == "online"
        assert case["status"] == "needs_clarification"
        assert case["clarifying_question"]
