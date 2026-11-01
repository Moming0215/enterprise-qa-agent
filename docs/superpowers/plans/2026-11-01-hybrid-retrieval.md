# Hybrid Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PDF/Markdown ingestion, parent-child chunking, local Qdrant dense+sparse hybrid retrieval, and measured retrieval evaluation to the enterprise QA Agent.

**Architecture:** New ingestion/index modules create a source-preserving local index. A new KnowledgeBase implementation exposes the existing `search_documents/read_snippet` interface, so the LangGraph loop and citation guard stay intact. CLI selects JSON or indexed mode explicitly.

**Tech Stack:** Python 3.12, pypdf, langchain-text-splitters, FastEmbed, Qdrant local, jieba, LangGraph, pytest.

**Spec:** `docs/superpowers/specs/2026-11-01-hybrid-retrieval-design.md`

## Global Constraints

- Keep current JSON mode and all existing tests operational.
- Do not commit secrets, downloaded model weights, or Qdrant files.
- Returned citations must resolve to exact extracted source text.
- Conflicting same-topic candidates must survive Top-k truncation.

## Review Focus

- Empty/scanned PDF must be reported as not indexed, not silently treated as no policy.
- Two files sharing a basename must not overwrite each other.
- Re-indexing updated source must not leave stale chunks.
- Model/index unavailable must return explicit incomplete or setup error.
- Retrieval metric denominator must come from a checked-in labeled dataset.

---

### Task 1: Ingestion and parent-child chunks

**Files:** `src/ingestion.py`, `tests/test_ingestion.py`, sample PDF/Markdown/metadata under `data/source_docs/`.

- [ ] Write failing tests for PDF/MD extraction, metadata, source location, chunk bounds, empty/corrupt files.
- [ ] Run focused tests to confirm RED.
- [ ] Implement parsers and hierarchical chunker with stable IDs.
- [ ] Run focused tests to confirm GREEN.

### Task 2: Hybrid index and retrieval adapter

**Files:** `src/hybrid_knowledge.py`, `tests/test_hybrid_knowledge.py`, `pyproject.toml`, `requirements.lock`.

- [ ] Write failing tests for local index build/load, hybrid search, parent read, conflict expansion, replacement rebuild.
- [ ] Run focused tests to confirm RED.
- [ ] Implement FastEmbed + Qdrant index and existing tool interface.
- [ ] Run focused tests and full suite to confirm GREEN.

### Task 3: CLI integration, evaluation and real traces

**Files:** `src/agent.py`, `src/cli.py`, `src/ingest_cli.py`, `src/evaluate_retrieval.py`, `tests/test_index_cli.py`, `data/eval_queries.json`, `examples/hybrid/`, `README.md`, `docs/03-evaluation.md`, `docs/04-ai-usage.md`.

- [ ] Write failing tests for indexed CLI, metric calculation and statuses.
- [ ] Run focused tests to confirm RED.
- [ ] Wire indexed backend into Agent and CLI; add ingestion and evaluation commands.
- [ ] Run full suite and online DeepSeek scenarios; save actual outputs, metrics and failure notes.
- [ ] Check staged files for secrets and source attribution; commit only after verification.
