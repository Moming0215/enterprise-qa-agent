"""Small deterministic document store used as the agent's business tools."""

import json
from pathlib import Path


DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / "data" / "documents.json"

ALIASES = {
    "reimbursement_deadline": ("报销", "费用", "发票"),
    "remote_work": ("远程", "在家办公", "居家办公"),
    "export_subtitles": ("字幕", "导出", "视频文件"),
}


class KnowledgeBase:
    def __init__(self, corpus_path: str | Path = DEFAULT_CORPUS):
        self.documents = json.loads(Path(corpus_path).read_text(encoding="utf-8"))

    def search_documents(self, query: str) -> list[dict]:
        query = query.strip().lower()
        topics = {
            topic for topic, aliases in ALIASES.items()
            if any(alias.lower() in query for alias in aliases)
        }
        return [
            {"doc_id": doc["doc_id"], "title": doc["title"],
             "version_date": doc["version_date"], "scope": doc["scope"],
             "snippet_id": snippet["snippet_id"], "topic": doc["topic"]}
            for doc in self.documents if doc["topic"] in topics
            for snippet in doc["snippets"]
        ]

    def read_snippet(self, doc_id: str, snippet_id: str) -> dict:
        for doc in self.documents:
            if doc["doc_id"] == doc_id:
                for snippet in doc["snippets"]:
                    if snippet["snippet_id"] == snippet_id:
                        return {"ok": True, "doc_id": doc_id,
                                "snippet_id": snippet_id, "text": snippet["text"],
                                "title": doc["title"], "version_date": doc["version_date"],
                                "scope": doc["scope"], "topic": doc["topic"]}
        return {"ok": False, "error": "snippet_not_found",
                "doc_id": doc_id, "snippet_id": snippet_id}
