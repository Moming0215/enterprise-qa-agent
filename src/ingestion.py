"""Extract PDF/Markdown evidence into source-preserving parent and child chunks.

The parent-child pattern is adapted from the MIT-licensed
GiovanniPasq/agentic-rag-for-dummies design; this implementation is original.
"""

import hashlib
import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


SUPPORTED_SUFFIXES = {".md", ".pdf"}


def extract_source(path: str | Path) -> list[dict]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported file type: {suffix}")
    if suffix == ".pdf":
        try:
            reader = PdfReader(str(path))
            sections = [
                {"text": page.extract_text().strip(), "source_location": f"page:{number}"}
                for number, page in enumerate(reader.pages, start=1)
            ]
        except Exception as exc:
            raise ValueError("pdf_parse_failed") from exc
        sections = [section for section in sections if section["text"]]
    else:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            sections = []
        else:
            chunks = re.split(r"(?=^#{1,3}\s+)", raw, flags=re.MULTILINE)
            sections = []
            for index, chunk in enumerate(chunks):
                text = chunk.strip()
                if not text:
                    continue
                heading = re.match(r"^#{1,3}\s+([^\n]+)", text)
                sections.append({"text": text, "source_location":
                                 f"section:{heading.group(1).strip() if heading else index}"})
    if not sections:
        raise ValueError("no extractable text")
    return sections


def _metadata(path: Path) -> dict:
    sidecar = path.with_name(path.name + ".meta.json")
    data = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    if not isinstance(data, dict):
        raise ValueError("metadata_must_be_object")
    path_token = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
    return {
        "doc_id": str(data.get("doc_id") or f"{path.stem}-{path_token}"),
        "topic": str(data.get("topic") or "unknown"),
        "version_date": str(data.get("version_date") or "unknown"),
        "scope": str(data.get("scope") or "unknown"),
    }


def build_chunks(path: str | Path, parent_size: int = 1200,
                 child_size: int = 320, overlap: int = 40) -> tuple[list[dict], list[dict]]:
    path = Path(path)
    if not (0 <= overlap < child_size <= parent_size):
        raise ValueError("invalid_chunk_sizes")
    metadata = _metadata(path)
    metadata["source_file"] = path.name
    metadata["file_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=parent_size, chunk_overlap=0, separators=["\n\n", "\n", "。", " ", ""])
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=child_size, chunk_overlap=overlap, separators=["\n\n", "\n", "。", " ", ""])
    parents, children = [], []
    for section in extract_source(path):
        for part in parent_splitter.split_text(section["text"]):
            parent_id = f"P{len(parents) + 1:04d}"
            parent = {**metadata, "snippet_id": parent_id,
                      "source_location": section["source_location"], "text": part}
            parents.append(parent)
            for child_index, text in enumerate(child_splitter.split_text(part), start=1):
                children.append({**metadata, "parent_id": parent_id,
                                 "child_id": f"{parent_id}-C{child_index:04d}",
                                 "source_location": section["source_location"], "text": text})
    return parents, children
