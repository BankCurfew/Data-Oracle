#!/usr/bin/env python3
"""
Extract training data from LINE chat history for Jarvis Bot.

Produces 3 outputs:
1. Q&A pairs — customer question → agent answer
2. Sales scripts — full conversation flows showing sales process
3. Objection handling — customer objections → agent responses

Usage:
    python3 scripts/extract-training-data.py              # full extraction
    python3 scripts/extract-training-data.py --dry-run     # preview counts only
    python3 scripts/extract-training-data.py --topic health # filter by topic
"""

import json
import os
import sys
import re
from datetime import datetime
from urllib.request import Request, urlopen

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

OUTPUT_DIR = "data/training"

# Objection keywords — customer pushback patterns
OBJECTION_KEYWORDS = [
    "แพง", "ราคา", "งบ", "ไม่มีเงิน", "ไม่พร้อม", "ยังก่อน",
    "ขอคิดดู", "ไม่แน่ใจ", "เดี๋ยวก่อน", "ไว้ก่อน",
    "มีที่อื่น", "เปรียบเทียบ", "ที่อื่น", "บริษัทอื่น",
    "ไม่ต้อง", "ไม่สนใจ", "ยกเลิก", "cancel",
    "ถามก่อน", "สงสัย", "กังวล", "กลัว",
    "หมดอายุ", "ค้าง", "ไม่ได้รับ", "ยังไม่ได้",
    "ทำไม", "แตกต่าง", "ข้อแตกต่าง",
]

# Noise patterns to filter out
NOISE_PATTERNS = [
    r"^https?://",           # URLs
    r"^Dream Arthit",        # Agent name mentions
    r"^MAY \(",              # Secretary mentions
    r"^ex_jira",             # Internal mentions
    r"^Front ",              # Front desk prefix
    r"^D\. ",                # Agent initial prefix
    r"^A\d{2} ",             # Contact code prefix
    r"^\s*$",                # Empty
]


def supabase_rpc(query):
    """Execute SQL via Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    # Fallback: use PostgREST
    # For views, we use REST API directly
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    return headers


def fetch_conversations():
    """Fetch training-worthy conversations from Supabase."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    # Fetch all messages from training-worthy conversations (4+ msgs)
    all_msgs = []
    offset = 0
    page_size = 1000

    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/line_chat_history"
            f"?select=conversation_id,contact_name,sender,message_text,timestamp"
            f"&order=conversation_id,timestamp"
            f"&offset={offset}&limit={page_size}"
        )
        req = Request(url, headers=headers)
        with urlopen(req) as resp:
            rows = json.loads(resp.read())

        if not rows:
            break
        all_msgs.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
        print(f"  Fetched {len(all_msgs)} messages...")

    print(f"Total messages fetched: {len(all_msgs)}")

    # Group by conversation
    convos = {}
    for msg in all_msgs:
        cid = msg["conversation_id"]
        if cid not in convos:
            convos[cid] = {
                "conversation_id": cid,
                "contact_name": msg["contact_name"],
                "messages": [],
            }
        convos[cid]["messages"].append(msg)

    # Filter: 4+ messages, has both sender types
    training_convos = {}
    for cid, convo in convos.items():
        msgs = convo["messages"]
        senders = set(m["sender"] for m in msgs)
        if len(msgs) >= 4 and "agent" in senders and "customer" in senders:
            training_convos[cid] = convo

    print(f"Training-worthy conversations: {len(training_convos)}")
    return training_convos


def clean_message(text):
    """Clean message text, removing noise."""
    if not text:
        return None
    text = text.strip()
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, text):
            return None
    if len(text) < 3:
        return None
    return text


def classify_topic(messages):
    """Classify conversation topic from message content."""
    text = " ".join(m.get("message_text", "") or "" for m in messages)
    if any(k in text for k in ["สุขภาพ", "health", "OPD", "IPD", "Health Happy"]):
        return "health"
    if "ประกันชีวิต" in text:
        return "life"
    if any(k in text for k in ["โรคร้ายแรง", "CI", "cancer"]):
        return "critical_illness"
    if any(k in text for k in ["เคลม", "claim", "เบิก"]):
        return "claims"
    if any(k in text for k in ["UDR", "unit linked", "กองทุน"]):
        return "unit_linked"
    if any(k in text for k in ["เด็ก", "ลูก"]):
        return "kids"
    if any(k in text for k in ["เบี้ย", "ราคา", "งบ"]):
        return "pricing"
    return "general"


def extract_qa_pairs(convos):
    """Extract customer question → agent answer pairs."""
    pairs = []

    for cid, convo in convos.items():
        msgs = convo["messages"]
        topic = classify_topic(msgs)

        for i, msg in enumerate(msgs):
            if msg["sender"] != "customer":
                continue

            q_text = clean_message(msg.get("message_text", ""))
            if not q_text or len(q_text) < 8:
                continue

            # Find next agent response(s)
            agent_responses = []
            for j in range(i + 1, min(i + 5, len(msgs))):
                if msgs[j]["sender"] == "agent":
                    a_text = clean_message(msgs[j].get("message_text", ""))
                    if a_text:
                        agent_responses.append(a_text)
                elif msgs[j]["sender"] == "customer":
                    break  # Next customer message = end of this Q&A

            if not agent_responses:
                continue

            pairs.append({
                "question": q_text,
                "answer": "\n".join(agent_responses),
                "topic": topic,
                "conversation_id": cid,
                "contact": convo["contact_name"],
            })

    return pairs


def extract_sales_scripts(convos):
    """Extract full sales conversation flows."""
    scripts = []

    for cid, convo in convos.items():
        msgs = convo["messages"]
        if len(msgs) < 8:  # Need substantial conversations for scripts
            continue

        topic = classify_topic(msgs)
        cleaned_flow = []

        for msg in msgs:
            text = clean_message(msg.get("message_text", ""))
            if text:
                cleaned_flow.append({
                    "role": msg["sender"],
                    "content": text,
                })

        if len(cleaned_flow) < 6:
            continue

        # Detect sales stages
        full_text = " ".join(m["content"] for m in cleaned_flow)
        stages = []
        if any(k in full_text for k in ["สนใจ", "สอบถาม", "ต้องการ"]):
            stages.append("inquiry")
        if any(k in full_text for k in ["อายุ", "งบ", "ทุน", "แผน"]):
            stages.append("qualify")
        if any(k in full_text for k in ["เสนอ", "แนะนำ", "เปรียบเทียบ"]):
            stages.append("propose")
        if any(k in full_text for k in ["สมัคร", "iSign", "กรอก"]):
            stages.append("application")
        if any(k in full_text for k in ["ชำระ", "โอน", "จ่าย"]):
            stages.append("payment")
        if any(k in full_text for k in ["อนุมัติ", "มีผลบังคับ", "เรียบร้อย"]):
            stages.append("close")

        scripts.append({
            "conversation_id": cid,
            "contact": convo["contact_name"],
            "topic": topic,
            "stages": stages,
            "msg_count": len(cleaned_flow),
            "flow": cleaned_flow,
        })

    return scripts


def extract_objection_handling(convos):
    """Extract customer objections and agent responses."""
    objections = []

    for cid, convo in convos.items():
        msgs = convo["messages"]
        topic = classify_topic(msgs)

        for i, msg in enumerate(msgs):
            if msg["sender"] != "customer":
                continue

            text = msg.get("message_text", "") or ""
            matched_keywords = [k for k in OBJECTION_KEYWORDS if k in text]

            if not matched_keywords:
                continue

            q_text = clean_message(text)
            if not q_text:
                continue

            # Get agent response to the objection
            agent_responses = []
            for j in range(i + 1, min(i + 5, len(msgs))):
                if msgs[j]["sender"] == "agent":
                    a_text = clean_message(msgs[j].get("message_text", ""))
                    if a_text:
                        agent_responses.append(a_text)
                elif msgs[j]["sender"] == "customer":
                    break

            if not agent_responses:
                continue

            # Get context (previous 2 messages)
            context = []
            for j in range(max(0, i - 2), i):
                c_text = clean_message(msgs[j].get("message_text", ""))
                if c_text:
                    context.append({
                        "role": msgs[j]["sender"],
                        "content": c_text,
                    })

            objections.append({
                "objection": q_text,
                "objection_type": matched_keywords,
                "agent_response": "\n".join(agent_responses),
                "context": context,
                "topic": topic,
                "conversation_id": cid,
            })

    return objections


def main():
    dry_run = "--dry-run" in sys.argv
    topic_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--topic" and i + 1 < len(sys.argv):
            topic_filter = sys.argv[i + 1]

    print("=" * 60)
    print("LINE Chat → Jarvis Bot Training Data Extraction")
    print("=" * 60)

    # Fetch data
    print("\n📥 Fetching conversations from Supabase...")
    convos = fetch_conversations()

    if topic_filter:
        convos = {
            cid: c for cid, c in convos.items()
            if classify_topic(c["messages"]) == topic_filter
        }
        print(f"Filtered to topic '{topic_filter}': {len(convos)} conversations")

    # Extract
    print("\n🔄 Extracting Q&A pairs...")
    qa_pairs = extract_qa_pairs(convos)
    print(f"   Found {len(qa_pairs)} Q&A pairs")

    print("\n🔄 Extracting sales scripts...")
    sales_scripts = extract_sales_scripts(convos)
    print(f"   Found {len(sales_scripts)} sales scripts")

    print("\n🔄 Extracting objection handling...")
    objections = extract_objection_handling(convos)
    print(f"   Found {len(objections)} objection patterns")

    # Stats
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    # Q&A by topic
    qa_topics = {}
    for p in qa_pairs:
        qa_topics[p["topic"]] = qa_topics.get(p["topic"], 0) + 1
    print("\nQ&A pairs by topic:")
    for t, c in sorted(qa_topics.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Sales scripts by stage coverage
    stage_counts = {}
    for s in sales_scripts:
        for stage in s["stages"]:
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
    print("\nSales scripts with stages:")
    for stage, c in sorted(stage_counts.items(), key=lambda x: -x[1]):
        print(f"  {stage}: {c}")

    # Objection types
    obj_types = {}
    for o in objections:
        for kw in o["objection_type"]:
            obj_types[kw] = obj_types.get(kw, 0) + 1
    print("\nObjection keywords:")
    for kw, c in sorted(obj_types.items(), key=lambda x: -x[1])[:15]:
        print(f"  {kw}: {c}")

    if dry_run:
        print(f"\n[DRY RUN] Would write {len(qa_pairs)} Q&A + {len(sales_scripts)} scripts + {len(objections)} objections")
        return

    # Write output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Q&A pairs
    qa_path = f"{OUTPUT_DIR}/qa_pairs_{timestamp}.json"
    with open(qa_path, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Q&A pairs → {qa_path}")

    # Sales scripts
    scripts_path = f"{OUTPUT_DIR}/sales_scripts_{timestamp}.json"
    with open(scripts_path, "w", encoding="utf-8") as f:
        json.dump(sales_scripts, f, ensure_ascii=False, indent=2)
    print(f"✅ Sales scripts → {scripts_path}")

    # Objection handling
    obj_path = f"{OUTPUT_DIR}/objection_handling_{timestamp}.json"
    with open(obj_path, "w", encoding="utf-8") as f:
        json.dump(objections, f, ensure_ascii=False, indent=2)
    print(f"✅ Objection handling → {obj_path}")

    # Combined training set (for direct KB ingest)
    combined = {
        "extracted_at": datetime.now().isoformat(),
        "source": "line_chat_history",
        "stats": {
            "total_conversations": len(convos),
            "qa_pairs": len(qa_pairs),
            "sales_scripts": len(sales_scripts),
            "objection_patterns": len(objections),
        },
        "qa_pairs": qa_pairs,
        "sales_scripts": sales_scripts,
        "objection_handling": objections,
    }
    combined_path = f"{OUTPUT_DIR}/jarvis_training_{timestamp}.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"✅ Combined training set → {combined_path}")

    print(f"\n🎯 Total: {len(qa_pairs)} Q&A + {len(sales_scripts)} scripts + {len(objections)} objections")
    print(f"   Ready for Jarvis Bot training pipeline")


if __name__ == "__main__":
    main()
