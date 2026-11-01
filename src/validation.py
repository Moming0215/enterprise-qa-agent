"""Programmatic guard against unsupported citations and premature answers."""


def incomplete(error: str) -> dict:
    return {"status": "incomplete", "answer": "", "citations": [],
            "gaps": [], "clarifying_question": None, "error": error}


def validate_answer(answer: dict, read_evidence: dict, candidates: list[dict]) -> dict:
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
        keys = list(dict.fromkeys((c["doc_id"], c["snippet_id"]) for c in citations))
        normalized["answer"] = "\n".join(read_evidence[key]["text"] for key in keys)
        normalized["gaps"] = []
        normalized["clarifying_question"] = None
    elif answer["status"] == "needs_clarification":
        if citations:
            keys = list(dict.fromkeys((c["doc_id"], c["snippet_id"]) for c in citations))
            normalized["answer"] = "资料需要确认。" + "；".join(
                f"{key[0]}：{read_evidence[key]['text']}" for key in keys)
        else:
            normalized["answer"] = "现有资料不足，无法给出有依据的答案。"
        if not normalized["clarifying_question"]:
            normalized["clarifying_question"] = "请提供适用资料或确认适用范围。"
    else:
        normalized["answer"] = "任务未完成。"
        normalized["error"] = normalized["error"] or "model_marked_incomplete"
    return normalized
