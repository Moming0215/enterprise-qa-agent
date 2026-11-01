"""Local Qdrant hybrid retrieval over source-preserving child chunks.

Architecture follows the MIT-licensed GiovanniPasq/agentic-rag-for-dummies
parent-child and dense+sparse retrieval pattern. This code is an adaptation.
"""

import json
import uuid
from functools import lru_cache
from pathlib import Path

import jieba
from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

from .ingestion import SUPPORTED_SUFFIXES, build_chunks


COLLECTION = "knowledge_children"
DENSE_MODEL = "BAAI/bge-small-zh-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
DENSE_MIN_SCORE = 0.57


@lru_cache(maxsize=1)
def _models():
    return TextEmbedding(model_name=DENSE_MODEL), SparseTextEmbedding(model_name=SPARSE_MODEL)


def _terms(text: str) -> str:
    return " ".join(term.strip() for term in jieba.cut(text) if term.strip())


def _vectors(texts: list[str]) -> tuple[list, list]:
    dense_model, sparse_model = _models()
    dense = list(dense_model.embed(texts))
    sparse = list(sparse_model.embed([_terms(text) for text in texts]))
    return dense, sparse


def build_index(source_dir: str | Path, index_dir: str | Path) -> dict:
    source_dir, index_dir = Path(source_dir), Path(index_dir)
    source_files = sorted(p for p in source_dir.rglob("*") if p.is_file()
                          and not p.name.endswith(".meta.json") and not p.name.startswith("."))
    paths = [p for p in source_files if p.suffix.lower() in SUPPORTED_SUFFIXES]
    if not paths:
        raise ValueError("no_supported_documents")
    parents, children = [], []
    failures = [{"file": p.name, "error": f"unsupported file type: {p.suffix.lower()}"}
                for p in source_files if p.suffix.lower() not in SUPPORTED_SUFFIXES]
    seen_ids = set()
    for path in paths:
        try:
            current_parents, current_children = build_chunks(path)
        except (ValueError, OSError, UnicodeError) as exc:
            failures.append({"file": path.name, "error": str(exc)})
            continue
        doc_id = current_parents[0]["doc_id"]
        if doc_id in seen_ids:
            raise ValueError(f"duplicate_doc_id:{doc_id}")
        seen_ids.add(doc_id)
        for chunk in (*current_parents, *current_children):
            chunk["source_file"] = path.relative_to(source_dir).as_posix()
        parents.extend(current_parents)
        children.extend(current_children)
    if not children:
        raise ValueError("no_extractable_documents")
    index_dir.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(index_dir / "qdrant"))
    try:
        if client.collection_exists(COLLECTION):
            client.delete_collection(COLLECTION)
        dense_vectors, sparse_vectors = _vectors([child["text"] for child in children])
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={"dense": models.VectorParams(size=len(dense_vectors[0]), distance=models.Distance.COSINE)},
            sparse_vectors_config={"sparse": models.SparseVectorParams()},
        )
        points = []
        for child, dense, sparse in zip(children, dense_vectors, sparse_vectors):
            key = f"{child['doc_id']}/{child['child_id']}/{child['file_hash']}"
            points.append(models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, key)),
                vector={"dense": dense.tolist(), "sparse": models.SparseVector(
                    indices=[int(value) for value in sparse.indices],
                    values=[float(value) for value in sparse.values])},
                payload={field: value for field, value in child.items() if field != "text"},
            ))
        client.upsert(COLLECTION, points=points, wait=True)
    finally:
        client.close()
    (index_dir / "parents.json").write_text(json.dumps(parents, ensure_ascii=False, indent=2), encoding="utf-8")
    (index_dir / "manifest.json").write_text(json.dumps({"indexed_files": len(seen_ids),
        "parent_count": len(parents), "child_count": len(children), "failures": failures,
        "dense_model": DENSE_MODEL, "sparse_model": SPARSE_MODEL}, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))


class HybridKnowledgeBase:
    def __init__(self, index_dir: str | Path):
        index_dir = Path(index_dir)
        if not (index_dir / "manifest.json").exists():
            raise ValueError("index_not_built")
        parents = json.loads((index_dir / "parents.json").read_text(encoding="utf-8"))
        self.parents = {(parent["doc_id"], parent["snippet_id"]): parent for parent in parents}
        self.client = QdrantClient(path=str(index_dir / "qdrant"))

    def close(self) -> None:
        self.client.close()

    def search_documents(self, query: str, limit: int = 5) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            return []
        dense, sparse = _vectors([query])
        fetch_limit = max(limit, 10)
        dense_hits = self.client.query_points(
            COLLECTION, query=dense[0].tolist(), using="dense", limit=fetch_limit).points
        sparse_hits = []
        if len(sparse[0].indices):
            sparse_hits = self.client.query_points(
                COLLECTION, query=models.SparseVector(
                    indices=[int(value) for value in sparse[0].indices],
                    values=[float(value) for value in sparse[0].values]),
                using="sparse", limit=fetch_limit).points
        scores = {}
        for rank, point in enumerate(dense_hits, start=1):
            if point.score >= DENSE_MIN_SCORE:
                key = (point.payload["doc_id"], point.payload["parent_id"])
                scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
        for rank, point in enumerate(sparse_hits, start=1):
            key = (point.payload["doc_id"], point.payload["parent_id"])
            scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
        keys = [key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]]
        retrieved_keys = set(keys)
        topics = {self.parents[key]["topic"] for key in keys if self.parents[key]["topic"] != "unknown"}
        for key, parent in self.parents.items():
            if parent["topic"] in topics and key not in keys:
                keys.append(key)
        return [{**{field: parent[field] for field in (
            "doc_id", "snippet_id", "topic", "version_date", "scope", "source_file", "source_location")}
            , "retrieval_score": round(scores.get(key, 0.0), 6),
            "expanded_for_conflict": key not in retrieved_keys}
            for key in keys for parent in [self.parents[key]]]

    def read_snippet(self, doc_id: str, snippet_id: str) -> dict:
        parent = self.parents.get((doc_id, snippet_id))
        if parent is None:
            return {"ok": False, "error": "snippet_not_found", "doc_id": doc_id, "snippet_id": snippet_id}
        return {"ok": True, **parent}
