# Data-Oracle — Safety Rules

## Git Safety

| Rule | Why |
|------|-----|
| NEVER `git push --force` | Violates "Nothing is Deleted" |
| NEVER push to `main` directly | Always feature branch + PR |
| NEVER merge PRs yourself | Wait for แบงค์ approval |
| NEVER `git commit --amend` on pushed commits | Breaks multi-agent sync |
| Always use `git -C /path` not `cd && git` | Respects worktree boundaries |

### PR Workflow

```
1. git checkout -b feat/description
2. Make changes
3. git add specific-files  (never git add -A blindly)
4. git commit -m "type: description"
5. git push -u origin feat/description
6. gh pr create
7. WAIT for แบงค์ to review + merge
```

### Forbidden Flags

`--force` `-f` (on destructive ops) `--no-verify` `--amend` (on pushed commits)

---

## File Safety

| Rule | Why |
|------|-----|
| NEVER `rm -rf` without backup | Data loss = trust loss |
| NEVER commit `.env` or credentials | Security |
| Use `.tmp/` for temp files (gitignored) | Clean repo |
| Ask before creating files in repo root | File placement matters |
| NEVER delete knowledge — use `oracle_supersede` | Nothing is Deleted |

### File Placement

| Type | Location |
|------|----------|
| Research / investigation | `ψ/active/` (ephemeral) |
| Session retrospective | `ψ/memory/retrospectives/YYYY-MM/DD/` |
| Discovered pattern | `ψ/memory/learnings/YYYY-MM-DD_name.md` |
| Soul / identity | `ψ/memory/resonance/` |
| Draft / article | `ψ/writing/` |
| Experiment | `ψ/lab/` |
| Temp files | `.tmp/` |

---

## Data Safety — CRITICAL

| Rule | Why |
|------|-----|
| NEVER ingest without schema validation | Garbage in = garbage out |
| NEVER delete source data | Lineage must be traceable |
| NEVER commit PDF/binary files to git | Use Supabase Storage |
| NEVER skip deduplication | Duplicates corrupt downstream |
| NEVER store PII without approval | Privacy compliance |
| NEVER overwrite production tables without backup | Data recovery |
| Always log pipeline runs | Audit trail |
| Always validate row counts after ETL | Catch silent data loss |

### Sensitive Data Checklist

Before committing any data-related file, check:
- [ ] No customer names, IDs, or personal data
- [ ] No API keys, tokens, or credentials
- [ ] No internal URLs or endpoints
- [ ] No PDF/binary files (should be in Supabase Storage)
- [ ] Manifest files don't contain sensitive metadata

---

## Oracle-v2 Safety

| Rule | Why |
|------|-----|
| NEVER query SQLite directly | Use MCP tools only — proper abstraction |
| Always pass `"origin": "Data"` in `oracle_learn` | Identity tracking in feed.log |
| Use `oracle_supersede` not deletion | Append-only architecture |
| NEVER use `ORACLE_READ_ONLY=true` unless testing | Disables write tools |
