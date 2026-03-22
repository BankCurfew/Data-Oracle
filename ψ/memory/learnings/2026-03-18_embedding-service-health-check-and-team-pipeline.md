---
date: 2026-03-18
session: Day 4 — Dashboard views + KB gap fill
---

# Lesson: Embedding Service Needs Output-Based Health Check

## Problem
Embedding service /health returned `{"status":"ok"}` but actual embeddings were all `None` (1024 NaN values serialized as null). Process had been running since 01:58 without the float64 fix being loaded.

## Solution
Restart the service. But the real fix is: health check should test actual embedding output, not just endpoint availability.

## Rule
- Always test actual output after service restart
- Consider adding a cron that embeds a test sentence and checks for NaN/None
- Long-running ML services may need periodic restarts or model reload mechanisms

---

# Lesson: Cross-Team Content Pipeline Works

## Pattern
Data audit (find gaps) → Writer (create content) → DocCon (verify accuracy) → Editor (review copy) → Data (ingest + embed)

## Result
10 CRITICAL gap entries + 6 pre-existing conditions = 16 entries ingested in one session. Zero errors, zero rework.

## Rule
- Trust the pipeline — don't skip DocCon/Editor review
- Have ingest script ready before content arrives (parallel preparation)
- Commit scripts immediately after creation, not at end of session
