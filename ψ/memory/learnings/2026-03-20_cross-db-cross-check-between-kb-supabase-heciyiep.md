---
title: Cross-DB cross-check between KB Supabase (heciyiepgxqtbphepalf) and FA Tools Sup
tags: [cross-check, supabase, fa-tools, kb, data-quality, two-db-pattern]
created: 2026-03-20
source: rrr: Data-Oracle Day 7 mega
project: github.com/bankcurfew/data-oracle
---

# Cross-DB cross-check between KB Supabase (heciyiepgxqtbphepalf) and FA Tools Sup

Cross-DB cross-check between KB Supabase (heciyiepgxqtbphepalf) and FA Tools Supabase (rugcuukelivcferjjzek) reveals hidden mismatches. Found: Vitality max 20% in DB vs 25% in KB; product_benefits amount < 1 = copayment not SA multiplier; CFC death benefit amount=1 displays ฿1 not SA. Single-repo analysis misses these — must query both DBs. Data engineers catch data bugs that code gracefully masks with fallbacks.

---
*Added via Oracle Learn*
