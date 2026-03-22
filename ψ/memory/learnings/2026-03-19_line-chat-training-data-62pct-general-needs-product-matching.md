---
date: 2026-03-19
type: learning
tags: [training-data, topic-classification, line-chat, jarvis-bot]
---

# LINE Chat Training Data — 62% "General" Needs Product Matching

## Problem
Simple keyword topic classification (สุขภาพ→health, ประกันชีวิต→life, etc.) leaves 62% of extracted Q&A pairs as "general". Many are actually about specific products but don't contain obvious keywords.

## Root Cause
Conversations often reference products by nickname, plan code, or indirect description rather than category keywords. E.g. "ทุน 5 ล้าน เบี้ยคงที่" = Health Happy UDR but doesn't contain "สุขภาพ".

## Solution
Enrich classification using:
1. `kb_product_aliases` table (247 aliases EN+TH) for product name matching
2. Conversation-level context (if any message mentions health, tag the whole conversation)
3. Embedding-based similarity to product descriptions for ambiguous cases

## Impact
Better topic classification → better training data quality → Jarvis Bot answers more accurately per product category.
