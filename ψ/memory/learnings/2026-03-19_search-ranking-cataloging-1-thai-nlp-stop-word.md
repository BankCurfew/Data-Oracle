---
title: Search Ranking & Cataloging: 1) Thai NLP stop words — "ประกัน", "คุ้มครอง", "เบี
tags: [search, thai-nlp, ranking, cataloging, stop-words, metadata]
created: 2026-03-19
source: QA-reported search issue fix 2026-03-16
project: github.com/bankcurfew/data-oracle
---

# Search Ranking & Cataloging: 1) Thai NLP stop words — "ประกัน", "คุ้มครอง", "เบี

Search Ranking & Cataloging: 1) Thai NLP stop words — "ประกัน", "คุ้มครอง", "เบี้ย" match almost everything, must be excluded from ILIKE scoring. 2) bot_boost at 1.5x is anti-pattern — combined with common Thai keywords, bot_summary beats specific product chunks. Reduce to 1.0. 3) Category taxonomy: pa, health, ci, investment, savings, vitality, rider, commission, underwriting. Filename pattern matching covers ~80%. 4) kb_files metadata priority: category → file_type → keywords[] → display_name_th.

---
*Added via Oracle Learn*
