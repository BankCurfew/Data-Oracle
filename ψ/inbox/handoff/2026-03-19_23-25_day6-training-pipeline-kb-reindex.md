# Handoff: Day 6 — Training Data Pipeline + KB Reindex

**Date**: 2026-03-19 23:25
**Context**: 95%

## What We Did

### Training Data Pipeline (🔴 priority)
- **Tag normalization** — 6 variant pairs fixed (152 records), 0 variants remaining
- **Dedup** — exact duplicate rows removed from line_chat_history (0 remaining)
- **Conversation labeling** — 66% coverage (6,537/9,905), matched 69 product aliases
- **Pattern extraction** — 386 trainable Q&A pairs from DB + 5 objection + 15 winning responses
- **JSONL v2 export** — `jarvis_finetune_v2_2026-03-19.jsonl` (524 clean examples)
- **New script** — `scripts/export-training-v2.py` (pulls labeled data from Supabase)
- **Notified** QA (thread #10), BotDev (thread #21), cc BoB (thread #6)

### KB Reindex (Ollama embeddings)
- **oracle_learn × 18** — all Data-Oracle learnings + retros + resonance re-indexed
- **bge-m3 indexer** — 312 docs → LanceDB, 0 errors, 180s
- **nomic indexer** — 312 docs → LanceDB, 0 errors, 73s
- **Nomic vector search** — WORKING ✅
- **bge-m3 vector search** — index exists but MCP server needs restart to reconnect

### Other
- Memorized Playwright 2-session limit (กฏเหล็กใหม่)
- Memorized external URLs (dashboard, KG, FA Tools, Jarvis API)
- Pipeline status report: YELLOW (11 missing embeddings in kb_chunks)

## Pending
- [ ] MCP server restart → bge-m3 vector search + Knowledge Graph active
- [ ] 11 kb_chunks missing dense embedding (training-objection-handling 6 + training-sales-scripts 5, IDs 11368-11378)
- [ ] QA verify training data quality (524 examples, especially 300 "general")
- [ ] BotDev feed JSONL for Jarvis Bot fine-tuning
- [ ] Enrich remaining 34% untagged messages with embedding similarity
- [ ] Dev scraper v2 batch (872 contacts) — waiting QA PASS

## Next Session
- [ ] Verify Knowledge Graph working after server restart
- [ ] Fix 11 missing embeddings (need BGE-M3 service or Ollama)
- [ ] Enrich "general" category (300 items) with embedding-based product matching
- [ ] Follow up QA training data verification
- [ ] Monitor scraper batch if Dev starts 872-contact run
- [ ] KB gap: 21 products at zero coverage — map 513 storage PDFs

## Key Files
- `scripts/export-training-v2.py` — v2 training data exporter
- `data/training/jarvis_finetune_v2_2026-03-19.jsonl` — 524 training examples
- `data/training/jarvis_finetune_v2_stats.json` — v2 stats
- `scripts/embed-health-check.py` — embedding output validator
- `ψ/memory/learnings/2026-03-19_lancedb-ollama-oracle-v2-vector-architecture.md` — KB reindex architecture discovery

## DB Status
- **KB**: 7,693 chunks (16 sources, post-dedup)
- **LINE chat**: 9,905 msgs (post-dedup), 66% labeled
- **Training**: 524 JSONL v2 examples ready
- **Oracle KB**: 312 docs, bge-m3 + nomic embeddings in LanceDB
- **Supabase project**: heciyiepgxqtbphepalf (AIA Oracle)
