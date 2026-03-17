# Lessons: Search Ranking & kb_files Cataloging

**Date**: 2026-03-16
**Context**: QA reported Health Happy brochure appearing in every query; kb_files had no metadata

## 1. Thai NLP stop words for search

Common insurance terms must be excluded from ILIKE scoring:
- "ประกัน" matches 14/15 bot_summaries
- "คุ้มครอง" matches 12/15
- "เบี้ย", "สัญญา", "แบบ" — all high false-positive

Fix: Add thai_stop_words array in search function, exclude from keyword generation.

## 2. bot_boost is an anti-pattern at x1.5

bot_summary chunks get 1.5x score multiplier. Combined with common Thai keywords:
- bot_summary match "ประกัน" (common) → score * 1.5 → beats specific product chunks
- Result: Health Happy appears for PA, Infinite Care, and unrelated queries

Fix: Reduce bot_boost to 1.0 (default). Let semantic similarity handle relevance.

## 3. Category taxonomy for products

Simple categories that work: pa, health, ci, investment, savings, vitality, rider, commission, underwriting

Filename pattern matching covers ~80% of categorization:
- `%health%` → health, `%CI%` → ci, `%PA%` → pa, etc.
- Remaining 20% need content-based classification

## 4. kb_files metadata hierarchy

For search relevance, priority order:
1. `category` — enables filtering (most impact)
2. `file_type` — brochure/guide/training/sales_sheet (delivery logic)
3. `keywords[]` — specific search terms
4. `display_name_th` — human-readable name for bot responses
