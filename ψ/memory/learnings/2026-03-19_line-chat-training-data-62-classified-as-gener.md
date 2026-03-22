---
title: LINE chat training data — 62% classified as "general" needs product matching. Si
tags: [training-data, topic-classification, line-chat, jarvis-bot, data-quality]
created: 2026-03-19
source: Data-Oracle Day 5 2026-03-19
project: github.com/bankcurfew/data-oracle
---

# LINE chat training data — 62% classified as "general" needs product matching. Si

LINE chat training data — 62% classified as "general" needs product matching. Simple keyword topic classification (สุขภาพ→health, ประกันชีวิต→life) leaves most Q&A as "general". Conversations reference products by nickname, plan code, or indirect description. Solution: kb_product_aliases (247 aliases EN+TH) + conversation-level context propagation + embedding similarity. SQL-first data transformation via MCP beats local scripts when Supabase credentials aren't in env vars.

---
*Added via Oracle Learn*
