# Lessons: First Day KB Embedding Pipeline

**Date**: 2026-03-16
**Context**: First session as Data-Oracle, full KB embedding pipeline execution

## 1. uv is the runtime

System has no `python`, `pip`, or `pip3`. Use `uv run python` for scripts with dependencies.
This applies to all scripts in this repo that need external packages (FlagEmbedding, etc.)

## 2. Supabase env lives in Dev-Oracle

```bash
set -a && source ~/repos/github.com/BankCurfew/Dev-Oracle/.env && set +a
```

Required vars: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
Project ID: `heciyiepgxqtbphepalf`

## 3. Parallel background embedding is safe

BGE-M3 model loads independently per process (~12-25s each).
5 parallel jobs ran without conflict — each writes to different source partition in kb_chunks.
Total throughput: 0.3-0.6 chunks/sec per process on CPU.

## 4. Two embedding scripts for two patterns

- `scripts/embed-chunks.py` — reads extracted JSON files from Dev-Oracle, upserts to Supabase
- `scripts/embed-missing.py` — fetches NULL-embedding rows from Supabase, embeds in place

Use embed-chunks.py for bulk source ingestion, embed-missing.py for admin-inserted data.

## 5. Special chars kill Storage uploads

Filenames with `[`, `]`, `#`, `'`, Thai characters fail Supabase Storage upload.
Found 18 files affected across brand, forms, products, regulations.
Always URL-encode or sanitize filenames before uploading.

## 6. Always audit after bulk ops

After embedding 2,183 chunks, the storage URL audit revealed 18 missing files.
Data pipeline = embed is only half the job; the delivery path (Storage → bot → customer) must also be verified.
