from pathlib import Path
from reportlab.pdfgen import canvas

from src.hybrid_knowledge import HybridKnowledgeBase, build_index


SOURCE_DIR = Path(__file__).resolve().parents[1] / "data" / "source_docs"


def test_hybrid_index_and_conflict_expansion(tmp_path):
    index_dir = tmp_path / "index"
    summary = build_index(SOURCE_DIR, index_dir)
    assert summary["indexed_files"] == 4
    kb = HybridKnowledgeBase(index_dir)
    hits = kb.search_documents("报销期限多久", limit=1)
    assert {hit["doc_id"] for hit in hits} == {"D01", "D02"}
    assert all(hit["source_location"].startswith("section:") for hit in hits)
    d01 = next(hit for hit in hits if hit["doc_id"] == "D01")
    read = kb.read_snippet(d01["doc_id"], d01["snippet_id"])
    assert read["ok"] and "30天" in read["text"]
    assert kb.search_documents("公司食堂几点开门") == []
    kb.close()


def test_rebuild_replaces_stale_source(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    doc = source_dir / "D03.md"
    doc.write_text("# 远程办公\n员工每周可远程办公两天。", encoding="utf-8")
    index_dir = tmp_path / "index"
    build_index(source_dir, index_dir)
    doc.write_text("# 远程办公\n员工每周可远程办公一天。", encoding="utf-8")
    build_index(source_dir, index_dir)
    kb = HybridKnowledgeBase(index_dir)
    hits = kb.search_documents("远程办公")
    assert len(hits) == 1
    assert "一天" in kb.read_snippet(hits[0]["doc_id"], hits[0]["snippet_id"])["text"]
    kb.close()


def test_same_basename_in_different_directories_does_not_collide(tmp_path):
    source_dir = tmp_path / "source"
    for folder, content in (("team_a", "# 甲\n员工甲规则。"), ("team_b", "# 乙\n员工乙规则。")):
        target = source_dir / folder
        target.mkdir(parents=True)
        (target / "policy.md").write_text(content, encoding="utf-8")
    index_dir = tmp_path / "index"
    assert build_index(source_dir, index_dir)["indexed_files"] == 2
    kb = HybridKnowledgeBase(index_dir)
    assert len({key[0] for key in kb.parents}) == 2
    kb.close()


def test_pdf_is_indexed_with_page_provenance(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    path = source_dir / "policy.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 700, "Expense deadline is thirty days.")
    pdf.showPage()
    pdf.save()
    index_dir = tmp_path / "index"
    summary = build_index(source_dir, index_dir)
    assert summary["indexed_files"] == 1
    kb = HybridKnowledgeBase(index_dir)
    parent = next(iter(kb.parents.values()))
    assert parent["source_location"] == "page:1"
    assert "thirty days" in parent["text"]
    kb.close()


def test_invalid_pdf_is_reported_while_valid_document_is_indexed(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "good.md").write_text("# 规则\n有效资料。", encoding="utf-8")
    (source_dir / "bad.pdf").write_bytes(b"not a pdf")
    summary = build_index(source_dir, tmp_path / "index")
    assert summary["indexed_files"] == 1
    assert summary["failures"][0]["file"] == "bad.pdf"
    assert summary["failures"][0]["error"] == "pdf_parse_failed"


def test_unsupported_document_is_reported_not_silently_skipped(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "good.md").write_text("# 规则\n有效资料。", encoding="utf-8")
    (source_dir / "policy.docx").write_bytes(b"placeholder")
    summary = build_index(source_dir, tmp_path / "index")
    assert summary["indexed_files"] == 1
    assert {failure["file"] for failure in summary["failures"]} == {"policy.docx"}
