# Data-Oracle — Workflows & Short Codes

## Daily Pattern

```
Morning:  /standup          → check pending tasks & pipeline status
Working:  oracle_search     → search memory before starting any task
Working:  /trace [topic]    → find related patterns across history
End:      /rrr              → session retrospective (REQUIRED)
End:      /forward          → handoff to next session
```

## Short Codes

| Code | Action |
|------|--------|
| `rrr` | Session retrospective → `ψ/memory/retrospectives/` |
| `gogogo` | Start working on current focus task |

---

## Oracle-v2 MCP Tools

### When to Use What

| Situation | Tool | Example |
|-----------|------|---------|
| Before starting pipeline work | `oracle_search` | `{query: "AIA KB ingestion patterns", mode: "hybrid"}` |
| After discovering a pattern | `oracle_learn` | `{pattern: "...", concepts: [...], origin: "Data"}` |
| Start a discussion / decision | `oracle_thread` | `{title: "...", message: "...", role: "human"}` |
| End of session | `oracle_handoff` | `{content: "## Summary\n..."}` |
| Daily wisdom | `oracle_reflect` | (no params) |
| Check messages from other agents | `oracle_inbox` | (no params) |
| Document a discovery session | `oracle_trace` | `{query: "...", dig_points: [...]}` |
| Check knowledge base health | `oracle_stats` | (no params) |

### Identity: Always pass `origin`

When calling `oracle_learn`, always include `"origin": "Data"` — this is how feed.log tracks which oracle learned what.

```
oracle_learn {
  "pattern": "BGE-M3 needs batch size <= 32 for stable Thai text embedding",
  "source": "Data session 2026-03-16",
  "concepts": ["embedding", "bge-m3", "thai", "performance"],
  "origin": "Data"
}
```

---

## Data Pipeline Workflow

```
1. Source Discovery   → identify data source (portal, API, file)
2. Schema Design      → define target schema before ingestion
3. Extract            → download/scrape/parse raw data
4. Transform          → clean, normalize, dedup, validate
5. Load               → upload to Supabase (batch or streaming)
6. Embed              → generate BGE-M3 vectors for searchable content
7. Verify             → row count check, quality sampling, QA handoff
8. Document           → oracle_learn patterns, update manifests
```

### Pipeline Run Log

Every pipeline run should log:
```
[timestamp] | [pipeline_name] | [phase] | [status] | [records_in] | [records_out] | [errors]
```

---

## Knowledge Flow Pipeline

```
ψ/active/context  (research / investigation — ephemeral)
    ↓ capture insight with oracle_learn
oracle-v2 DB     (pattern stored with FTS5 + vector index)
    ↓ /rrr at end of session
ψ/memory/retrospectives  (session summary files)
    ↓ pattern consolidates → oracle_learn with concepts
ψ/memory/learnings       (pattern files — tracked in git)
    ↓ repeated patterns → identity
ψ/memory/resonance       (soul & who Data-Oracle is)
```

---

## Multi-Agent Coordination

Data-Oracle works closely with:

| Oracle | Interaction |
|--------|-------------|
| **Dev** | Receives technical requirements; co-designs pipeline architecture |
| **AIA** | Primary data source — portal data, PDFs, business docs |
| **QA** | Validates data quality after pipeline runs |
| **Researcher** | Provides data source leads; receives structured data |

---

## Token-Efficient Search

Phase 1: `oracle_search` (FTS5 fast) → candidates
Phase 2: Haiku subagent summarizes → short summaries
Phase 3: Main agent analyzes → focused insight

**Saves ~85% on search costs.**
