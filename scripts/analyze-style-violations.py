#!/usr/bin/env python3
"""Analyze v3.1 training data for style guide violations."""
import json

with open("data/training/jarvis_finetune_v3.1_round7_2026-03-20.jsonl") as f:
    examples = [json.loads(l) for l in f]

total = 0
violations = {"long_200": 0, "long_300": 0, "bullet": 0, "newline_heavy": 0, "markdown": 0, "formal": 0, "multi_kha": 0}
long_examples = []

for ex in examples:
    for m in ex["messages"]:
        if m["role"] != "assistant":
            continue
        text = m["content"]
        total += 1

        if len(text) > 300:
            violations["long_300"] += 1
        if len(text) > 200:
            violations["long_200"] += 1
            long_examples.append(text[:100])
        if any(c in text for c in ["- ", "• "]):
            if text.count("- ") >= 2 or "• " in text:
                violations["bullet"] += 1
        if text.count("\n") >= 3:
            violations["newline_heavy"] += 1
        if "**" in text or "##" in text:
            violations["markdown"] += 1
        formal_phrases = ["ขอแจ้งให้ทราบ", "สรุปข้อมูลดังนี้", "หากท่าน", "ท่านลูกค้า", "ยินดีให้บริการ"]
        if any(f in text for f in formal_phrases):
            violations["formal"] += 1
        if text.count("ค่ะ") >= 4:
            violations["multi_kha"] += 1

print(f"Total assistant messages: {total}")
print(f"Total examples: {len(examples)}")
print()
for k, v in violations.items():
    pct = v / total * 100 if total > 0 else 0
    print(f"  {k}: {v} ({pct:.1f}%)")
print()
print(f"Sample long messages (>200 chars):")
for ex in long_examples[:5]:
    print(f"  [{len(ex)}] {ex}...")
