# Video Tool Knowledge Base Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Add an explicitly fictional short-video software enterprise corpus that the existing QA Agent can index and evaluate.

**Architecture:** Store source Markdown and per-file metadata in `data/video_tool_kb/`. Keep the existing ingestion and Agent interfaces. Add labeled queries and saved retrieval/Agent examples.

**Tech Stack:** Markdown, JSON, Python CLI, Qdrant local index, pytest.

**Spec:** `docs/superpowers/specs/2026-11-01-video-tool-kb-design.md`

## Tasks

- [x] Create product, operations, governance, and support documents with stable IDs and source metadata; mark all content synthetic.
- [x] Add labeled positive, conflict, paraphrase, and negative retrieval cases; build index and inspect scores.
- [x] Add tests for ingestion, source citations, conflict handling, and absent information.
- [x] Save actual index manifest, retrieval metrics, and Agent traces; document commands and limitations.
- [ ] Run full suite, scan staged files for secrets, commit and attempt GitHub push.
