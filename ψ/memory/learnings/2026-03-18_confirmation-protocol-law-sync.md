# Confirmation Protocol + THE LAW Sync Pattern

**Date**: 2026-03-18
**Context**: Syncing CLAUDE.md rules with BoB-Oracle's THE LAW
**Tags**: protocol, law, confirmation, team-sync

## Pattern

When แบงค์ orders a THE LAW sync:
1. `git pull` the source oracle repo (BoB-Oracle)
2. Read their CLAUDE.md THE LAW section completely
3. Compare each rule against your own CLAUDE.md
4. Add missing rules, verify existing ones match
5. Commit + push + maw hey bob cc

## Confirmation Protocol (Rule 5)

Every task must close explicitly:
- `maw hey <requester> "done — สรุป: ..."`
- `maw hey bob "cc: done [task]"`
- No "sent and forgot" — track until deliverable confirmed

## Why This Matters

Multi-oracle systems break when tasks fall through cracks. BoB can't track what he can't see. Explicit "done" signals create a reliable audit trail across all 9+ oracles. Without this, tasks silently stall and nobody notices until แบงค์ asks "where's X?"
