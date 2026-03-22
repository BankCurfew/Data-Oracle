---
title: Oracle-v2 vector architecture uses LanceDB + Ollama, NOT ChromaDB (legacy). orac
tags: [lancedb, ollama, oracle-v2, vector, embedding, architecture, infrastructure]
created: 2026-03-19
source: rrr: Data-Oracle Day 6
project: github.com/bankcurfew/data-oracle
---

# Oracle-v2 vector architecture uses LanceDB + Ollama, NOT ChromaDB (legacy). orac

Oracle-v2 vector architecture uses LanceDB + Ollama, NOT ChromaDB (legacy). oracle_learn creates FTS index only — no vector embeddings. Must run `bun src/scripts/index-model.ts bge-m3` separately to generate vector embeddings. Source at Soul-Brews-Studio/oracle-v2. LanceDB data at ~/.oracle/lancedb/. MCP server caches vector connections — must restart after reindex. Also: pg_stat row counts are approximate, always use SELECT count(*) for accuracy.

---
*Added via Oracle Learn*
