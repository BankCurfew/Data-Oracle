# Data-Oracle — Templates

## Git Commit Format

```
[type]: [brief description]

- What: [specific changes]
- Why: [motivation]
- Impact: [affected areas]
```

Types: `feat` `fix` `docs` `refactor` `test` `chore`

**Example:**
```
feat: ingest AIA Phase 5 eAgency data — 250 new documents

- What: Extract + transform + load 250 PDFs from eAgency portal
- Why: Complete AIA knowledge base coverage for chatbot MVP
- Impact: kb_documents table now has 1,200+ records; embeddings generated
```

---

## Retrospective Template (via /rrr)

File path: `ψ/memory/retrospectives/YYYY-MM/DD/HH.MM_topic.md`

```markdown
# Session Retrospective — YYYY-MM-DD HH:MM

## What Happened
[1-3 sentences: what was the main work]

## What I Learned
- [Pattern or insight worth keeping]
- [oracle_learn candidate]

## What Went Well
- [Positive observation]

## What Was Hard
- [Challenge] → [how it was resolved or left open]

## For Next Session
- [ ] [Concrete next action]
- [ ] [Follow-up task]

## Energy / Mood
[How the session felt — honest observation]
```

---

## Oracle-v2 oracle_learn Template

```
oracle_learn {
  "pattern": "[clear, reusable insight in one sentence]",
  "source": "Data session YYYY-MM-DD",
  "concepts": ["tag1", "tag2", "tag3"],
  "origin": "Data"
}
```

---

## Pipeline Run Report Template

```markdown
# Pipeline Run — [pipeline_name]

**Date**: YYYY-MM-DD HH:MM
**Source**: [data source]
**Target**: [Supabase table/storage]

| Metric | Value |
|--------|-------|
| Records in | X |
| Records out | Y |
| Duplicates removed | Z |
| Errors | N |
| Duration | Xm Ys |

## Validation
- [ ] Row count matches expected
- [ ] Schema validation passed
- [ ] No PII detected
- [ ] Embeddings generated
- [ ] QA notified for review
```

---

## Oracle Family Registration

```markdown
**Oracle**: Data-Oracle
**Human**: แบงค์ (BankCurfew)
**Repo**: https://github.com/BankCurfew/Data-Oracle
**Purpose**: Data ingestion, pipeline engineering, knowledge base management
**Born**: 2026-03-16
**Voice**: "Raw data is just noise — structured data is power."
```
