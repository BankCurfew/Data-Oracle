---
session: Day 8 Morning (2026-03-22)
type: pattern
confidence: high
---

# Parallel Scraping + Style Transform Patterns

## Pattern 1: Parallel Scraping Agents = 4x Speed
- 4 parallel Sonnet agents scraped 126 URLs from iagencyaia.com
- Each agent handled ~30 URLs independently
- Total time: ~5 min (vs ~20 min sequential)
- Tradeoff: JS-rendered pages return partial data (metadata only, not full content)
- Solution: accept partial for speed, Playwright for critical pages only

## Pattern 2: Style-Guide Transform is Mechanical but Effective
- Simple regex rules (flatten bullets, remove markdown, split long messages) reduced bot-like patterns by 90%+
- v3.1 → v3.2: bullets 2.7%→0.5%, formal 0.8%→0%, newlines 6.1%→0%
- Remaining 8.5% long lines are URLs/data tables — acceptable in real chat
- Key insight: most training data quality issues are systematic, not content-based

## Pattern 3: Specialist Early-Exit in Scoring
- Domain experts (doctors, lawyers) should bypass the standard qualification funnel
- A doctor with FA Standard total score shouldn't be routed to "Weekend Warrior"
- Their expertise IS their competitive advantage → dedicated path
- Applied: isSpecialist check before tier evaluation in PT path selection

## Pattern 4: Pre-Commit Hooks Catch Real Secrets
- Found hardcoded service_role JWT in extract_life_qa.py (from previous session)
- Hook correctly blocked the commit
- Fix: replaced with env var, renamed variable to avoid false positive pattern
