# Enterprise QA Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI enterprise QA Agent that uses DeepSeek tool calls to retrieve evidence, identify conflicts and gaps, and produce verifiable citations and traces.

**Architecture:** A LangGraph model node and tool node form a bounded loop. Local deterministic tools search and read synthetic documents; a final validator checks the model's structured answer against snippets actually read. A separate Mock model verifies control flow offline.

**Tech Stack:** Python, LangGraph, OpenAI-compatible DeepSeek API, pytest.

**Spec:** `docs/superpowers/specs/2026-11-01-enterprise-qa-design.md`

## Global Constraints

- CLI is the primary interface. All output and trace files are UTF-8 JSON.
- The real key comes from `DEEPSEEK_API_KEY` in an ignored `.env`; never commit it.
- Online traces prove model decisions; Mock traces prove only flow.
- No answer may cite a snippet that was not successfully read, and no quote may differ from the source text.
- On the step limit or tool failure without recovery, return `incomplete`.

## Review Focus

- Empty or malformed question: fail clearly before model invocation.
- Search returns both conflicting documents, regardless of ranking.
- Reworded query and follow-up resolve to the right topic without inventing evidence.
- Invalid model tool arguments or final JSON: return explicit `incomplete`, never a false answer.
- Fault injection is one-shot and records the failure without marking a failed read as evidence.

---

### Task 1: Local corpus and tools

**Files:** `data/documents.json`, `src/knowledge.py`, `tests/test_knowledge.py`, `.gitignore`, `.env.example`, `pyproject.toml`

**Interfaces:** `search_documents(query: str) -> list[dict]`; `read_snippet(doc_id: str, snippet_id: str) -> dict`.

- [ ] Write tests for exact lookup, conflict recall, paraphrase recall, missing record and injected failure.
- [ ] Run focused tests and confirm failure.
- [ ] Add synthetic documents, deterministic retrieval and read tools; add dependencies and ignored `.env`.
- [ ] Run focused tests and confirm pass.
- [ ] Commit when a repository exists.

### Task 2: Model-driven graph and trace

**Files:** `src/agent.py`, `src/model.py`, `src/trace.py`, `tests/test_agent.py`

**Interfaces:** `run_agent(request: dict, mode: str, max_steps: int, fail_tool: str | None = None) -> dict`.

- [ ] Write Mock model tests for two different observations leading to different calls, tool failure and step cap.
- [ ] Run focused tests and confirm failure.
- [ ] Implement LangGraph loop, DeepSeek adapter, trace recording and one-shot fault injection.
- [ ] Run focused tests and confirm pass.
- [ ] Commit when a repository exists.

### Task 3: Citation validator and CLI

**Files:** `src/validation.py`, `src/cli.py`, `tests/test_validation.py`, `tests/test_cli.py`

**Interfaces:** `validate_answer(answer: dict, read_evidence: dict) -> dict`; `python -m src.cli --input <json> --mode online|mock`.

- [ ] Write tests for valid quote, unseen source, altered quote, conflicting answer, malformed input and output.
- [ ] Run focused tests and confirm failure.
- [ ] Implement output schema, evidence guard and CLI errors.
- [ ] Run focused tests and confirm pass.
- [ ] Commit when a repository exists.

### Task 4: Real-model evaluation and documentation

**Files:** `examples/`, `README.md`, `docs/01-requirements.md` through `docs/05-retrospective.md`, `tests/test_scenarios.py`

- [ ] Run six acceptance scenarios online where a local key is available; save at least three actual inputs, outputs and traces, including two distinct model reactions. Mark unavailable online runs honestly.
- [ ] Run source replacement experiment and one-shot failure; inspect citations and traces.
- [ ] Run `python -m pytest -q`; save the actual result in `examples/`.
- [ ] Document setup, version, provenance, AI usage, actual work time, results and limitations.
- [ ] Confirm `.env` and other secrets are absent from tracked files; commit and report final SHA if a GitHub destination is available.
