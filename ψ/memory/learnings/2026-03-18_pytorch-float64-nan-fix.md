# PyTorch 2.10 CPU Float32 → NaN in Deep Transformers

**Date**: 2026-03-18
**Context**: BGE-M3 embedding service returning all-NaN vectors
**Tags**: pytorch, embedding, bge-m3, nan, float64, infrastructure

## Problem

BGE-M3 (XLM-RoBERTa, 24 layers, 568M params) produces NaN outputs on CPU with PyTorch 2.10 + float32.

- Model weights: zero NaN (verified all 567,754,752 params)
- Embedding layer output: valid
- Layer 0-12: valid, max activation ~24
- **Layer 13: NaN detected** — numerical overflow in attention/FFN
- All subsequent layers: NaN propagated

## Root Cause

PyTorch 2.10 changed CPU float32 arithmetic behavior. Deep transformer layers accumulate numerical instability that overflows float32 range. CUDA would handle this differently (hardware FP units), but WSL2 CUDA was also incompatible (no kernel image).

## Fix

```python
# In embedding-service.py, after model load:
if DEVICE == "cpu":
    model.model = model.model.double()  # float64
```

- Memory: ~2x (2.5GB → ~5GB) — acceptable for service
- Speed: ~same latency (~210ms per text)
- Quality: 1024 valid dims, zero NaN

## Detection

The service was "healthy" but broken — health check only verified model was loaded, not that it produced valid output.

**Fix**: Add startup validation — embed a known test string, verify output is non-NaN before serving.

## Lesson

- Always validate embedding *output*, not just service *status*
- Deep transformers (20+ layers) are vulnerable to CPU float32 overflow in newer PyTorch versions
- `tolist()` converts NaN → `null` in JSON, making it look like "no data" rather than "corrupt data"
