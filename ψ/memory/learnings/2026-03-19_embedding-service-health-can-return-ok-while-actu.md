---
title: Embedding service /health can return OK while actual embeddings are all None/NaN
tags: [embedding, health-check, NaN, BGE-M3, reliability, monitoring]
created: 2026-03-19
source: Data-Oracle Day 4 NaN debugging 2026-03-18
project: github.com/bankcurfew/data-oracle
---

# Embedding service /health can return OK while actual embeddings are all None/NaN

Embedding service /health can return OK while actual embeddings are all None/NaN. Long-running ML services need output-based health checks, not just endpoint availability. Always test actual embedding output after restart. Consider cron that embeds test sentence and alerts on NaN. Process had been running since 01:58 without float64 fix being loaded.

---
*Added via Oracle Learn*
