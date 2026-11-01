import json

import pytest
from reportlab.pdfgen import canvas

from src.ingestion import build_chunks, extract_source


def test_markdown_parent_child_and_metadata(tmp_path):
    path = tmp_path / "policy.md"
    path.write_text("# 报销制度\n\n员工应在费用发生后30天内提交报销申请。\n", encoding="utf-8")
    path.with_name("policy.md.meta.json").write_text(json.dumps({
        "doc_id": "D01", "topic": "reimbursement_deadline", "version_date": "2026-01-01",
        "scope": "全体员工"}, ensure_ascii=False), encoding="utf-8")
    parents, children = build_chunks(path, parent_size=100, child_size=20, overlap=4)
    assert len(parents) == 1
    assert parents[0]["doc_id"] == "D01"
    assert parents[0]["topic"] == "reimbursement_deadline"
    assert parents[0]["source_location"].startswith("section:")
    assert all(c["text"] in parents[0]["text"] for c in children)
    assert all(c["parent_id"] == parents[0]["snippet_id"] for c in children)


def test_pdf_pages_are_extracted_and_empty_pdf_rejected(tmp_path):
    path = tmp_path / "policy.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 700, "Reimbursement deadline: 30 days")
    pdf.showPage()
    pdf.save()
    pages = extract_source(path)
    assert len(pages) == 1
    assert pages[0]["source_location"] == "page:1"
    assert "30 days" in pages[0]["text"]
    empty = tmp_path / "empty.pdf"
    pdf = canvas.Canvas(str(empty))
    pdf.showPage()
    pdf.save()
    with pytest.raises(ValueError, match="no extractable text"):
        extract_source(empty)


def test_unsupported_and_corrupt_file_fail_explicitly(tmp_path):
    unsupported = tmp_path / "policy.docx"
    unsupported.write_bytes(b"not a docx")
    with pytest.raises(ValueError, match="unsupported"):
        extract_source(unsupported)
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="pdf_parse_failed"):
        extract_source(broken)
