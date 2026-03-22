#!/usr/bin/env python3
"""
Ingest KB Gap Fill v2 — 5 zero-coverage products into kb_chunks via Ollama BGE-M3.

Products:
1. MICRO500 (accident_pa)
2. MICRO1000 (accident_pa)
3. AIA NPA3000 (accident_pa)
4. AIA Care for Cancer - UDR (critical_illness_riders)
5. AIA Med Care Package (standalone_health)

Usage:
    python scripts/ingest-kb-gap-fill-v2.py --dry-run    # preview only
    python scripts/ingest-kb-gap-fill-v2.py              # embed + upload
"""

import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SB_AUTH = os.environ.get("SUPABASE_SERVICE_KEY", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

SOURCE = "kb-gap-fill-zero-coverage"
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024

KB_ENTRIES = [
    {
        "document_name": "MICRO500 — แผนประกันภัยไมโครอินชัวรันส์ เบี้ย 500 บาท/ปี",
        "category": "accident_pa",
        "product_name": "MICRO500",
        "section": "MICRO500 overview + benefits",
        "chunk_text": """MICRO500 — แผนประกันภัยไมโครอินชัวรันส์ เบี้ยประกันภัย 500 บาท/ปี

รับประกันภัยสำหรับขั้นอาชีพ 1 และ 2 เท่านั้น อายุ 6-60 ปี ต่ออายุได้ถึง 60 ปี
ใช้ใบคำขอฯ อุบัติเหตุส่วนบุคคล สำหรับรายย่อย (ไมโครอินชัวรันส์)

ความคุ้มครอง MICRO500:
- เสียชีวิต สูญเสียอวัยวะ สายตา หรือทุพพลภาพถาวรสิ้นเชิง: 100,000 บาท
- เสียชีวิต/สูญเสียอวัยวะจากอุบัติเหตุขณะขับขี่หรือโดยสารรถจักรยานยนต์: 50,000 บาท
- ชดเชยรายได้ระหว่างเข้ารักษาตัวในโรงพยาบาล: 200 บาท/วัน (สูงสุด 20 วัน/ปี)
- ค่าใช้จ่ายในการจัดการงานศพ (เสียชีวิตจากบาดเจ็บหรือเจ็บป่วย): 10,000 บาท
  (ยกเว้นเสียชีวิตจากเจ็บป่วยภายใน 180 วันแรก)
- คุ้มครองอุบัติเหตุในวันหยุดนักขัตฤกษ์และวันหยุดชดเชย: 100,000 บาท

เบี้ยประกันภัย: 500 บาท/ปี (ประมาณวันละ 1.37 บาท)

เหมาะกับ: คนทำงานอาชีพ 1-2 ที่ต้องการความคุ้มครองอุบัติเหตุพื้นฐานในราคาประหยัด
เทียบกับ MICRO100/200/300: วงเงินสูงกว่า + มีคุ้มครองวันหยุด + ชดเชยรายได้/วันสูงกว่า"""
    },
    {
        "document_name": "MICRO1000 — แผนประกันภัยไมโครอินชัวรันส์ เบี้ย 1,000 บาท/ปี",
        "category": "accident_pa",
        "product_name": "MICRO1000",
        "section": "MICRO1000 overview + benefits",
        "chunk_text": """MICRO1000 — แผนประกันภัยไมโครอินชัวรันส์ เบี้ยประกันภัย 1,000 บาท/ปี

รับประกันภัยสำหรับขั้นอาชีพ 1 และ 2 เท่านั้น อายุ 6-60 ปี ต่ออายุได้ถึง 60 ปี
ใช้ใบคำขอฯ อุบัติเหตุส่วนบุคคล สำหรับรายย่อย (ไมโครอินชัวรันส์)

ความคุ้มครอง MICRO1000:
- เสียชีวิต สูญเสียอวัยวะ สายตา หรือทุพพลภาพถาวรสิ้นเชิง: 200,000 บาท
- เสียชีวิต/สูญเสียอวัยวะจากอุบัติเหตุขณะขับขี่หรือโดยสารรถจักรยานยนต์: 100,000 บาท
- ชดเชยรายได้ระหว่างเข้ารักษาตัวในโรงพยาบาล: 400 บาท/วัน (สูงสุด 20 วัน/ปี)
- ค่าใช้จ่ายในการจัดการงานศพ (เสียชีวิตจากบาดเจ็บหรือเจ็บป่วย): 20,000 บาท
  (ยกเว้นเสียชีวิตจากเจ็บป่วยภายใน 180 วันแรก)
- คุ้มครองอุบัติเหตุในวันหยุดนักขัตฤกษ์และวันหยุดชดเชย: 200,000 บาท

เบี้ยประกันภัย: 1,000 บาท/ปี (ประมาณวันละ 2.74 บาท)

เหมาะกับ: คนทำงานอาชีพ 1-2 ที่ต้องการความคุ้มครองอุบัติเหตุสูงสุดในกลุ่มไมโคร
เทียบ MICRO500 vs MICRO1000: MICRO1000 วงเงินทุกข้อเป็น 2 เท่าของ MICRO500 เบี้ยเพิ่มแค่ 500 บาท/ปี — คุ้มค่ากว่ามาก"""
    },
    {
        "document_name": "MICRO500 vs MICRO1000 เปรียบเทียบ",
        "category": "accident_pa",
        "product_name": "MICRO500",
        "section": "MICRO500 vs MICRO1000 comparison",
        "chunk_text": """เปรียบเทียบ MICRO500 vs MICRO1000:

| ความคุ้มครอง | MICRO500 | MICRO1000 |
|-------------|----------|-----------|
| เสียชีวิต/ทุพพลภาพ | 100,000 | 200,000 |
| อุบัติเหตุมอเตอร์ไซค์ | 50,000 | 100,000 |
| ชดเชยรายได้/วัน | 200 | 400 |
| ค่าจัดการงานศพ | 10,000 | 20,000 |
| อุบัติเหตุวันหยุด | 100,000 | 200,000 |
| เบี้ย/ปี | 500 | 1,000 |

ทั้ง 2 แผน: อายุ 6-60 ปี ขั้นอาชีพ 1-2 เท่านั้น
ซื้อได้รวมทุกบริษัทไม่เกิน 2 กรมธรรม์/ราย

แนะนำ: MICRO1000 คุ้มค่ากว่า — จ่ายเพิ่ม 500 บาท/ปี ได้วงเงิน 2 เท่าทุกข้อ
ถ้างบจำกัดมาก → MICRO500 ก็เพียงพอสำหรับความคุ้มครองพื้นฐาน"""
    },
    {
        "document_name": "AIA NPA3000 — ประกันอุบัติเหตุส่วนบุคคล",
        "category": "accident_pa",
        "product_name": "AIA NPA3000",
        "section": "NPA3000 overview",
        "chunk_text": """AIA NPA3000 — ประกันอุบัติเหตุส่วนบุคคล (Personal Accident)

NPA3000 เป็นแผนประกันอุบัติเหตุส่วนบุคคลรายปี ในกลุ่ม NPA (Non-life Personal Accident)
อยู่ในกลุ่มเดียวกับ NPA5500 แต่เบี้ยและวงเงินต่ำกว่า

ลักษณะทั่วไป:
- ประกันอุบัติเหตุส่วนบุคคลแบบรายปี (Annual PA)
- คุ้มครอง: เสียชีวิต ทุพพลภาพ สูญเสียอวัยวะจากอุบัติเหตุ
- มีผลประโยชน์ค่ารักษาพยาบาลจากอุบัติเหตุ
- เบี้ยประกันภัย: 3,000 บาท/ปี
- ซื้อเป็นกรมธรรม์เดี่ยวได้ ไม่ต้องแนบกับแบบหลัก

เทียบกับ NPA5500:
- NPA5500 วงเงินสูงกว่า เบี้ย 5,500 บาท/ปี
- NPA3000 เหมาะกับคนที่ต้องการ PA พื้นฐานในราคาย่อมเยา

หมายเหตุ: สำหรับรายละเอียดความคุ้มครองเต็ม ติดต่อตัวแทนเพื่อขอโบรชัวร์ NPA3000 ฉบับเต็ม"""
    },
    {
        "document_name": "AIA Care for Cancer - UDR — ประกันโรคมะเร็ง ผ่าน Unit-Linked",
        "category": "critical_illness_riders",
        "product_name": "AIA Care for Cancer - UDR",
        "section": "Care for Cancer UDR overview",
        "chunk_text": """AIA Care for Cancer - UDR — สัญญาเพิ่มเติมคุ้มครองโรคมะเร็ง แบบ UDR

Care for Cancer - UDR เป็นสัญญาเพิ่มเติม (rider) คุ้มครองโรคมะเร็ง ที่ออกแบบมาสำหรับแนบกับกรมธรรม์ Unit-Linked เช่น Issara Plus, 20 Pay Link, Smart Select

ลักษณะเฉพาะ UDR:
- เบี้ยหักจาก unit value ของกรมธรรม์ Unit-Linked อัตโนมัติ
- เบี้ยคงที่ตลอดสัญญา (ต่างจาก PPR ที่เบี้ยปรับตามอายุ)
- ไม่ต้องจ่ายเบี้ยแยก — ระบบหักอัตโนมัติ

ความคุ้มครอง (เหมือน Care for Cancer ปกติ):
- ตรวจพบมะเร็งระยะลุกลาม → จ่ายเต็มทุนประกัน
- ตรวจพบมะเร็งระยะไม่ลุกลาม (Carcinoma in Situ) → จ่าย 20% ของทุน
- คุ้มครองมะเร็งทุกชนิด ทุกระยะ

เหมาะกับ:
- คนที่มีกรมธรรม์ Unit-Linked อยู่แล้ว ต้องการเสริมคุ้มครองมะเร็ง
- ต้องการเบี้ยคงที่ ไม่ปรับตามอายุ

เทียบกับ Care for Cancer (PPR):
- PPR: แนบกับแบบหลักทั่วไป (Pay Life Plus, 20 Pay Life ฯลฯ) เบี้ยปรับตามอายุ
- UDR: แนบกับ Unit-Linked เท่านั้น เบี้ยคงที่หักจาก unit

ข้อควรระวัง: ต้องดูแล unit value ให้เพียงพอ ถ้า unit value หมด สัญญาจะสิ้นผล"""
    },
    {
        "document_name": "AIA Med Care Package — แพคเกจประกันสุขภาพแบบเดี่ยว",
        "category": "standalone_health",
        "product_name": "AIA Med Care Package",
        "section": "Med Care Package overview",
        "chunk_text": """AIA Med Care Package — แพคเกจประกันสุขภาพที่ซื้อเดี่ยวได้ (Standalone)

Med Care Package เป็นแพคเกจประกันสุขภาพแบบพิเศษของ AIA ที่สามารถซื้อเป็นกรมธรรม์เดี่ยวได้ ไม่ต้องซื้อพร้อมแบบหลัก (ต่างจาก rider สุขภาพทั่วไปที่ต้องแนบกับแบบหลัก)

ลักษณะสำคัญ:
- ซื้อเดี่ยวได้ ไม่ต้องมีแบบหลัก — เหมาะกับคนที่ต้องการแค่ประกันสุขภาพ
- คุ้มครองค่ารักษาพยาบาลผู้ป่วยใน (IPD)
- มีหลายแผนให้เลือกตามวงเงิน

เหมาะกับ:
- คนที่ต้องการประกันสุขภาพอย่างเดียว ไม่ต้องการประกันชีวิต
- คนที่มีประกันชีวิตอยู่แล้ว ต้องการเสริมสุขภาพ
- คนงบจำกัด ไม่อยากจ่ายเบี้ยแบบหลัก

เทียบกับ Health Happy (rider):
- Health Happy ต้องซื้อพร้อมแบบหลัก (เช่น Pay Life Plus) — เบี้ยรวมสูงกว่า
- Med Care Package ซื้อเดี่ยวได้ — เบี้ยเฉพาะสุขภาพ
- Health Happy วงเงินสูงกว่า (1M-25M) — Med Care Package วงเงินต่ำกว่า

หมายเหตุ: สำหรับรายละเอียดแผนและเบี้ยเต็ม ติดต่อตัวแทนเพื่อขอโบรชัวร์ Med Care Package"""
    },
]


def ollama_embed(texts):
    """Get embeddings from Ollama BGE-M3."""
    embeddings = []
    for text in texts:
        payload = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
        req = Request(
            f"{OLLAMA_URL}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urlopen(req, timeout=120)
        data = json.loads(resp.read())
        emb = data["embeddings"][0]
        embeddings.append(emb)
    return embeddings


def supabase_post(table, rows):
    """Insert rows to Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    payload = json.dumps(rows, ensure_ascii=False).encode()
    req = Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "apikey": SB_AUTH,
        "Authorization": f"Bearer {SB_AUTH}",
        "Prefer": "return=representation",
    })
    try:
        resp = urlopen(req, timeout=60)
        return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()[:500] if hasattr(e, 'read') else str(e)
        print(f"   ERROR: {e.code} — {body}")
        raise


def estimate_tokens(text):
    return max(len(text) // 3, len(text.split()))


def main():
    dry_run = "--dry-run" in sys.argv

    if not SB_AUTH:
        print("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    print(f"=== KB Gap Fill v2 — {len(KB_ENTRIES)} entries ===")
    print(f"Ollama: {OLLAMA_URL} (model: {EMBED_MODEL})")
    print(f"Supabase: {SUPABASE_URL}")
    print()

    for i, entry in enumerate(KB_ENTRIES):
        print(f"  [{i+1}] {entry['product_name']} — {entry['document_name'][:60]}")

    if dry_run:
        print(f"\n[DRY RUN] Would embed and upload {len(KB_ENTRIES)} entries. Exiting.")
        return

    # Embed via Ollama BGE-M3
    print(f"\nEmbedding {len(KB_ENTRIES)} texts via Ollama {EMBED_MODEL}...")
    start = time.time()
    texts = [e["chunk_text"] for e in KB_ENTRIES]
    embeddings = ollama_embed(texts)
    elapsed = time.time() - start
    print(f"  Embedded {len(embeddings)} texts in {elapsed:.1f}s (dim={len(embeddings[0])})")

    # Validate embeddings
    for i, emb in enumerate(embeddings):
        nan_count = sum(1 for v in emb if v != v)
        if nan_count > 0:
            print(f"  WARNING: {nan_count} NaN values in embedding [{i}] — replacing with 0.0")
            embeddings[i] = [0.0 if v != v else v for v in emb]
        if len(emb) != EMBED_DIM:
            print(f"  WARNING: embedding [{i}] dim={len(emb)}, expected {EMBED_DIM}")

    # Build rows
    rows = []
    for idx, entry in enumerate(KB_ENTRIES):
        embedding_str = "[" + ",".join(str(v) for v in embeddings[idx]) + "]"
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
            "metadata": {
                "pipeline": "ingest-kb-gap-fill-v2",
                "gap_priority": "zero-coverage",
                "created_by": "Data-Oracle",
                "date": "2026-03-20",
            },
        })

    # Upload to Supabase
    print(f"\nUploading {len(rows)} rows to kb_chunks...")
    result = supabase_post("kb_chunks", rows)
    print(f"  Inserted {len(result)} rows!")

    # Summary
    print(f"\n{'='*50}")
    print(f"DONE — {len(result)} zero-coverage gap-fill entries ingested")
    print(f"  Source: {SOURCE}")
    products = sorted(set(e["product_name"] for e in KB_ENTRIES))
    print(f"  Products: {', '.join(products)}")
    for r in result:
        print(f"  id={r['id']} | {r['product_name']} | {r['document_name'][:60]}")

    # Verify zero-coverage resolved
    print(f"\nVerifying zero-coverage resolved...")
    from urllib.request import Request as Req
    for prod in products:
        from urllib.parse import quote
        req = Req(
            f"{SUPABASE_URL}/rest/v1/kb_chunks?product_name=eq.{quote(prod)}&select=id",
            headers={"apikey": SB_AUTH, "Authorization": f"Bearer {SB_AUTH}"},
        )
        resp = urlopen(req)
        count = len(json.loads(resp.read()))
        status = "COVERED" if count > 0 else "STILL ZERO"
        print(f"  {prod}: {count} chunks — {status}")


if __name__ == "__main__":
    main()
