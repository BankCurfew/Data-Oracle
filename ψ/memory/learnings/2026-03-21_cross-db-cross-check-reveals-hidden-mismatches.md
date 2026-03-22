---
date: 2026-03-21
type: learning
tags: [cross-check, supabase, fa-tools, kb, data-quality, vitality]
---

# Cross-DB Cross-Check Reveals Hidden Mismatches

When KB data (heciyiepgxqtbphepalf) and app data (rugcuukelivcferjjzek) live in separate Supabase projects, inconsistencies hide in plain sight. Found: Vitality discount max 20% in app DB but KB claims 25%; product_benefits amount<1 = copayment rates that code interprets as SA multipliers; Care For Cancer death benefit stored as amount=1 displays as ฿1.

These bugs don't surface in single-repo analysis — you need to query both DBs and compare. Data engineers catch data bugs that frontend developers' code gracefully masks with fallbacks.
