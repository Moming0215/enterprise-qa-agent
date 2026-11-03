from src.validation import validate_answer


EVIDENCE = {("D03", "S1"): {"text": "员工每周最多可申请两天远程办公。", "topic": "remote_work"}}


def test_valid_citation():
    answer = {"status": "answered", "answer": "每周最多两天。", "citations": [
        {"doc_id": "D03", "snippet_id": "S1", "quote": "每周最多可申请两天远程办公"}],
        "gaps": [], "clarifying_question": None, "error": None}
    result = validate_answer(answer, EVIDENCE, [])
    assert result["status"] == "answered"
    assert result["answer"] == "D03：每周最多可申请两天远程办公。"


def test_fabricated_claim_is_replaced_by_source_text():
    answer = {"status": "answered", "answer": "员工每周可远程办公三天，效率提升80%。",
              "citations": [{"doc_id": "D03", "snippet_id": "S1", "quote": "员工每周最多可申请两天远程办公。"}],
              "gaps": "", "clarifying_question": "", "error": ""}
    result = validate_answer(answer, EVIDENCE, [])
    assert result["answer"] == "D03：员工每周最多可申请两天远程办公。"
    assert result["gaps"] == []
    assert result["clarifying_question"] is None
    assert result["error"] is None


def test_unread_quote_is_rejected():
    answer = {"status": "answered", "answer": "15天", "citations": [
        {"doc_id": "D02", "snippet_id": "S1", "quote": "15天"}],
        "gaps": [], "clarifying_question": None, "error": None}
    assert validate_answer(answer, EVIDENCE, [])["status"] == "incomplete"


def test_conflicting_candidates_cannot_be_answered_from_one_source():
    answer = {"status": "answered", "answer": "30天", "citations": [
        {"doc_id": "D01", "snippet_id": "S1", "quote": "30天"}],
        "gaps": [], "clarifying_question": None, "error": None}
    evidence = {("D01", "S1"): {"text": "30天", "topic": "reimbursement_deadline"}}
    candidates = [{"doc_id": "D01", "snippet_id": "S1", "topic": "reimbursement_deadline"},
                  {"doc_id": "D02", "snippet_id": "S1", "topic": "reimbursement_deadline"}]
    assert validate_answer(answer, evidence, candidates)["status"] == "incomplete"


def test_conflict_clarification_must_cite_both_read_sources():
    answer = {"status": "needs_clarification", "answer": "资料冲突", "citations": [
        {"doc_id": "D01", "snippet_id": "S1", "quote": "30天"}],
        "gaps": ["资料冲突"], "clarifying_question": "哪份适用？", "error": None}
    evidence = {("D01", "S1"): {"text": "30天", "topic": "reimbursement_deadline"},
                ("D02", "S1"): {"text": "15天", "topic": "reimbursement_deadline"}}
    candidates = [{"doc_id": doc, "snippet_id": "S1", "topic": "reimbursement_deadline"}
                  for doc in ("D01", "D02")]
    assert validate_answer(answer, evidence, candidates)["error"] == "conflict_requires_both_citations"


def test_long_verified_quote_produces_short_answer_and_deduplicates_citations():
    source = "# 字幕流程\n适用对象：客服。\n编辑器可以生成字幕初稿。创作者需要逐句校对字幕中的人名和数字。本文不承诺识别准确率。"
    citation = {"doc_id": "K01", "snippet_id": "P1", "quote": source}
    result = validate_answer({"status": "answered", "answer": "准确率为99%", "citations":
        [citation, citation], "gaps": [], "error": None},
        {("K01", "P1"): {"text": source, "topic": "subtitle"}}, [], "字幕人名需要校对吗")
    assert result["status"] == "answered"
    assert len(result["citations"]) == 1
    assert "校对字幕中的人名和数字" in result["answer"]
    assert "适用对象" not in result["answer"]
    assert "99%" not in result["answer"]


def test_related_mp4_quote_cannot_answer_4k_hdr_support():
    text = "模拟产品支持 MP4 文件导出。本文没有规定 4K 或 HDR 导出能力。"
    answer = {"status": "answered", "answer": "支持 4K HDR", "citations": [
        {"doc_id": "K02", "snippet_id": "P1", "quote": "模拟产品支持 MP4 文件导出。"}]}
    result = validate_answer(answer, {("K02", "P1"): {"text": text, "topic": "video_export"}},
                             [], "产品支持 4K HDR 导出吗？")
    assert result["status"] == "needs_clarification"
    assert result["citations"] == []


def test_explicit_document_gap_cannot_be_answered_as_supported():
    text = "本文没有规定 4K 或 HDR 导出能力。"
    answer = {"status": "answered", "answer": "支持 4K", "citations": [
        {"doc_id": "K02", "snippet_id": "P1", "quote": text}]}
    result = validate_answer(answer, {("K02", "P1"): {"text": text, "topic": "video_export"}},
                             [], "支持 4K 导出吗？")
    assert result["status"] == "needs_clarification"


def test_unrelated_quote_cannot_answer_question():
    text = "编辑器支持 MP4 文件导出。"
    answer = {"status": "answered", "answer": "每周两天", "citations": [
        {"doc_id": "K02", "snippet_id": "P1", "quote": text}]}
    result = validate_answer(answer, {("K02", "P1"): {"text": text, "topic": "video_export"}},
                             [], "员工每周远程办公几天？")
    assert result["status"] == "needs_clarification"


def test_gap_about_4k_does_not_block_mp4_answer():
    text = "模拟产品支持 MP4 文件导出。本文没有规定 4K 或 HDR 导出能力。"
    answer = {"status": "answered", "answer": "支持 MP4", "citations": [
        {"doc_id": "K02", "snippet_id": "P1", "quote": text}]}
    evidence = {("K02", "P1"): {"text": text, "topic": "video_export"}}
    assert validate_answer(answer, evidence, [], "支持 MP4 导出吗？")["status"] == "answered"
    assert validate_answer(answer, evidence, [], "支持 4K 导出吗？")["status"] == "needs_clarification"
