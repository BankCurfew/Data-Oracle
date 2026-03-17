# Jarvis KB Database Audit — Gap Report

**Date**: 2026-03-17
**Auditor**: Data-Oracle
**Priority**: 🔴 HIGHEST

## Executive Summary

**CRITICAL GAP: 387 out of 518 product files (74.7%) exist in `kb_files` but have NO embeddings in `kb_chunks`.**

The bot can only answer questions about products that have chunks + embeddings. Files that exist only in `kb_files` are invisible to the search/RAG pipeline.

## Database Overview

### kb_chunks (searchable by bot)

| Source | Documents | Chunks |
|--------|-----------|--------|
| products | 131 | 1,261 |
| forms | 116 | 577 |
| bqm | 37 | 200 |
| bot_summary | 16 | 16 |
| faq | 15 | 15 |
| pdpa | 12 | 66 |
| brand | 7 | 42 |
| regulations | — | 37 |
| news | — | 0 |
| **Total** | **~216** | **2,214** |

### kb_files (catalog only — NOT searchable)

| Source | Files |
|--------|-------|
| products | 518 |
| forms | 137 |
| bqm | 38 |
| news | 607 |
| pdpa | 13 |
| brand | 7 |

## Product Gap Breakdown

| Category | Files in kb_files | Embedded in kb_chunks | GAP |
|----------|------------------|-----------------------|-----|
| investment | 99 | 12 | **87** |
| no-cat | 100 | 19 | **81** |
| pa | 86 | 17 | **69** |
| ci | 75 | 25 | **50** |
| savings | 99 | 49 | **50** |
| health | 42 | 14 | **28** |
| vitality | 13 | 4 | **9** |
| rider | 2 | 2 | 0 |
| commission | 1 | 1 | 0 |
| underwriting | 1 | 1 | 0 |

## Specific "AIA Pay Life" Finding

- `AIA_PayLife_Plus_Brochure.pdf` — in kb_files (savings) but **NOT embedded**
- `AIA_15PayLife_Brochure.pdf` — in kb_files (savings) but **NOT embedded**
- `AIA_20PayLife_Brochure.pdf` — in kb_files (savings) but **NOT embedded**
- `AIA_10_15PayLife_Brochure.pdf` — in kb_files (savings) but **NOT embedded**
- `AIA+Pay+Life+Plus+(Non+Par)_16Feb2023_20230217.pdf` — ✅ embedded (general_product)
- `AIA_PayLifePlus_EN_20240219.pdf` — ✅ embedded (general_product)

**Root cause**: The dedicated Pay Life brochures were never extracted/chunked. Only the Non-Par and EN versions got embedded.

## Top Priority Products Missing (bot cannot answer about these)

### Investment (87 missing) — CRITICAL
- AIA 20PayLink, 20PayLink Prestige
- AIA Elite Income Prestige
- AIA Exclusive Wealth Prestige
- AIA Infinite Gift Prestige, Infinite Wealth Prestige
- AIA Issara Plus, Issara Prestige Plus
- AIA Smart Select, Smart Select Prestige
- AIA Smart Wealth, Smart Wealth Prestige
- AIA Wealth Max, Wealth Max Prestige
- All SalesSheets (EN/TH) for above products

### Savings (50 missing)
- AIA Pay Life brochures (10Pay, 15Pay, 20Pay variants)
- AIA Protection 65 (manual, placemat)
- AIA Legacy Prestige (New) manuals
- AIA Annuity Sure (training, manual)
- AIA Saving Sure (training)
- AIA Senior Happy (training, slide)

### Health (28 missing)
- AIA Health Happy (dedicated brochures)
- AIA Health Happy Kids
- AIA Health Starter
- AIA Infinite Care (new standard)
- AIA HB Extra
- AIA Health Saver
- Teladoc Health brochures

### CI (50 missing)
- AIA CI Plus, CI Plus Gold, CI ProCare
- AIA CI SuperCare, SuperCare Prestige
- AIA Multi Pay CI Plus
- AIA Care for Cancer
- AIA TPD
- All training slides for above

## Root Cause

Day 1 embedding pipeline used `Dev-Oracle/knowledge-base/extracted/{source}/` JSON files. Only 131 products had been extracted to JSON. The remaining 387 files exist as PDFs in Supabase Storage but were never:
1. Downloaded from storage
2. Extracted (PDF → text → JSON)
3. Chunked and embedded

## Recommended Action Plan

1. **Phase 1 — Extract missing 387 PDFs** (download from Supabase Storage → extract text)
2. **Phase 2 — Chunk and embed** (run embed-chunks.py on new extractions)
3. **Phase 3 — Validate** (spot-check search for previously missing products)
4. **Phase 4 — News** (607 news files have 0 chunks — assess priority)

## Pending: AIA Website Cross-Check

Waiting for AIA-Oracle to send the full product list from the AIA website. Once received, will cross-check against both kb_files and kb_chunks to identify products completely missing from our database (not just unembedded).
