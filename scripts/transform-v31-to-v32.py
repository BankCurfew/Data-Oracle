#!/usr/bin/env python3
"""
Transform v3.1 training data → v3.2 (style-guide compliant)

Rules from jarvis_style_guide_v1.md:
1. SHORT — target 50-80 chars, max 200. If >200, split into multiple messages
2. NO LIST — flatten bullet points into continuous text
3. NO NEWLINES — write continuous, no \n breaks (except multi-message split)
4. NO MARKDOWN — remove **, ##, ```, etc.
5. CASUAL — remove formal language, vary ค่ะ/คะ/นะคะ
6. SPLIT — long messages → 2-3 short messages separated by \n
"""
import json
import re
import sys
from pathlib import Path

INPUT = Path("data/training/jarvis_finetune_v3.1_round7_2026-03-20.jsonl")
OUTPUT = Path("data/training/jarvis_finetune_v3.2_style_2026-03-22.jsonl")

def remove_markdown(text: str) -> str:
    """Strip markdown formatting."""
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)        # *italic*
    text = re.sub(r'`([^`]+)`', r'\1', text)          # `code`
    text = re.sub(r'#{1,6}\s+', '', text)              # ## heading
    text = re.sub(r'```[\s\S]*?```', '', text)         # ```code block```
    return text

def flatten_bullets(text: str) -> str:
    """Convert bullet/numbered lists to continuous text."""
    # Replace bullet lines with comma-separated
    lines = text.split('\n')
    result = []
    bullet_buffer = []

    for line in lines:
        stripped = line.strip()
        is_bullet = bool(re.match(r'^[-•]\s+', stripped)) or bool(re.match(r'^\d+\.\s+', stripped))

        if is_bullet:
            clean = re.sub(r'^[-•]\s+', '', stripped)
            clean = re.sub(r'^\d+\.\s+', '', clean)
            bullet_buffer.append(clean.strip())
        else:
            if bullet_buffer:
                result.append(', '.join(bullet_buffer))
                bullet_buffer = []
            if stripped:
                result.append(stripped)

    if bullet_buffer:
        result.append(', '.join(bullet_buffer))

    return ' '.join(result)

def remove_formal(text: str) -> str:
    """Replace formal/bot-like phrases with casual alternatives."""
    replacements = [
        ("ขอแจ้งให้ทราบว่า", ""),
        ("สรุปข้อมูลดังนี้:", ""),
        ("สรุปข้อมูลดังนี้", ""),
        ("หากท่านมีข้อสงสัยเพิ่มเติม", "สงสัยอะไรถามได้เลยนะคะ"),
        ("ท่านลูกค้า", "คุณลูกค้า"),
        ("หากท่าน", "ถ้า"),
        ("ยินดีให้บริการค่ะ", ""),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text.strip()

def reduce_kha(text: str) -> str:
    """Reduce excessive ค่ะ repetition (keep max 2 per message)."""
    count = text.count("ค่ะ")
    if count <= 2:
        return text

    # Keep first and last ค่ะ, replace middle ones with คะ/นะคะ alternating
    parts = text.split("ค่ะ")
    if len(parts) <= 3:
        return text

    result = []
    for i, part in enumerate(parts[:-1]):
        result.append(part)
        if i == 0 or i == len(parts) - 2:
            result.append("ค่ะ")
        elif i % 2 == 1:
            result.append("คะ")
        else:
            result.append("นะคะ")
    result.append(parts[-1])
    return "".join(result)

def condense_newlines(text: str) -> str:
    """Remove excessive newlines, keep text continuous."""
    # Replace multiple newlines with space
    text = re.sub(r'\n{2,}', ' ', text)
    # Replace single newlines (not multi-message splits) with space
    # But preserve intentional message splits (short line + newline + short line)
    lines = text.split('\n')
    if len(lines) <= 2:
        return text

    # If lines are all short (<100 chars), they might be multi-message — keep
    if all(len(l.strip()) < 120 for l in lines if l.strip()):
        return text

    # Otherwise condense
    return ' '.join(l.strip() for l in lines if l.strip())

def split_long_message(text: str) -> str:
    """Split messages >200 chars into 2-3 shorter messages."""
    if len(text) <= 200:
        return text

    # Try to split at sentence boundaries
    # Thai sentence enders: ค่ะ คะ ครับ นะคะ นะครับ จ้า
    boundaries = list(re.finditer(r'(ค่ะ|คะ|ครับ|นะคะ|นะครับ|จ้า)\s+', text))

    if not boundaries:
        # Try splitting at commas, periods, or space near 150 chars
        if len(text) > 200:
            # Try comma/period split first
            for sep in [', ', ' / ', '。', '. ']:
                idx = text.rfind(sep, 80, 180)
                if idx > 0:
                    return text[:idx + len(sep)].strip() + '\n' + text[idx + len(sep):].strip()
            # Fallback: split at space
            split_at = text.rfind(' ', 80, 180)
            if split_at > 0:
                return text[:split_at].strip() + '\n' + text[split_at:].strip()
            # Last resort: hard split at 180
            return text[:180].strip() + '\n' + text[180:].strip()
        return text

    # Find best split point near middle
    mid = len(text) // 2
    best = min(boundaries, key=lambda m: abs(m.end() - mid))

    part1 = text[:best.end()].strip()
    part2 = text[best.end():].strip()

    # If part2 is still >200, try splitting again
    if len(part2) > 200:
        part2 = split_long_message(part2)

    return part1 + '\n' + part2

def transform_message(text: str) -> str:
    """Apply all style transformations."""
    text = remove_markdown(text)
    text = flatten_bullets(text)
    text = remove_formal(text)
    text = condense_newlines(text)
    text = reduce_kha(text)
    text = split_long_message(text)

    # Final cleanup
    text = re.sub(r'\s{2,}', ' ', text)  # double spaces
    text = text.strip()

    return text

def main():
    with open(INPUT) as f:
        examples = [json.loads(l) for l in f]

    transformed = []
    stats = {"total": 0, "modified": 0, "split": 0, "dropped": 0}

    for ex in examples:
        new_messages = []
        modified = False

        for m in ex["messages"]:
            if m["role"] != "assistant":
                new_messages.append(m)
                continue

            stats["total"] += 1
            original = m["content"]
            new_text = transform_message(original)

            if new_text != original:
                modified = True

            if '\n' in new_text and '\n' not in original:
                stats["split"] += 1

            # Skip empty results
            if not new_text or len(new_text) < 5:
                stats["dropped"] += 1
                new_messages.append(m)  # keep original if transform failed
                continue

            new_messages.append({"role": "assistant", "content": new_text})

        if modified:
            stats["modified"] += 1

        transformed.append({"messages": new_messages})

    # Write output
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for ex in transformed:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Input:  {INPUT} ({len(examples)} examples)")
    print(f"Output: {OUTPUT} ({len(transformed)} examples)")
    print(f"\nStats:")
    print(f"  Total assistant msgs: {stats['total']}")
    print(f"  Modified:             {stats['modified']}")
    print(f"  Split into multi-msg: {stats['split']}")
    print(f"  Dropped (empty):      {stats['dropped']}")

    # Verify output quality
    print(f"\n--- Output Quality Check ---")
    with open(OUTPUT) as f:
        out_examples = [json.loads(l) for l in f]

    v = {"long_200": 0, "bullet": 0, "newline_heavy": 0, "markdown": 0, "formal": 0}
    total_out = 0
    for ex in out_examples:
        for m in ex["messages"]:
            if m["role"] != "assistant":
                continue
            text = m["content"]
            total_out += 1
            # Check each line of multi-message (split by \n)
            for line in text.split('\n'):
                if len(line) > 200:
                    v["long_200"] += 1
                    break
            if text.count("- ") >= 2 or "• " in text:
                v["bullet"] += 1
            if "**" in text or "##" in text:
                v["markdown"] += 1
            formal_phrases = ["ขอแจ้งให้ทราบ", "สรุปข้อมูลดังนี้", "หากท่าน", "ท่านลูกค้า"]
            if any(f in text for f in formal_phrases):
                v["formal"] += 1

    print(f"  Total msgs: {total_out}")
    for k, val in v.items():
        pct = val / total_out * 100 if total_out > 0 else 0
        print(f"  {k}: {val} ({pct:.1f}%) {'✅' if pct < 5 else '⚠️'}")

if __name__ == "__main__":
    main()
