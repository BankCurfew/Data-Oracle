---
title: KB Embedding Pipeline Day 1: 1) uv is the runtime — system has no pip/python3, u
tags: [embedding, bge-m3, supabase, pipeline, uv, storage]
created: 2026-03-19
source: Data-Oracle Day 1 session 2026-03-16
project: github.com/bankcurfew/data-oracle
---

# KB Embedding Pipeline Day 1: 1) uv is the runtime — system has no pip/python3, u

KB Embedding Pipeline Day 1: 1) uv is the runtime — system has no pip/python3, use uv run python. 2) Supabase env lives in Dev-Oracle (.env), project ID: heciyiepgxqtbphepalf. 3) Parallel background embedding is safe — BGE-M3 loads independently per process, 5 parallel jobs ran without conflict. 4) Two embedding scripts: embed-chunks.py for bulk ingestion, embed-missing.py for admin-inserted data. 5) Special chars kill Storage uploads — filenames with [, ], #, Thai chars fail. Always sanitize. 6) Always audit after bulk ops — delivery path must also be verified.

---
*Added via Oracle Learn*
