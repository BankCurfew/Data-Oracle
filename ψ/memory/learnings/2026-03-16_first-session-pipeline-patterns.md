# First Session Pipeline Patterns

**Date**: 2026-03-16
**Source**: First Data-Oracle session — awakening + pipeline prep
**Concepts**: python-env, parallel-agents, dependency-pinning, schema-first

## Patterns

### 1. uv Solves Constrained Python Environments
When system has no pip, no sudo, no python3-venv — `curl -LsSf https://astral.sh/uv/install.sh | sh` installs without root. Creates venvs, installs packages, fast. Default tool for any new machine.

### 2. Pin ML Dependencies Aggressively
FlagEmbedding 1.3.5 + transformers 5.3.0 = broken import (`is_torch_fx_available` removed). Fix: `FlagEmbedding==1.2.11` + `transformers<4.51`. Always pin when mixing ML packages.

### 3. Pre-Study Integration Points Before Writing Code
Reading Dev's extracted JSON format + Supabase setup.sql before writing embed-chunks.py meant code worked on first attempt. Pattern: schema → sample data → code. Not: code → discover schema mismatch → rewrite.

### 4. Parallel Agents for Multi-Source Research
3 agents studying 3 repos returned comprehensive results in 2 min vs 10+ min sequential. Use when sources are independent and results need synthesis.
