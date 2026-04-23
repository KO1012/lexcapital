---
name: lexcapital-runner-builder
description: Use this skill when building model adapters, policy runners, agent runners, or suite runners.
---

Runner rules:

1. The evaluated model receives only render_model_prompt output.
2. Never pass scenario YAML or hidden fields to adapters.
3. Policy mode has no tools.
4. Agent mode only has whitelisted benchmark tools.
5. No shell, filesystem, web, real trading API, or hidden scenario access for evaluated agents.
6. Always save actions.jsonl.
7. Leaderboard must score replayed actions, not live model outputs.
8. Invalid model output becomes HOLD plus soft penalty.
