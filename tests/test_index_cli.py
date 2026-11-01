import json
import subprocess
import sys
from pathlib import Path

from src.agent import run_agent
from src.hybrid_knowledge import build_index


ROOT = Path(__file__).resolve().parents[1]


def test_agent_uses_indexed_backend_and_keeps_conflict_rule(tmp_path):
    index_dir = tmp_path / "index"
    build_index(ROOT / "data" / "source_docs", index_dir)
    conflict = run_agent({"question": "报销期限多久？"}, mode="mock", index_dir=str(index_dir))
    assert conflict["status"] == "needs_clarification"
    assert {c["doc_id"] for c in conflict["citations"]} == {"D01", "D02"}
    assert all(c["source_file"].endswith(".md") and c["source_location"].startswith("section:")
               for c in conflict["citations"])
    missing = run_agent({"question": "公司食堂几点开门？"}, mode="mock", index_dir=str(index_dir))
    assert missing["status"] == "needs_clarification"
    assert missing["citations"] == []
    capped = run_agent({"question": "报销期限多久？"}, mode="mock", index_dir=str(index_dir), max_steps=1)
    assert capped["status"] == "incomplete" and capped["error"] == "step_limit"


def test_ingest_cli_and_indexed_query(tmp_path):
    index_dir = tmp_path / "index"
    command = [sys.executable, "-m", "src.ingest_cli", "--source", str(ROOT / "data" / "source_docs"),
               "--index", str(index_dir)]
    created = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["indexed_files"] == 4
    queried = subprocess.run([sys.executable, "-m", "src.cli", "--input", "examples/inputs/conflict.json",
                              "--mode", "mock", "--index-dir", str(index_dir)],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert queried.returncode == 0, queried.stderr
    assert json.loads(queried.stdout)["status"] == "needs_clarification"
