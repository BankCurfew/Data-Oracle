---
title: PyTorch 2.10 CPU float32 causes NaN in deep transformers (BGE-M3 layer 13/24). F
tags: [pytorch, embedding, bge-m3, nan, float64, infrastructure, debugging]
created: 2026-03-17
source: rrr: Data-Oracle
project: github.com/bankcurfew/data-oracle
---

# PyTorch 2.10 CPU float32 causes NaN in deep transformers (BGE-M3 layer 13/24). F

PyTorch 2.10 CPU float32 causes NaN in deep transformers (BGE-M3 layer 13/24). Fix: model.double() for float64. Always validate embedding output on startup — health checks that don't verify vector quality are useless. tolist() converts NaN → null in JSON, masking corruption as missing data.

---
*Added via Oracle Learn*
