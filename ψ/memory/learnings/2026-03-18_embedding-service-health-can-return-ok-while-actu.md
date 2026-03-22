---
title: Embedding service /health can return OK while actual embeddings are all None/NaN
tags: [embedding, health-check, NaN, BGE-M3, reliability]
created: 2026-03-18
source: rrr: Data-Oracle Day 4
project: github.com/bankcurfew/data-oracle
---

# Embedding service /health can return OK while actual embeddings are all None/NaN

Embedding service /health can return OK while actual embeddings are all None/NaN. Long-running ML services need output-based health checks, not just endpoint availability. Always test actual embedding output after restart. Consider cron that embeds test sentence and alerts on NaN.

---
*Added via Oracle Learn*
