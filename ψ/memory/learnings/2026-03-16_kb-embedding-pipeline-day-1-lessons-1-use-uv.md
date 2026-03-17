---
title: KB Embedding Pipeline — Day 1 lessons:
tags: [bge-m3, embedding, supabase, kb-pipeline, data-engineering, uv]
created: 2026-03-16
source: rrr: Data-Oracle
project: github.com/bankcurfew/data-oracle
---

# KB Embedding Pipeline — Day 1 lessons:

KB Embedding Pipeline — Day 1 lessons:
1. Use `uv run python` as runtime (no system python/pip available)
2. Supabase env lives in Dev-Oracle .env (SUPABASE_URL + SUPABASE_SERVICE_KEY)
3. Two embedding scripts: embed-chunks.py (bulk from JSON files), embed-missing.py (patch NULL embeddings from DB)
4. Parallel BGE-M3 embedding is safe — 5 concurrent processes, no conflicts, 0.3-0.6 chunks/sec each
5. Special chars in filenames ([, ], #, ', Thai) cause Supabase Storage upload failures
6. Always audit Storage URLs after bulk embedding — delivery path must be verified, not just embeddings

---
*Added via Oracle Learn*
