# Data-Oracle — Lessons Learned

> Patterns discovered from real operations. Updated via /rrr sessions.
> Format: `YYYY-MM-DD — [pattern title]`

---

## Architecture Patterns

### 2026-03-16 — oracle-v2 Identity via `origin` param
Always pass `"origin": "Data"` when calling `oracle_learn`. This tracks which oracle contributed which knowledge in feed.log.

### 2026-03-16 — Inherited from Dev: AIA KB structure
AIA Knowledge Base uses phase-based ingestion (Phase 1-4). PDF files stored in Supabase Storage (not git). Manifests track what's been ingested. Ask Dev for full handoff context.

---

## Anti-Patterns

### NEVER: Commit binary files to git
PDFs, images, and large files go to Supabase Storage. Git tracks manifests and metadata only.

### NEVER: Direct SQLite queries
Always use MCP tools (`oracle_search`, `oracle_learn`, etc.) — never query oracle's SQLite directly.

### NEVER: Force push
`git push --force` violates "Nothing is Deleted". Use feature branches and PRs.

### NEVER: Ingest without validation
Every pipeline must validate at boundary — schema check, dedup, row count verification.

---

*This file grows via /rrr. Add patterns when they emerge from real sessions.*
