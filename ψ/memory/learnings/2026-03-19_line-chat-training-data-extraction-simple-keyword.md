---
title: LINE chat training data extraction: simple keyword topic classification leaves 6
tags: [["training-data", "topic-classification", "line-chat", "jarvis-bot", "data-quality", "sql-transformation"]]
created: 2026-03-19
source: rrr: Data-Oracle Day 5
project: github.com/bankcurfew/data-oracle
---

# LINE chat training data extraction: simple keyword topic classification leaves 6

LINE chat training data extraction: simple keyword topic classification leaves 62% as 'general'. Need product alias matching from kb_product_aliases (247 aliases) + conversation-level context propagation + embedding similarity for ambiguous cases. Also: SQL-first data transformation via MCP beats local scripts when Supabase credentials aren't in env vars.

---
*Added via Oracle Learn*
