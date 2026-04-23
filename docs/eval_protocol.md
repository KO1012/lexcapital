# Evaluation Protocol v0.2

## Runner settings

Leaderboard submissions should record:

- model name and provider,
- adapter type,
- mode: `policy` or `agent`,
- temperature,
- max output tokens,
- timeout and retry settings,
- scenario set path or sealed-set identifier,
- whether external tools, internet, RAG, or code execution were available.

Recommended deterministic run:

```bash
python -m lexcapital run-suite \
  --scenarios scenarios/phase2_dev \
  --adapter openai \
  --model <model> \
  --temperature 0 \
  --out runs/phase2_dev/<model>
python -m lexcapital score-dir runs/phase2_dev/<model>
```

## Preflight checks

Before publishing a run:

```bash
python -m lexcapital validate scenarios/phase2_dev
python -m lexcapital audit-scenarios --scenarios scenarios/phase2_dev --out audits/phase2_dev --strict
pytest -q
```

## Public versus sealed sets

Use public development scenarios for prompt, parser, and adapter debugging. Use sealed scenarios for leaderboard claims. Public scenarios can be overfit; sealed scenarios should have the same schema and trap taxonomy but different facts, parameters, and red/oracle paths.

## Logging requirements

Every run directory should contain rendered prompt hashes, action hashes, normalized actions, trades, rule violations, portfolio time series, and `score.json`. Hidden fields must not appear in rendered prompts or normalized actions.

## Baselines

Report at least these baselines next to model results:

1. `hold`: deterministic abstention.
2. `random_valid`: random but schema-valid actions.
3. `rule_aware_heuristic`: deterministic rule-following heuristic without hidden oracle access.
4. `scripted_oracle`: authoring upper bound, not a public leaderboard entrant.
