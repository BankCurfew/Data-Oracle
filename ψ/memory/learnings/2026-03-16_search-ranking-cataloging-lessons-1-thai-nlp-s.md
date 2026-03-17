---
title: Search ranking + cataloging lessons:
tags: [search-ranking, thai-nlp, stop-words, categorization, kb-files, data-quality]
created: 2026-03-16
source: rrr: Data-Oracle
project: github.com/bankcurfew/data-oracle
---

# Search ranking + cataloging lessons:

Search ranking + cataloging lessons:
1. Thai NLP stop words critical — "ประกัน" matches 14/15 bot_summaries, must exclude from ILIKE scoring
2. bot_boost x1.5 is anti-pattern — combined with common keywords creates false positives in every query
3. Category taxonomy (pa/health/ci/investment/savings/vitality) enables search filtering — simple but high impact
4. Filename pattern matching covers ~80% of file categorization — remaining 20% needs content-based classification
5. kb_files metadata priority: category > file_type > keywords > display_name_th

---
*Added via Oracle Learn*
