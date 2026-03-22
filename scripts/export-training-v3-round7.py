#!/usr/bin/env python3
"""
Export Training Data v3 — Q&A pairs from 27K LINE chat for Jarvis Bot round 7.

Strategy:
1. Pull high-value tagged conversations from Supabase
2. Build customer→agent Q&A pairs from conversation flow
3. Add objection scripts from Researcher analysis
4. Add 10 conversation flow templates
5. Export as JSONL for fine-tuning

Usage:
    python3 scripts/export-training-v3-round7.py --dry-run    # preview stats
    python3 scripts/export-training-v3-round7.py              # full export
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://heciyiepgxqtbphepalf.supabase.co")
SB_AUTH = os.environ.get("SUPABASE_SERVICE_KEY", "")

OUTPUT_DIR = "data/training"
DATE = "2026-03-20"

SYSTEM_PROMPT = """คุณคือ Jarvis Bot — ผู้ช่วยตัวแทนประกันชีวิต AIA (iAgencyAIA) ที่เชี่ยวชาญ
หน้าที่: ตอบคำถามลูกค้าเกี่ยวกับผลิตภัณฑ์ AIA, ช่วยปิดการขาย, จัดการข้อโต้แย้ง, และให้บริการหลังการขาย
สไตล์: สุภาพ เป็นมิตร ใช้ภาษาไทย ตอบตรงประเด็น ให้ข้อมูลถูกต้อง ใช้ข้อความสั้นกระชับ ไม่เกิน 300 ตัวอักษรต่อข้อความ
ห้าม: ให้ข้อมูลเท็จ, สัญญาสิ่งที่ทำไม่ได้, เปิดเผยข้อมูลลูกค้า, ส่ง profile link เมื่อลูกค้าลังเล, ส่ง data collection form ก่อนถาม needs"""

OBJECTION_SYSTEM = SYSTEM_PROMPT + """
สถานการณ์: ลูกค้ามีข้อกังวล/ข้อโต้แย้ง ต้องรับฟัง เข้าใจ ให้ข้อมูลชัดเจน และพยายามแก้ข้อกังวล"""

CLOSING_SYSTEM = SYSTEM_PROMPT + """
สถานการณ์: ลูกค้าสนใจและพร้อมสมัคร ต้อง guide ขั้นตอน iSign + เอกสารที่ใช้ + วิธีชำระเบี้ย"""

# High-value tags to extract (priority order)
PRIORITY_TAGS = [
    "winning_response",   # 15 — gold tier
    "objection",          # 44 — objection handling
    "closing",            # 10 — closing patterns
    "comparison",         # 23 — product comparison
    "sales-process",      # 224 — full sales cycle
    "pricing",            # 640 — premium Q&A
    "health-insurance",   # 1,154
    "life-insurance",     # 1,307
    "critical-illness",   # 232
    "savings-investment", # 172
    "child-insurance",    # (subset of health)
    "claims-service",     # claims handling
    "pre-existing",       # pre-existing conditions
]

# Tags to SKIP
SKIP_TAGS = {"internal-chat", "greeting", "introduction"}

# Noise patterns
NOISE_PATTERNS = [
    r"^(สวัสดี|ดี|หวัดดี|hello|hi|hey|ok|ครับ|ค่ะ|ขอบคุณ|ดีจ้า|ดีค่ะ|ดีครับ|555|ไม่เป็นไร|โอเค|จ้า|อืม|ได้เลย|ได้ครับ|ได้ค่ะ|ตกลง|รับทราบ|เรียบร้อย|ดีจ้ะ|ค่า|จ๊ะ|คะ|นะคะ|ขอบคุณมากค่ะ|สวัสดีค่ะ|สวัสดีครับ)\s*$",
    r"^https?://",
    r"^iAgencyAIA\.com$",
    r"^\[?(รูปภาพ|sticker|image|photo|video|วิดีโอ|ไฟล์)\]?$",
    r"^(D\.|MAY \(|Dream Arthit|Front |ex_jira)",
    r"^\d{1,2}[\./]\d{1,2}[\./]\d{2,4}$",  # dates only
]

TAG_TO_CATEGORY = {
    "health-insurance": "health",
    "life-insurance": "life",
    "critical-illness": "ci",
    "savings-investment": "savings",
    "accident": "accident",
    "pricing": "pricing",
    "claims-service": "claims",
    "objection": "objection",
    "sales-process": "sales",
    "child-insurance": "kids",
    "comparison": "comparison",
    "closing": "closing",
    "pre-existing": "pre_existing",
    "winning_response": "winning",
    "general-inquiry": "general",
}


def supabase_get(path):
    req = Request(f"{SUPABASE_URL}/rest/v1/{path}", headers={
        "apikey": SB_AUTH, "Authorization": f"Bearer {SB_AUTH}"
    })
    return json.loads(urlopen(req, timeout=30).read())


def supabase_get_all(path):
    """Paginated GET — fetch all rows."""
    all_rows = []
    offset = 0
    while True:
        sep = "&" if "?" in path else "?"
        rows = supabase_get(f"{path}{sep}limit=1000&offset={offset}&order=id")
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    return all_rows


def is_noise(text):
    if not text or len(text.strip()) < 4:
        return True
    for p in NOISE_PATTERNS:
        if re.match(p, text.strip(), re.IGNORECASE):
            return True
    return False


def clean_text(text):
    if not text:
        return None
    text = text.strip()
    # Remove agent prefixes
    text = re.sub(r"^(D\.\s*|MAY \(เลขาคุณดรีม\)\s*|Dream Arthit\s*|Front\s+|iAgencyAIA\.com\s*)", "", text)
    # Remove contact codes
    text = re.sub(r"^(CL|CG|A)\d+[\.\s]\S+\s*", "", text)
    # Redact PII
    text = re.sub(r"0[689]\d[\s-]?\d{3}[\s-]?\d{4}", "[เบอร์โทร]", text)
    text = re.sub(r"\d{1}-\d{4}-\d{5}-\d{2}-\d{1}", "[เลขบัตร]", text)
    text = re.sub(r"[A-Z]\d{8,}", "[เลขกรมธรรม์]", text)
    text = text.strip()
    return text if len(text) >= 5 else None


def get_category(tags):
    for t in PRIORITY_TAGS:
        if t in tags:
            return TAG_TO_CATEGORY.get(t, "general")
    return "general"


def get_system_prompt(tags):
    if "objection" in tags:
        return OBJECTION_SYSTEM
    if "closing" in tags:
        return CLOSING_SYSTEM
    return SYSTEM_PROMPT


def build_qa_pairs_from_conversations(conversations):
    """Build Q&A pairs from grouped conversation messages."""
    pairs = []

    for conv_id, messages in conversations.items():
        # Sort by timestamp
        messages.sort(key=lambda m: m["timestamp"] or "")

        # Collect tags from all messages in this conversation
        conv_tags = set()
        for m in messages:
            if m.get("tags"):
                tags = m["tags"]
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = [tags]
                for t in tags:
                    conv_tags.add(t)

        # Skip internal-only conversations
        if conv_tags.issubset(SKIP_TAGS):
            continue

        # Build Q&A pairs: find customer msg followed by agent msg
        i = 0
        while i < len(messages) - 1:
            # Find customer message
            if messages[i]["sender"] == "customer":
                q_text = messages[i]["message_text"]
                q_tags = messages[i].get("tags", [])
                if isinstance(q_tags, str):
                    try:
                        q_tags = json.loads(q_tags)
                    except:
                        q_tags = [q_tags]

                # Collect consecutive agent responses
                agent_parts = []
                j = i + 1
                while j < len(messages) and messages[j]["sender"] == "agent":
                    agent_parts.append(messages[j]["message_text"])
                    j += 1

                if agent_parts and not is_noise(q_text):
                    # Combine agent messages (max 3 to keep reasonable length)
                    a_text = "\n".join(agent_parts[:3])

                    q_clean = clean_text(q_text)
                    a_clean = clean_text(a_text)

                    if q_clean and a_clean and len(q_clean) >= 8 and len(a_clean) >= 10:
                        all_tags = list(conv_tags.union(set(q_tags)))
                        category = get_category(all_tags)
                        is_winning = "winning_response" in all_tags

                        pairs.append({
                            "question": q_clean,
                            "answer": a_clean,
                            "tags": all_tags,
                            "category": category,
                            "conv_id": conv_id,
                            "is_winning": is_winning,
                            "is_objection": "objection" in all_tags,
                            "is_closing": "closing" in all_tags,
                        })

                    i = j
                    continue
            i += 1

    return pairs


# 8 Objection handling scripts from Researcher analysis
OBJECTION_SCRIPTS = [
    {
        "question": "เบี้ยแพงเกินไป จ่ายไม่ไหว",
        "answer": "เข้าใจค่ะ มีแผนเบี้ยถูกกว่าให้ดูค่ะ: Health Saver 500K เบี้ยเริ่ม ~12,000/ปี หรือเพิ่ม Deductible 30K ลดเบี้ยได้อีก ส่งเปรียบเทียบให้ไหมคะ?",
        "category": "objection",
    },
    {
        "question": "ขอคิดดูก่อนนะคะ",
        "answer": "ได้เลยค่ะ แจ้งว่า Health Happy ปิดรับ 31 มี.ค. นี้ หลังจากนั้นจะเป็นแผนร่วมจ่ายค่ะ ถ้าตัดสินใจก่อนได้แผนเดิมที่ดีกว่า มีสงสัยทักมาได้เลยนะคะ",
        "category": "objection",
    },
    {
        "question": "พอแข่งราคากับที่อื่นได้ไหม มีผลิตภัณฑ์เปรียบเทียบให้ดูไหม",
        "answer": "ได้ค่ะ AIA จุดเด่น: ทุนสูงสุด 25M + เบิ้ล 2x โรคร้าย + Smart Network 1,249 รพ. + ไม่ต้องสำรองจ่าย ส่ง iCompare เปรียบเทียบให้ดูไหมคะ?",
        "category": "objection",
    },
    {
        "question": "จะติดปัญหาโรคประจำตัวไหม มีประวัติการรักษา",
        "answer": "ถ้าเคยเป็นแล้วหายขาด สามารถแถลงตามจริง บริษัทอาจรับทำแบบมีข้อยกเว้น ถ้าหาย 2 ปี ถอดข้อยกเว้นได้ค่ะ แนะนำแถลงตามจริงเสมอนะคะ",
        "category": "objection",
    },
    {
        "question": "ร่วมจ่ายคืออะไร copayment เริ่มเมื่อไหร่",
        "answer": "Copayment = ผู้เอาประกันร่วมจ่ายบางส่วนค่ารักษา เริ่มบังคับใช้แล้วค่ะ แต่ AIA มีแผน Balanced + Smart Network ที่ร่วมจ่าย 0% เท่ากับไม่ต้องจ่ายเพิ่มเลย เป็นเงื่อนไขทั้งวงการ ไม่ใช่แค่ AIA",
        "category": "objection",
    },
    {
        "question": "เบี้ยที่จ่ายคือจ่ายทิ้งหรอคะ",
        "answer": "ถ้าเป็นประกันสุขภาพ = เบี้ยจ่ายทิ้ง แต่คุ้มครองค่ารักษาจริง (ป่วยครั้งเดียวคุ้มทั้งปี) ถ้าอยากได้แบบมีเงินคืน → Unit Linked หรือสะสมทรัพย์ค่ะ บอกงบมา ช่วยหาแผนที่เหมาะสมให้ได้",
        "category": "objection",
    },
    {
        "question": "ซื้อออนไลน์ได้ไหม ต้องเจอหน้าไหม",
        "answer": "สมัครออนไลน์ได้ค่ะ ผ่านระบบ AIA iSign สะดวก ง่าย ปลอดภัย ไม่ต้องเจอหน้ากัน ใช้บัตรประชาชน + selfie + ชำระเบี้ยผ่านบัตรเครดิต/โอนได้เลย ส่ง link ให้เลยนะคะ",
        "category": "objection",
    },
    {
        "question": "เสียชีวิตช่วงก่อนครบสัญญา เบี้ยที่จ่ายไปคืนไหม",
        "answer": "กรณีเสียชีวิต ได้รับทุนประกันชีวิตค่ะ ไม่ใช่คืนเบี้ย แต่ได้ทุนเต็ม เช่น ทุน 1M จ่ายไป 3 ปี ก็ได้ 1M เต็มเลยค่ะ นี่คือจุดเด่นของประกันชีวิต — คุ้มครองตั้งแต่วันแรก",
        "category": "objection",
    },
]

# 10 Conversation flow templates
FLOW_TEMPLATES = [
    {
        "question": "สอบถามเรื่องประกันค่ะ",
        "answer": "สวัสดีค่ะ ยินดีให้บริการค่ะ สนใจประกันประเภทไหนคะ?\n\n1. ประกันสุขภาพ — คุ้มครองค่ารักษาพยาบาล\n2. ประกันชีวิต — คุ้มครองครอบครัว\n3. โรคร้ายแรง — เจอจ่ายจบ\n4. ออมทรัพย์/ลงทุน — สะสมเงินพร้อมคุ้มครอง\n5. ประกันเด็ก — ดูแลลูกน้อย\n\nหรือบอกความต้องการมา ช่วยแนะนำให้ได้ค่ะ",
        "category": "greeting",
    },
    {
        "question": "สนใจประกันสุขภาพ อยากดูแผนที่เหมาะสม",
        "answer": "ดีค่ะ ขอถามข้อมูลเบื้องต้นนะคะ:\n1. อายุเท่าไหร่คะ?\n2. เคยมีประกันสุขภาพมาก่อนไหมคะ?\n3. สนใจวงเงินค่ารักษาประมาณเท่าไหร่คะ? (1M / 5M / 15M / 25M)\n4. มีงบเบี้ยต่อปีประมาณเท่าไหร่คะ?\n5. มีโรคประจำตัวไหมคะ?",
        "category": "health",
    },
    {
        "question": "สนใจประกันชีวิต",
        "answer": "ดีค่ะ ประกันชีวิตมีหลายวัตถุประสงค์ สนใจด้านไหนคะ?\n\n1. คุ้มครองครอบครัว — Pay Life Plus, 20 Pay Life\n2. ออมเงิน/ลดหย่อนภาษี — Saving Sure, Excellent, 5Pay10\n3. มรดก/Estate Planning — Legacy Prestige Plus (ทุน 10M+)\n4. ลงทุน + คุ้มครอง — Issara Plus, 20 Pay Link\n\nบอกอายุกับความต้องการมา ช่วยหาแผนที่เหมาะสมให้ค่ะ",
        "category": "life",
    },
    {
        "question": "ประกันสุขภาพเด็ก มีแบบไหนบ้าง",
        "answer": "ประกันสุขภาพเด็ก AIA มี 2 แบบค่ะ:\n\n1. Health Happy Kids — เหมาจ่าย IPD+OPD สำหรับเด็ก 15 วัน–10 ปี โตแล้วเปลี่ยนเป็น Health Happy ผู้ใหญ่ได้\n2. Health Happy Kids - UDR — เบี้ยคงที่ หักจาก Unit-Linked\n\nน้องอายุเท่าไหร่คะ? แล้วสนใจวงเงินประมาณเท่าไหร่?",
        "category": "kids",
    },
    {
        "question": "สนใจประกันโรคร้ายแรง เจอจ่ายจบ",
        "answer": "ประกันโรคร้ายแรง AIA มีหลายแบบค่ะ:\n\n- CI SuperCare — แบบหลัก ซื้อเดี่ยวได้ จ่าย 20%/80%/100% ตามระดับ เป็นที่นิยม\n- CI ProCare — แบบหลัก จ่ายซ้ำ 5 ครั้ง + Vitality Bonus สูงสุด 9%\n- CI Plus — rider แนบกับแบบหลัก เจอจ่ายจบ เบี้ยถูกกว่า\n- Care for Cancer — คุ้มครองเฉพาะมะเร็ง เบี้ยต่ำ\n\nอายุเท่าไหร่คะ? สนใจทุน CI เท่าไหร่?",
        "category": "ci",
    },
    {
        "question": "ขอเปรียบเทียบแผนสุขภาพ 2-3 แผน",
        "answer": "ได้เลยค่ะ ส่ง iCompare ให้เปรียบเทียบแบบละเอียดนะคะ บอกอายุกับเพศมา ช่วยคำนวณเบี้ยจริงให้ค่ะ\n\nตัวอย่างเปรียบเทียบ (อายุ 30 หญิง):\n- Health Saver 500K → เบี้ย ~12,000/ปี มี OPD\n- Health Happy 5M → เบี้ย ~20,000/ปี เหมาจ่ายเต็ม\n- Infinite Care → เบี้ย ~35,000/ปี คุ้มครองทั่วโลก\n\nสนใจแผนไหนเป็นพิเศษคะ?",
        "category": "comparison",
    },
    {
        "question": "ตัดสินใจแล้ว อยากสมัครเลย",
        "answer": "ยินดีมากค่ะ ขั้นตอนสมัครง่ายๆ ผ่าน AIA iSign:\n\n1. ส่ง link ใบสมัครให้ทาง LINE\n2. กรอกข้อมูล + ถ่ายรูปบัตรประชาชน + selfie\n3. ตอบแบบสอบถามสุขภาพ\n4. ชำระเบี้ย (บัตรเครดิต 0% 6 เดือน / โอนเงิน)\n5. รอพิจารณา 1-3 วันทำการ\n\nใช้เอกสาร: สำเนาบัตรประชาชน + สมุดบัญชี ส่ง link ให้เลยนะคะ",
        "category": "closing",
    },
    {
        "question": "จะเคลมประกันยังไง",
        "answer": "เคลมได้ 3 ช่องทางค่ะ:\n\n1. AIA+ App — สะดวกที่สุด ถ่ายรูปเอกสารส่งได้เลย\n2. AIA iClaim — ผ่านเว็บ\n3. โทร AIA 1581 — จันทร์-ศุกร์ 8:00-20:00\n\nเอกสารที่ใช้: ใบเสร็จค่ารักษา + ใบรับรองแพทย์ + สำเนาบัตรประชาชน\n\nถ้าเข้า รพ. เครือข่าย AIA ไม่ต้องสำรองจ่ายค่ะ แจ้งเลข กรมธรรม์ตอนเข้า รพ. ได้เลย",
        "category": "claims",
    },
    {
        "question": "ผ่อนเบี้ยได้ไหม จ่ายรายเดือนได้ไหม",
        "answer": "ผ่อนได้ค่ะ มีหลายวิธี:\n\n1. ผ่อน 0% ผ่านบัตรเครดิต 6 เดือน (ธนาคารที่ร่วมรายการ)\n2. จ่ายรายเดือน — เบี้ยจะแพงกว่ารายปีเล็กน้อย\n3. จ่ายราย 6 เดือน / ราย 3 เดือน\n\nแนะนำ: จ่ายรายปี + ผ่อนบัตรเครดิต 0% คุ้มที่สุดค่ะ ไม่มีค่าธรรมเนียมเพิ่ม บอกยอดเบี้ย ช่วยดูตัวเลือกให้ค่ะ",
        "category": "pricing",
    },
    {
        "question": "ลดหย่อนภาษีได้เท่าไหร่",
        "answer": "ลดหย่อนภาษีได้ตามประเภทค่ะ:\n\n- เบี้ยประกันชีวิต → สูงสุด 100,000 บาท/ปี\n- เบี้ยประกันสุขภาพ → สูงสุด 25,000 บาท/ปี (รวมชีวิตไม่เกิน 100,000)\n- เบี้ยประกันบำนาญ → สูงสุด 200,000 บาท/ปี\n\nรวมลดหย่อนได้สูงสุดถึง 300,000 บาท/ปี ยิ่งเสียภาษีสูง ยิ่งคุ้ม บอกรายได้มา ช่วยคำนวณภาษีที่ประหยัดได้ค่ะ",
        "category": "pricing",
    },
]

# AIA competitive advantages for competitor objections
COMPETITOR_SCRIPTS = [
    {
        "question": "AIA เปรียบเทียบกับเมืองไทยประกันชีวิต D Health Plus ยังไง",
        "answer": "AIA Health Happy vs เมืองไทย D Health Plus — จุดเด่น AIA:\n\n1. เหมาจ่ายเต็ม ไม่มี sub-limit ค่าห้อง (เมืองไทยมี sub-limit)\n2. โรคร้ายแรงจ่ายเพิ่ม 2 เท่า ต่อเนื่อง 4 ปี\n3. Smart Network 1,249 รพ. ไม่ต้องสำรองจ่าย\n4. วงเงินสูงสุด 25M/ปี\n5. มีแผน UDR เบี้ยคงที่ตลอดสัญญา\n\nส่ง iCompare ให้เปรียบเทียบตัวเลขจริงไหมคะ?",
        "category": "comparison",
    },
    {
        "question": "FWD ถูกกว่า AIA ไม่ใช่เหรอ",
        "answer": "FWD Easy E-Health เบี้ยเริ่มถูกกว่าจริงค่ะ แต่ AIA Health Happy จุดเด่นกว่า:\n\n1. วงเงินสูงกว่า (25M vs 5M)\n2. Smart Network 1,249 รพ. ไม่ต้องสำรองจ่าย (FWD มีน้อยกว่า)\n3. Copayment 0% ที่ รพ. เครือข่าย (FWD ร่วมจ่ายบางแผน)\n4. โรคร้าย 2x ต่อเนื่อง 4 ปี (FWD ไม่มี)\n\nเบี้ยถูกกว่า แต่คุ้มครองน้อยกว่า — ดูที่ความคุ้มครองรวมค่ะ",
        "category": "comparison",
    },
    {
        "question": "AIA Care for Cancer เทียบกับ FWD Cancer Fighter ยังไง",
        "answer": "AIA Care for Cancer vs FWD Cancer Fighter:\n\n1. AIA จ่าย 20% ระยะไม่ลุกลาม + 100% ระยะลุกลาม (FWD จ่ายเฉพาะลุกลาม)\n2. AIA มีแบบ UDR เบี้ยคงที่ (FWD ไม่มี)\n3. AIA แนบกับ rider อื่นได้ (CI Plus, Health Happy)\n4. AIA network รพ. ใหญ่กว่า\n\nถ้าต้องการคุ้มครองมะเร็งครบทุกระยะ AIA ดีกว่าค่ะ บอกอายุมา ส่งเบี้ยจริงให้ดู",
        "category": "comparison",
    },
]


def main():
    dry_run = "--dry-run" in sys.argv

    if not SB_AUTH:
        print("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    print(f"=== Export Training v3 — Round 7 ===")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Date: {DATE}")

    # Step 1: Pull conversations with high-value tags
    print(f"\n[1/4] Pulling LINE chat conversations...")
    start = time.time()
    all_msgs = supabase_get_all("line_chat_history?select=id,conversation_id,sender,message_text,timestamp,tags")
    print(f"  Fetched {len(all_msgs)} messages in {time.time()-start:.1f}s")

    # Group by conversation
    conversations = {}
    for m in all_msgs:
        cid = m["conversation_id"]
        if cid not in conversations:
            conversations[cid] = []
        conversations[cid].append(m)

    print(f"  {len(conversations)} conversations")

    # Filter conversations with high-value tags
    valuable_convs = {}
    for cid, msgs in conversations.items():
        conv_tags = set()
        for m in msgs:
            if m.get("tags"):
                tags = m["tags"]
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = [tags]
                for t in tags:
                    conv_tags.add(t)

        has_value = any(t in conv_tags for t in PRIORITY_TAGS)
        not_just_internal = not conv_tags.issubset(SKIP_TAGS)
        if has_value and not_just_internal:
            valuable_convs[cid] = msgs

    print(f"  {len(valuable_convs)} valuable conversations (with priority tags)")

    # Step 2: Build Q&A pairs
    print(f"\n[2/4] Building Q&A pairs from conversations...")
    raw_pairs = build_qa_pairs_from_conversations(valuable_convs)
    print(f"  {len(raw_pairs)} raw Q&A pairs extracted")

    # Dedup by question
    seen = set()
    unique_pairs = []
    for p in raw_pairs:
        key = p["question"][:80].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)
    print(f"  {len(unique_pairs)} after dedup (removed {len(raw_pairs)-len(unique_pairs)} dups)")

    # Step 3: Add scripted examples
    print(f"\n[3/4] Adding scripted training examples...")
    scripted = []

    # Objection scripts
    for obj in OBJECTION_SCRIPTS:
        key = obj["question"][:80].lower()
        if key not in seen:
            seen.add(key)
            scripted.append({
                "question": obj["question"],
                "answer": obj["answer"],
                "tags": ["objection"],
                "category": "objection",
                "conv_id": "scripted-objection",
                "is_winning": True,
                "is_objection": True,
                "is_closing": False,
            })

    # Flow templates
    for flow in FLOW_TEMPLATES:
        key = flow["question"][:80].lower()
        if key not in seen:
            seen.add(key)
            scripted.append({
                "question": flow["question"],
                "answer": flow["answer"],
                "tags": [flow["category"]],
                "category": flow["category"],
                "conv_id": "scripted-flow",
                "is_winning": True,
                "is_objection": False,
                "is_closing": flow["category"] == "closing",
            })

    # Competitor scripts
    for comp in COMPETITOR_SCRIPTS:
        key = comp["question"][:80].lower()
        if key not in seen:
            seen.add(key)
            scripted.append({
                "question": comp["question"],
                "answer": comp["answer"],
                "tags": ["comparison", "objection"],
                "category": "comparison",
                "conv_id": "scripted-competitor",
                "is_winning": True,
                "is_objection": True,
                "is_closing": False,
            })

    print(f"  +{len(scripted)} scripted examples (objections + flows + competitor)")

    all_pairs = unique_pairs + scripted
    print(f"  Total: {len(all_pairs)} training pairs")

    # Step 4: Format as JSONL
    print(f"\n[4/4] Formatting JSONL...")

    results = []
    for p in all_pairs:
        system = get_system_prompt(p["tags"])
        source = "scripted" if p["conv_id"].startswith("scripted") else "line_chat_27k"

        results.append({
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": p["question"]},
                {"role": "assistant", "content": p["answer"]},
            ],
            "metadata": {
                "type": "objection_handling" if p["is_objection"] else "closing" if p["is_closing"] else "qa",
                "category": p["category"],
                "tags": p["tags"],
                "source": source,
                "is_winning": p["is_winning"],
                "round": 7,
            },
        })

    # Stats
    from collections import Counter
    cats = Counter(r["metadata"]["category"] for r in results)
    types = Counter(r["metadata"]["type"] for r in results)
    sources = Counter(r["metadata"]["source"] for r in results)
    winning = sum(1 for r in results if r["metadata"]["is_winning"])

    print(f"\n{'='*60}")
    print(f"TRAINING DATA v3 — ROUND 7")
    print(f"{'='*60}")
    print(f"\n  Total examples: {len(results)}")
    print(f"  Winning responses: {winning}")
    print(f"\n  By source:")
    for s, n in sources.most_common():
        print(f"    {s}: {n}")
    print(f"\n  By category:")
    for c, n in cats.most_common():
        print(f"    {c}: {n}")
    print(f"\n  By type:")
    for t, n in types.most_common():
        print(f"    {t}: {n}")

    if dry_run:
        print(f"\n[DRY RUN] Would write {len(results)} examples. Exiting.")
        print(f"\nSample (first 3):")
        for r in results[:3]:
            print(f"  [{r['metadata']['category']}] Q: {r['messages'][1]['content'][:60]}...")
            print(f"           A: {r['messages'][2]['content'][:60]}...")
        return

    # Write JSONL
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    jsonl_path = os.path.join(OUTPUT_DIR, f"jarvis_finetune_v3_round7_{DATE}.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n  JSONL → {jsonl_path}")

    # Write stats
    stats = {
        "created_at": datetime.now().isoformat(),
        "version": "v3",
        "round": 7,
        "source": "line_chat_27k + scripted (objections, flows, competitor)",
        "total_examples": len(results),
        "winning_responses": winning,
        "categories": dict(cats),
        "types": dict(types),
        "sources": dict(sources),
        "system_prompt": SYSTEM_PROMPT,
        "improvements_over_v2": [
            "Full 27K messages (vs 9.9K in v2)",
            "+8 objection scripts from Researcher analysis",
            "+10 conversation flow templates",
            "+3 competitor comparison scripts",
            "Better noise filtering",
            "Multi-message agent responses combined",
        ],
    }
    stats_path = os.path.join(OUTPUT_DIR, f"jarvis_finetune_v3_round7_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  Stats → {stats_path}")

    print(f"\n  {len(results)} training examples ready for Jarvis Bot round 7 🎯")


if __name__ == "__main__":
    main()
