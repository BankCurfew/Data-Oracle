# Handoff: Day 5 — Training Data Pipeline + KB Dedup + Embedding Health

**Date**: 2026-03-19 14:18
**Context**: 95%

## What We Did
- **KB Dedup** — 9,139→7,693 chunks (1,446 duplicates removed, mostly products)
- **LINE Chat History** verified — 4,521 msgs / 261 contacts (up from 778 yesterday)
- **Training Data Extraction** — 869 Q&A + 82 sales scripts + 65 objection patterns
- **Fine-Tuning Format** — 748 clean JSONL examples (684 Q&A + 64 objection handling)
- **Embedding Health Check** — `scripts/embed-health-check.py` (output-based, catches NaN bug)
- **SQL View** — `v_training_conversations` for training-worthy conversation filtering
- **3 commits** pushed (b40ce0d, a83dfb6, 132f995)
- **Scraper coordination** — Dev batch 100 verified, messaged QA/Dev/BoB

## Pending
- [ ] QA to verify training data quality (especially 462 "general" category)
- [ ] BotDev to receive JSONL for Jarvis Bot fine-tuning
- [ ] Enrich training data with product names from kb_product_aliases
- [ ] Dev scraper v2 batch run (872 contacts) — waiting QA PASS
- [ ] KB gap: 21 products at zero coverage, 11 minimal
- [ ] 513 product PDFs in storage — some may fill gap products (unmapped)

## Next Session
- [ ] Follow up QA on training data verification
- [ ] Enrich "general" Q&A with product alias matching (462 items)
- [ ] Monitor scraper batch progress if Dev runs 872 contacts
- [ ] Continue KB gap filling — map storage PDFs to gap products
- [ ] Run embed-health-check.py before any embedding batch

## Key Files
- `data/training/jarvis_finetune_2026-03-19.jsonl` — 748 fine-tuning examples
- `data/training/qa_pairs_2026-03-19.json` — 869 raw Q&A pairs
- `scripts/extract-training-data.py` — extraction pipeline
- `scripts/convert-training-format.py` — noise filter + JSONL converter
- `scripts/embed-health-check.py` — embedding output validator

## DB Status
- **KB**: 7,693 chunks (16 sources, post-dedup)
- **Coverage**: 6 well-covered, 28 partial, 11 minimal, 21 gap
- **LINE chat**: 4,521 msgs / 261 contacts / 12 batches
- **Training**: 748 JSONL examples ready
- **Embedding**: HEALTHY (1024-dim, 293ms warm)
- **Views**: 16 SQL views (15 dashboard + 1 training)
- **Supabase project**: heciyiepgxqtbphepalf (AIA Oracle)