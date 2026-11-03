"""Labeled retrieval evaluation; no LLM judge or inferred ground truth."""

import argparse
import json
from pathlib import Path

from .hybrid_knowledge import HybridKnowledgeBase
from .knowledge import KnowledgeBase


def score_retrieval(retriever, cases: list[dict], limit: int = 3) -> dict:
    positive_raw, positive_delivered, conflict_hits, negative_hits = [], [], [], []
    details = []
    for case in cases:
        expected = set(case["relevant_doc_ids"])
        hits = retriever.search_documents(case["query"], limit=limit) if isinstance(
            retriever, HybridKnowledgeBase) else retriever.search_documents(case["query"])
        delivered = {hit["doc_id"] for hit in hits}
        raw = {hit["doc_id"] for hit in hits if not hit.get("expanded_for_conflict", False)}
        if expected:
            positive_raw.append(len(expected & raw) / len(expected))
            positive_delivered.append(len(expected & delivered) / len(expected))
            if case.get("conflict", False):
                conflict_hits.append(expected.issubset(delivered))
        else:
            negative_hits.append(bool(delivered))
        details.append({"query": case["query"], "expected": sorted(expected),
                        "raw": sorted(raw), "delivered": sorted(delivered),
                        "expanded": sorted(delivered - raw)})

    mean = lambda numbers: round(sum(numbers) / len(numbers), 4) if numbers else None
    return {"total_queries": len(cases), "positive_queries": len(positive_raw),
            "negative_queries": len(negative_hits), "conflict_queries": len(conflict_hits),
            f"raw_recall_at_{limit}": mean(positive_raw),
            f"delivered_recall_at_{limit}": mean(positive_delivered),
            "negative_candidate_rate": mean(negative_hits),
            "conflict_pair_recall": mean(conflict_hits), "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate labeled retrieval queries")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    cases = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    hybrid = HybridKnowledgeBase(args.index_dir)
    try:
        result = {"hybrid": score_retrieval(hybrid, cases, args.limit),
                  "legacy": score_retrieval(KnowledgeBase(), cases, args.limit)}
    finally:
        hybrid.close()
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
