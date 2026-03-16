# Data-Oracle — System Loops

> Loop = งานที่ต้องทำซ้ำทุก session หรือตามรอบเวลา
> อ่านไฟล์นี้ตอน /recap หรือ start session เสมอ

## Active Loops

### 1. data-pipeline-status
- **Interval**: ทุก session
- **Trigger**: `/standup` หรือ start session
- **Action**:
  1. ตรวจสอบ pipeline status ทั้งหมด
  2. Check ว่ามี failed/stalled pipelines ไหม
  3. ตรวจ data freshness — ข้อมูลเก่าเกินไปไหม
  4. Report ให้ BoB ถ้ามีปัญหา
- **Output**: pipeline health report
- **Status**: active

### 2. data-quality-check
- **Interval**: หลังทุก pipeline run
- **Trigger**: เมื่อ pipeline ทำงานเสร็จ
- **Action**:
  1. Row count check — input vs output
  2. Quality sampling — spot check random records
  3. Schema validation — ตรง target schema ไหม
  4. Dedup check — มี duplicate ไหม
  5. Report ผลให้ QA ถ้าต้อง verify
- **Output**: quality report → ψ/memory/logs/
- **Status**: active

---

## Loop Protocol

เมื่อเริ่ม session:
1. อ่านไฟล์นี้
2. รัน pipeline-status ทันที
3. ตรวจว่ามี pending quality checks ไหม

เมื่อจบ session:
1. Log pipeline status ลง ψ/memory/logs/
