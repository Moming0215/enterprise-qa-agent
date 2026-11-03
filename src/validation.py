"""Programmatic guard against unsupported citations and premature answers."""

import re

import jieba


def _excerpt(quote: str, question: str) -> str:
    """Select short, verbatim sentences from a verified quote."""
    sentences = [part.strip(" #；;，, ") for part in re.split(r"[。\n]+", quote)
                 if part.strip(" #；;，, ") and not part.lstrip().startswith("#")
                 and not part.strip().startswith(("适用对象：", "负责人："))]
    if not sentences:
        return quote.strip()
    terms = {term for term in jieba.cut(question.lower()) if len(term.strip()) >= 2}
    ranked = sorted(range(len(sentences)), key=lambda i: (
        -sum(term in sentences[i].lower() for term in terms),
        -sum(word in sentences[i] for word in ("应", "需", "不得", "保留", "支持", "没有规定")), i))
    selected = sorted(ranked[:2])
    return "。".join(sentences[i] for i in selected) + "。"


def incomplete(error: str) -> dict:
    return {"status": "incomplete", "answer": "", "citations": [],
            "gaps": [], "clarifying_question": None, "error": error}


def validate_answer(answer: dict, read_evidence: dict, candidates: list[dict], question: str = "") -> dict:
    if not isinstance(answer, dict) or answer.get("status") not in {
        "answered", "needs_clarification", "incomplete"
    }:
        return incomplete("invalid_model_output")
    citations = answer.get("citations", [])
    if not isinstance(citations, list):
        return incomplete("invalid_citations")
    verified_citations = []
    for citation in citations:
        if not isinstance(citation, dict):
            return incomplete("invalid_citation")
        key = (citation.get("doc_id"), citation.get("snippet_id"))
        quote = citation.get("quote")
        if key not in read_evidence or not isinstance(quote, str) or not quote or quote not in read_evidence[key]["text"]:
            return incomplete("citation_not_in_read_source")
        verified = {"doc_id": key[0], "snippet_id": key[1], "quote": quote}
        for field in ("source_file", "source_location", "version_date", "scope"):
            if field in read_evidence[key]:
                verified[field] = read_evidence[key][field]
        if verified not in verified_citations:
            verified_citations.append(verified)
    competing = {}
    for candidate in candidates:
        competing.setdefault(candidate["topic"], set()).add((candidate["doc_id"], candidate["snippet_id"]))
    for group in competing.values():
        if len(group) > 1 and group.issubset(read_evidence):
            if len({read_evidence[key]["text"] for key in group}) > 1:
                if answer["status"] == "answered":
                    return incomplete("unresolved_source_conflict")
                cited = {(c["doc_id"], c["snippet_id"]) for c in citations}
                if answer["status"] == "needs_clarification" and not group.issubset(cited):
                    return incomplete("conflict_requires_both_citations")
    if answer["status"] == "answered":
        if not citations:
            return incomplete("answer_without_citation")
        cited = {(c["doc_id"], c["snippet_id"]) for c in citations}
        topics = {read_evidence[key]["topic"] for key in cited}
        for topic in topics:
            expected = {(c["doc_id"], c["snippet_id"]) for c in candidates if c["topic"] == topic}
            if len(expected) > 1 and not expected.issubset(read_evidence):
                return incomplete("unread_competing_source")
    normalized = {
        "status": answer["status"],
        "answer": "",
        "citations": verified_citations,
        "gaps": answer.get("gaps") if isinstance(answer.get("gaps"), list) else [],
        "clarifying_question": answer.get("clarifying_question") if isinstance(answer.get("clarifying_question"), str) and answer.get("clarifying_question") else None,
        "error": answer.get("error") if isinstance(answer.get("error"), str) and answer.get("error") else None,
    }
    if answer["status"] == "answered":
        normalized["answer"] = "\n".join(
            f"{c['doc_id']}：{_excerpt(c['quote'], question)}" for c in verified_citations)
        normalized["gaps"] = []
        normalized["clarifying_question"] = None
    elif answer["status"] == "needs_clarification":
        if citations:
            normalized["answer"] = "资料需要确认。" + "；".join(
                f"{c['doc_id']}：{_excerpt(c['quote'], question)}" for c in verified_citations)
        else:
            normalized["answer"] = "现有资料不足，无法给出有依据的答案。"
        if not normalized["clarifying_question"]:
            normalized["clarifying_question"] = "请提供适用资料或确认适用范围。"
    else:
        normalized["answer"] = "任务未完成。"
        normalized["error"] = normalized["error"] or "model_marked_incomplete"
    return normalized
