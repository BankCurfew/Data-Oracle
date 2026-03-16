# OKR — Data-Oracle Q1 2026

> Objectives & Key Results | Prepared by: HR-Oracle | Period: March — May 2026

---

## Role-Specific OKRs

### Data-Oracle — Chief Data Engineer

**Objective 1**: รับ handoff data pipeline จาก Dev สำเร็จภายใน 1 สัปดาห์

| # | Key Result | Target | Deadline | Status |
|---|-----------|--------|----------|--------|
| KR1 | Complete knowledge transfer from Dev — AIA KB Phase 1-4 | Full handoff | Mar 22 | 🔵 Not Started |
| KR2 | Run all existing pipelines independently (no Dev support) | 100% | Mar 23 | 🔵 Not Started |
| KR3 | Document all pipeline architectures in `ψ/memory/learnings/` | 4 docs | Mar 23 | 🔵 Not Started |

---

**Objective 2**: ทำ AIA Knowledge Base ให้ครบและ production-ready

| # | Key Result | Target | Deadline | Status |
|---|-----------|--------|----------|--------|
| KR1 | Complete remaining AIA data phases (Phase 5+) | All phases done | Apr 05 | 🔵 Not Started |
| KR2 | Generate BGE-M3 embeddings for all KB documents | 100% coverage | Apr 10 | 🔵 Not Started |
| KR3 | Data quality score (validated, deduped, schema-correct) | >= 95% | Apr 10 | 🔵 Not Started |
| KR4 | Search accuracy (RAG pipeline returns relevant results) | >= 85% | Apr 15 | 🔵 Not Started |

---

**Objective 3**: สร้าง data pipeline framework ที่ reusable

| # | Key Result | Target | Deadline | Status |
|---|-----------|--------|----------|--------|
| KR1 | Standardized ETL template for new data sources | 1 template | Apr 01 | 🔵 Not Started |
| KR2 | Pipeline monitoring + alerting (fail loud) | Operational | Apr 15 | 🔵 Not Started |
| KR3 | Automated data quality checks (pre/post ingestion) | 5+ checks | Apr 15 | 🔵 Not Started |
| KR4 | Pipeline documentation — runbooks for each data source | 3+ runbooks | May 01 | 🔵 Not Started |

---

**Objective 4**: สนับสนุน MVP (OKR O3 ระดับ company)

| # | Key Result | Target | Deadline | Status |
|---|-----------|--------|----------|--------|
| KR1 | Provide structured data API for chatbot/search feature | Endpoint ready | Apr 20 | 🔵 Not Started |
| KR2 | Sub-second search latency on knowledge base | < 1s p95 | Apr 25 | 🔵 Not Started |
| KR3 | Zero data-related blockers for Dev during MVP sprint | 0 blockers | May 15 | 🔵 Not Started |

---

## KPIs

| KPI | Definition | Target | Cadence |
|-----|-----------|--------|---------|
| Pipeline Success Rate | % of pipeline runs that complete without error | >= 95% | Weekly |
| Data Freshness | Time from source update to KB availability | <= 24h | Daily |
| Ingestion Throughput | Documents processed per session | >= 50 | Per session |
| Data Quality Score | % of records passing all validation checks | >= 95% | Weekly |
| Embedding Coverage | % of KB documents with vector embeddings | 100% | Weekly |

---

*Data is the foundation. If the foundation is wrong, everything built on top will crumble.*
