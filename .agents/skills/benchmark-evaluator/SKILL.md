---
name: benchmark-evaluator
description: Use this skill when you are asked to run FinRuleBench against a configured model from inside the repository.
---

When evaluating a model with this repository:

1. Do not read scenario hidden fields directly.
2. Prefer the built-in config-driven workflow.
3. If no config exists, generate one:

```bash
python -m finrulebench write-agent-template --out agent_eval.yaml
```

4. Edit `agent_eval.yaml` to set:
- adapter
- model
- mode
- scenarios
- out

5. Run:

```bash
python -m finrulebench agent-eval --config agent_eval.yaml
```

6. Report:
- `runs/.../suite_summary.json`
- `runs/.../leaderboard_row.json`
- per-scenario `score.json`

Hard rules:
- never connect to real trading systems
- never bypass prompt rendering
- never leak hidden oracle text, trap conditions, hidden future data, or scoring config
- keep all trading simulated
