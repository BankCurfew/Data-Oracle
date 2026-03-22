---
title: First Session Pipeline Patterns: 1) uv solves constrained Python environments — 
tags: [python-env, parallel-agents, dependency-pinning, schema-first, ml]
created: 2026-03-19
source: Data-Oracle first session 2026-03-16
project: github.com/bankcurfew/data-oracle
---

# First Session Pipeline Patterns: 1) uv solves constrained Python environments — 

First Session Pipeline Patterns: 1) uv solves constrained Python environments — no pip, no sudo, no venv needed. 2) Pin ML dependencies aggressively — FlagEmbedding 1.3.5 + transformers 5.3.0 = broken import. Fix: FlagEmbedding==1.2.11 + transformers<4.51. 3) Pre-study integration points before writing code — reading Dev's JSON format + setup.sql meant code worked first attempt. Pattern: schema → sample data → code. 4) Parallel agents for multi-source research — 3 agents, 3 repos, 2 min vs 10+ min sequential.

---
*Added via Oracle Learn*
