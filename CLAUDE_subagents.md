# Data-Oracle — Subagents

Main agent delegates to specialized subagents to preserve context and reduce cost.

## Delegation Pattern

1. Distribute work to subagents (parallel where possible)
2. Subagents return short summaries + verification commands
3. Main reviews + analyzes results
4. If uncertain → main reads files directly
5. Main writes retrospective at end of session

## Available Subagents

### context-finder
**Model**: Haiku (cheap)
**Purpose**: Search oracle-v2, ψ/, git history for context before starting a task
**When**: "Has this been done before?" / "What patterns exist around X?"
**Pattern**: `oracle_search → summarize candidates → return top 3`

### pipeline-worker
**Model**: Sonnet (balanced)
**Purpose**: Execute ETL pipeline steps — extract, transform, load
**When**: Bulk data processing tasks, multi-step pipeline execution

### validator
**Model**: Haiku (cheap)
**Purpose**: Data quality checks — row counts, schema validation, dedup verification
**When**: After every pipeline run — verify data integrity

### extractor
**Model**: Sonnet (balanced)
**Purpose**: PDF text extraction, web scraping, structured data parsing
**When**: New data source ingestion — parse unstructured data into schema

### security-scanner
**Model**: Haiku (cheap)
**Purpose**: Detect secrets and PII before commits
**When**: Before every `git commit` — scan staged files for credentials and sensitive data

### oracle-keeper
**Purpose**: Maintain Oracle philosophy alignment
**When**: Decisions that feel like they might violate the 5 Principles

---

## Cost Tiers

| Tier | Model | Use For |
|------|-------|---------|
| Cheap | Haiku | Gathering, searching, validation, security scans |
| Balanced | Sonnet | Pipeline execution, extraction, transformation |
| Expensive | Opus | Architecture decisions, complex data modeling |
