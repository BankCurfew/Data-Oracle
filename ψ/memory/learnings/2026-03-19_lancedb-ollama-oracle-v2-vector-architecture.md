---
date: 2026-03-19
type: learning
tags: [lancedb, ollama, oracle-v2, vector, embedding, architecture]
---

# Oracle-v2 Vector Architecture: LanceDB + Ollama (not ChromaDB)

## Discovery

oracle-v2 uses two vector backends:
- **Legacy**: ChromaDB (default in factory.ts, uses chroma-mcp Python adapter)
- **Current**: LanceDB + Ollama (used by model-specific indices: bge-m3, nomic, qwen3)

## Key Facts

1. `oracle_learn` creates **FTS index only** — no vector embeddings generated
2. `bun src/scripts/index-model.ts <model>` creates **vector embeddings via Ollama → LanceDB**
3. Source: `~/repos/github.com/Soul-Brews-Studio/oracle-v2/src/`
4. LanceDB data: `~/.oracle/lancedb/`
5. Model presets in `src/vector/factory.ts:getEmbeddingModels()`
6. MCP server caches vector store connections — **must restart after reindex**

## Two-Step Process

```bash
# Step 1: Index to FTS (oracle_learn or bun run index)
oracle_learn({ pattern: "...", concepts: [...] })

# Step 2: Generate vector embeddings
cd ~/repos/github.com/Soul-Brews-Studio/oracle-v2
bun src/scripts/index-model.ts bge-m3   # 312 docs, ~180s
bun src/scripts/index-model.ts nomic    # 312 docs, ~73s
```

## Gotcha

pg_stat_user_tables.n_live_tup is approximate — always use `SELECT count(*)` for accurate row counts. Stale stats caused confusion during dedup (showed 4,521 when actual was 9,868).
