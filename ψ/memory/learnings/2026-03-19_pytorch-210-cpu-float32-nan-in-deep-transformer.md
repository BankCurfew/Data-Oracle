---
title: PyTorch 2.10 CPU Float32 → NaN in Deep Transformers: BGE-M3 (XLM-RoBERTa, 24 lay
tags: [pytorch, embedding, bge-m3, nan, float64, infrastructure, health-check]
created: 2026-03-19
source: BGE-M3 NaN debugging 2026-03-18
project: github.com/bankcurfew/data-oracle
---

# PyTorch 2.10 CPU Float32 → NaN in Deep Transformers: BGE-M3 (XLM-RoBERTa, 24 lay

PyTorch 2.10 CPU Float32 → NaN in Deep Transformers: BGE-M3 (XLM-RoBERTa, 24 layers, 568M params) produces NaN at Layer 13 on CPU with PyTorch 2.10 + float32. Root cause: changed CPU float32 arithmetic causes overflow in deep attention layers. Fix: model.model.double() — uses float64, ~2x memory but same latency. Critical lesson: embedding service health check must validate OUTPUT (non-NaN vectors), not just service STATUS. tolist() converts NaN → null in JSON, making corrupt data look like missing data.

---
*Added via Oracle Learn*
