---
title: First Session Pipeline Patterns (2026-03-16):
tags: [python-env, uv, dependency-pinning, bge-m3, parallel-agents, schema-first, pipeline]
created: 2026-03-16
source: rrr: Data-Oracle first session
project: github.com/bankcurfew/data-oracle
---

# First Session Pipeline Patterns (2026-03-16):

First Session Pipeline Patterns (2026-03-16):

1. uv solves constrained Python envs — no pip, no sudo, no venv? `curl -LsSf https://astral.sh/uv/install.sh | sh` works without root. Default tool for new machines.

2. Pin ML dependencies aggressively — FlagEmbedding 1.3.5 + transformers 5.3.0 = broken import. Fix: pin FlagEmbedding==1.2.11 + transformers<4.51. Always pin when mixing ML packages.

3. Pre-study integration points before code — read extracted JSON format + Supabase schema before writing embed-chunks.py → code worked first attempt. Pattern: schema → sample data → code.

4. Parallel agents compress multi-source research — 3 agents on 3 repos = 2 min vs 10+ sequential. Use when sources are independent.

---
*Added via Oracle Learn*
