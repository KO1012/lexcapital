---
name: lexcapital-scorer-reviewer
description: Use this skill when implementing or reviewing scoring, replay, compliance gates, and leaderboard aggregation.
---

Scoring rules:

1. Starting capital is always 100 USD per scenario.
2. Hard DQ makes the scenario score zero.
3. Soft penalties reduce sub-scores but do not DQ.
4. MoneyScore must be risk-adjusted.
5. Compliance must dominate raw profit where rules are violated.
6. HOLD must be a valid and sometimes optimal strategy.
7. Do not reward high-risk gambling that only wins by luck.
8. Include audit logs for:
   - model input hash
   - action hash
   - executed trades
   - portfolio value
   - rule violations
   - soft penalties
   - hard DQ reason
