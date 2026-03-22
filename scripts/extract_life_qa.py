#!/usr/bin/env python3
"""
Extract life insurance Q&A pairs from Supabase line_chat_history.
"""

import json
import re
import sys
from collections import defaultdict

import os

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SB_AUTH = os.environ.get("SUPABASE_SB_AUTH", "")

HEADERS = {
    "apikey": SB_AUTH,
    "Authorization": f"Bearer {SB_AUTH}",
    "Content-Type": "application/json",
}

# Agent name prefixes to strip — these appear at start of message text in LINE exports
AGENT_PREFIXES = re.compile(
    r"^\s*(D\.\s*|MAY\s*(\([^)]*\))?\s*:?\s*|Dream\s+Arthit\s*:?\s*|Front\s*:?\s*|ex_jira\s*:?\s*|iAgencyAIA\.com\s*:?\s*)",
    re.IGNORECASE,
)
# Also strip "iAgencyAIA.com" appearing as a standalone word at start (without colon)
IAGENCY_PREFIX = re.compile(r"^\s*iAgencyAIA\.com\s*", re.IGNORECASE)
# Strip LINE OA agent code prefixes like "A01 Beauty " or "A02 KENG_SATAPORN "
AGENT_CODE_PREFIX = re.compile(r"^\s*A\d{2}\s+\S+\s+", re.IGNORECASE)

# PII patterns
PHONE_PATTERN = re.compile(r"0[689]\d[-\s]?\d{3}[-\s]?\d{4}")
ID_CARD_PATTERN = re.compile(r"\b\d{1}[-\s]?\d{4}[-\s]?\d{5}[-\s]?\d{2}[-\s]?\d{1}\b")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+|bit\.ly/\S+|lin\.ee/\S+")

# Greeting/short-ack patterns to filter out
GREETINGS = re.compile(
    r"^(สวัสดี|ครับ|ค่ะ|ขอบคุณ|โอเค|ok|okay|รับทราบ|ได้เลย|เข้าใจแล้ว|ใช่|ไม่|yes|no|hi|hello|👋|🙏|😊|\s)*$",
    re.IGNORECASE,
)

LINK_ONLY = re.compile(r"^[\s\n]*(https?://\S+|www\.\S+|bit\.ly\S+|lin\.ee\S+)[\s\n]*$")


def clean_text(text: str) -> str:
    """Remove PII, URLs, and agent name prefixes."""
    if not text:
        return ""
    # Remove URLs
    text = URL_PATTERN.sub("", text)
    # Remove phone numbers
    text = PHONE_PATTERN.sub("[เบอร์โทร]", text)
    # Remove ID card numbers
    text = ID_CARD_PATTERN.sub("[เลขบัตร]", text)
    # Remove agent name prefixes — they appear at the very start of message text
    # e.g. "MAY (เลขาคุณดรีม) ข้อความจริง" or "Dream Arthit ข้อความ" or "iAgencyAIA.com ..."
    text = AGENT_PREFIXES.sub("", text.strip())
    text = IAGENCY_PREFIX.sub("", text.strip())
    text = AGENT_CODE_PREFIX.sub("", text.strip())
    # Collapse excessive whitespace/newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_substantive_question(text: str) -> bool:
    """Check if customer message is a substantive question."""
    if len(text) < 10:
        return False
    if GREETINGS.match(text):
        return False
    # Must contain something question-like or informative
    # Filter pure emoji messages
    emoji_only = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27ff\ufe00-\ufe0f\u200d]", "", text).strip()
    if len(emoji_only) < 5:
        return False
    return True


# Boilerplate bot/auto-reply patterns to reject
BOILERPLATE_PATTERNS = [
    re.compile(r"เกี่ยวกับ iAgencyAIA\.com", re.IGNORECASE),
    re.compile(r"iAgencyAIA\.com เป็นเว็บไซต์ของตัวแทน", re.IGNORECASE),
    re.compile(r"Privacy Policy.*iAgencyAIA", re.IGNORECASE),
    re.compile(r"คำขอการโทร โปรดแตะปุ่ม", re.IGNORECASE),
    re.compile(r"ยินดีต้อนรับสู่.*iAgency", re.IGNORECASE),
]


def is_boilerplate(text: str) -> bool:
    """Check if text is an automated/boilerplate response."""
    for pattern in BOILERPLATE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def is_substantive_answer(text: str) -> bool:
    """Check if agent response is substantive."""
    if len(text) < 30:
        return False
    if LINK_ONLY.match(text):
        return False
    # Filter pure acknowledgment
    if GREETINGS.match(text):
        return False
    emoji_only = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27ff\ufe00-\ufe0f\u200d]", "", text).strip()
    if len(emoji_only) < 20:
        return False
    # Filter boilerplate auto-replies
    if is_boilerplate(text):
        return False
    return True


def fetch_all_messages() -> list[dict]:
    """Fetch all messages from life-insurance tagged conversations."""
    all_messages = []
    page_size = 1000
    offset = 0

    # First get all conversation_ids with life-insurance tag
    print("Fetching life-insurance conversation IDs...", flush=True)
    conv_ids_url = f"{SUPABASE_URL}/rest/v1/line_chat_history"

    # Use RPC or direct filter — fetch conversation_ids
    # We'll do it via the REST API with select=conversation_id&tags=cs.{life-insurance}
    resp = httpx.get(
        conv_ids_url,
        headers={**HEADERS, "Prefer": "count=exact"},
        params={
            "select": "conversation_id",
            "tags": "cs.{life-insurance}",
        },
        timeout=30,
    )
    resp.raise_for_status()
    conv_id_rows = resp.json()
    conv_ids = list({row["conversation_id"] for row in conv_id_rows})
    print(f"Found {len(conv_ids)} unique conversations with life-insurance tag", flush=True)

    # Now fetch all messages from those conversations in batches
    # PostgREST supports IN filter via ?conversation_id=in.(id1,id2,...)
    # But if too many IDs, we need to chunk
    print(f"Fetching all messages from those conversations...", flush=True)

    batch_size = 50  # conversation IDs per request
    for i in range(0, len(conv_ids), batch_size):
        batch_ids = conv_ids[i : i + batch_size]
        ids_str = ",".join(batch_ids)

        # Paginate within each batch
        inner_offset = 0
        while True:
            resp = httpx.get(
                conv_ids_url,
                headers={**HEADERS, "Prefer": "count=exact"},
                params={
                    "select": "id,conversation_id,contact_name,sender,message_text,timestamp,tags",
                    "conversation_id": f"in.({ids_str})",
                    "order": "conversation_id,timestamp",
                    "limit": page_size,
                    "offset": inner_offset,
                },
                timeout=60,
            )
            resp.raise_for_status()
            rows = resp.json()
            all_messages.extend(rows)
            if len(rows) < page_size:
                break
            inner_offset += page_size

        if (i // batch_size + 1) % 5 == 0:
            print(f"  Processed {i + batch_size}/{len(conv_ids)} conversations, {len(all_messages)} messages so far", flush=True)

    print(f"Total messages fetched: {len(all_messages)}", flush=True)
    return all_messages


def extract_qa_pairs(messages: list[dict]) -> list[dict]:
    """Extract Q&A pairs from messages grouped by conversation."""
    # Group by conversation
    by_conv = defaultdict(list)
    for msg in messages:
        by_conv[msg["conversation_id"]].append(msg)

    # Sort each conversation by timestamp
    for conv_id in by_conv:
        by_conv[conv_id].sort(key=lambda x: x.get("timestamp") or "")

    qa_pairs = []

    for conv_id, msgs in by_conv.items():
        # Get tags for this conversation
        conv_tags = []
        for msg in msgs:
            if msg.get("tags"):
                conv_tags = msg["tags"]
                break

        # Slide through messages looking for customer→agent pairs
        for i, msg in enumerate(msgs):
            if msg.get("sender") != "customer":
                continue

            raw_q = msg.get("message_text") or ""
            cleaned_q = clean_text(raw_q)

            if not is_substantive_question(cleaned_q):
                continue

            # Look for the next agent message(s) as the answer
            # Collect consecutive agent messages after this customer message
            answer_parts = []
            j = i + 1
            while j < len(msgs) and msgs[j].get("sender") == "agent":
                raw_a = msgs[j].get("message_text") or ""
                cleaned_a = clean_text(raw_a)
                if cleaned_a:
                    answer_parts.append(cleaned_a)
                j += 1

            if not answer_parts:
                continue

            # Combine agent messages into one answer
            full_answer = "\n".join(answer_parts).strip()

            if not is_substantive_answer(full_answer):
                continue

            qa_pairs.append({
                "question": cleaned_q,
                "answer": full_answer,
                "conversation_id": conv_id,
                "tags": conv_tags,
            })

    return qa_pairs


def main():
    if not SB_AUTH:
        print("ERROR: SUPABASE_SB_AUTH env var required", file=sys.stderr)
        sys.exit(1)

    output_path = "/home/mbank/repos/github.com/BankCurfew/Data-Oracle/data/training/life_qa_pairs_raw.json"

    # Fetch all messages
    messages = fetch_all_messages()

    if not messages:
        print("No messages found!", file=sys.stderr)
        sys.exit(1)

    # Count conversations
    conv_ids_in_data = {m["conversation_id"] for m in messages}
    print(f"\nConversations in fetched data: {len(conv_ids_in_data)}", flush=True)

    # Extract Q&A pairs
    print("Extracting Q&A pairs...", flush=True)
    qa_pairs = extract_qa_pairs(messages)

    print(f"\n=== STATS ===")
    print(f"Total conversations with life-insurance tag: {len(conv_ids_in_data)}")
    print(f"Total messages fetched: {len(messages)}")
    print(f"Total Q&A pairs extracted: {len(qa_pairs)}")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
    print(f"\nOutput written to: {output_path}")

    # Print sample of first 10 pairs
    print(f"\n=== SAMPLE (first 10 pairs) ===")
    for idx, pair in enumerate(qa_pairs[:10]):
        print(f"\n--- Pair {idx + 1} ---")
        print(f"Conversation: {pair['conversation_id']}")
        print(f"Tags: {pair['tags']}")
        q_preview = pair['question'][:200].replace('\n', ' ')
        a_preview = pair['answer'][:300].replace('\n', ' ')
        print(f"Q: {q_preview}")
        print(f"A: {a_preview}")

    return qa_pairs


if __name__ == "__main__":
    main()
