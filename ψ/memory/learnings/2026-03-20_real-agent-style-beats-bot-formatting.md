---
date: 2026-03-20
type: learning
tags: [training-data, style-guide, line-chat, agent-patterns, bot-training]
---

# Real Agent Style Beats Bot Formatting — Data Proves It

## Discovery

Analyzed 5,544 real agent messages from LINE OA (27K total, 828 contacts) to understand how successful insurance agents actually communicate vs how Jarvis Bot was trained to respond.

## Key Numbers

- Agent median message length: **50 characters** (bot was generating 300+)
- Messages with no \n: **99.2%** (bot used \n constantly)
- Messages using bullet lists: **0%** (bot used lists in almost every response)
- Multi-message sequences (2-3 msgs in a row): **32% of interactions**
- Ending particle distribution: คะ 40%, ค่ะ 18%, ครับ 16% (bot was 100% ค่ะ)

## Winning Agent Patterns

1. **Short + direct**: "จากใจคนขายประกันอยากแนะนำแผนเหมาจ่าย 5ล้านขึ้นไปนะคะ ^^" (55 chars)
2. **Real numbers**: "Health Saver 4แสน เบี้ย 19,853/ปี" — not "Health Saver เหมาจ่าย + OPD"
3. **Ask first, answer later**: agents ask 1-2 questions before presenting plans
4. **Break into chunks**: 2-3 short messages instead of 1 long one

## Anti-Pattern

Training data formatted with bullets, numbered lists, and markdown creates bots that sound like documentation, not people. Real LINE chat is messy, short, and conversational.

## Application

- Rewrite system prompt to enforce 50-80 char target, no bullets, no \n
- Reformat training examples to match real agent style
- Add multi-message response capability to bot
