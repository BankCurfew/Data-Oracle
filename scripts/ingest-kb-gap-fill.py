#!/usr/bin/env python3
"""Ingest KB Gap Fill — 10 entries from Writer-Oracle into kb_chunks via embedding-service."""

import json
import os
import sys
from urllib.request import Request, urlopen

EMBED_URL = os.environ.get("EMBED_URL", "http://localhost:8100/embed")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

SOURCE = "kb-gap-fill-critical"
BATCH_SIZE = 4

# 10 KB entries parsed from Writer-Oracle content
KB_ENTRIES = [
    {
        "document_name": "KB-GAP-1A: ประกันสุขภาพ AIA มีแบบไหนบ้าง",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "health-rider overview",
        "chunk_text": """ประกันสุขภาพ AIA มี 5 แบบหลัก เลือกตามงบและความต้องการ:

เหมาจ่ายเต็ม (ไม่ต้องจ่ายเพิ่ม):
- Health Happy — ยอดนิยม 4 แผน (1M/5M/15M/25M ต่อปี) ไม่ต้องสำรองจ่ายที่ รพ. เครือข่าย อายุ 11–75 ปี โรคร้ายแรงจ่ายเพิ่ม 2 เท่า
- Health Happy Kids — สำหรับเด็ก 15 วัน–10 ปี เหมาจ่าย IPD+OPD เปลี่ยนเป็น Health Happy ผู้ใหญ่ได้เมื่อโต
- Infinite Care — ระดับพรีเมียม คุ้มครองทั่วโลก เหมาะกับคนเดินทางบ่อย

เหมาจ่าย + ร่วมจ่าย (เบี้ยถูกกว่า):
- Health Starter — แบบ BEGIN ร่วมจ่าย 30% หรือ BALANCED ร่วมจ่าย 20%/0% เหมาะกับคนงบจำกัด

เบี้ยคงที่ (แก้ปัญหาเบี้ยแพงตอนแก่):
- Health Happy UDR — เบี้ยคงที่ตลอดสัญญา หักจาก unit value ของ Unit-Linked (Issara Plus) อัตโนมัติ
- Health Happy Kids UDR — เบี้ยคงที่สำหรับเด็ก ผ่าน Unit-Linked

สำคัญ: ประกันสุขภาพทุกแบบเป็นสัญญาเพิ่มเติม (rider) ซื้อเดี่ยวไม่ได้ ต้องซื้อพร้อมแบบหลัก เช่น Pay Life Plus หรือ Issara Plus"""
    },
    {
        "document_name": "KB-GAP-1B: เลือกประกันสุขภาพแบบไหนดี",
        "category": "health",
        "product_name": "Category: health-rider",
        "section": "health-rider recommendation",
        "chunk_text": """เลือกประกันสุขภาพแบบไหนดี แนะนำตามสถานการณ์:

- คนทั่วไป งบปานกลาง → Health Happy แผน 5M — เหมาจ่ายเต็ม วงเงินพอดี เบี้ยจับต้องได้
- ต้องการคุ้มครองสูงสุด → Health Happy แผน 25M — มี OPD + วงเงินสูงสุด
- งบจำกัด → Health Starter BEGIN — เหมาจ่าย + ร่วมจ่าย 30% เบี้ยถูก
- ไม่อยากจ่ายเบี้ยทิ้ง → Health Happy UDR + Issara Plus — เบี้ยหักจากกองทุน มีมูลค่าสะสม
- เด็ก 15 วัน–10 ปี → Health Happy Kids — เหมาจ่าย IPD+OPD สำหรับเด็ก
- เดินทางต่างประเทศบ่อย → Infinite Care — คุ้มครองทั่วโลก
- กังวลเบี้ยแพงตอนแก่ → Health Happy UDR — เบี้ยคงที่ตลอดสัญญา"""
    },
    {
        "document_name": "KB-GAP-1C: Health Happy มีกี่แผน เบี้ยเท่าไหร่",
        "category": "health",
        "product_name": "AIA Health Happy",
        "section": "Health Happy plans and pricing",
        "chunk_text": """Health Happy มี 4 แผน:

แผน 1M — วงเงินสูงสุด 1 ล้านบาท/ปี ไม่มี OPD เบี้ยประมาณ 10,000–15,000 บาท/ปี (อายุ 30) ประมาณวันละ 34 บาท
แผน 5M — วงเงินสูงสุด 5 ล้านบาท/ปี ไม่มี OPD เบี้ยประมาณ 15,000–25,000 บาท/ปี (อายุ 30) ประมาณวันละ 55 บาท
แผน 15M — วงเงินสูงสุด 15 ล้านบาท/ปี ไม่มี OPD เบี้ยประมาณ 25,000–40,000 บาท/ปี (อายุ 30) ประมาณวันละ 89 บาท
แผน 25M — วงเงินสูงสุด 25 ล้านบาท/ปี มี OPD เบี้ยประมาณ 35,000–55,000 บาท/ปี (อายุ 30) ประมาณวันละ 123 บาท

ราคาเป็น range เบื้องต้น ตัวเลขจริงขึ้นอยู่กับอายุ เพศ สุขภาพ ติดต่อตัวแทนเพื่อคำนวณเบี้ยที่แม่นยำ
เบี้ยนี้เป็นค่า rider อย่างเดียว ต้องมีเบี้ยแบบหลักเพิ่มด้วย (เช่น Pay Life Plus)"""
    },
    {
        "document_name": "KB-GAP-1D: มีโบรชัวร์ประกันสุขภาพไหม",
        "category": "health",
        "product_name": "AIA Health Happy",
        "section": "Health Happy brochure summary",
        "chunk_text": """สรุปข้อมูล Health Happy สั้นๆ:
- เหมาจ่าย 4 แผน (1M/5M/15M/25M) ไม่ต้องสำรองจ่ายที่ รพ. เครือข่าย
- โรคร้ายแรงจ่ายเพิ่ม 2 เท่า ต่อเนื่อง 4 ปี
- อายุ 11–75 ปี คุ้มครองถึง 99 ปี

ดูรายละเอียดเพิ่มเติมได้ที่: https://www.iagencyaia.com/product/35334-50728/aia-health-happy — มีข้อมูลแผนทั้ง 4 เบี้ยเบื้องต้น ความคุ้มครอง และเงื่อนไขสำคัญ

สนใจแผนไหน บอกอายุมา คุณแบงค์ช่วยคำนวณเบี้ยจริงให้ได้"""
    },
    {
        "document_name": "KB-GAP-2: ประกันชีวิตแบบคุ้มครอง AIA",
        "category": "life-protection",
        "product_name": "Category: life-protection",
        "section": "life-protection overview",
        "chunk_text": """ประกันชีวิตเน้นคุ้มครอง AIA แบ่งเป็น 3 กลุ่ม:

ตลอดชีพ (Whole Life) — คุ้มครองถึง 99 ปี:
- Pay Life Plus — ยอดนิยม คุ้มครองตลอดชีพ + ผลประโยชน์เพิ่ม เหมาะเป็นแบบหลักแนบ rider สุขภาพ
- 20 Pay Life — จ่าย 20 ปี คุ้มครองถึง 99 ปี ทุน 1 ล้านขึ้นไป เบี้ยคงที่
- 10&15 Pay Life — จ่ายสั้น 10/15 ปี คุ้มครองตลอดชีพ
- Legacy Prestige — ทุน 10 ล้าน จ่าย 10/15 ปี สำหรับมรดก estate planning
- Legacy Prestige Plus — ทุน 10 ล้านขึ้นไป จ่าย 10/15/20 ปี ส่วนลด 5% ลดหย่อนภาษีได้ 100,000 บาท/ปี

ผู้สูงอายุ:
- Senior Happy — ไม่ต้องตอบคำถามสุขภาพ เหมาะกับพ่อแม่

เลือกยังไง:
- งบจำกัด ต้องการแบบหลักแนบ rider → Pay Life Plus
- จ่ายสั้น คุ้มครองยาว → 10&15 Pay Life
- ทุนสูง 10 ล้านขึ้นไป estate planning → Legacy Prestige Plus
- ซื้อให้พ่อแม่ ไม่อยากตรวจสุขภาพ → Senior Happy"""
    },
    {
        "document_name": "KB-GAP-3: Elite Income Prestige คืออะไร",
        "category": "unit-linked",
        "product_name": "AIA Elite Income Prestige (Unit Linked)",
        "section": "Elite Income Prestige overview",
        "chunk_text": """Elite Income Prestige เป็นประกันชีวิตควบการลงทุน (Unit-Linked) ที่เน้น passive income:

จุดเด่น:
- จ่ายเบี้ย 5 ปี แล้วได้เงินคืนอัตโนมัติตั้งแต่ปีแรก (Auto-Redemption)
- ลงทุนใน AIA Global Asset Income Fund (GAIF) กองทุนระดับโลก
- เบี้ยขั้นต่ำ 500,000 บาท/ปี

เหมาะกับ:
- คนที่มีเงินก้อน อยากให้เงินทำงานแล้วมีรายได้เข้ามาเรื่อยๆ
- ต้องการ passive income ไม่ต้องรอนาน

ข้อควรรู้:
- ผลตอบแทนไม่รับประกัน ขึ้นอยู่กับผลประกอบการของกองทุน
- แนบ rider สุขภาพ (UDR) ไม่ได้ เพราะจ่ายเบี้ยแค่ 5 ปี + auto-redemption ทำให้ unit value ลดเรื่อยๆ
- ถ้าต้องการ Elite Income + สุขภาพ → ทำ 2 กรมธรรม์แยก: Elite Income (ลงทุน) + Pay Life Plus + Health Happy (สุขภาพ)"""
    },
    {
        "document_name": "KB-GAP-4: แบบ Prestige ของ AIA มีอะไรบ้าง",
        "category": "prestige",
        "product_name": "Category: prestige",
        "section": "Prestige products overview",
        "chunk_text": """แบบ Prestige เป็นผลิตภัณฑ์สำหรับลูกค้าทุนสูง (10 ล้านบาทขึ้นไป) ได้สิทธิพิเศษ:

ประกันชีวิต Prestige:
- Legacy Prestige — ทุน 10 ล้าน จ่าย 10/15 ปี คุ้มครองถึง 99 ปี estate planning
- Legacy Prestige Plus — ทุน 10 ล้านขึ้นไป จ่าย 10/15/20 ปี ส่วนลดเบี้ย 5% + Privilege Program

Unit-Linked Prestige:
- Issara Prestige Plus — ยืดหยุ่นสุด ทุน 10 ล้านขึ้นไป ค่าธรรมเนียมปีแรกต่ำกว่า (50% vs 60%) + COI discount
- Smart Select Prestige — เน้นสะสมทรัพย์ ทุนสูง จัดพอร์ตได้
- 20 Pay Link Prestige — จ่าย 20 ปี คุ้มครองตลอดชีพ ระดับพรีเมียม
- Infinite Wealth Prestige — ลงทุนระดับสากล เน้นสะสมทรัพย์สูงสุด เหมาะกับ estate/retirement planning

สิทธิพิเศษ Prestige:
- ส่วนลดค่าการประกัน (COI discount)
- ค่าธรรมเนียมปีแรกต่ำกว่า
- Prestige Club — บริการระดับพิเศษ

เหมาะกับลูกค้าที่มีงบลงทุน 10 ล้านบาทขึ้นไป และต้องการบริการระดับสูง"""
    },
    {
        "document_name": "KB-GAP-5: CI Plus กับ Multi-Pay CI Plus ต่างกันยังไง",
        "category": "ci",
        "product_name": "Category: ci-rider",
        "section": "CI rider comparison",
        "chunk_text": """CI Plus กับ Multi-Pay CI Plus ต่างกันยังไง? ทั้งสองเป็น rider (สัญญาเพิ่มเติม PPR) แนบกับแบบหลักได้:

CI Plus — จ่ายครั้งเดียว (เจอ จ่าย จบ) จ่ายเมื่อตรวจพบ เบี้ยถูกกว่า เหมาะกับคนต้องการทุน CI ในราคาประหยัด
Multi-Pay CI Plus — จ่ายหลายครั้ง (เจอ จ่าย หลายจบ) จ่ายตามระดับ: ต้น กลาง รุนแรง เบี้ยสูงกว่า เหมาะกับคนต้องการคุ้มครองเต็มที่ จ่ายซ้ำได้

เปรียบเทียบกับแบบหลัก CI:
- CI SuperCare — เป็นแบบหลัก ซื้อเดี่ยวได้ จ่าย 20%/80%/100% ส่งเบี้ย 10/20 ปี เป็นที่นิยม
- CI ProCare — เป็นแบบหลัก จ่ายซ้ำ 5 ครั้ง + Vitality Bonus สูงสุด 9%

สรุป: งบจำกัดต้องการ rider → CI Plus | ต้องการ rider จ่ายหลายครั้ง → Multi-Pay CI Plus | ต้องการแบบหลัก CI → CI SuperCare หรือ CI ProCare"""
    },
    {
        "document_name": "KB-GAP-6: แนะนำแผนประกันรวม ครบทุกด้าน",
        "category": "general",
        "product_name": "Category: multiple",
        "section": "package recommendation",
        "chunk_text": """แพคเกจประกันยอดนิยมที่ครอบคลุมทุกด้าน:

แพคเกจ 1: คนทั่วไป (งบหลักหมื่น/ปี)
- แบบหลัก: Pay Life Plus — คุ้มครองชีวิตตลอดชีพ
- สุขภาพ: Health Happy แผน 5M — เหมาจ่าย 5 ล้าน
- อุบัติเหตุ: PA — คุ้มครอง 24 ชั่วโมง
- รวมเบี้ยเริ่มต้นหลักพันต่อเดือน

แพคเกจ 2: คุ้มครองครบทุกด้าน
- แบบหลัก: Legacy Prestige Plus — ชีวิตตลอดชีพ + มรดก
- สุขภาพ: Health Happy แผน 15M/25M — เหมาจ่ายสูง
- โรคร้าย: CI SuperCare — เจอ จ่าย หลายจบ
- อุบัติเหตุ: PA
- ลดหย่อนภาษีได้ทั้งชีวิต + สุขภาพ

แพคเกจ 3: ไม่อยากจ่ายทิ้ง
- แบบหลัก: Issara Plus — ลงทุนในกองทุน
- สุขภาพ: Health Happy UDR — เบี้ยคงที่หักจาก unit
- โรคร้าย: เสริมได้
- มีมูลค่ากรมธรรม์สะสม

แพคเกจ 4: ครอบครัว
- พ่อแม่: Legacy Prestige + Health Happy
- ลูก: แบบหลัก + Health Happy Kids
- ผู้สูงอายุ: Senior Happy (ไม่ต้องตรวจสุขภาพ)

บอกอายุ งบ และความต้องการมา คุณแบงค์ช่วยจัดแพคเกจที่เหมาะสมให้ได้"""
    },
    {
        "document_name": "KB-GAP-7: ประกันสะสมทรัพย์ AIA เปรียบเทียบ",
        "category": "savings",
        "product_name": "Category: savings",
        "section": "savings comparison",
        "chunk_text": """ประกันสะสมทรัพย์ AIA มี 4 แบบ:

5 Pay 10 — จ่ายเบี้ย 5 ปี คุ้มครอง 10 ปี จุดเด่น: จ่ายสั้น ได้เงินก้อน เหมาะกับออมระยะสั้น
Endowment 15/25 — จ่ายเบี้ย 15 ปี คุ้มครอง 25 ปี จุดเด่น: ได้เงินคืนเป็นงวด เหมาะกับการศึกษาบุตร
Excellent 20/20 — จ่ายเบี้ย 20 ปี คุ้มครอง 20 ปี จุดเด่น: เงินก้อนทุก 4 ปี ลดหย่อนภาษีไม่ต้องต่ออายุ เหมาะกับออมระยะยาว + ภาษี
Saving Sure — จ่ายเบี้ย 10 ปี คุ้มครองตลอดชีพ จุดเด่น: รับเงินเกษียณตลอดชีพ เหมาะกับวางแผนเกษียณ

เลือกยังไง:
- ออมสั้น 5 ปี ได้เงินก้อน → 5 Pay 10
- เก็บเงินให้ลูกเรียน → Endowment 15/25 (ได้เงินคืนตรงจังหวะค่าเทอม)
- ออมยาว + ลดหย่อนภาษีทุกปี → Excellent 20/20
- วางแผนเกษียณ + รายได้ตลอดชีพ → Saving Sure

ทุกแบบลดหย่อนภาษีได้สูงสุด 100,000 บาท/ปี (เบี้ยประกันชีวิต)"""
    },
]


def get_embeddings(texts):
    """Get dense + sparse embeddings from embedding-service."""
    payload = json.dumps({"texts": texts, "return_dense": True, "return_sparse": True}).encode()
    req = Request(EMBED_URL, data=payload, headers={"Content-Type": "application/json"})
    resp = urlopen(req, timeout=120)
    data = json.loads(resp.read())
    return data["dense"], data["sparse"]


def supabase_post(table, rows):
    """Insert rows to Supabase."""
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
    except Exception as e:
        if hasattr(e, 'read'):
            print(f"   ERROR body: {e.read().decode()[:500]}")
        raise


def estimate_tokens(text):
    """Rough token estimate for Thai+English text."""
    return max(len(text) // 3, len(text.split()))


def main():
    if not SUPABASE_KEY:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY not set")
        sys.exit(1)

    print(f"📦 Ingesting {len(KB_ENTRIES)} KB gap-fill entries...")
    print(f"🔗 Embed service: {EMBED_URL}")
    print(f"🗄️  Supabase: {SUPABASE_URL}")

    # Embed in batches
    all_texts = [e["chunk_text"] for e in KB_ENTRIES]
    all_dense = []
    all_sparse = []

    for i in range(0, len(all_texts), BATCH_SIZE):
        batch = all_texts[i:i + BATCH_SIZE]
        print(f"\n⚡ Embedding batch {i // BATCH_SIZE + 1}/{(len(all_texts) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch)} texts)...")
        dense, sparse = get_embeddings(batch)
        all_dense.extend(dense)
        all_sparse.extend(sparse)
        print(f"   ✅ Got {len(dense)} embeddings (dim={len(dense[0])})")

    # Build rows
    rows = []
    for idx, entry in enumerate(KB_ENTRIES):
        # Check for NaN in embeddings
        embedding = all_dense[idx]
        if any(v != v for v in embedding):  # NaN check
            print(f"   ⚠️  NaN detected in embedding for {entry['document_name']} — converting to 0.0")
            embedding = [0.0 if v != v else v for v in embedding]

        # pgvector expects string format "[0.1,0.2,...]"
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

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
            "sparse_embedding": all_sparse[idx],
            "metadata": {
                "pipeline": "ingest-kb-gap-fill-v1",
                "source_file": "Writer-Oracle/ψ/writing/kb-gap-fill-7-critical.md",
                "qa_status": "DocCon FULL PASS + Editor PASS",
                "gap_priority": "CRITICAL",
            },
        })

    # Upload to Supabase
    print(f"\n📤 Uploading {len(rows)} rows to kb_chunks...")
    result = supabase_post("kb_chunks", rows)
    print(f"   ✅ Inserted {len(result)} rows!")

    # Summary
    print(f"\n{'='*50}")
    print(f"✅ DONE — {len(result)} KB gap-fill entries ingested")
    print(f"   Source: {SOURCE}")
    print(f"   Categories: {', '.join(sorted(set(e['category'] for e in KB_ENTRIES)))}")
    print(f"   Products: {', '.join(sorted(set(e['product_name'] for e in KB_ENTRIES)))}")
    for r in result:
        print(f"   📄 id={r['id']} {r['document_name']}")


if __name__ == "__main__":
    main()
