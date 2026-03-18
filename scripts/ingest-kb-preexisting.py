#!/usr/bin/env python3
"""Ingest KB Pre-existing Conditions — 6 entries from Writer-Oracle."""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

EMBED_URL = os.environ.get("EMBED_URL", "http://localhost:8100/embed")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

SOURCE = "kb-preexisting-conditions"
BATCH_SIZE = 6

KB_ENTRIES = [
    {
        "document_name": "KB-PRE-1: มีโรคประจำตัว สมัครประกันสุขภาพได้ไหม",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "pre-existing conditions overview",
        "chunk_text": """มีโรคประจำตัวไม่ได้แปลว่าทำประกันไม่ได้ ขั้นตอนคือแถลงสุขภาพตามจริงในใบสมัคร แล้ว AIA พิจารณาเป็นรายกรณี ผลที่เป็นไปได้:

- อนุมัติปกติ — รับประกันเต็มที่
- เพิ่มเบี้ย — รับ แต่เบี้ยสูงขึ้นตามความเสี่ยง
- ยกเว้นโรค (Pre-existing exclusion) — รับ แต่ไม่คุ้มครองโรคที่เป็นอยู่
- ปฏิเสธ — กรณีความเสี่ยงสูงมาก (พบน้อย)

สำคัญที่สุด: ต้องแถลงสุขภาพตามจริงเสมอ ถ้าปกปิดแล้วเกิดเคลม AIA มีสิทธิ์ปฏิเสธได้

แนะนำให้ปรึกษาตัวแทนเพื่อช่วยเตรียมเอกสารและยื่นใบสมัครให้ถูกต้อง"""
    },
    {
        "document_name": "KB-PRE-2: Pre-existing exclusion คืออะไร",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "pre-existing exclusion explained",
        "chunk_text": """Pre-existing exclusion คือ AIA รับทำประกันให้ แต่ไม่คุ้มครองโรคที่เป็นอยู่ก่อนสมัคร

ตัวอย่าง: ถ้าเป็นเบาหวานก่อนสมัคร แล้ว AIA รับแบบยกเว้นเบาหวาน
- ป่วยเป็นเบาหวาน → ไม่คุ้มครอง
- ป่วยเป็นไข้หวัดใหญ่ → คุ้มครองปกติ
- ประสบอุบัติเหตุ → คุ้มครองปกติ

สิ่งที่หลายคนมองข้าม: แม้ยกเว้นโรคเดิม แต่ยังคุ้มครองโรคอื่นทั้งหมด ดีกว่าไม่มีประกันเลย

หากต้องการสอบถามเงื่อนไขการทบทวน exclusion ติดต่อตัวแทนหรือ AIA Call Center 1581"""
    },
    {
        "document_name": "KB-PRE-3: เบาหวาน Stroke โรคประจำตัว ทำประกันได้ไหม",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "chronic disease insurance eligibility",
        "chunk_text": """มีโรคประจำตัวเช่นเบาหวานหรือ Stroke ทำประกันได้ — AIA พิจารณาเป็นรายกรณี ขึ้นอยู่กับหลายปัจจัย เช่น:
- เป็นมานานเท่าไหร่
- ควบคุมอาการได้ดีแค่ไหน
- ผลตรวจล่าสุดเป็นอย่างไร
- มียาที่ต้องทานประจำไหม

เนื่องจากเงื่อนไขการพิจารณาแตกต่างกันตามประเภทโรคและความรุนแรง กรุณาแจ้งประวัติสุขภาพครบถ้วนในใบสมัคร — ตัวแทนช่วยเตรียมเอกสารและยื่นให้ถูกต้องเพื่อโอกาสอนุมัติสูงสุด

ข้อดี: ถ้าสมัครได้ เบี้ยล็อคตามอายุตอนสมัคร ไม่เพิ่มตามอาการ ยิ่งสมัครเร็วยิ่งดี"""
    },
    {
        "document_name": "KB-PRE-4: Waiting period คืออะไร",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "waiting period explained",
        "chunk_text": """Waiting period คือช่วงเวลารอหลังกรมธรรม์เริ่มคุ้มครอง — ช่วงนี้ยังเคลมโรคบางประเภทไม่ได้

โดยทั่วไปประกันสุขภาพมีช่วงรอดังนี้:
- อุบัติเหตุ — โดยทั่วไปคุ้มครองทันที
- โรคทั่วไป — โดยทั่วไปรอประมาณ 30 วัน
- โรคที่กำหนดเฉพาะ (เช่น ไส้เลื่อน ต้อกระจก นิ่ว ริดสีดวง) — โดยทั่วไปรอนานกว่า
- โรคร้ายแรง — โดยทั่วไปรอประมาณ 90 วัน

ระยะเวลารอที่แน่นอนขึ้นอยู่กับเงื่อนไขของแต่ละแบบประกันและ rider กรุณาตรวจสอบรายละเอียดในกรมธรรม์หรือสอบถามตัวแทน

หลังผ่านช่วงรอแล้ว เคลมได้ปกติทุกอย่าง"""
    },
    {
        "document_name": "KB-PRE-5: ลูกเคยป่วย RSV ทำประกันสุขภาพเด็กได้ไหม",
        "category": "health",
        "product_name": "AIA Health Happy Kids - UDR",
        "section": "RSV child insurance",
        "chunk_text": """ลูกเคยป่วย RSV ทำประกันสุขภาพเด็กได้ — เคยป่วย RSV ไม่ได้แปลว่าทำประกันไม่ได้ AIA พิจารณาเป็นรายกรณี ขึ้นอยู่กับ:
- หายเป็นปกติหรือยัง
- มีภาวะแทรกซ้อนหลงเหลือไหม
- อายุปัจจุบันของเด็ก

ประกันสุขภาพเด็กที่แนะนำ:
- Health Happy Kids — เหมาจ่าย อายุ 15 วัน–10 ปี IPD+OPD
- Health Happy Kids UDR — เบี้ยคงที่ผ่าน Unit-Linked

กรุณาแจ้งประวัติสุขภาพครบถ้วนในใบสมัคร ตัวแทนช่วยเตรียมเอกสารให้ถูกต้อง

ดูเพิ่มเติม: https://www.iagencyaia.com/blog/6966/child-rsv"""
    },
    {
        "document_name": "KB-PRE-6: ประกันสุขภาพไม่คุ้มครองกรณีไหน",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "health insurance exclusions",
        "chunk_text": """กรณีที่โดยทั่วไปไม่อยู่ในความคุ้มครองประกันสุขภาพ:
- โรคที่เป็นมาก่อนสมัครที่ไม่ได้แถลงหรือถูกยกเว้น
- การรักษาที่ไม่จำเป็นทางการแพทย์
- การศัลยกรรมเพื่อความสวยงาม
- การรักษาที่เป็นการทดลอง
- ช่วง waiting period ของแต่ละประเภทโรค

เงื่อนไขเฉพาะขึ้นอยู่กับแต่ละแบบประกัน กรุณาตรวจสอบรายละเอียดในกรมธรรม์

สิ่งสำคัญที่สุดคือแถลงสุขภาพตามจริง — AIA พิจารณาอย่างยุติธรรม

ดูเพิ่มเติม: https://www.iagencyaia.com/blog/6005/health-insurance-exclusions"""
    },
]


def get_embeddings(texts):
    payload = json.dumps({"texts": texts, "return_dense": True, "return_sparse": True}).encode()
    req = Request(EMBED_URL, data=payload, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=120)
    data = json.loads(resp.read())
    return data["dense"], data["sparse"]


def supabase_post(table, rows):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    payload = json.dumps(rows, ensure_ascii=False).encode()
    req = Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=representation",
    })
    try:
        resp = urlopen(req, timeout=60)
        return json.loads(resp.read())
    except HTTPError as e:
        print(f"   ERROR: {e.code} {e.read().decode()[:500]}")
        raise


def estimate_tokens(text):
    return max(len(text) // 3, len(text.split()))


def main():
    if not SUPABASE_KEY:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY not set")
        sys.exit(1)

    print(f"📦 Ingesting {len(KB_ENTRIES)} pre-existing conditions entries...")

    # Embed all at once (6 texts)
    all_texts = [e["chunk_text"] for e in KB_ENTRIES]
    print(f"⚡ Embedding {len(all_texts)} texts...")
    dense, sparse = get_embeddings(all_texts)
    print(f"   ✅ Got {len(dense)} embeddings (dim={len(dense[0])})")

    # Check for None/NaN
    for i, emb in enumerate(dense):
        if any(v is None or v != v for v in emb):
            print(f"   ⚠️ Bad embedding at index {i} — aborting!")
            sys.exit(1)

    # Build rows
    rows = []
    for idx, entry in enumerate(KB_ENTRIES):
        embedding_str = "[" + ",".join(str(v) for v in dense[idx]) + "]"
        rows.append({
            "document_name": entry["document_name"],
            "source": SOURCE,
            "category": entry["category"],
            "section": entry["section"],
            "product_name": entry["product_name"],
            "chunk_index": idx,
            "chunk_text": entry["chunk_text"],
            "chunk_tokens": estimate_tokens(entry["chunk_text"]),
            "embedding": embedding_str,
            "sparse_embedding": sparse[idx],
            "metadata": {
                "pipeline": "ingest-kb-preexisting-v1",
                "source_file": "Writer-Oracle/ψ/writing/kb-preexisting-conditions.md",
                "qa_status": "DocCon FULL PASS",
                "aia_verified": True,
            },
        })

    print(f"📤 Uploading {len(rows)} rows to kb_chunks...")
    result = supabase_post("kb_chunks", rows)
    print(f"   ✅ Inserted {len(result)} rows!")

    print(f"\n{'='*50}")
    print(f"✅ DONE — {len(result)} pre-existing conditions entries ingested")
    print(f"   Source: {SOURCE}")
    for r in result:
        print(f"   📄 id={r['id']} {r['document_name']}")


if __name__ == "__main__":
    main()
