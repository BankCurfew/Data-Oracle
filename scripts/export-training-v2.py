#!/usr/bin/env python3
"""
Export training data v2 — pulls labeled Q&A pairs directly from Supabase.

Improvements over v1:
- Uses normalized tags from DB (post tag-normalization)
- Includes newly labeled conversations (66% coverage)
- Exports objection patterns + winning responses separately
- Proper category labels from product alias matching

Usage:
    python3 scripts/export-training-v2.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

OUTPUT_DIR = "data/training"
DATE = "2026-03-19"
SUPABASE_PROJECT = "heciyiepgxqtbphepalf"

SYSTEM_PROMPT = """คุณคือ Jarvis Bot — ผู้ช่วยตัวแทนประกันชีวิต AIA (iAgencyAIA) ที่เชี่ยวชาญ
หน้าที่: ตอบคำถามลูกค้าเกี่ยวกับผลิตภัณฑ์ AIA, ช่วยปิดการขาย, จัดการข้อโต้แย้ง, และให้บริการหลังการขาย
สไตล์: สุภาพ เป็นมิตร ใช้ภาษาไทย ตอบตรงประเด็น ให้ข้อมูลถูกต้อง
ห้าม: ให้ข้อมูลเท็จ, สัญญาสิ่งที่ทำไม่ได้, เปิดเผยข้อมูลลูกค้า"""

OBJECTION_SYSTEM = SYSTEM_PROMPT + """

สถานการณ์: ลูกค้ามีข้อกังวล/ข้อโต้แย้ง
ต้องตอบอย่างเข้าใจ ให้ข้อมูลชัดเจน และพยายามแก้ข้อกังวลเพื่อปิดการขาย"""

# Tag to category mapping
TAG_TO_CATEGORY = {
    "health-insurance": "health",
    "life-insurance": "life",
    "critical-illness": "critical_illness",
    "savings-investment": "savings_investment",
    "accident": "accident",
    "pricing": "pricing",
    "claims-service": "claims",
    "objection": "objection",
    "sales-process": "sales",
    "child-insurance": "kids",
    "group-insurance": "group",
    "pre-existing": "pre_existing",
    "general-inquiry": "general",
}

# Noise filters
NOISE_PATTERNS = [
    r"^(สวัสดี|ดี|หวัดดี|hello|hi|hey|ok|ครับ|ค่ะ|ขอบคุณ|ดีจ้า|ดีค่ะ|ดีครับ|555|ไม่เป็นไร|โอเค|จ้า|อืม|ได้เลย|ได้ครับ|ได้ค่ะ|ตกลง|รับทราบ|เรียบร้อย)[\s]*$",
    r"^https?://",
    r"^iAgencyAIA\.com$",
    r"^Dream Arthit",
    r"^MAY \(",
    r"^ex_jira",
]


def clean_text(text):
    if not text:
        return None
    text = text.strip()
    # Remove internal prefixes
    text = re.sub(r"^D\.\s*", "", text)
    text = re.sub(r"^MAY \(เลขาคุณดรีม\)\s*", "", text)
    text = re.sub(r"^Dream Arthit\s*", "", text)
    text = re.sub(r"^Front\s+", "", text)
    text = re.sub(r"^iAgencyAIA\.com\s*", "", text)
    # Remove contact codes
    text = re.sub(r"^(CL|CG|A)\d+[\.\s]\S+\s*", "", text)
    # Redact phone numbers
    text = re.sub(r"0[689]\d-?\d{3}-?\d{4}", "[เบอร์โทร]", text)
    # Redact ID card numbers
    text = re.sub(r"\d{1}-\d{4}-\d{5}-\d{2}-\d{1}", "[เลขบัตร]", text)
    text = text.strip()
    return text if len(text) >= 5 else None


def is_noise(text):
    for p in NOISE_PATTERNS:
        if re.match(p, text.strip(), re.IGNORECASE):
            return True
    return len(text.strip()) < 5


def get_primary_category(tags):
    """Get the most specific category from tags."""
    priority = ["health-insurance", "life-insurance", "critical-illness",
                 "savings-investment", "accident", "child-insurance",
                 "claims-service", "pricing", "sales-process",
                 "group-insurance", "pre-existing", "objection",
                 "general-inquiry"]
    for p in priority:
        if p in tags:
            return TAG_TO_CATEGORY.get(p, "general")
    return "general"


def main():
    # Read the exported Q&A pairs file
    # Accept file path as CLI arg, or search tool-results dirs
    result_file = sys.argv[1] if len(sys.argv) > 1 else None

    if not result_file:
        tool_results_base = os.path.expanduser(
            "~/.claude/projects/-home-mbank-repos-github-com-BankCurfew-Data-Oracle/"
        )
        for root, dirs, files in os.walk(tool_results_base):
            for fname in files:
                if not fname.endswith(".txt"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r') as fh:
                        content = fh.read()
                        if '"q_id"' in content and '"question"' in content and '"answer"' in content:
                            result_file = fpath
                            break
                except Exception:
                    continue
            if result_file:
                break

    if not result_file:
        print("ERROR: No Q&A export file found. Pass file path as argument.")
        sys.exit(1)

    print(f"Reading Q&A data from: {result_file}")

    with open(result_file, 'r') as f:
        raw = f.read()

    # Parse JSON — file format: [{type, text}] → text contains {result: "...untrusted-data..."}
    outer = json.loads(raw)
    if isinstance(outer, list) and len(outer) > 0 and 'text' in outer[0]:
        text = outer[0]['text']
    else:
        text = raw

    result_obj = json.loads(text) if isinstance(text, str) else text
    result_str = result_obj.get('result', text)

    # Extract JSON array from between untrusted-data tags
    match = re.search(r'<untrusted-data[^>]*>\n(.*?)\n</untrusted-data', result_str, re.DOTALL)
    if match:
        pairs_raw = json.loads(match.group(1))
    else:
        print("ERROR: Could not parse Q&A data from result")
        sys.exit(1)

    print(f"Loaded {len(pairs_raw)} Q&A pairs from DB")

    # Also load existing local data for enrichment
    local_qa_path = os.path.join(OUTPUT_DIR, "qa_pairs_2026-03-19.json")
    local_pairs = []
    if os.path.exists(local_qa_path):
        with open(local_qa_path) as f:
            local_pairs = json.load(f)
        print(f"Loaded {len(local_pairs)} local Q&A pairs for enrichment")

    # Build training examples from DB pairs
    results = []
    filtered = {"noise_q": 0, "noise_a": 0, "short": 0, "clean_fail": 0, "dup": 0}
    seen_questions = set()

    for pair in pairs_raw:
        q = pair.get("question", "")
        a = pair.get("answer", "")
        tags = pair.get("category_tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags) if tags.startswith('[') else [tags]

        if is_noise(q):
            filtered["noise_q"] += 1
            continue
        if is_noise(a):
            filtered["noise_a"] += 1
            continue

        q_clean = clean_text(q)
        a_clean = clean_text(a)

        if not q_clean or not a_clean:
            filtered["clean_fail"] += 1
            continue
        if len(q_clean) < 8 or len(a_clean) < 8:
            filtered["short"] += 1
            continue

        # Dedup by question
        q_key = q_clean[:80].lower()
        if q_key in seen_questions:
            filtered["dup"] += 1
            continue
        seen_questions.add(q_key)

        category = get_primary_category(tags)

        # Determine if objection
        is_objection = "objection" in tags
        system = OBJECTION_SYSTEM if is_objection else SYSTEM_PROMPT
        ex_type = "objection_handling" if is_objection else "qa"

        results.append({
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": q_clean},
                {"role": "assistant", "content": a_clean},
            ],
            "metadata": {
                "type": ex_type,
                "category": category,
                "tags": tags,
                "source": "line_chat_history",
            },
        })

    # Add local pairs that aren't already included
    for pair in local_pairs:
        q = pair.get("question", "")
        a = pair.get("answer", "")
        topic = pair.get("topic", "general")

        if is_noise(q) or is_noise(a):
            continue
        q_clean = clean_text(q)
        a_clean = clean_text(a)
        if not q_clean or not a_clean or len(q_clean) < 8 or len(a_clean) < 8:
            continue

        q_key = q_clean[:80].lower()
        if q_key in seen_questions:
            continue
        seen_questions.add(q_key)

        results.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": q_clean},
                {"role": "assistant", "content": a_clean},
            ],
            "metadata": {
                "type": "qa",
                "category": topic,
                "tags": [],
                "source": "line_chat_history_local",
            },
        })

    # Stats
    categories = {}
    types = {}
    for r in results:
        c = r["metadata"]["category"]
        t = r["metadata"]["type"]
        categories[c] = categories.get(c, 0) + 1
        types[t] = types.get(t, 0) + 1

    print("\n" + "=" * 60)
    print("TRAINING DATA v2 — EXPORT RESULTS")
    print("=" * 60)
    print(f"\n  Total examples: {len(results)}")
    print(f"  Filtered: {filtered}")
    print(f"\n  By category:")
    for c, n in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {c}: {n}")
    print(f"\n  By type:")
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        print(f"    {t}: {n}")

    # Write JSONL
    jsonl_path = os.path.join(OUTPUT_DIR, f"jarvis_finetune_v2_{DATE}.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n  JSONL → {jsonl_path}")

    # Write stats
    stats = {
        "created_at": datetime.now().isoformat(),
        "version": "v2",
        "source": "line_chat_history (post-normalization)",
        "total_examples": len(results),
        "filtered": filtered,
        "categories": categories,
        "types": types,
        "tag_normalization": "complete",
        "dedup": "complete",
        "labeling_coverage": "66%",
        "system_prompt": SYSTEM_PROMPT,
    }
    stats_path = os.path.join(OUTPUT_DIR, f"jarvis_finetune_v2_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  Stats → {stats_path}")

    print(f"\n  {len(results)} training examples ready for Jarvis Bot fine-tuning")


if __name__ == "__main__":
    main()
