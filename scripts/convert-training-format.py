#!/usr/bin/env python3
"""
Convert extracted LINE chat training data to fine-tuning JSONL format.

Filters noise, enriches with context, outputs:
- data/training/jarvis_finetune_2026-03-19.jsonl  (OpenAI/Claude format)
- data/training/jarvis_finetune_stats.json         (stats)

Usage:
    python3 scripts/convert-training-format.py
    python3 scripts/convert-training-format.py --dry-run
"""

import json
import os
import re
import sys
from datetime import datetime

INPUT_DIR = "data/training"
OUTPUT_DIR = "data/training"

SYSTEM_PROMPT = """คุณคือ Jarvis Bot — ผู้ช่วยตัวแทนประกันชีวิต AIA (iAgencyAIA) ที่เชี่ยวชาญ
หน้าที่: ตอบคำถามลูกค้าเกี่ยวกับผลิตภัณฑ์ AIA, ช่วยปิดการขาย, จัดการข้อโต้แย้ง, และให้บริการหลังการขาย
สไตล์: สุภาพ เป็นมิตร ใช้ภาษาไทย ตอบตรงประเด็น ให้ข้อมูลถูกต้อง
ห้าม: ให้ข้อมูลเท็จ, สัญญาสิ่งที่ทำไม่ได้, เปิดเผยข้อมูลลูกค้า"""

# Noise patterns to filter out entirely
NOISE_QUESTIONS = [
    r"^Dream Arthit",
    r"^MAY \(",
    r"^ex_jira",
    r"^Front ",
    r"^D\. ",
    r"^A\d{2} V ",
    r"^https?://",
    r"^iAgencyAIA\.com$",
    r"^CL\d+\.",           # Internal contact codes as standalone
    r"^CG\d+\.",
    r"^ขอบคุณ",
    r"^เรียบร้อย",
    r"^รับทราบ",
    r"^ค่ะ$",
    r"^ครับ$",
    r"^โอเค",
    r"^OK",
]

NOISE_ANSWERS = [
    r"^Dream Arthit$",
    r"^MAY \(เลขาคุณดรีม\)$",
    r"^ex_jira$",
    r"^D\.$",
    r"^https?://",
]

# Topic to Thai description
TOPIC_LABELS = {
    "health": "ประกันสุขภาพ",
    "life": "ประกันชีวิต",
    "critical_illness": "โรคร้ายแรง",
    "claims": "เคลม/เบิกประกัน",
    "pricing": "เบี้ยประกัน/ราคา",
    "kids": "ประกันเด็ก",
    "unit_linked": "Unit Linked/กองทุน",
    "general": "ทั่วไป",
}

OBJECTION_TYPE_LABELS = {
    "ราคา": "pricing",
    "งบ": "budget",
    "แพง": "expensive",
    "ยังก่อน": "hesitation",
    "ขอคิดดู": "thinking",
    "ไม่แน่ใจ": "uncertain",
    "เปรียบเทียบ": "comparison",
    "ที่อื่น": "competitor",
    "แตกต่าง": "difference",
    "ทำไม": "why",
    "กลัว": "fear",
    "กังวล": "concern",
    "ยกเลิก": "cancellation",
    "หมดอายุ": "expired",
    "ไม่ได้รับ": "not_received",
    "ค้าง": "pending",
}


def is_noise_question(text):
    for pattern in NOISE_QUESTIONS:
        if re.match(pattern, text.strip()):
            return True
    if len(text.strip()) < 5:
        return True
    return False


def is_noise_answer(text):
    for pattern in NOISE_ANSWERS:
        if re.match(pattern, text.strip()):
            return True
    if len(text.strip()) < 5:
        return True
    return False


def clean_text(text):
    """Clean agent/customer text for training."""
    if not text:
        return None
    # Remove common prefixes
    text = re.sub(r"^D\.\s*", "", text.strip())
    text = re.sub(r"^MAY \(เลขาคุณดรีม\)\s*", "", text.strip())
    text = re.sub(r"^ex_jira\s*", "", text.strip())
    text = re.sub(r"^Front\s+", "", text.strip())
    text = re.sub(r"^Dream Arthit\s*", "", text.strip())
    # Remove iAgencyAIA.com prefix
    text = re.sub(r"^iAgencyAIA\.com\s*", "", text.strip())
    # Remove URLs
    text = re.sub(r"https?://\S+", "[ลิงก์]", text)
    # Remove contact codes at start
    text = re.sub(r"^(CL|CG|A)\d+[\.\s]\S+\s*", "", text.strip())
    text = text.strip()
    return text if len(text) >= 3 else None


def convert_qa_pairs():
    """Convert Q&A pairs to fine-tuning format."""
    path = os.path.join(INPUT_DIR, "qa_pairs_2026-03-19.json")
    with open(path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    results = []
    filtered = {"noise_q": 0, "noise_a": 0, "short": 0, "clean_fail": 0}

    for pair in pairs:
        q = pair.get("question", "")
        a = pair.get("answer", "")
        topic = pair.get("topic", "general")

        # Filter noise
        if is_noise_question(q):
            filtered["noise_q"] += 1
            continue
        if is_noise_answer(a):
            filtered["noise_a"] += 1
            continue

        # Clean
        q_clean = clean_text(q)
        a_clean = clean_text(a)

        if not q_clean or not a_clean:
            filtered["clean_fail"] += 1
            continue

        if len(q_clean) < 8 or len(a_clean) < 8:
            filtered["short"] += 1
            continue

        topic_label = TOPIC_LABELS.get(topic, topic)

        results.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": q_clean},
                {"role": "assistant", "content": a_clean},
            ],
            "metadata": {
                "type": "qa",
                "topic": topic,
                "topic_label": topic_label,
                "source": "line_chat_history",
            },
        })

    return results, filtered


def convert_objection_handling():
    """Convert objection patterns to fine-tuning format with context."""
    # We'll re-extract from Supabase results embedded in the summary
    # For now, use the objection data we have
    path = os.path.join(INPUT_DIR, "training_summary_2026-03-19.json")
    with open(path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # The actual objection data was in the SQL result but not saved separately
    # We'll create training examples from the Q&A pairs that match objection keywords
    path = os.path.join(INPUT_DIR, "qa_pairs_2026-03-19.json")
    with open(path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    objection_keywords = list(OBJECTION_TYPE_LABELS.keys())
    results = []

    for pair in pairs:
        q = pair.get("question", "")
        a = pair.get("answer", "")

        matched = [kw for kw in objection_keywords if kw in q]
        if not matched:
            continue

        q_clean = clean_text(q)
        a_clean = clean_text(a)
        if not q_clean or not a_clean or len(q_clean) < 8 or len(a_clean) < 8:
            continue

        if is_noise_question(q) or is_noise_answer(a):
            continue

        obj_types = [OBJECTION_TYPE_LABELS[kw] for kw in matched]

        system_with_context = (
            SYSTEM_PROMPT + "\n\n"
            "สถานการณ์: ลูกค้ามีข้อกังวล/ข้อโต้แย้ง "
            "ต้องตอบอย่างเข้าใจ ให้ข้อมูลชัดเจน และพยายามแก้ข้อกังวลเพื่อปิดการขาย"
        )

        results.append({
            "messages": [
                {"role": "system", "content": system_with_context},
                {"role": "user", "content": q_clean},
                {"role": "assistant", "content": a_clean},
            ],
            "metadata": {
                "type": "objection_handling",
                "objection_types": obj_types,
                "topic": pair.get("topic", "general"),
                "source": "line_chat_history",
            },
        })

    return results


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Training Data → Fine-Tuning Format Converter")
    print("=" * 60)

    # Convert Q&A
    print("\n📝 Converting Q&A pairs...")
    qa_results, qa_filtered = convert_qa_pairs()
    print(f"   Clean Q&A: {len(qa_results)}")
    print(f"   Filtered: {qa_filtered}")

    # Convert objection handling
    print("\n🛡️ Converting objection handling...")
    obj_results = convert_objection_handling()
    print(f"   Objection examples: {len(obj_results)}")

    # Combine (deduplicate objections that are also in Q&A)
    obj_questions = set(
        r["messages"][1]["content"] for r in obj_results
    )
    qa_deduped = [
        r for r in qa_results
        if r["messages"][1]["content"] not in obj_questions
    ]

    all_results = qa_deduped + obj_results

    # Stats
    print("\n" + "=" * 60)
    print("📊 FINAL STATS")
    print("=" * 60)
    print(f"  Q&A examples: {len(qa_deduped)}")
    print(f"  Objection examples: {len(obj_results)}")
    print(f"  Total training examples: {len(all_results)}")

    # Topic breakdown
    topics = {}
    for r in all_results:
        t = r["metadata"]["topic"]
        topics[t] = topics.get(t, 0) + 1
    print("\n  By topic:")
    for t, c in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"    {TOPIC_LABELS.get(t, t)}: {c}")

    # Type breakdown
    types = {}
    for r in all_results:
        t = r["metadata"]["type"]
        types[t] = types.get(t, 0) + 1
    print("\n  By type:")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")

    if dry_run:
        print(f"\n[DRY RUN] Would write {len(all_results)} examples")
        # Show 3 samples
        print("\n--- Sample outputs ---")
        for r in all_results[:3]:
            print(json.dumps(r["messages"][1:], ensure_ascii=False, indent=2)[:200])
            print("---")
        return

    # Write JSONL
    date = "2026-03-19"
    jsonl_path = os.path.join(OUTPUT_DIR, f"jarvis_finetune_{date}.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n✅ JSONL → {jsonl_path}")

    # Write stats
    stats = {
        "created_at": datetime.now().isoformat(),
        "source": "line_chat_history",
        "total_examples": len(all_results),
        "qa_examples": len(qa_deduped),
        "objection_examples": len(obj_results),
        "filtered": qa_filtered,
        "topics": topics,
        "types": types,
        "system_prompt": SYSTEM_PROMPT,
    }
    stats_path = os.path.join(OUTPUT_DIR, f"jarvis_finetune_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"✅ Stats → {stats_path}")

    print(f"\n🎯 {len(all_results)} training examples ready for Jarvis Bot fine-tuning")


if __name__ == "__main__":
    main()
